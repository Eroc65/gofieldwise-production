const { test, expect } = require("@playwright/test");

test("exit-intent audit modal appears once per session", async ({ page }) => {
  await page.goto("/");

  await page.evaluate(() => {
    window.localStorage.removeItem("gf_exit_audit_seen");
    window.sessionStorage.removeItem("gf_exit_audit_session_seen");
  });

  await page.waitForTimeout(1700);

  await page.evaluate(() => {
    document.dispatchEvent(
      new MouseEvent("mouseout", {
        bubbles: true,
        clientY: 0,
      }),
    );
  });

  const title = page.getByRole("heading", { name: "Don't leave your leads on the table." });
  await expect(title).toBeVisible();

  await page.getByRole("button", { name: "Close" }).click();
  await expect(title).toHaveCount(0);

  await page.evaluate(() => {
    document.dispatchEvent(
      new MouseEvent("mouseout", {
        bubbles: true,
        clientY: 0,
      }),
    );
  });

  await expect(title).toHaveCount(0);
});
