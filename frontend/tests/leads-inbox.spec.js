const { test, expect } = require("@playwright/test");

test("lead inbox flow works", async ({ page }) => {
  let leadState = {
    id: 301,
    name: "Leak Lead",
    phone: "555-3001",
    email: "lead@example.com",
    source: "web_form",
    status: "new",
    priority_score: null,
    created_at: new Date().toISOString(),
  };

  await page.route("**/api/auth/login", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ access_token: "test-token", token_type: "bearer" }),
    });
  });

  await page.route("**/api/leads", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([leadState]),
    });
  });

  await page.route("**/api/technicians", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([{ id: 11, name: "Taylor Tech" }]),
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
          intakes: 10,
          qualified: 7,
          booked: 4,
          qualification_rate: 70.0,
          booking_rate: 40.0,
        },
        timeline: [],
      }),
    });
  });

  await page.route("**/api/leads/301/status", async (route) => {
    leadState = { ...leadState, status: "contacted" };
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(leadState),
    });
  });

  await page.route("**/api/leads/301/qualify", async (route) => {
    leadState = { ...leadState, status: "qualified", priority_score: 95 };
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        lead: leadState,
        booking_reminder_created: true,
      }),
    });
  });

  await page.route("**/api/leads/301/book", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        lead_id: 301,
        customer_id: 710,
        job_id: 880,
        job_status: "dispatched",
        scheduled_time: new Date(Date.now() + 3600000).toISOString(),
        technician_id: 11,
        booking_reminders_dismissed: 1,
      }),
    });
  });

  await page.goto("/leads");

  await expect(page.getByRole("heading", { name: "Review, Qualify, And Book New Leads Fast" })).toBeVisible();

  await page.getByLabel("Auth Email").fill("owner@example.com");
  await page.getByLabel("Auth Password").fill("testpass123");
  await page.getByRole("button", { name: "Login" }).click();

  await expect(page.getByLabel("Pick Lead")).toContainText("#301 Leak Lead (new)");
  await expect(page.getByText("7 Day Intakes")).toBeVisible();
  await expect(page.getByText("10").first()).toBeVisible();
  await page.getByLabel("Pick Lead").selectOption("301");
  await page.getByLabel("Booking Technician").selectOption("11");
  await page.getByLabel("Service Category").fill("plumbing");

  await page.getByRole("button", { name: "Mark Contacted" }).click();
  await expect(page.getByText("Lead #301 moved to contacted.")).toBeVisible();

  await page.getByRole("button", { name: "Qualify Lead" }).click();
  await expect(page.getByText("Lead #301 qualified with score 95.")).toBeVisible();

  await page.getByRole("button", { name: "Book Lead" }).click();
  await expect(page.getByText("Lead booked. Job #880 scheduled")).toBeVisible();
});
