import { expect, test, type Page } from "@playwright/test";
import { makeAttempt, makeEvidence, makeRun, health } from "../tests/fixtures";
import type { RunEvidence } from "../lib/contracts.generated";
async function mockApi(page: Page, evidence: RunEvidence) {
  await page.route("**/api/**", (route) => {
    const path = new URL(route.request().url()).pathname;
    const headers = {
      "access-control-allow-origin": "*",
      "content-type": "application/json"
    };
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
          rubric_json: {
            alignment: { score: 0.9, evidence: ["Requirements inspected."] }
          }
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
    await page.screenshot({
      path: `/tmp/dehalu-ui-checks/composer-${width}.png`,
      fullPage: true
    });
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
    await page.screenshot({
      path: `/tmp/dehalu-ui-checks/code-${width}.png`,
      fullPage: true
    });
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
    await page.screenshot({
      path: `/tmp/dehalu-ui-checks/evidence-${width}.png`,
      fullPage: true
    });
    await page.emulateMedia({ reducedMotion: "reduce" });
    expect(await page.evaluate(() => matchMedia("(prefers-reduced-motion: reduce)").matches)).toBe(
      true
    );
  });
}

for (const width of [360, 1280]) {
  test(`clarification choices and Run Anyway at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    const evidence = makeEvidence({
      attempts: [],
      run: makeRun({
        status: "needs_clarification",
        inferred: {
          ...makeRun().inferred,
          needs_clarification: true,
          clarification_questions: ["How should your calculator work?"],
          clarification_details: [
            {
              question: "How should your calculator work?",
              choices: [
                {
                  label: "Add two numbers",
                  value: "Add two numbers",
                  recommended: true
                },
                {
                  label: "Basic arithmetic",
                  value: "Support basic arithmetic",
                  recommended: false
                },
                {
                  label: "Scientific functions",
                  value: "Support scientific functions",
                  recommended: false
                }
              ]
            }
          ]
        }
      })
    });
    await mockApi(page, evidence);
    await page.route("**/api/runs/*/clarification", async (route) => {
      const body = route.request().postDataJSON();
      expect(body.skip_clarification).toBe(true);
      expect(body.answers).toContain("Use multiplication");
      evidence.run.status = "completed";
      evidence.run.inferred.needs_clarification = false;
      evidence.attempts = [makeAttempt()];
      await route.fulfill({
        json: evidence.run,
        headers: { "access-control-allow-origin": "*" }
      });
    });
    await generate(page);
    await expect(page.getByRole("radio")).toHaveCount(3);
    await page.getByLabel("Clarification answers").fill("Use multiplication");
    await page.screenshot({
      path: `/tmp/dehalu-ui-checks/clarification-${width}.png`,
      fullPage: true
    });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(
      true
    );
    await page.getByRole("button", { name: "Run Anyway" }).click();
    await expect(page.getByRole("button", { name: "Copy code" })).toBeVisible();
    await page.reload();
    await expect(page.getByRole("button", { name: "Run Anyway" })).toHaveCount(0);
  });
  test(`entropy details and repair chart at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    const attempts = [makeAttempt(1, "repair"), makeAttempt(2, "warn")];
    attempts[0].metrics.hallucination_risk_score = 0.8;
    attempts[1].metrics.hallucination_risk_score = 0.2;
    attempts[1].metrics.entropy_score = 0.1;
    attempts[1].output.entropy_summary = {
      available: true,
      mean_nats: 0.179,
      measured_tokens: 20,
      generated_tokens: 20
    };
    await mockApi(page, makeEvidence({ attempts }));
    await generate(page);
    await page.context().grantPermissions(["clipboard-read", "clipboard-write"]);
    await page.getByRole("button", { name: "Copy code" }).click();
    await expect(page.getByText("Copied", { exact: true })).toBeVisible();
    expect(await page.evaluate(() => navigator.clipboard.readText())).toBe(attempts[1].output.code);
    await page.getByRole("tab", { name: "Evidence", exact: true }).click();
    await page.getByRole("tab", { name: "Metrics", exact: true }).click();
    await expect(page.getByRole("region", { name: "Hallucination trend" })).toBeVisible();
    await expect(page.getByText("80.0% → 20.0% · -60.0 pp")).toBeVisible();
    await expect(page.getByText(/0.179 nats/)).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(
      true
    );
    await page.screenshot({
      path: `/tmp/dehalu-ui-checks/metrics-${width}.png`,
      fullPage: true
    });
  });
}

test("failed prose repair preserves source code and shows failure instead of repair status", async ({
  page
}) => {
  const prose = "Based on the provided evidence, processor.predict is uncertain.";
  const evidence = makeEvidence({
    run: makeRun({
      status: "failed",
      error: "Model did not produce a valid code artifact after one format recovery attempt."
    }),
    attempts: [makeAttempt(1, "repair")],
    partial: { attempt_no: 2, raw_response: prose }
  });
  await mockApi(page, evidence);
  await page.route("**/api/runs/*/events", (route) =>
    route.fulfill({
      headers: { "access-control-allow-origin": "*", "content-type": "text/event-stream" },
      body: `id: 1\ndata: ${JSON.stringify({ type: "token", attempt_no: 2, text: prose })}\n\nid: 2\ndata: ${JSON.stringify({ type: "run_completed", run: evidence.run, evidence })}\n\n`
    })
  );
  await generate(page);
  await expect(
    page.getByRole("region", { name: "Run outcome" }).getByText("failed", { exact: true })
  ).toBeVisible();
  await expect(page.locator(".editor code")).toContainText("return a - b");
  await expect(page.getByText(prose)).toHaveCount(0);
  await expect(page.getByText("Generation explanation")).toHaveCount(0);
  await page.screenshot({ path: "/tmp/dehalu-ui-checks/failed-repair.png", fullPage: true });
});
