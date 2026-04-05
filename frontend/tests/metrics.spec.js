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
  await expect(page.getByText("Intakes").first()).toBeVisible();
  await expect(page.locator(".results-grid .panel").filter({ hasText: "Intakes" }).getByText("12", { exact: true })).toBeVisible();
  await expect(page.locator(".results-grid .panel").filter({ hasText: "Qualification Rate" }).getByText("75%", { exact: true })).toBeVisible();
  await expect(page.getByText("2026-04-01")).toBeVisible();
});
