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
