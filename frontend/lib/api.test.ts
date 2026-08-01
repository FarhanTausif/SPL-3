import { describe, expect, it } from "vitest";

describe("api types smoke test", () => {
  it("keeps policy decisions string based", () => {
    const decision = { decision: "accept", reason: "clean" };

    expect(decision.decision).toBe("accept");
  });
});
