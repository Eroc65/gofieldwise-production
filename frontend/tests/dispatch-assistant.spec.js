const { test, expect } = require("@playwright/test");

test("dispatch assistant full flow works", async ({ page }) => {
  await page.route("**/api/auth/login", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ access_token: "test-token", token_type: "bearer" }),
    });
  });

  await page.route("**/api/jobs", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        { id: 101, title: "Water Heater Replace", status: "pending" },
      ]),
    });
  });

  await page.route("**/api/technicians", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        { id: 7, name: "Sam Tech" },
      ]),
    });
  });

  await page.route("**/api/jobs/scheduling/conflict**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        conflict: false,
        conflicting_job_id: null,
        message: "No scheduling conflict detected",
      }),
    });
  });

  await page.route("**/api/jobs/scheduling/next-slot**", async (route) => {
    const requested = new URL(route.request().url()).searchParams.get("requested_time");
    const suggested = requested
      ? new Date(new Date(requested).getTime() + 30 * 60 * 1000).toISOString()
      : new Date().toISOString();
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        technician_id: 7,
        requested_time: requested,
        search_hours: 24,
        step_minutes: 30,
        next_available_time: suggested,
        conflicting_job_ids: [],
      }),
    });
  });

  await page.route("**/api/jobs/101/dispatch", async (route) => {
    const payload = route.request().postDataJSON();
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: 101,
        title: "Water Heater Replace",
        status: "dispatched",
        technician_id: payload.technician_id,
        scheduled_time: payload.scheduled_time,
      }),
    });
  });

  await page.goto("/");

  await expect(page.getByRole("heading", { name: "Dispatch With Less Chaos" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Dispatch Assistant" })).toBeVisible();

  await page.getByLabel("Auth Email").fill("operator@example.com");
  await page.getByLabel("Auth Password").fill("testpass123");
  await page.getByRole("button", { name: "Login And Set Token" }).click();

  await expect(page.getByLabel("Pick Job")).toContainText("#101 Water Heater Replace (pending)");
  await expect(page.getByLabel("Pick Technician")).toContainText("#7 Sam Tech");

  await page.getByLabel("Pick Job").selectOption("101");
  await page.getByLabel("Pick Technician").selectOption("7");

  await page.getByRole("button", { name: "Check Conflict" }).click();
  await expect(page.getByText("Conflict: false")).toBeVisible();

  await page.getByRole("button", { name: "Suggest Next Slot" }).click();
  await expect(page.getByText("Conflicts seen: none")).toBeVisible();

  await page.getByRole("button", { name: "Dispatch At Suggested Time" }).click();
  await expect(page.getByText("Status: dispatched")).toBeVisible();
  await expect(page.getByText("Job ID: 101")).toBeVisible();
});
