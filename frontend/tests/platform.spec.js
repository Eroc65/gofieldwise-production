const { test, expect } = require("@playwright/test");

test("platform campaign orchestrator flow works", async ({ page }) => {
  await page.route("**/api/auth/login", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ access_token: "test-token", token_type: "bearer" }),
    });
  });

  await page.route("**/api/org/ai-guide", async (route) => {
    if (route.request().method() === "PATCH") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: route.request().postData() || "{}",
      });
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ enabled: true, stage: "onboarding" }),
    });
  });

  await page.route("**/api/help/articles**", async (route) => {
    if (route.request().method() === "POST") {
      await route.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify({ id: 1, title: "How to Follow Up", context_key: "general" }),
      });
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([{ id: 1, title: "How to Follow Up", context_key: "general" }]),
    });
  });

  await page.route("**/api/coaching/snippets**", async (route) => {
    if (route.request().method() === "POST") {
      await route.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify({ id: 1, trade: "hvac", title: "Reassure And Rebook" }),
      });
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([{ id: 1, trade: "hvac", title: "Reassure And Rebook" }]),
    });
  });

  await page.route("**/api/marketing/service-packages", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        { code: "growth-core", name: "Growth Core", monthly_price_usd: 1499, summary: "Core demand generation ops." },
      ]),
    });
  });

  await page.route("**/api/marketing/reactivation/run", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ queued_count: 3, candidate_count: 9 }),
    });
  });

  await page.route("**/api/org/comm-profile", async (route) => {
    if (route.request().method() === "PATCH") {
      const payload = route.request().postDataJSON();
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(payload),
      });
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ active: false }),
    });
  });

  await page.route("**/api/marketing/campaigns**", async (route) => {
    const method = route.request().method();
    if (method === "POST") {
      const payload = route.request().postDataJSON();
      await route.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify({
          id: 502,
          name: payload.name,
          kind: payload.kind,
          status: "draft",
          channel: payload.channel,
          template: payload.template || null,
          lookback_days: payload.lookback_days,
          launched_at: null,
          organization_id: 11,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        }),
      });
      return;
    }

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          id: 401,
          name: "Review Push",
          kind: "review_harvester",
          status: "draft",
          channel: "sms",
          template: "Please leave a review",
          lookback_days: 90,
          organization_id: 11,
          launched_at: null,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
      ]),
    });
  });

  await page.route("**/api/marketing/campaigns/*/launch", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ campaign_id: 502, status: "launched", generated_recipients: 7 }),
    });
  });

  await page.goto("/platform");

  await expect(page.getByRole("heading", { name: "Operator Access" })).toBeVisible();
  const accessCard = page.locator("section.dispatch-card", { has: page.getByRole("heading", { name: "Operator Access" }) });

  await accessCard.getByLabel("Email").fill("owner@example.com");
  await accessCard.getByLabel("Password").fill("testpass123");
  await accessCard.getByRole("button", { name: "Login" }).click();

  await page.getByRole("button", { name: "Refresh Platform Data" }).click();
  await expect(page.getByText("Review Push")).toBeVisible();

  await page.getByLabel("Campaign Name").fill("Spring Reactivation");
  await page.getByLabel("Kind").selectOption("reactivation");
  await page.getByLabel("Channel").selectOption("sms");
  await page.getByLabel("Lookback Days").fill("120");
  await page.getByLabel("Template").fill("We can get you on the schedule this week.");
  await page.getByRole("button", { name: "Create Campaign" }).click();

  await expect(page.getByText("Campaign created: Spring Reactivation")).toBeVisible();
  await expect(page.getByRole("cell", { name: "Spring Reactivation", exact: true })).toBeVisible();

  await page.getByRole("button", { name: "Launch Spring Reactivation" }).click();
  await expect(page.getByText("Campaign launched with 7 queued recipients.")).toBeVisible();
  await expect(page.locator("tr", { hasText: "Spring Reactivation" }).getByText("launched")).toBeVisible();
});
