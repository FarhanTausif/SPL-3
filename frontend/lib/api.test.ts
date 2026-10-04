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
        controller.enqueue(new TextEncoder().encode('data: {"type":"token","attempt_no":1,"text":"def"}\n\n'));
        controller.enqueue(new TextEncoder().encode('data: {"type":"error","message":"stop"}\n\n'));
        controller.close();
      }
    });
    const originalFetch = global.fetch;
    global.fetch = async () => new Response(body, { status: 200, headers: { "content-type": "text/event-stream" } });

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
  const raw = encoder.encode('id: 1\r\ndata: {"type":"token","sequence":1,"attempt_no":1,"text":"বাংলা"}\r\n\r\n: heartbeat\r\n\r\n');
  const events: RunStreamEvent[] = [];
  const body = new ReadableStream({ start(controller) { for (const byte of raw) controller.enqueue(new Uint8Array([byte])); controller.close(); } });
  await readEventStream(new Response(body), event => events.push(event));
  expect(events).toHaveLength(1);
  expect(events[0]).toMatchObject({ text: "বাংলা", sequence: 1 });
});

it("reports malformed event payloads", async () => {
  const body = new ReadableStream({ start(controller) { controller.enqueue(new TextEncoder().encode("data: invalid\n\n")); controller.close(); } });
  await expect(readEventStream(new Response(body), () => {})).rejects.toThrow();
});
