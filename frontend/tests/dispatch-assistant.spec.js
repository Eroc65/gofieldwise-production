const { test, expect } = require("@playwright/test");

test("dispatch assistant core UI renders", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("heading", { name: "Dispatch With Less Chaos" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Dispatch Assistant" })).toBeVisible();
  await expect(page.getByLabel("Auth Email")).toBeVisible();
  await expect(page.getByLabel("Auth Password")).toBeVisible();
  await expect(page.getByLabel("Job ID", { exact: true })).toBeVisible();
  await expect(page.getByLabel("Technician ID", { exact: true })).toBeVisible();
  await expect(page.getByLabel("Pick Job")).toBeVisible();
  await expect(page.getByLabel("Pick Technician")).toBeVisible();
  await expect(page.getByRole("button", { name: "Check Conflict" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Suggest Next Slot" })).toBeVisible();
});
