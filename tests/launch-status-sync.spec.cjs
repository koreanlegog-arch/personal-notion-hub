const { test, expect } = require("playwright/test");

const baseURL = process.env.PNH_QA_BASE_URL || "http://127.0.0.1:4173";
const artifactDir = process.env.PNH_QA_ARTIFACT_DIR || "ops/runs/PNH-LAUNCH-STATUS-SYNC-QA-20260605/artifacts";
const storageKey = "personalNotionHubState";
const launchId = "launch-status-sync-fixture";
const packetId = "capture-5345e37040604a2fca64f317";

test.describe("Launch dispatch status sync", () => {
  test("Confirm Task Status syncs redacted dispatch evidence into boards", async ({ page }) => {
    await page.addInitScript(
      ({ storageKey, launchId, packetId }) => {
        const now = new Date().toISOString();
        window.localStorage.setItem(
          storageKey,
          JSON.stringify({
            schemaVersion: 1,
            settings: { theme: "light", density: "comfortable", activeView: "launch" },
            projects: [],
            tasks: [],
            notes: [],
            routines: [],
            links: [],
            assistantCaptures: [],
            launches: [
              {
                id: launchId,
                workspaceCaptureId: packetId,
                companionCaptureId: packetId,
                title: "Synthetic Launch Status Sync",
                commandType: "project_brief",
                objective: "Verify browser-local board sync from redacted dispatch evidence.",
                desiredOutcome: "Launch, Projects, and Tasks all reflect worker_done metadata.",
                constraints: "Use synthetic fixture data only.",
                deadline: "",
                priority: "high",
                sensitivity: "internal",
                deliveryTarget: "workspace_dispatch",
                status: "draft",
                commandStatus: "stored",
                dispatchState: "not_dispatched",
                createdProjectId: "",
                createdTaskIds: [],
                createdAt: now,
                updatedAt: now,
              },
            ],
          })
        );
      },
      { storageKey, launchId, packetId }
    );

    await page.goto(baseURL);
    await page.waitForFunction(() => window.PNHCompanionBridge);
    await page.evaluate(({ packetId }) => {
      const dispatchState = {
        totalRecords: 1,
        githubLinked: 1,
        discordLinked: 1,
        workerResults: 1,
        privateValuesPrinted: false,
        records: [
          {
            packetId,
            githubIssueNumber: 2,
            githubIssueSet: true,
            discordThreadId: "1512295718054793419",
            discordThreadSet: true,
            workerSessionId: "pnh:capture-5345e37040604a2fca64f317:qa",
            workerStatus: "done",
            workerResultSet: true,
            workerEvidenceRefSet: true,
            workerResultRecordedAt: "2026-06-05T03:28:43+00:00",
            taskStatus: "worker_done",
            evidenceCompleteness: 100,
            missingEvidence: [],
            nextAction: "summarize_worker_result_for_supervisor_review",
            updatedAt: "2026-06-05T03:28:43+00:00",
          },
        ],
      };
      window.PNHCompanionBridge = Object.freeze({
        ...window.PNHCompanionBridge,
        health: async () => ({ ok: true, mode: "qa-fixture", writesEnabled: false }),
        isPaired: () => true,
        dispatchState: async () => dispatchState,
      });
    }, { packetId });

    await page.getByRole("button", { name: "Launch" }).click();
    await page.getByRole("button", { name: "Check" }).click();
    await expect(page.getByText("Companion reachable at")).toBeVisible();
    await page.getByRole("button", { name: "Refresh Status" }).click();
    const launchCard = page.locator(".item-card").filter({ hasText: "Synthetic Launch Status Sync" });
    await expect(launchCard.getByText("Dispatch mapping: ledger_and_discord_linked")).toBeVisible();
    await expect(launchCard.getByText("Task worker_done")).toBeVisible();
    await expect(launchCard.getByText("Evidence 100%")).toBeVisible();

    await page.getByRole("button", { name: "Confirm Mapping" }).click();
    await page.getByRole("button", { name: "Confirm Task Status" }).click();
    await expect(page.getByText("Board progress synced at")).toBeVisible();
    await expect(page.getByText("Task status confirmed at")).toBeVisible();

    const syncedState = await page.evaluate((storageKey) => JSON.parse(window.localStorage.getItem(storageKey)), storageKey);
    const launch = syncedState.launches.find((item) => item.id === "launch-status-sync-fixture");
    expect(launch.dispatchState).toBe("ledger_and_discord_linked");
    expect(launch.githubIssueNumber).toBe("2");
    expect(launch.discordThreadId).toBe("1512295718054793419");
    expect(launch.taskStatus).toBe("worker_done");
    expect(launch.evidenceCompleteness).toBe(100);
    expect(launch.missingEvidence).toEqual([]);
    expect(launch.progressSyncedAt).toBeTruthy();
    expect(syncedState.projects).toHaveLength(1);
    expect(syncedState.projects[0].status).toBe("review");
    expect(syncedState.tasks).toHaveLength(1);
    expect(syncedState.tasks[0].status).toBe("today");
    expect(syncedState.tasks[0].tags).toContain("dispatch-progress");
    expect(JSON.stringify(syncedState)).not.toContain("Private command body");

    await page.screenshot({
      path: `${artifactDir}/launch-status-sync-desktop.png`,
      fullPage: true,
    });
  });
});
