const { test, expect } = require("@playwright/test");

test("metrics dashboard flow works", async ({ page }) => {
  await page.route("**/api/auth/login", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ access_token: "test-token", token_type: "bearer" }),
    });
  });

  await page.route("**/api/reports/lead-conversion**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        organization_id: 11,
        timestamp: new Date().toISOString(),
        days: 7,
        totals: {
          intakes: 12,
          qualified: 9,
          booked: 5,
          qualification_rate: 75.0,
          booking_rate: 41.7,
        },
        recommended_next_action: "Maintain current process and monitor booked volume for consistency.",
        timeline: [
          {
            date: "2026-04-01",
            intakes: 2,
            qualified: 1,
            booked: 1,
            qualification_rate: 50.0,
            booking_rate: 50.0,
          },
          {
            date: "2026-04-02",
            intakes: 3,
            qualified: 2,
            booked: 1,
            qualification_rate: 66.7,
            booking_rate: 33.3,
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
        organization_id: 11,
        timestamp: new Date().toISOString(),
        lead_pipeline: { total: 1 },
        job_status: { total: 1 },
        invoice_summary: {
          unpaid: 3,
          paid: 4,
          void: 0,
          total: 7,
          unpaid_total_amount: 1450.5,
          overdue_count: 2,
        },
        overdue_invoices: {
          due_today: 1,
          "3_days_overdue": 1,
          "7_days_overdue": 0,
          "14_plus_days_overdue": 1,
          total_overdue: 2,
          aging_buckets: {
            current_not_due: { count: 1, amount: 200.0 },
            days_1_7: { count: 1, amount: 150.0 },
            days_8_14: { count: 1, amount: 450.0 },
            days_15_30: { count: 0, amount: 0.0 },
            days_31_plus: { count: 0, amount: 0.0 },
          },
        },
      }),
    });
  });

  await page.goto("/metrics");

  await expect(page.getByRole("heading", { name: "Lead Conversion Dashboard" })).toBeVisible();

  await page.getByLabel("Auth Email").fill("owner@example.com");
  await page.getByLabel("Auth Password").fill("testpass123");
  await page.getByRole("button", { name: "Login" }).click();

  await page.getByLabel("Days").fill("7");
  await page.getByRole("button", { name: "Load Metrics" }).click();

  await expect(page.getByRole("heading", { name: "Recommended Next Action" })).toBeVisible();
  await expect(page.getByText("Maintain current process and monitor booked volume for consistency.")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Daily Timeline" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Collections Snapshot" })).toBeVisible();
  await expect(page.getByText("Intakes").first()).toBeVisible();
  await expect(page.locator(".results-grid .panel").filter({ hasText: "Intakes" }).getByText("12", { exact: true })).toBeVisible();
  await expect(page.locator(".results-grid .panel").filter({ hasText: "Qualification Rate" }).getByText("75%", { exact: true })).toBeVisible();
  await expect(page.locator(".results-grid .panel").filter({ hasText: "Unpaid Total" }).getByText("$1450.50", { exact: true })).toBeVisible();
  await expect(page.locator(".results-grid .panel").filter({ hasText: "Overdue Count" }).getByText("2", { exact: true })).toBeVisible();
  await expect(page.locator(".results-grid .panel").filter({ hasText: "8 To 14 Days" }).getByText("1", { exact: true })).toBeVisible();
  await expect(page.locator(".results-grid .panel").filter({ hasText: "8 To 14 Days" }).getByText("$450.00", { exact: true })).toBeVisible();
  const bucketHeadings = page.locator(".collections-aging-grid .panel h3");
  await expect(bucketHeadings.nth(0)).toHaveText("31 Plus Days");
  await expect(bucketHeadings.nth(1)).toHaveText("15 To 30 Days");
  await expect(bucketHeadings.nth(2)).toHaveText("8 To 14 Days");
  await expect(bucketHeadings.nth(3)).toHaveText("1 To 7 Days");
  await expect(bucketHeadings.nth(4)).toHaveText("Current Not Due");
  await expect(page.getByText("2026-04-01")).toBeVisible();
});
