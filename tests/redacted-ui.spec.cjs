const { test, expect } = require("playwright/test");

const baseURL = process.env.PNH_QA_BASE_URL || "http://127.0.0.1:4173";
const artifactDir = process.env.PNH_QA_ARTIFACT_DIR || "ops/runs/PNH-REDACTED-BROWSER-QA-20260604/artifacts";
const forbiddenBody = "SYNTHETIC_REDACTED_QA_BODY_NEVER_REAL_PRIVATE_DATA";

test.describe("redacted browser UI QA", () => {
  test("Assistant input can be redacted before screenshot evidence", async ({ page }) => {
    await page.goto(baseURL);
    await page.getByRole("button", { name: "Assistant" }).click();
    await expect(page.getByRole("heading", { name: "Assistant control page" })).toBeVisible();

    await page.locator('input[name="title"]').fill("Synthetic redacted QA note");
    await page.locator('textarea[name="body"]').fill(forbiddenBody);
    await page.getByRole("button", { name: "Add to assistant" }).click();
    await expect(page.locator('[data-sensitive="true"]').filter({ hasText: forbiddenBody }).first()).toBeVisible();

    await page.getByRole("button", { name: "Redact Screen" }).click();
    await expect
      .poll(() => page.evaluate(() => document.body.classList.contains("screenshot-redaction")))
      .toBe(true);

    const sensitiveStyles = await page.locator('[data-sensitive="true"]').evaluateAll((elements) =>
      elements.map((element) => {
        const style = window.getComputedStyle(element);
        return {
          tag: element.tagName,
          color: style.color,
          textShadow: style.textShadow,
          caretColor: style.caretColor,
        };
      })
    );
    expect(sensitiveStyles.length).toBeGreaterThan(0);
    expect(
      sensitiveStyles.some((style) => style.color === "rgba(0, 0, 0, 0)" || style.textShadow !== "none")
    ).toBeTruthy();

    const browserStorage = await page.evaluate(() => ({
      localStorage: { ...window.localStorage },
      sessionStorage: { ...window.sessionStorage },
    }));
    const storageText = JSON.stringify(browserStorage);
    expect(storageText).not.toContain("pairing");
    expect(storageText).not.toContain("sessionToken");
    expect(storageText).not.toContain("X-PNH-Browser-Session");

    await page.screenshot({
      path: `${artifactDir}/assistant-redacted-desktop.png`,
      fullPage: true,
    });
  });

  test("Core views fit desktop and mobile viewports without horizontal overflow", async ({ page }) => {
    for (const viewport of [
      { width: 1440, height: 900 },
      { width: 390, height: 844 },
    ]) {
      await page.setViewportSize(viewport);
      await page.goto(baseURL);
      for (const view of ["Dashboard", "Launch", "Assistant"]) {
        await page.evaluate((viewName) => {
          const button = [...document.querySelectorAll(".nav-item")].find((item) => item.textContent.trim() === viewName);
          if (!button) throw new Error(`missing nav item: ${viewName}`);
          button.click();
        }, view);
        const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
        expect(overflow).toBeLessThanOrEqual(2);
      }
    }
  });
});
