import { expect, test, type Page } from "@playwright/test";
import { makeAttempt, makeEvidence, makeRun, health } from "../tests/fixtures";
import type { RunEvidence } from "../lib/contracts.generated";
async function mockApi(page: Page, evidence: RunEvidence) {
  await page.route("**/api/**", (route) => {
    const path = new URL(route.request().url()).pathname;
    const headers = { "access-control-allow-origin": "*", "content-type": "application/json" };
    if (route.request().method() === "OPTIONS")
      return route.fulfill({
        status: 204,
        headers: {
          ...headers,
          "access-control-allow-methods": "GET, POST, OPTIONS",
          "access-control-allow-headers": "content-type"
        }
      });
    if (path.endsWith("/events"))
      return route.fulfill({
        headers: { ...headers, "content-type": "text/event-stream" },
        body: `id: 1\ndata: ${JSON.stringify({ type: "run_completed", sequence: 1, run: evidence.run, evidence })}\n\n`
      });
    return route.fulfill({
      headers,
      json: path.endsWith("/health")
        ? health
        : path.endsWith("/evidence")
          ? evidence
          : path.endsWith("/runs") && route.request().method() === "GET"
            ? [evidence.run]
            : evidence.run
    });
  });
}
async function generate(page: Page) {
  await page.goto("/");
  await page.getByLabel("Prompt", { exact: true }).fill("Write a Python addition function.");
  await page.getByRole("button", { name: "Generate", exact: true }).click();
  await expect(page.getByRole("region", { name: "Run outcome" })).toBeVisible();
}
for (const scenario of ["clean", "repaired", "rejected", "degraded"] as const) {
  test(`${scenario} completion preserves inspectable code and evidence`, async ({ page }) => {
    const decision =
      scenario === "rejected" ? "reject" : scenario === "degraded" ? "warn" : "accept";
    const attempts =
      scenario === "repaired"
        ? [makeAttempt(1, "repair"), makeAttempt(2, "accept")]
        : [makeAttempt(1, decision)];
    if (scenario === "clean") {
      attempts[0].output.code = "def add(a, b):\n    return a + b";
      attempts[0].claims[0].status = "supported";
      attempts[0].static_findings = [];
      attempts[0].metrics.unsupported_count = 0;
      attempts[0].metrics.mihn = 0;
      attempts[0].metrics.mahr = 0;
    }
    if (scenario !== "degraded")
      for (const a of attempts) {
        a.judge_results = ["Gemini", "Groq", "Mistral"].map((name) => ({
          ...a.judge_results[0],
          judge_name: name,
          status: "ok",
          verdict: "pass",
          score: 0.9,
          explanation: "Requirements supported.",
          rubric_json: { alignment: { score: 0.9, evidence: ["Requirements inspected."] } }
        }));
        a.judge_consensus = {
          ...a.judge_consensus,
          valid_count: 3,
          final_verdict: "pass",
          average_score: 0.9
        };
      }
    const evidence = makeEvidence({
      attempts,
      run: makeRun({
        status: scenario === "rejected" ? "rejected" : "completed",
        policy_decision: attempts.at(-1)!.policy
      })
    });
    await mockApi(page, evidence);
    await generate(page);
    await expect(
      page.getByRole("region", { name: "Run outcome" }).getByText(decision, { exact: true })
    ).toBeVisible();
    await page.getByRole("tab", { name: "Evidence", exact: true }).click();
    await page.getByRole("tab", { name: "Metrics", exact: true }).click();
    await expect(page.getByText("Unavailable", { exact: true }).first()).toBeVisible();
    if (scenario === "degraded") {
      await page.getByRole("tab", { name: "Judges", exact: true }).click();
      await expect(page.getByText("Provider quota exceeded.", { exact: true })).toBeVisible();
    }
    await page.reload();
    await expect(page.getByRole("region", { name: "Run outcome" })).toBeVisible();
    if (scenario === "repaired") {
      await page.getByRole("combobox", { name: "Inspect" }).click();
      await page.getByRole("option", { name: "Attempt 1", exact: true }).click();
      await expect(page.getByRole("tab", { name: "Changes", exact: true })).toBeDisabled();
      await page.getByRole("tab", { name: "Evidence", exact: true }).click();
      await page.getByRole("tab", { name: /Claims/ }).click();
      await expect(page.getByText("unsupported", { exact: true })).toBeVisible();
      await page.getByRole("combobox", { name: "Inspect" }).click();
      await page.getByRole("option", { name: "Latest attempt", exact: true }).click();
      await expect(page.getByText("supported", { exact: true })).toBeVisible();
      await page.getByRole("tab", { name: "Code", exact: true }).first().click();
      await page.getByRole("tab", { name: "Changes", exact: true }).click();
      await expect(page.getByText("Attempt 1 → attempt 2")).toBeVisible();
    }
  });
}
for (const width of [360, 768, 1280, 1440]) {
  test(`layout, fonts, keyboard, and source navigation at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await mockApi(page, makeEvidence());
    await page.goto("/");
    await expect(
      page.getByRole("heading", { name: "What would you like to build?" })
    ).toBeVisible();
    await page.screenshot({ path: `/tmp/dehalu-ui-checks/composer-${width}.png`, fullPage: true });
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)
    ).toBe(true);
    await page.getByLabel("Prompt", { exact: true }).fill("Write Python addition");
    await page.getByLabel("Prompt", { exact: true }).press("Control+Enter");
    await expect(page.getByRole("region", { name: "Run outcome" })).toBeVisible();
    await page.getByRole("tab", { name: "Evidence", exact: true }).click();
    await page.getByRole("tab", { name: /Findings/ }).click();
    await page.getByText("Inspect arithmetic operation", { exact: true }).click();
    await page.getByRole("button", { name: "Line 2", exact: true }).click();
    await expect(page.locator("#code-1-line-2")).toHaveClass(/source-highlight/);
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)
    ).toBe(true);
    await page.screenshot({ path: `/tmp/dehalu-ui-checks/code-${width}.png`, fullPage: true });
    const fonts = await page.evaluate(async () => {
      await document.fonts.ready;
      const families = [
        getComputedStyle(document.body).fontFamily,
        getComputedStyle(document.querySelector(".editor code")!).fontFamily
      ].map((value) => value.split(",")[0].replace(/["']/g, "").trim());
      return {
        sans: getComputedStyle(document.body).fontFamily,
        mono: getComputedStyle(document.querySelector(".editor code")!).fontFamily,
        count: document.fonts.size,
        loaded: families.every((family) =>
          Array.from(document.fonts).some(
            (font) => font.family.replace(/["']/g, "") === family && font.status === "loaded"
          )
        )
      };
    });
    expect(fonts.sans).toContain("geist");
    expect(fonts.mono).toContain("mono");
    expect(fonts.count).toBeGreaterThan(0);
    expect(fonts.loaded).toBe(true);
    await page.getByRole("tab", { name: "Evidence", exact: true }).click();
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.screenshot({ path: `/tmp/dehalu-ui-checks/evidence-${width}.png`, fullPage: true });
    await page.emulateMedia({ reducedMotion: "reduce" });
    expect(await page.evaluate(() => matchMedia("(prefers-reduced-motion: reduce)").matches)).toBe(
      true
    );
  });
}
