const { test, expect } = require("playwright/test");

const baseURL = process.env.PNH_QA_BASE_URL || "http://127.0.0.1:4175";
const artifactDir = process.env.PNH_QA_ARTIFACT_DIR || "ops/runs/PNH-ASSISTANT-DISPATCH-INTENT-QA-20260605/artifacts";

test.describe("Assistant dispatch intent", () => {
  test("Assistant input can be stored as a command packet without alias correction", async ({ page }) => {
    await page.goto(baseURL);
    await page.evaluate(
      () =>
        new Promise((resolve) => {
          window.localStorage.clear();
          window.sessionStorage.clear();
          const request = window.indexedDB.deleteDatabase("personalNotionHubAssistant");
          request.onsuccess = resolve;
          request.onerror = resolve;
          request.onblocked = resolve;
        })
    );
    await page.reload();
    await page.waitForFunction(() => window.PNHCompanionBridge);
    await page.evaluate(() => {
      window.__assistantWorkspaceCalls = [];
      window.PNHCompanionBridge = Object.freeze({
        ...window.PNHCompanionBridge,
        isPaired: () => true,
        sendAssistantCapture: async (packet) => {
          window.__assistantWorkspaceCalls.push({ route: "assistant", packet });
          return { ok: true, status: 201, writesPerformed: true, captureId: packet.id };
        },
        sendMobileCommandPacket: async (packet) => {
          window.__assistantWorkspaceCalls.push({ route: "command", packet });
          return { ok: true, status: 201, writesPerformed: true, captureId: packet.id };
        },
      });
    });

    await page.getByRole("button", { name: "Assistant" }).click();
    await expect(page.getByRole("heading", { name: "Assistant control page" })).toBeVisible();

    await page.locator('select[name="dispatchIntent"]').selectOption("daily_command");
    await page.locator('input[name="title"]').fill("Synthetic assistant command");
    await page.locator('textarea[name="body"]').fill("Fixture-only assistant command body.");
    await page.getByRole("button", { name: "Add to assistant" }).click();

    const commandCard = page.locator(".item-card").filter({ hasText: "Synthetic assistant command" }).first();
    await expect(commandCard.locator(".badge").filter({ hasText: /^Daily command$/ })).toBeVisible();
    await commandCard.getByRole("button", { name: "Send to Workspace" }).click();

    let calls = await page.evaluate(() => window.__assistantWorkspaceCalls);
    expect(calls).toHaveLength(1);
    expect(calls[0].route).toBe("command");
    expect(calls[0].packet.kind).toBe("daily_command");
    expect(calls[0].packet.commandType).toBe("daily_command");
    expect(calls[0].packet.payloadType).toBe("pnh_mobile_command_packet");
    expect(calls[0].packet.dispatchState).toBe("not_dispatched");

    await page.locator('select[name="dispatchIntent"]').selectOption("assistant_capture");
    await page.locator('input[name="title"]').fill("Synthetic assistant note");
    await page.locator('textarea[name="body"]').fill("Fixture-only assistant note body.");
    await page.getByRole("button", { name: "Add to assistant" }).click();

    const noteCard = page.locator(".item-card").filter({ hasText: "Synthetic assistant note" }).first();
    await expect(noteCard.locator(".badge").filter({ hasText: /^Assistant note$/ })).toBeVisible();
    await noteCard.getByRole("button", { name: "Send to Workspace" }).click();

    calls = await page.evaluate(() => window.__assistantWorkspaceCalls);
    expect(calls).toHaveLength(2);
    expect(calls[1].route).toBe("assistant");
    expect(calls[1].packet.kind).toBe("assistant_capture");
    expect(calls[1].packet.payloadType).toBe("pnh_assistant_capture");
    expect(calls[1].packet.commandType).toBeUndefined();

    await page.screenshot({
      path: `${artifactDir}/assistant-dispatch-intent-desktop.png`,
      fullPage: true,
    });
  });
});
