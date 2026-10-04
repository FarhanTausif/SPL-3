"""Run with python -m dehalu.worker; PostgreSQL is the durable queue."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event, Thread
import logging
import signal
import time
from uuid import uuid4
from dehalu.core.settings import settings
from dehalu.state.database import SessionLocal
from dehalu.state.workflow import claim_job, heartbeat, sweep_expired
from dehalu.services.pipeline import DeHaluPipeline

log = logging.getLogger(__name__)


def process(run_id, owner):
    stopped = Event()
    def pulse():
        while not stopped.wait(max(1, settings.worker_lease_seconds / 3)):
            try:
                with SessionLocal() as db:
                    if not heartbeat(db, run_id, owner): return
            except Exception: log.exception('Worker heartbeat failed')
    thread = Thread(target=pulse, daemon=True)
    thread.start()
    try:
        with SessionLocal() as db: DeHaluPipeline(db).execute(run_id)
    finally:
        stopped.set()
        thread.join(timeout=2)


def main():
    logging.basicConfig(level=logging.INFO)
    stop = Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    owner = str(uuid4())
    with ThreadPoolExecutor(max_workers=max(1, settings.worker_concurrency)) as pool:
        futures = set()
        while not stop.is_set():
            for future in list(futures):
                if future.done():
                    try: future.result()
                    except Exception: log.exception('Run worker failed')
                    futures.remove(future)
            try:
                with SessionLocal() as db:
                    sweep_expired(db)
                    while len(futures) < max(1, settings.worker_concurrency):
                        run_id = claim_job(db, owner)
                        if not run_id: break
                        futures.add(pool.submit(process, run_id, owner))
            except Exception: log.exception('Queue poll failed')
            stop.wait(1)


if __name__ == '__main__': main()
