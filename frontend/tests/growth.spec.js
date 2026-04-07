const { test, expect } = require("@playwright/test");

test("growth infrastructure control tower works", async ({ page }) => {
  await page.route("**/api/auth/login", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ access_token: "test-token", token_type: "bearer" }),
    });
  });

  await page.route("**/api/marketing/campaigns", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        { id: 1, name: "Review Push", status: "launched", kind: "review_harvester", channel: "sms" },
        { id: 2, name: "Reactivation Sweep", status: "draft", kind: "reactivation", channel: "sms" },
      ]),
    });
  });

  await page.route("**/api/leads", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        { id: 10, status: "new" },
        { id: 11, status: "new" },
        { id: 12, status: "contacted" },
      ]),
    });
  });

  await page.route("**/api/reports/operator-queue?**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        organization_id: 11,
        timestamp: new Date().toISOString(),
        limit: 5,
        total_candidates: 2,
        items: [
          {
            item_type: "invoice_collection",
            entity_id: 401,
            title: "Collect invoice #401",
            urgency: "critical",
            priority_score: 148,
            action: "Call customer and collect payment today.",
          },
          {
            item_type: "lead_followup",
            entity_id: 91,
            title: "Follow up with lead #91",
            urgency: "medium",
            priority_score: 70,
            action: "Call or text lead and book the job.",
          },
        ],
      }),
    });
  });

  await page.route("**/api/reports/operational-dashboard", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        invoice_summary: {
          unpaid_total_amount: 2500.0,
          overdue_count: 4,
        },
      }),
    });
  });

  await page.goto("/growth");

  await expect(page.getByRole("heading", { name: "AI Growth Infrastructure For Modern Businesses" })).toBeVisible();

  await page.getByLabel("Email").fill("owner@example.com");
  await page.getByLabel("Password").fill("testpass123");
  await page.getByRole("button", { name: "Login" }).click();
  await page.getByRole("button", { name: "Load Control Tower" }).click();

  await expect(page.locator(".results-grid .panel").filter({ hasText: "Campaigns Launched" }).getByText("1", { exact: true })).toBeVisible();
  await expect(page.locator(".results-grid .panel").filter({ hasText: "Total Leads" }).getByText("3", { exact: true })).toBeVisible();
  await expect(page.locator(".results-grid .panel").filter({ hasText: "New Leads" }).getByText("2", { exact: true })).toBeVisible();
  await expect(page.locator(".results-grid .panel").filter({ hasText: "Priority Queue Items" }).getByText("2", { exact: true })).toBeVisible();
  await expect(page.locator(".results-grid .panel").filter({ hasText: "Unpaid Exposure" }).getByText("$2500.00", { exact: true })).toBeVisible();
  await expect(page.locator(".results-grid .panel").filter({ hasText: "Overdue Count" }).getByText("4", { exact: true })).toBeVisible();

  await expect(page.getByRole("heading", { name: "Growth Priorities" })).toBeVisible();
  await expect(page.getByText("Collect invoice #401")).toBeVisible();
  await expect(page.getByText("Call customer and collect payment today.")).toBeVisible();
});
