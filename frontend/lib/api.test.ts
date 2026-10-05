import { describe, expect, it } from "vitest";
import { streamRun, type RunStreamEvent } from "./api";

describe("api types smoke test", () => {
  it("keeps policy decisions string based", () => {
    const decision = { decision: "accept", reason: "clean" };

    expect(decision.decision).toBe("accept");
  });

  it("parses streamed run events", async () => {
    const events: RunStreamEvent[] = [];
    const body = new ReadableStream({
      start(controller) {
        controller.enqueue(
          new TextEncoder().encode('data: {"type":"token","attempt_no":1,"text":"def"}\n\n')
        );
        controller.enqueue(new TextEncoder().encode('data: {"type":"error","message":"stop"}\n\n'));
        controller.close();
      }
    });
    const originalFetch = global.fetch;
    global.fetch = async () =>
      new Response(body, { status: 200, headers: { "content-type": "text/event-stream" } });

    try {
      await streamRun({ prompt: "Write code" }, (event) => events.push(event));
    } finally {
      global.fetch = originalFetch;
    }

    expect(events).toHaveLength(2);
    expect(events[0]).toMatchObject({ type: "token", text: "def" });
    expect(events[1]).toMatchObject({ type: "error", message: "stop" });
  });
});

import { readEventStream } from "./api";

it("handles split UTF-8, CRLF boundaries, IDs and heartbeats", async () => {
  const encoder = new TextEncoder();
  const raw = encoder.encode(
    'id: 1\r\ndata: {"type":"token","sequence":1,"attempt_no":1,"text":"বাংলা"}\r\n\r\n: heartbeat\r\n\r\n'
  );
  const events: RunStreamEvent[] = [];
  const body = new ReadableStream({
    start(controller) {
      for (const byte of raw) controller.enqueue(new Uint8Array([byte]));
      controller.close();
    }
  });
  await readEventStream(new Response(body), (event) => events.push(event));
  expect(events).toHaveLength(1);
  expect(events[0]).toMatchObject({ text: "বাংলা", sequence: 1 });
});

it("reports malformed event payloads", async () => {
  const body = new ReadableStream({
    start(controller) {
      controller.enqueue(new TextEncoder().encode("data: invalid\n\n"));
      controller.close();
    }
  });
  await expect(readEventStream(new Response(body), () => {})).rejects.toThrow();
});

import { watchRun, createRun } from "./api";
import { vi } from "vitest";
it("replays from the last sequence and ignores duplicate events after reconnection", async () => {
  vi.useFakeTimers();
  const originalFetch = global.fetch;
  const seen: RunStreamEvent[] = [];
  let stream = 0;
  global.fetch = async (url) => {
    if (String(url).includes("/events")) {
      stream++;
      if (stream === 2) expect(String(url)).toContain("after=1");
      const events =
        stream === 1
          ? [{ type: "token", sequence: 1, attempt_no: 1, text: "a" }]
          : [
              { type: "token", sequence: 1, attempt_no: 1, text: "a" },
              { type: "token", sequence: 2, attempt_no: 1, text: "b" }
            ];
      return new Response(
        new ReadableStream({
          start(controller) {
            controller.enqueue(
              new TextEncoder().encode(events.map((e) => `data: ${JSON.stringify(e)}\n\n`).join(""))
            );
            controller.close();
          }
        })
      );
    }
    return new Response(JSON.stringify({ status: stream === 1 ? "running" : "completed" }), {
      headers: { "content-type": "application/json" }
    });
  };
  try {
    const pending = watchRun("r", (event) => seen.push(event), new AbortController().signal);
    await vi.advanceTimersByTimeAsync(600);
    await pending;
    expect(seen.map((e) => (e.type === "token" ? e.text : ""))).toEqual(["a", "b"]);
  } finally {
    global.fetch = originalFetch;
    vi.useRealTimers();
  }
});
it("turns API validation failures into readable field errors", async () => {
  const originalFetch = global.fetch;
  global.fetch = async () =>
    new Response(
      JSON.stringify({
        detail: [{ loc: ["body", "prompt"], msg: "String should have at least 3 characters" }]
      }),
      { status: 422 }
    );
  try {
    await expect(createRun({ prompt: "a" })).rejects.toThrow(
      "prompt: String should have at least 3 characters"
    );
  } finally {
    global.fetch = originalFetch;
  }
});
