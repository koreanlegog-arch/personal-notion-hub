const STORAGE_KEY = "personalNotionHubState";

const todayISO = () => new Date().toISOString().slice(0, 10);
const nowISO = () => new Date().toISOString();

const uid = (prefix) => `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;

const ASSISTANT_SOURCES = [
  "slack",
  "email",
  "sms",
  "kakao",
  "call",
  "voice_memo",
  "my_memo",
  "youtube",
  "bible",
];

const COMMAND_TYPES = ["project_brief", "task_request", "daily_command", "urgent_approval"];
const ASSISTANT_DISPATCH_INTENTS = ["assistant_capture", ...COMMAND_TYPES];

let storageState = {
  available: true,
  lastError: "",
};

let assistantState = {
  ready: false,
  persistent: false,
  error: "",
  captures: [],
};

let companionState = {
  checked: false,
  online: false,
  paired: false,
  screenshotRedaction: false,
  dispatchState: null,
  commandPacketStatus: null,
  singleCommandPacketRun: null,
  statusText: "Not checked",
  lastResult: "",
};

const seedState = {
  schemaVersion: 1,
  settings: {
    theme: "light",
    density: "comfortable",
    activeView: "dashboard",
  },
  projects: [
    {
      id: "project-delivery-os",
      title: "AI Delivery Operating System",
      status: "active",
      priority: "high",
      summary: "Codex, OpenClaw, Discord, GitHub ledger를 연결한 운영 체계 고도화.",
      nextAction: "두 번째 supervisor-orchestrator 리허설 진행",
      tags: ["ops", "automation"],
      createdAt: nowISO(),
      updatedAt: nowISO(),
    },
    {
      id: "project-personal-hub",
      title: "Personal Notion Hub",
      status: "active",
      priority: "medium",
      summary: "개인 운영 정보를 localStorage 기반 정적 웹 hub로 정리.",
      nextAction: "배포 후 모바일 사용성 점검",
      tags: ["dashboard", "personal-os"],
      createdAt: nowISO(),
      updatedAt: nowISO(),
    },
  ],
  tasks: [
    {
      id: "task-supervisor-rehearsal",
      title: "supervisor-orchestrator 리허설 결과 review",
      status: "today",
      priority: "high",
      dueDate: todayISO(),
      projectId: "project-delivery-os",
      notes: "효율, 병목, 개선점을 기록한다.",
      tags: ["review"],
      createdAt: nowISO(),
      updatedAt: nowISO(),
    },
    {
      id: "task-export-backup",
      title: "첫 데이터 export 백업 생성",
      status: "inbox",
      priority: "medium",
      dueDate: "",
      projectId: "project-personal-hub",
      notes: "배포 후 실제 사용 전 JSON 백업 흐름을 확인한다.",
      tags: ["backup"],
      createdAt: nowISO(),
      updatedAt: nowISO(),
    },
  ],
  notes: [
    {
      id: "note-data-policy",
      title: "Data policy",
      body: "이 hub는 서버 저장이 없다. 실제 민감한 키, 계정 정보, 고객 정보는 기록하지 않는다.",
      tags: ["security", "policy"],
      projectId: "project-personal-hub",
      createdAt: nowISO(),
      updatedAt: nowISO(),
    },
  ],
  routines: [
    {
      id: "routine-weekly-review",
      title: "Weekly operations review",
      frequency: "weekly",
      checklist: ["Backlog 정리", "진행 중 프로젝트 상태 점검", "export backup 생성"],
      lastCompletedAt: "",
      createdAt: nowISO(),
      updatedAt: nowISO(),
    },
  ],
  links: [
    {
      id: "link-github",
      title: "GitHub Project Group",
      url: "https://github.com/koreanlegog-arch/project-group",
      category: "operations",
      notes: "Delivery OS 운영 repo",
      createdAt: nowISO(),
      updatedAt: nowISO(),
    },
  ],
  launches: [
    {
      id: "launch-demo-control-plane",
      title: "모바일 프로젝트 개요로 팀 착수 packet 만들기",
      commandType: "project_brief",
      objective: "모바일에서 짧은 프로젝트 개요를 작성하면 집의 작업 팀이 바로 읽을 수 있는 착수 패킷으로 변환한다.",
      desiredOutcome: "프로젝트, 초기 task, QA/security gate, Discord/GitHub 전달 초안이 한 번에 생성된다.",
      constraints: "외부 API 연동 없음. 실제 민감 데이터 없음. 수동 copy/export만 허용.",
      deadline: "",
      priority: "high",
      sensitivity: "internal",
      deliveryTarget: "local_packet",
      status: "draft",
      commandStatus: "queued",
      dispatchState: "not_dispatched",
      createdProjectId: "",
      createdTaskIds: [],
      createdAt: nowISO(),
      updatedAt: nowISO(),
    },
  ],
};

let state = loadState();
let activeView = state.settings.activeView || "dashboard";
let searchQuery = "";

const appView = document.querySelector("#appView");
const inspector = document.querySelector("#inspector");
const editorForm = document.querySelector("#editorForm");
const inspectorTitle = document.querySelector("#inspectorTitle");
const inspectorType = document.querySelector("#inspectorType");
const toastRegion = document.querySelector("#toastRegion");
const globalSearch = document.querySelector("#globalSearch");
const storageMeter = document.querySelector("#storageMeter");
const storageText = document.querySelector("#storageText");
const sidebar = document.querySelector(".sidebar");

document.documentElement.dataset.theme = state.settings.theme;

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function loadState() {
  const raw = readStoredState();
  if (!raw) return clone(seedState);

  try {
    const parsed = JSON.parse(raw);
    return normalizeState(parsed);
  } catch (error) {
    console.warn("Recovered from invalid localStorage state", error);
    const recovered = clone(seedState);
    recovered.system = {
      recoveredAt: nowISO(),
      reason: "invalid-json",
    };
    return recovered;
  }
}

function readStoredState() {
  try {
    storageState.available = true;
    storageState.lastError = "";
    return localStorage.getItem(STORAGE_KEY);
  } catch (error) {
    storageState.available = false;
    storageState.lastError = error?.name || "StorageError";
    console.warn("localStorage read failed", error);
    return null;
  }
}

function writeStoredState() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    storageState.available = true;
    storageState.lastError = "";
    return true;
  } catch (error) {
    storageState.available = false;
    storageState.lastError = error?.name || "StorageError";
    console.warn("localStorage write failed", error);
    return false;
  }
}

function normalizeState(candidate) {
  const base = clone(seedState);
  return {
    schemaVersion: 1,
    settings: { ...base.settings, ...(candidate.settings || {}) },
    projects: Array.isArray(candidate.projects) ? candidate.projects : base.projects,
    tasks: Array.isArray(candidate.tasks) ? candidate.tasks : base.tasks,
    notes: Array.isArray(candidate.notes) ? candidate.notes : base.notes,
    routines: Array.isArray(candidate.routines) ? candidate.routines : base.routines,
    links: Array.isArray(candidate.links) ? candidate.links : base.links,
    launches: Array.isArray(candidate.launches) ? candidate.launches.map(normalizeLaunch) : [],
    system: candidate.system || {},
  };
}

function persist(message = "Saved") {
  state.settings.activeView = activeView;
  const saved = writeStoredState();
  updateStorageMeter();
  render();
  if (saved) {
    toast(message);
  } else {
    toast("Save failed", "브라우저 저장소에 기록하지 못했습니다. Export JSON으로 백업하세요.");
  }
}

function updateStorageMeter() {
  const bytes = new Blob([JSON.stringify(state)]).size;
  const limit = 5 * 1024 * 1024;
  const percent = Math.min(100, Math.round((bytes / limit) * 100));
  storageMeter.style.width = `${Math.max(percent, 4)}%`;
  if (storageState.available) {
    storageText.textContent = `${(bytes / 1024).toFixed(1)} KB stored locally`;
  } else {
    storageText.textContent = `Storage unavailable: ${storageState.lastError || "unknown"}`;
  }
}

function toast(title, detail = "") {
  const el = document.createElement("div");
  el.className = "toast";
  const strong = document.createElement("strong");
  strong.textContent = title;
  el.append(strong);
  if (detail) {
    const p = document.createElement("p");
    p.textContent = detail;
    el.append(p);
  }
  toastRegion.append(el);
  window.setTimeout(() => el.remove(), 3200);
}

function matchesQuery(item) {
  if (!searchQuery) return true;
  const haystack = [
    item.title,
    item.summary,
    item.nextAction,
    item.notes,
    item.body,
    item.objective,
    item.desiredOutcome,
    item.constraints,
    item.deliveryTarget,
    item.url,
    item.category,
    ...(item.tags || []),
    ...(item.checklist || []),
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
  return haystack.includes(searchQuery.toLowerCase());
}

function projectTitle(projectId) {
  return state.projects.find((project) => project.id === projectId)?.title || "No project";
}

function clearView() {
  appView.replaceChildren();
}

function make(tag, className, text) {
  const el = document.createElement(tag);
  if (className) el.className = className;
  if (text !== undefined) el.textContent = text;
  return el;
}

function badge(text, extra = "") {
  return make("span", `badge ${extra}`.trim(), text);
}

function sensitive(el) {
  el.setAttribute("data-sensitive", "true");
  return el;
}

function syncScreenshotRedaction() {
  document.body.classList.toggle("screenshot-redaction", companionState.screenshotRedaction);
}

function viewHeader(title, description, actionLabel, action) {
  const header = make("div", "view-header");
  const titleWrap = make("div", "view-title");
  titleWrap.append(make("p", "eyebrow", "Workspace"));
  titleWrap.append(make("h2", "", title));
  titleWrap.append(make("p", "", description));
  header.append(titleWrap);
  if (actionLabel && action) {
    const button = make("button", "primary-button", actionLabel);
    button.type = "button";
    button.addEventListener("click", action);
    header.append(button);
  }
  return header;
}

function render() {
  syncScreenshotRedaction();
  updateActiveNav();
  updateStorageMeter();
  clearView();
  const renderers = {
    dashboard: renderDashboard,
    launch: renderLaunch,
    assistant: renderAssistant,
    projects: renderProjects,
    tasks: renderTasks,
    notes: renderNotes,
    routines: renderRoutines,
    links: renderLinks,
    settings: renderSettings,
  };
  (renderers[activeView] || renderDashboard)();
}

function updateActiveNav() {
  document.querySelectorAll(".nav-item").forEach((button) => {
    button.classList.toggle("is-active", button.dataset.view === activeView);
  });
}

function renderDashboard() {
  appView.append(
    viewHeader(
      "Operations dashboard",
      "오늘의 focus, 진행 중인 프로젝트, 빠른 capture, 최근 노트를 한 화면에서 관리합니다.",
      "New Task",
      () => openEditor("task")
    )
  );

  const activeProjects = state.projects.filter((project) => project.status === "active");
  const openTasks = state.tasks.filter((task) => task.status !== "done");
  const todayTasks = state.tasks.filter((task) => task.status === "today" || task.dueDate === todayISO());
  const notes = state.notes.slice().sort((a, b) => b.updatedAt.localeCompare(a.updatedAt));
  const brief = buildAssistantBrief();

  const hero = make("section", "hero-strip");
  const focus = make("div", "focus-panel");
  focus.append(make("p", "eyebrow", "Today"));
  focus.append(make("h3", "", todayTasks[0]?.title || brief.title));
  focus.append(
    make(
      "p",
      "",
      todayTasks[0]?.notes || brief.body
    )
  );
  focus.append(quickCaptureForm());

  const visual = make("div", "visual-panel");
  visual.setAttribute("role", "img");
  visual.setAttribute("aria-label", "Workspace board preview");
  visual.append(make("div", "visual-grid"));
  const stack = make("div", "visual-stack");
  for (let i = 0; i < 3; i += 1) {
    const sheet = make("div", "mini-sheet");
    sheet.append(make("span", "mini-row"));
    sheet.append(make("span", "mini-row"));
    sheet.append(make("span", "mini-row"));
    stack.append(sheet);
  }
  visual.append(stack);
  hero.append(focus, visual);
  appView.append(hero);

  const stats = make("section", "stat-grid");
  [
    ["Active projects", activeProjects.length],
    ["Open tasks", openTasks.length],
    ["Launch packets", state.launches.length],
    ["Assistant inbox", assistantState.captures.filter((capture) => capture.status !== "archived").length],
    ["Notes", state.notes.length],
  ].forEach(([label, value]) => {
    const card = make("div", "stat-card");
    card.append(make("strong", "", String(value)));
    card.append(make("span", "", label));
    stats.append(card);
  });
  appView.append(stats);

  const grid = make("section", "content-grid three");
  grid.append(
    panel("Today", todayTasks.slice(0, 5), (task) => taskCard(task), "오늘 지정된 task가 없습니다."),
    panel("Assistant Brief", assistantBriefCards(), (item) => assistantBriefCard(item), "assistant 입력이 아직 없습니다."),
    panel("Active Projects", activeProjects.slice(0, 5), (project) => projectCard(project), "진행 중 프로젝트가 없습니다."),
    panel("Recent Notes", notes.slice(0, 5), (note) => noteCard(note), "최근 note가 없습니다.")
  );
  appView.append(grid);
}

function renderLaunch() {
  appView.append(
    viewHeader(
      "Project launch control",
      "모바일에서 프로젝트 개요를 남기면 집의 작업 팀이 바로 읽고 착수할 수 있는 dispatch packet으로 정리합니다.",
      "Export Data",
      exportState
    )
  );

  const topGrid = make("section", "content-grid launch-grid");
  topGrid.append(launchIntakePanel(), launchCompanionPanel(), launchDispatchStatusPanel(), launchDirectionPanel());
  appView.append(topGrid);

  const launchList = state.launches
    .filter(matchesQuery)
    .slice()
    .sort((a, b) => b.updatedAt.localeCompare(a.updatedAt));

  const board = make("section", "content-grid");
  board.append(panel("Dispatch Packets", launchList, launchPacketCard, "작성된 dispatch packet이 없습니다."));
  appView.append(board);
}

function launchIntakePanel() {
  const section = make("section", "section-panel launch-intake-panel");
  const header = make("div", "section-header");
  header.append(make("h3", "", "Mobile project brief"));
  header.append(badge("local-only"));
  section.append(header);

  const form = make("form", "launch-form");
  form.append(
    launchField("title", "Project title", "text", ""),
    launchField("commandType", "Command type", "select", "project_brief", COMMAND_TYPES),
    launchField("objective", "Objective", "textarea", ""),
    launchField("desiredOutcome", "Desired outcome", "textarea", ""),
    launchField("constraints", "Constraints / risks", "textarea", ""),
    launchField("deadline", "Target date", "date", ""),
    launchField("priority", "Priority", "select", "medium", ["high", "medium", "low"]),
    launchField("sensitivity", "Data sensitivity", "select", "internal", ["public-demo", "internal", "private-sensitive"]),
    launchField("deliveryTarget", "Dispatch target", "select", "local_packet", ["local_packet", "discord_draft", "github_issue_draft"])
  );

  const actions = make("div", "form-actions");
  const submit = make("button", "primary-button", "Create dispatch packet");
  submit.type = "submit";
  actions.append(submit, button("Load demo brief", loadLaunchDemo, "ghost-button"));
  form.append(actions);
  form.addEventListener("submit", handleLaunchSubmit);
  section.append(form);
  section.append(make("p", "fine-print", "이 MVP는 packet 생성, local companion 저장, metadata-safe dry-run, dispatch 상태 확인을 지원합니다."));
  return section;
}

function launchField(name, labelText, type, value, options = []) {
  const wrap = make("div", "field");
  const label = document.createElement("label");
  label.htmlFor = `launch-field-${name}`;
  label.textContent = labelText;
  let control;
  if (type === "textarea") {
    control = document.createElement("textarea");
    control.value = value;
  } else if (type === "select") {
    control = document.createElement("select");
    options.forEach((optionValue) => {
      const option = document.createElement("option");
      option.value = optionValue;
      option.textContent = optionValue;
      control.append(option);
    });
    control.value = value;
  } else {
    control = document.createElement("input");
    control.type = type;
    control.value = value;
  }
  control.name = name;
  control.id = `launch-field-${name}`;
  if (["title", "objective", "desiredOutcome", "constraints"].includes(name)) {
    sensitive(control);
  }
  wrap.append(label, control);
  return wrap;
}

function normalizeLaunch(launch) {
  return {
    commandType: "project_brief",
    commandStatus: "queued",
    dispatchState: "not_dispatched",
    ...launch,
  };
}

function commandTypeLabel(commandType) {
  const labels = {
    project_brief: "Project brief",
    task_request: "Task request",
    daily_command: "Daily command",
    urgent_approval: "Urgent approval",
  };
  return labels[commandType] || commandType || "Project brief";
}

function assistantDispatchIntentLabel(intent) {
  if (!intent || intent === "assistant_capture") return "Assistant note";
  return commandTypeLabel(intent);
}

function isCommandDispatchIntent(intent) {
  return COMMAND_TYPES.includes(intent);
}

function launchDirectionPanel() {
  const section = make("section", "section-panel launch-direction-panel");
  section.append(make("p", "eyebrow", "Automation direction"));
  section.append(make("h3", "", "Mobile brief -> team execution"));
  const steps = [
    ["1", "Capture", "모바일에서 목표, 결과물, 제약, 민감도 입력"],
    ["2", "Packet", "작업 착수 기준, acceptance criteria, lane, approval gate 생성"],
    ["3", "Ledger", "Projects/Tasks 또는 GitHub issue draft로 전환"],
    ["4", "Dispatch", "Discord/OpenClaw 팀 지시문으로 전달"],
    ["5", "Evidence", "QA/security/release-readiness 결과를 다시 hub에 기록"],
  ];
  const list = make("div", "launch-step-list");
  steps.forEach(([number, title, body]) => {
    const item = make("article", "launch-step");
    item.append(make("strong", "", number));
    const copy = make("div", "");
    copy.append(make("h4", "", title));
    copy.append(make("p", "", body));
    item.append(copy);
    list.append(item);
  });
  section.append(list);
  return section;
}

function launchCompanionPanel() {
  const section = make("section", "section-panel companion-panel");
  const header = make("div", "section-header");
  header.append(make("h3", "", "Local companion"));
  header.append(badge(companionStatusLabel(), companionState.online ? "status-online" : "status-offline"));
  section.append(header);

  const status = make("div", "companion-status");
  status.append(make("p", "", companionState.statusText));
  if (companionState.lastResult) status.append(make("p", "fine-print", companionState.lastResult));
  section.append(status);

  const form = make("form", "companion-form");
  const label = document.createElement("label");
  label.htmlFor = "companion-pair-code";
  label.textContent = "Pairing code";
  const input = document.createElement("input");
  input.id = "companion-pair-code";
  input.name = "pairingCode";
  input.type = "text";
  input.inputMode = "text";
  input.autocomplete = "off";
  input.placeholder = "One-time code";
  sensitive(input);
  const actions = make("div", "form-actions");
  const pairButton = make("button", "primary-button", companionState.paired ? "Paired" : "Pair");
  pairButton.type = "submit";
  pairButton.disabled = companionState.paired;
  actions.append(
    pairButton,
    button("Check", checkCompanionStatus, "ghost-button"),
    button("Disconnect", disconnectCompanion, "ghost-button"),
    button(companionState.screenshotRedaction ? "Show Screen" : "Redact Screen", toggleScreenshotRedaction, "ghost-button")
  );
  form.append(label, input, actions);
  form.addEventListener("submit", pairCompanion);
  section.append(form);

  const latest = latestLaunchPacket();
  const send = button("Send Latest Packet", sendLatestLaunchToCompanion, "small-button");
  send.disabled = !latest || !companionState.paired;
  const sendRow = make("div", "item-actions");
  sendRow.append(send);
  if (latest) {
    sendRow.append(sensitive(make("span", "fine-print", latest.title)));
  } else {
    sendRow.append(make("span", "fine-print", "Create a dispatch packet first."));
  }
  section.append(sendRow);
  section.append(make("p", "fine-print", "Session token stays in memory only. Pairing code and token are not shown or saved. Use Redact Screen before screenshots."));
  return section;
}

function launchDispatchStatusPanel() {
  const section = make("section", "section-panel companion-panel");
  const header = make("div", "section-header");
  header.append(make("h3", "", "Dispatch status"));
  header.append(badge(companionState.dispatchState || companionState.commandPacketStatus ? "synced" : "local"));
  section.append(header);

  const status = companionState.dispatchState;
  const packetStatus = companionState.commandPacketStatus;
  const rows = [
    ["Records", status?.totalRecords ?? 0],
    ["GitHub linked", status?.githubLinked ?? 0],
    ["Discord linked", status?.discordLinked ?? 0],
    ["Worker results", status?.workerResults ?? 0],
    ["Queue", packetStatus?.queueCount ?? 0],
    ["Ready review", packetStatus?.readyForSupervisorReview ?? 0],
  ];
  const statList = make("div", "dispatch-status-list");
  rows.forEach(([label, value]) => {
    const item = make("div", "dispatch-status-item");
    item.append(make("span", "", label));
    item.append(make("strong", "", String(value)));
    statList.append(item);
  });
  section.append(statList);

  const records = Array.isArray(status?.records) ? status.records.slice(0, 3) : [];
  if (records.length) {
    const list = make("div", "dispatch-record-list");
    records.forEach((record) => {
      const item = make("article", "dispatch-record");
      item.append(make("strong", "", record.packetId || "packet"));
      item.append(
        make(
          "p",
          "fine-print",
          `GitHub #${record.githubIssueNumber || "-"} · Discord ${record.discordThreadId || "-"}`
        )
      );
      if (record.workerResultSet) {
        item.append(make("p", "fine-print", `Worker ${record.workerStatus || "recorded"} · ${record.workerSessionId || "-"}`));
      }
      if (record.taskStatus) {
        item.append(make("p", "fine-print", `Task ${record.taskStatus} · Evidence ${record.evidenceCompleteness ?? 0}%`));
      }
      list.append(item);
    });
    section.append(list);
  } else {
    section.append(make("p", "fine-print", "No dispatch state records are available yet."));
  }

  section.append(commandPacketStatusCard(packetStatus));

  const refresh = button("Refresh Status", refreshDispatchState, "small-button");
  const refreshPacket = button("Refresh Packet Status", refreshCommandPacketStatus, "small-button");
  const runDry = button("Run Dry-Run", runSingleCommandPacketDryRun, "small-button");
  const applyLocked = button("Apply Locked", () => toast("Apply locked", "Browser apply requires companion runtime enablement."), "small-button");
  refresh.disabled = !companionState.paired;
  refreshPacket.disabled = !companionState.paired;
  runDry.disabled = !companionState.paired;
  applyLocked.disabled = true;
  const actions = make("div", "item-actions");
  actions.append(refresh, refreshPacket, runDry, applyLocked);
  section.append(actions);
  section.append(make("p", "fine-print", "Reads redacted local dispatch metadata only. URLs and private bodies are not shown."));
  return section;
}

function commandPacketStatusCard(status) {
  const card = make("article", "dispatch-record command-packet-status");
  card.append(make("strong", "", "Single command packet"));
  if (!status) {
    card.append(operatorActionBanner({
      label: "Pair required",
      title: "Operator action: pair companion",
      body: "Pair companion and refresh before running packet checks.",
      variant: "muted",
    }));
    card.append(make("p", "fine-print", "Pair companion and refresh to read wrapper status."));
    return card;
  }
  card.append(operatorActionBanner(commandPacketOperatorAction(status, companionState.singleCommandPacketRun)));
  const latestRun = status.latestRun || {};
  const latestDispatch = status.latestDispatch || {};
  const facts = [
    ["Stage", status.stageLabel || commandPacketStageLabel(latestDispatch)],
    ["Queue", status.queueCount ?? 0],
    ["Last run", latestRun.runDir || "-"],
    ["Issue", status.lastIssue ? `#${status.lastIssue}` : latestDispatch.githubIssueNumber ? `#${latestDispatch.githubIssueNumber}` : "-"],
    ["Worker", status.lastWorkerStatus || latestRun.workerStatus || "-"],
    ["Next", status.nextAction || "-"],
  ];
  card.append(commandPacketStageRail(status.stageSteps || commandPacketStageSteps(latestDispatch, status.queueCount ?? 0)));
  facts.forEach(([label, value]) => {
    const row = make("p", "fine-print command-packet-status-row");
    row.append(make("span", "", `${label}: `));
    row.append(make("strong", "", String(value)));
    card.append(row);
  });
  if (latestRun.mode) {
    card.append(make("p", "fine-print", `Wrapper mode: ${latestRun.mode} · external writes ${latestRun.externalWritesPerformed ? "yes" : "no"} · worker run ${latestRun.workerRunPerformed ? "yes" : "no"}`));
  }
  if (companionState.singleCommandPacketRun) {
    const run = companionState.singleCommandPacketRun;
    card.append(make("p", "fine-print", `Last browser run: ${run.mode || "-"} · external writes ${run.externalWritesPerformed ? "yes" : "no"} · worker run ${run.workerRunPerformed ? "yes" : "no"}`));
  }
  card.append(make("p", "fine-print", "metadata-only · private body hidden"));
  return card;
}

function commandPacketStageRail(steps) {
  const rail = make("ol", "command-packet-stage-rail");
  steps.forEach((step) => {
    const item = make("li", `command-packet-stage command-packet-stage-${step.state || "waiting"}`);
    item.append(make("span", "", step.label || step.key || "Step"));
    rail.append(item);
  });
  return rail;
}

function commandPacketStageSteps(record, queueCount = 0) {
  return [
    { key: "queued", label: "Inbox", state: queueCount > 0 || record ? "done" : "current" },
    { key: "github", label: "Ledger", state: record?.githubIssueSet ? "done" : record ? "current" : "waiting" },
    { key: "discord", label: "Thread", state: record?.discordThreadSet ? "done" : record?.githubIssueSet ? "current" : "waiting" },
    { key: "worker", label: "Worker", state: record?.workerResultSet || record?.workerStatus ? "done" : record?.discordThreadSet ? "current" : "waiting" },
    { key: "review", label: "Review", state: record?.taskStatus === "worker_done" ? "done" : record?.workerResultSet ? "current" : "waiting" },
  ];
}

function commandPacketStageLabel(record) {
  if (!record) return "Idle";
  if (record.taskStatus === "worker_done") return "Review ready";
  if (record.workerResultSet || record.workerStatus) return "Worker result";
  if (record.discordThreadSet) return "Worker thread";
  if (record.githubIssueSet) return "Ledger ready";
  return "Queued";
}

function commandPacketOperatorAction(status, run) {
  const latestRun = status.latestRun || {};
  if (run?.ok === false) {
    return {
      label: "Dry-run failed",
      title: "Operator action: inspect run evidence",
      body: "Open the latest run evidence before retrying the browser dry-run.",
      variant: "blocked",
    };
  }
  if ((status.readyForSupervisorReview ?? 0) > 0) {
    return {
      label: "Review ready",
      title: "Operator action: review worker evidence",
      body: "At least one worker-done packet is ready for supervisor review summary.",
      variant: "ready",
    };
  }
  if ((status.pendingWorkerSession ?? 0) > 0) {
    return {
      label: "Worker pending",
      title: "Operator action: capture worker result",
      body: "A dispatched packet is waiting for worker-session capture or refresh.",
      variant: "pending",
    };
  }
  if ((status.queueCount ?? 0) > 0 && !latestRun.externalWritesPerformed) {
    return {
      label: "Packet queued",
      title: "Operator action: run dry-run first",
      body: "A command packet is waiting. Use Run Dry-Run to inspect the safe plan before apply.",
      variant: "pending",
    };
  }
  if (run?.mode === "dry-run" || latestRun.message === "queue_empty" || (status.queueCount ?? 0) === 0) {
    return {
      label: "Queue clear",
      title: "Operator action: wait for next packet",
      body: "No command packet is currently queued for dispatch.",
      variant: "ready",
    };
  }
  return {
    label: "Check needed",
    title: "Operator action: refresh status",
    body: "Refresh packet status before choosing the next dispatch step.",
    variant: "muted",
  };
}

function operatorActionBanner(action) {
  const banner = make("div", `operator-action-banner operator-action-${action.variant || "muted"}`);
  banner.append(badge(action.label || "Action"));
  const copy = make("div", "");
  copy.append(make("strong", "", action.title || "Operator action"));
  copy.append(make("p", "fine-print", action.body || ""));
  banner.append(copy);
  return banner;
}

function dispatchRecordForLaunch(launch) {
  const records = Array.isArray(companionState.dispatchState?.records) ? companionState.dispatchState.records : [];
  const ids = new Set(
    [
      launch.workspaceCaptureId,
      launch.companionCaptureId,
      `launch-packet-${launch.id}`,
      launch.id,
    ]
      .filter(Boolean)
      .map(String)
  );
  return records.find((record) => ids.has(String(record.packetId || ""))) || null;
}

function dispatchRecordLabel(record) {
  if (!record) return "not_dispatched";
  if (record.githubIssueSet && record.discordThreadSet) return "ledger_and_discord_linked";
  if (record.githubIssueSet) return "github_ledger_linked";
  if (record.discordThreadSet) return "discord_thread_linked";
  return "dispatch_state_recorded";
}

function confirmDispatchMappingForLaunch(id) {
  const launch = state.launches.find((item) => item.id === id);
  if (!launch) return;
  const record = dispatchRecordForLaunch(launch);
  if (!record) {
    toast("No dispatch mapping", "companion dispatch state를 먼저 refresh하세요.");
    return;
  }
  launch.dispatchState = dispatchRecordLabel(record);
  launch.dispatchConfirmedAt = nowISO();
  launch.dispatchRecordUpdatedAt = record.updatedAt || "";
  launch.githubIssueNumber = record.githubIssueNumber ? String(record.githubIssueNumber) : "";
  launch.githubIssueSet = Boolean(record.githubIssueSet);
  launch.discordThreadId = record.discordThreadId ? String(record.discordThreadId) : "";
  launch.discordThreadSet = Boolean(record.discordThreadSet);
  launch.updatedAt = nowISO();
  persist("Dispatch mapping confirmed", "GitHub/Discord 외부 ID metadata만 browser-local launch record에 저장했습니다.");
}

function confirmTaskStatusForLaunch(id) {
  const launch = state.launches.find((item) => item.id === id);
  if (!launch) return;
  const record = dispatchRecordForLaunch(launch);
  if (!record?.taskStatus) {
    toast("No task status", "worker metadata가 포함된 dispatch state를 먼저 refresh하세요.");
    return;
  }
  launch.taskStatus = record.taskStatus;
  launch.evidenceCompleteness = Number(record.evidenceCompleteness || 0);
  launch.missingEvidence = Array.isArray(record.missingEvidence) ? record.missingEvidence.slice(0, 8) : [];
  launch.nextAction = record.nextAction || "";
  launch.workerStatus = record.workerStatus || "";
  launch.workerSessionId = record.workerSessionId || "";
  launch.taskStatusConfirmedAt = nowISO();
  syncLaunchProgressToBoards(launch, record);
  launch.updatedAt = nowISO();
  persist("Task status confirmed", "worker/evidence metadata를 Launch, Projects, Tasks 보드에 반영했습니다.");
}

function syncLaunchProgressToBoards(launch, record) {
  const project = ensureLaunchProgressProject(launch, record);
  const task = ensureLaunchProgressTask(launch, project, record);
  project.status = projectStatusForDispatchRecord(record);
  project.priority = launch.priority || project.priority || "medium";
  project.nextAction = record.nextAction || project.nextAction || "Review dispatch evidence";
  project.updatedAt = nowISO();
  task.status = taskStatusForDispatchRecord(record);
  task.priority = taskPriorityForDispatchRecord(launch, record);
  task.dueDate = task.status === "today" ? todayISO() : task.dueDate || "";
  task.notes = buildDispatchProgressNotes(launch, record);
  task.updatedAt = nowISO();
  launch.createdProjectId = project.id;
  launch.progressTaskId = task.id;
  launch.progressSyncedAt = nowISO();
}

function ensureLaunchProgressProject(launch, record) {
  let project = state.projects.find((item) => item.id === launch.createdProjectId);
  if (!project) {
    const projectId = launch.createdProjectId || uid("project");
    project = {
      id: projectId,
      title: launch.title,
      status: projectStatusForDispatchRecord(record),
      priority: launch.priority || "medium",
      summary: launch.objective || "Launch-driven project created from dispatch status.",
      nextAction: record.nextAction || "Review dispatch evidence",
      tags: ["launch", "dispatch"],
      createdAt: nowISO(),
      updatedAt: nowISO(),
    };
    state.projects.unshift(project);
    launch.createdProjectId = projectId;
  }
  project.tags = uniqueStrings([...(project.tags || []), "launch", "dispatch"]);
  return project;
}

function ensureLaunchProgressTask(launch, project, record) {
  let task = state.tasks.find((item) => item.id === launch.progressTaskId);
  if (!task) {
    task = state.tasks.find(
      (item) => item.launchId === launch.id && Array.isArray(item.tags) && item.tags.includes("dispatch-progress")
    );
  }
  if (!task) {
    task = {
      id: uid("task"),
      title: `${launch.title}: Dispatch evidence follow-up`,
      status: taskStatusForDispatchRecord(record),
      priority: taskPriorityForDispatchRecord(launch, record),
      dueDate: "",
      projectId: project.id,
      launchId: launch.id,
      notes: "",
      tags: ["launch", "dispatch", "dispatch-progress"],
      createdAt: nowISO(),
      updatedAt: nowISO(),
    };
    state.tasks.unshift(task);
  }
  task.projectId = project.id;
  task.launchId = launch.id;
  task.tags = uniqueStrings([...(task.tags || []), "launch", "dispatch", "dispatch-progress"]);
  return task;
}

function projectStatusForDispatchRecord(record) {
  if (["worker_failed", "worker_blocked"].includes(record.taskStatus)) return "blocked";
  if (record.taskStatus === "worker_done") return "review";
  return "active";
}

function taskStatusForDispatchRecord(record) {
  if (["worker_failed", "worker_blocked", "worker_done"].includes(record.taskStatus)) return "today";
  if (record.taskStatus === "dispatched_to_worker_thread") return "today";
  return "upcoming";
}

function taskPriorityForDispatchRecord(launch, record) {
  if (["worker_failed", "worker_blocked"].includes(record.taskStatus)) return "high";
  return launch.priority || "medium";
}

function buildDispatchProgressNotes(launch, record) {
  return [
    `Launch ID: ${launch.id}`,
    `Task status: ${record.taskStatus || "unknown"}`,
    `Evidence completeness: ${record.evidenceCompleteness ?? 0}%`,
    `Missing evidence: ${Array.isArray(record.missingEvidence) && record.missingEvidence.length ? record.missingEvidence.join(", ") : "none"}`,
    `Next action: ${record.nextAction || "Review dispatch evidence"}`,
    record.workerSessionId ? `Worker session: ${record.workerSessionId}` : "",
    record.githubIssueNumber ? `GitHub issue: #${record.githubIssueNumber}` : "",
    record.discordThreadId ? `Discord thread: ${record.discordThreadId}` : "",
  ]
    .filter(Boolean)
    .join("\n");
}

function uniqueStrings(values) {
  return [...new Set(values.filter(Boolean).map(String))];
}

function companionStatusLabel() {
  if (companionState.paired) return "paired";
  if (companionState.online) return "online";
  if (companionState.checked) return "offline";
  return "local-only";
}

async function checkCompanionStatus() {
  const bridge = window.PNHCompanionBridge;
  if (!bridge?.health) {
    companionState = {
      ...companionState,
      checked: true,
      online: false,
      paired: false,
      statusText: "Companion bridge script is unavailable. Browser-only mode is active.",
      lastResult: "",
    };
    render();
    return;
  }
  try {
    const health = await bridge.health();
    let restored = null;
    if (health.ok && !bridge.isPaired() && bridge.restoreOwnerDeviceSession) {
      restored = await bridge.restoreOwnerDeviceSession();
    }
    companionState = {
      checked: true,
      online: health.ok,
      paired: bridge.isPaired(),
      statusText: health.ok
        ? `Companion reachable at ${bridge.baseUrl}. Mode: ${health.mode}.`
        : "Companion did not report a healthy loopback bridge.",
      lastResult: restored?.restored
        ? "Owner device session restored. Private inbox writes are enabled."
        : health.writesEnabled ? "Private inbox writes are enabled." : "Private inbox writes are disabled.",
    };
  } catch (error) {
    companionState = {
      checked: true,
      online: false,
      paired: false,
      statusText: "Companion is not reachable. Browser-only mode is active.",
      lastResult: error?.message || "Loopback request failed.",
    };
  }
  render();
}

async function pairCompanion(event) {
  event.preventDefault();
  const bridge = window.PNHCompanionBridge;
  if (!bridge?.pair) {
    toast("Companion unavailable", "브라우저 전용 모드로 계속 사용할 수 있습니다.");
    return;
  }
  const input = event.currentTarget.elements.pairingCode;
  const pairingCode = String(input?.value || "").trim();
  try {
    const pairResult = await bridge.pair(pairingCode);
    if (input) input.value = "";
    companionState = {
      ...companionState,
      checked: true,
      online: true,
      paired: true,
      statusText: `Companion paired at ${bridge.baseUrl}.`,
      lastResult: pairResult.ownerDeviceIssued
        ? "Ready to send the latest launch packet. Owner device session saved for reconnect."
        : "Ready to send the latest launch packet.",
    };
    await refreshDispatchState({ silent: true });
    toast("Companion paired");
  } catch (error) {
    if (input) input.value = "";
    companionState = {
      ...companionState,
      checked: true,
      online: false,
      paired: false,
      statusText: "Pairing failed. Browser-only mode is still available.",
      lastResult: error?.message || "Pairing failed.",
    };
    render();
    toast("Pairing failed", "코드를 확인하고 companion이 bridge mode로 실행 중인지 확인하세요.");
  }
}

async function refreshDispatchState(options = {}) {
  const bridge = window.PNHCompanionBridge;
  if (!bridge?.dispatchState || !bridge.isPaired()) {
    companionState = {
      ...companionState,
      dispatchState: null,
      commandPacketStatus: null,
      singleCommandPacketRun: null,
      lastResult: options.silent ? companionState.lastResult : "Pair companion before checking dispatch state.",
    };
    render();
    if (!options.silent) toast("Dispatch status unavailable", "companion pairing 후 다시 확인하세요.");
    return;
  }
  try {
    const status = await bridge.dispatchState();
    let packetStatus = companionState.commandPacketStatus;
    if (bridge.commandPacketStatus) {
      packetStatus = await bridge.commandPacketStatus();
    }
    companionState = {
      ...companionState,
      dispatchState: status,
      commandPacketStatus: packetStatus,
      lastResult: options.silent ? companionState.lastResult : "Dispatch state refreshed.",
    };
    render();
    if (!options.silent) toast("Dispatch state refreshed");
  } catch (error) {
    companionState = {
      ...companionState,
      dispatchState: null,
      commandPacketStatus: null,
      singleCommandPacketRun: null,
      lastResult: error?.message || "Dispatch state check failed.",
    };
    render();
    if (!options.silent) toast("Dispatch state unavailable");
  }
}

async function refreshCommandPacketStatus(options = {}) {
  const bridge = window.PNHCompanionBridge;
  if (!bridge?.commandPacketStatus || !bridge.isPaired()) {
    companionState = {
      ...companionState,
      commandPacketStatus: null,
      lastResult: options.silent ? companionState.lastResult : "Pair companion before checking command packet status.",
    };
    render();
    if (!options.silent) toast("Command packet status unavailable", "companion pairing 후 다시 확인하세요.");
    return;
  }
  try {
    const status = await bridge.commandPacketStatus();
    companionState = {
      ...companionState,
      commandPacketStatus: status,
      lastResult: options.silent ? companionState.lastResult : "Command packet status refreshed.",
    };
    render();
    if (!options.silent) toast("Command packet status refreshed");
  } catch (error) {
    companionState = {
      ...companionState,
      commandPacketStatus: null,
      lastResult: error?.message || "Command packet status check failed.",
    };
    render();
    if (!options.silent) toast("Command packet status unavailable");
  }
}

async function runSingleCommandPacketDryRun() {
  const bridge = window.PNHCompanionBridge;
  if (!bridge?.runSingleCommandPacket || !bridge.isPaired()) {
    companionState = {
      ...companionState,
      singleCommandPacketRun: null,
      lastResult: "Pair companion before running single command packet dry-run.",
    };
    render();
    toast("Dry-run unavailable", "companion pairing 후 다시 실행하세요.");
    return;
  }
  try {
    companionState = {
      ...companionState,
      lastResult: "Single command packet dry-run is running...",
    };
    render();
    const run = await bridge.runSingleCommandPacket("dry-run");
    const mergedStatus = mergeSingleCommandPacketRunStatus(companionState.commandPacketStatus, run);
    companionState = {
      ...companionState,
      singleCommandPacketRun: run,
      commandPacketStatus: mergedStatus,
      lastResult: run.ok === false ? "Single command packet dry-run failed." : "Single command packet dry-run completed.",
    };
    await refreshDispatchState({ silent: true });
    companionState = {
      ...companionState,
      singleCommandPacketRun: run,
      commandPacketStatus: mergeSingleCommandPacketRunStatus(companionState.commandPacketStatus, run),
      lastResult: run.ok === false ? "Single command packet dry-run failed." : "Single command packet dry-run completed.",
    };
    render();
    toast("Dry-run completed", "wrapper summary와 dispatch metadata를 갱신했습니다.");
  } catch (error) {
    companionState = {
      ...companionState,
      singleCommandPacketRun: {
        ok: false,
        mode: "dry-run",
        externalWritesPerformed: false,
        workerRunPerformed: false,
        privateValuesPrinted: false,
        rawPrivateBodyRead: false,
      },
      lastResult: error?.message || "Single command packet dry-run failed.",
    };
    render();
    toast("Dry-run failed");
  }
}

function mergeSingleCommandPacketRunStatus(currentStatus, run) {
  const summary = run?.summary || {};
  const latestRun = {
    ...(currentStatus?.latestRun || {}),
    runDir: summary.runDir || currentStatus?.latestRun?.runDir || "",
    runId: summary.runId || run?.runId || currentStatus?.latestRun?.runId || "",
    mode: summary.mode || run?.mode || currentStatus?.latestRun?.mode || "",
    selectedCaptureId: summary.selectedCaptureId || currentStatus?.latestRun?.selectedCaptureId || "",
    queuedCount: Number(summary.queuedCount ?? currentStatus?.latestRun?.queuedCount ?? currentStatus?.queueCount ?? 0),
    externalWritesPerformed: Boolean(summary.externalWritesPerformed ?? run?.externalWritesPerformed),
    workerRunPerformed: Boolean(summary.workerRunPerformed ?? run?.workerRunPerformed),
    pendingExternalWriteCount: Number(summary.pendingExternalWriteCount ?? currentStatus?.latestRun?.pendingExternalWriteCount ?? 0),
    privateValuesPrinted: false,
    rawPrivateBodyRead: false,
    readable: true,
  };
  const queueCount = Number(summary.queuedCount ?? currentStatus?.queueCount ?? 0);
  const merged = {
    ...(currentStatus || {}),
    queueCount,
    latestRun,
    privateValuesPrinted: false,
    rawPrivateBodyRead: false,
    responsePolicy: currentStatus?.responsePolicy || "metadata-only",
  };
  if (!merged.stage || !merged.stageLabel || !Array.isArray(merged.stageSteps)) {
    const record = merged.latestDispatch || null;
    merged.stage = commandPacketStageKey(record, latestRun, queueCount);
    merged.stageLabel = commandPacketStageLabelForKey(merged.stage);
    merged.stageSteps = commandPacketStageSteps(record, queueCount);
  }
  return merged;
}

function commandPacketStageKey(record, latestRun = {}, queueCount = 0) {
  if (record?.taskStatus === "worker_done") return "review_ready";
  if (record?.workerResultSet || record?.workerStatus) return "worker_result";
  if (record?.discordThreadSet) return "worker_thread";
  if (record?.githubIssueSet) return "ledger_ready";
  if (queueCount > 0) return "queued";
  if (latestRun.message === "queue_empty" || queueCount === 0) return "idle";
  return "unknown";
}

function commandPacketStageLabelForKey(stage) {
  const labels = {
    idle: "Idle",
    queued: "Queued",
    ledger_ready: "Ledger ready",
    worker_thread: "Worker thread",
    worker_result: "Worker result",
    review_ready: "Review ready",
    unknown: "Unknown",
  };
  return labels[stage] || "Unknown";
}

function disconnectCompanion() {
  window.PNHCompanionBridge?.disconnect?.();
  companionState = {
    ...companionState,
    paired: false,
    dispatchState: null,
    commandPacketStatus: null,
    singleCommandPacketRun: null,
    lastResult: "Disconnected. No browser session token is retained.",
  };
  render();
  toast("Companion disconnected");
}

function toggleScreenshotRedaction() {
  companionState = {
    ...companionState,
    screenshotRedaction: !companionState.screenshotRedaction,
    lastResult: companionState.screenshotRedaction
      ? "Screenshot redaction disabled."
      : "Screenshot redaction enabled for sensitive launch text.",
  };
  syncScreenshotRedaction();
  render();
  toast(companionState.screenshotRedaction ? "Redaction enabled" : "Redaction disabled");
}

function latestLaunchPacket() {
  return state.launches
    .filter((launch) => launch.status !== "archived")
    .slice()
    .sort((a, b) => b.updatedAt.localeCompare(a.updatedAt))[0];
}

function companionPayloadForLaunch(launch) {
  return {
    id: `launch-packet-${launch.id}`,
    source: "mobile_web",
    kind: launch.commandType || "project_brief",
    title: `${commandTypeLabel(launch.commandType)}: ${launch.title}`,
    body: buildLaunchPacket(launch),
    sensitivity: launch.sensitivity === "private-sensitive" ? "highly_sensitive" : "internal",
    createdAt: nowISO(),
    payloadType: "pnh_mobile_command_packet",
    commandType: launch.commandType || "project_brief",
    commandStatus: "queued",
    dispatchState: "not_dispatched",
  };
}

async function sendLatestLaunchToCompanion() {
  const bridge = window.PNHCompanionBridge;
  const launch = latestLaunchPacket();
  if (!launch) {
    toast("No launch packet", "먼저 dispatch packet을 생성하세요.");
    return;
  }
  if (!bridge?.sendLaunchPacket || !bridge.isPaired()) {
    toast("Companion not paired", "pairing code로 연결한 뒤 전송하세요.");
    return;
  }
  try {
    const sendCommand = bridge.sendMobileCommandPacket || bridge.sendLaunchPacket;
    const result = await sendCommand(companionPayloadForLaunch(launch));
    companionState = {
      ...companionState,
      online: true,
      paired: true,
      lastResult: captureSendResultMessage(result, "Latest mobile command packet"),
    };
    launch.commandStatus = result.writesPerformed ? "stored" : "send_failed";
    launch.dispatchState = "not_dispatched";
    launch.workspaceSentAt = nowISO();
    launch.workspaceCaptureId = result.captureId;
    launch.updatedAt = nowISO();
    writeStoredState();
    render();
    toast("Command packet stored", result.autoDispatch?.requested ? "Workspace dispatch가 background로 시작됐습니다." : "Local companion private inbox에 metadata-only 응답으로 저장했습니다.");
  } catch (error) {
    companionState = {
      ...companionState,
      lastResult: error?.message || "Send failed.",
    };
    render();
    toast("Send failed", "companion 상태와 pairing을 확인하세요.");
  }
}

function captureSendResultMessage(result, label) {
  if (!result?.writesPerformed) return "Companion responded without a private write.";
  if (result.autoDispatch?.requested) return `${label} stored and workspace dispatch started.`;
  return `${label} stored in private inbox.`;
}

function handleLaunchSubmit(event) {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(event.currentTarget).entries());
  const title = String(data.title || "").trim();
  const objective = String(data.objective || "").trim();
  if (!title || !objective) {
    toast("Launch brief incomplete", "Project title과 objective는 필수입니다.");
    return;
  }

  const launch = {
    id: uid("launch"),
    title,
    commandType: data.commandType || "project_brief",
    objective,
    desiredOutcome: String(data.desiredOutcome || "").trim(),
    constraints: String(data.constraints || "").trim(),
    deadline: data.deadline || "",
    priority: data.priority || "medium",
    sensitivity: data.sensitivity || "internal",
    deliveryTarget: data.deliveryTarget || "local_packet",
    status: "draft",
    commandStatus: "queued",
    dispatchState: "not_dispatched",
    createdProjectId: "",
    createdTaskIds: [],
    createdAt: nowISO(),
    updatedAt: nowISO(),
  };

  state.launches.unshift(launch);
  activeView = "launch";
  event.currentTarget.reset();
  persist("Dispatch packet created", "Launch 화면에서 copy/export 또는 local start를 선택하세요.");
}

function loadLaunchDemo() {
  const title = document.querySelector("#launch-field-title");
  const objective = document.querySelector("#launch-field-objective");
  const desiredOutcome = document.querySelector("#launch-field-desiredOutcome");
  const constraints = document.querySelector("#launch-field-constraints");
  const priority = document.querySelector("#launch-field-priority");
  const sensitivity = document.querySelector("#launch-field-sensitivity");
  const target = document.querySelector("#launch-field-deliveryTarget");
  if (title) title.value = "PNH 모바일 착수 자동화";
  if (objective) objective.value = "모바일에서 작성한 프로젝트 개요를 작업 팀이 바로 실행할 수 있는 착수 패킷으로 변환한다.";
  if (desiredOutcome) desiredOutcome.value = "작업 범위, acceptance criteria, 초기 tasks, QA/security gates, Discord/GitHub 전달 초안이 생성된다.";
  if (constraints) constraints.value = "실제 민감 데이터, 외부 전송, live OpenClaw 실행, GitHub issue 생성은 아직 하지 않는다.";
  if (priority) priority.value = "high";
  if (sensitivity) sensitivity.value = "internal";
  if (target) target.value = "discord_draft";
  const commandType = document.querySelector("#launch-field-commandType");
  if (commandType) commandType.value = "project_brief";
  toast("Demo brief loaded");
}

function launchPacketCard(launch) {
  const card = itemShell(launch.title);
  const title = card.querySelector(".item-title");
  if (title) sensitive(title);
  card.append(
    metaRow(
      [
        commandTypeLabel(launch.commandType),
        launch.commandStatus || "queued",
        launch.dispatchState || "not_dispatched",
        launch.status,
        launch.priority,
        launch.sensitivity,
        launch.deliveryTarget,
        launch.deadline,
      ],
      launch.priority
    )
  );
  card.append(sensitive(make("p", "", launch.objective)));
  if (launch.desiredOutcome) card.append(sensitive(make("p", "", `Outcome: ${launch.desiredOutcome}`)));
  if (launch.constraints) card.append(sensitive(make("p", "", `Constraints: ${launch.constraints}`)));

  const packetPreview = make("pre", "packet-preview", buildLaunchPacket(launch));
  card.append(sensitive(packetPreview));

  const actions = make("div", "item-actions");
  actions.append(button("Copy Packet", () => copyAssistantText(buildLaunchPacket(launch)), "small-button"));
  actions.append(button("Copy Discord Draft", () => copyAssistantText(buildDiscordDispatchDraft(launch)), "small-button"));
  actions.append(button("Copy GitHub Issue", () => copyAssistantText(buildGithubIssueDraft(launch)), "small-button"));
  actions.append(button("Start Locally", () => startLaunchLocally(launch.id), "small-button"));
  actions.append(button("Archive", () => updateLaunchStatus(launch.id, "archived"), "small-button"));
  card.append(actions);

  if (launch.createdProjectId || launch.createdTaskIds?.length) {
    card.append(make("p", "fine-print", `Local start created project/tasks: ${[launch.createdProjectId, ...(launch.createdTaskIds || [])].filter(Boolean).length}`));
  }
  if (launch.workspaceSentAt) {
    card.append(make("p", "fine-print", `Workspace private inbox: ${launch.commandStatus || "stored"} at ${launch.workspaceSentAt}`));
  }
  if (launch.progressSyncedAt) {
    card.append(make("p", "fine-print", `Board progress synced at ${launch.progressSyncedAt}`));
  }
  const dispatchRecord = dispatchRecordForLaunch(launch);
  if (dispatchRecord) {
    const mappedDispatchState = dispatchRecordLabel(dispatchRecord);
    const stage = commandPacketStageLabel(dispatchRecord);
    const statusLine = [
      `Stage: ${stage}`,
      `Dispatch mapping: ${mappedDispatchState}`,
      dispatchRecord.githubIssueNumber ? `GitHub #${dispatchRecord.githubIssueNumber}` : "",
      dispatchRecord.discordThreadId ? `Discord ${dispatchRecord.discordThreadId}` : "",
      dispatchRecord.workerResultSet ? `Worker ${dispatchRecord.workerStatus || "recorded"}` : "",
      dispatchRecord.taskStatus ? `Task ${dispatchRecord.taskStatus}` : "",
      dispatchRecord.evidenceCompleteness !== undefined ? `Evidence ${dispatchRecord.evidenceCompleteness}%` : "",
      dispatchRecord.updatedAt ? `updated ${dispatchRecord.updatedAt}` : "",
    ]
      .filter(Boolean)
      .join(" · ");
    card.append(make("p", "fine-print", statusLine));
    if (dispatchRecord.nextAction) {
      card.append(make("p", "fine-print", `Next action: ${dispatchRecord.nextAction}`));
    }
    if (launch.dispatchState !== mappedDispatchState || !launch.dispatchConfirmedAt) {
      const confirmActions = make("div", "item-actions");
      confirmActions.append(button("Confirm Mapping", () => confirmDispatchMappingForLaunch(launch.id), "small-button"));
      card.append(confirmActions);
    } else {
      card.append(make("p", "fine-print", `Dispatch mapping confirmed at ${launch.dispatchConfirmedAt}`));
    }
    if (dispatchRecord.taskStatus && (launch.taskStatus !== dispatchRecord.taskStatus || !launch.taskStatusConfirmedAt)) {
      const statusActions = make("div", "item-actions");
      statusActions.append(button("Confirm Task Status", () => confirmTaskStatusForLaunch(launch.id), "small-button"));
      card.append(statusActions);
    } else if (launch.taskStatusConfirmedAt) {
      card.append(make("p", "fine-print", `Task status confirmed at ${launch.taskStatusConfirmedAt}`));
    }
  }
  return card;
}

function buildLaunchPacket(launch) {
  const criteria = launchAcceptanceCriteria(launch);
  const lanes = launchLanes(launch);
  return [
    `# Project Dispatch Packet`,
    ``,
    `ID: ${launch.id}`,
    `Title: ${launch.title}`,
    `Command Type: ${commandTypeLabel(launch.commandType)} (${launch.commandType || "project_brief"})`,
    `Priority: ${launch.priority}`,
    `Sensitivity: ${launch.sensitivity}`,
    `Target: ${launch.deliveryTarget}`,
    `Deadline: ${launch.deadline || "not set"}`,
    ``,
    `## Objective`,
    launch.objective,
    ``,
    `## Desired Outcome`,
    launch.desiredOutcome || "Define expected outcome before implementation.",
    ``,
    `## Constraints`,
    launch.constraints || "No extra constraints recorded.",
    ``,
    `## Acceptance Criteria`,
    ...criteria.map((item, index) => `${index + 1}. ${item}`),
    ``,
    `## Suggested Lanes`,
    ...lanes.map((item) => `- ${item}`),
    ``,
    `## Approval Gates`,
    ...launchApprovalGates(launch).map((item) => `- ${item}`),
    ``,
    `## Next Action`,
    `Create a task packet, confirm scope, and start with the smallest safe implementation slice.`,
  ].join("\n");
}

function buildDiscordDispatchDraft(launch) {
  return [
    `/task create`,
    `title: ${launch.title}`,
    `command_type: ${launch.commandType || "project_brief"}`,
    `priority: ${launch.priority}`,
    `sensitivity: ${launch.sensitivity}`,
    `objective: ${launch.objective}`,
    `outcome: ${launch.desiredOutcome || "TBD"}`,
    `constraints: ${launch.constraints || "none recorded"}`,
    `approval: ${launchApprovalGates(launch).join("; ")}`,
    ``,
    `/agent spawn supervisor-orchestrator`,
    `Use the packet above. Route architect, implementer, reviewer, QA, security, and delivery lanes only when they reduce risk or critical path.`,
  ].join("\n");
}

function buildGithubIssueDraft(launch) {
  return [
    `# ${launch.title}`,
    ``,
    `Command type: ${commandTypeLabel(launch.commandType)}`,
    ``,
    `## Objective`,
    launch.objective,
    ``,
    `## Desired Outcome`,
    launch.desiredOutcome || "TBD",
    ``,
    `## Acceptance Criteria`,
    ...launchAcceptanceCriteria(launch).map((item) => `- [ ] ${item}`),
    ``,
    `## Constraints`,
    launch.constraints || "None recorded.",
    ``,
    `## Suggested Lanes`,
    ...launchLanes(launch).map((item) => `- ${item}`),
    ``,
    `## Approval Gates`,
    ...launchApprovalGates(launch).map((item) => `- ${item}`),
  ].join("\n");
}

function launchAcceptanceCriteria(launch) {
  const criteria = [
    "Scope and out-of-scope are explicit before implementation.",
    "Implementation produces a reviewable diff or documented no-code outcome.",
    "Validation commands or manual checks are recorded.",
    "Security/privacy risks are checked before delivery.",
    launch.desiredOutcome ? `Delivered outcome matches: ${launch.desiredOutcome}` : "Expected outcome is clarified before work starts.",
  ];
  if (launch.commandType === "urgent_approval") {
    criteria.unshift("Approval decision, deadline, and risk of delay are explicit before action.");
  }
  if (launch.commandType === "daily_command") {
    criteria.unshift("Daily command is converted into a bounded task list or status update.");
  }
  return criteria;
}

function launchLanes(launch) {
  const lanes = ["architect/planner", "implementer", "reviewer", "QA"];
  if (launch.sensitivity !== "public-demo") lanes.push("security");
  if (launch.deliveryTarget !== "local_packet") lanes.push("delivery-manager");
  return lanes;
}

function launchApprovalGates(launch) {
  const gates = ["scope approval before broad implementation", "release-readiness before delivery"];
  if (launch.sensitivity === "private-sensitive") {
    gates.push("explicit approval before handling private data");
    gates.push("no screenshots/logs with private values");
  }
  if (launch.deliveryTarget !== "local_packet") {
    gates.push("explicit approval before external dispatch or live automation");
  }
  if (launch.commandType === "urgent_approval") {
    gates.push("human supervisor decision required before irreversible action");
  }
  return gates;
}

function startLaunchLocally(id) {
  const launch = state.launches.find((item) => item.id === id);
  if (!launch) return;
  if (launch.createdTaskIds?.length) {
    launch.status = "started";
    launch.updatedAt = nowISO();
    persist("Launch already started", "중복 task 생성을 막았습니다. 기존 Projects/Tasks를 확인하세요.");
    return;
  }
  let projectId = launch.createdProjectId;
  if (!projectId) {
    projectId = uid("project");
    state.projects.unshift({
      id: projectId,
      title: launch.title,
      status: "active",
      priority: launch.priority,
      summary: launch.objective,
      nextAction: "Review dispatch packet and confirm first implementation slice",
      tags: ["launch", "dispatch"],
      createdAt: nowISO(),
      updatedAt: nowISO(),
    });
    launch.createdProjectId = projectId;
  }

  const taskTemplates = [
    ["Clarify scope and out-of-scope", "architect"],
    ["Create implementation plan", "architect"],
    ["Execute first safe slice", "implementer"],
    ["Review diff and evidence", "reviewer"],
    ["Run QA and release-readiness", "qa"],
  ];
  const created = [];
  taskTemplates.forEach(([title, tag]) => {
    const taskId = uid("task");
    state.tasks.unshift({
      id: taskId,
      title: `${launch.title}: ${title}`,
      status: tag === "architect" ? "today" : "inbox",
      priority: launch.priority,
      dueDate: launch.deadline || "",
      projectId,
      notes: buildLaunchPacket(launch).slice(0, 900),
      tags: ["launch", tag],
      createdAt: nowISO(),
      updatedAt: nowISO(),
    });
    created.push(taskId);
  });
  launch.createdTaskIds = [...(launch.createdTaskIds || []), ...created];
  launch.status = "started";
  launch.updatedAt = nowISO();
  persist("Launch started locally", "Projects와 Tasks에 초기 작업 단위를 생성했습니다.");
}

function updateLaunchStatus(id, status) {
  const launch = state.launches.find((item) => item.id === id);
  if (!launch) return;
  launch.status = status;
  launch.updatedAt = nowISO();
  persist("Launch updated");
}

function renderAssistant() {
  appView.append(
    viewHeader(
      "Assistant control page",
      "수동 입력을 local-only assistant inbox에 넣고, 로컬 rule로 작업 기록, 할 일, 일별 요약, 알림 초안을 만듭니다.",
      "Refresh Inbox",
      refreshAssistant
    )
  );

  const workflow = make("section", "assistant-workflow");
  workflow.append(
    assistantLane("Input routes", ASSISTANT_SOURCES.map(sourceLabel), "수동 paste/import만 허용"),
    assistantLane("Local processing", ["중복/노이즈 줄이기", "rule-based 분류", "검토 후 반영", "주간/월간 회고 재료"], "외부 API 없음"),
    assistantLane("Output drafts", ["작업 기록", "할 일 목록", "일별 요약", "Slack-style 알림", "Calendar draft"], "복사/다운로드 중심")
  );
  appView.append(workflow);

  const topGrid = make("section", "content-grid");
  topGrid.append(assistantCapturePanel(), assistantWorkspacePanel(), assistantBiblePanel());
  appView.append(topGrid);

  const suggestions = buildAssistantSuggestions();
  const reviewGrid = make("section", "content-grid three");
  reviewGrid.append(
    panel("Inbox", assistantState.captures.slice(0, 8), assistantCaptureCard, "assistant inbox가 비어 있습니다."),
    panel("Suggested Outputs", suggestions.slice(0, 8), assistantSuggestionCard, "입력을 추가하면 제안이 표시됩니다."),
    panel("Daily Summary", assistantBriefCards(), assistantBriefCard, "오늘 처리할 assistant context가 없습니다.")
  );
  appView.append(reviewGrid);
}

function sourceLabel(source) {
  const labels = {
    slack: "Slack",
    email: "Email",
    sms: "SMS",
    kakao: "KakaoTalk",
    call: "Call",
    voice_memo: "Voice memo",
    my_memo: "My memo",
    youtube: "YouTube",
    bible: "Bible verse",
  };
  return labels[source] || source;
}

function assistantLane(title, items, note) {
  const lane = make("article", "assistant-lane");
  lane.append(make("p", "eyebrow", note));
  lane.append(make("h3", "", title));
  const list = make("div", "route-list");
  items.forEach((item) => list.append(make("span", "route-pill", item)));
  lane.append(list);
  return lane;
}

function captureSource(capture) {
  return capture.source || capture.sourceType || "my_memo";
}

function captureStatus(capture) {
  return capture.status || "inbox";
}

function assistantStorageLabel() {
  if (assistantState.persistent) return "IndexedDB ready";
  if (assistantState.ready) return "Session fallback";
  return "Storage pending";
}

function assistantCapturePanel() {
  const section = make("section", "section-panel assistant-capture-panel");
  const header = make("div", "section-header");
  header.append(make("h3", "", "Manual input"));
  header.append(badge(assistantStorageLabel()));
  section.append(header);

  const form = make("form", "assistant-form");
  const source = document.createElement("select");
  source.name = "source";
  ASSISTANT_SOURCES.forEach((value) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = sourceLabel(value);
    source.append(option);
  });

  const title = document.createElement("input");
  title.name = "title";
  title.type = "text";
  title.placeholder = "제목 또는 한 줄 요약";

  const body = document.createElement("textarea");
  body.name = "body";
  body.placeholder = "Slack, 이메일, 문자, 카톡, 통화 메모, 음성메모 전사, 유튜브 메모, 성경 말씀을 직접 붙여넣으세요.";

  const dispatchIntent = document.createElement("select");
  dispatchIntent.name = "dispatchIntent";
  ASSISTANT_DISPATCH_INTENTS.forEach((value) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = assistantDispatchIntentLabel(value);
    dispatchIntent.append(option);
  });
  dispatchIntent.value = "task_request";

  const actions = make("div", "form-actions");
  const submit = make("button", "primary-button", "Add to assistant");
  submit.type = "submit";
  actions.append(submit, button("Load demo fixture", loadAssistantFixture, "ghost-button"));
  form.append(source, title, body, dispatchIntent, actions);
  form.addEventListener("submit", handleAssistantCapture);
  section.append(form);

  const warning = make("p", "fine-print", "실제 연락처, 통화기록, 녹음파일, 토큰, 고객 데이터는 repo나 evidence에 넣지 마세요. 이 MVP는 수동 입력/fixture 전용입니다.");
  section.append(warning);
  return section;
}

function assistantWorkspacePanel() {
  const section = make("section", "section-panel assistant-workspace-panel");
  const header = make("div", "section-header");
  header.append(make("h3", "", "Workspace ingress"));
  header.append(badge(companionStatusLabel(), companionState.online ? "status-online" : "status-offline"));
  section.append(header);

  const status = make("div", "companion-status");
  status.append(make("p", "", companionState.statusText));
  if (companionState.lastResult) status.append(make("p", "fine-print", companionState.lastResult));
  section.append(status);

  const form = make("form", "companion-form");
  const label = document.createElement("label");
  label.htmlFor = "assistant-companion-pair-code";
  label.textContent = "Pairing code";
  const input = document.createElement("input");
  input.id = "assistant-companion-pair-code";
  input.name = "pairingCode";
  input.type = "text";
  input.inputMode = "text";
  input.autocomplete = "off";
  input.placeholder = "One-time code";
  sensitive(input);
  const actions = make("div", "form-actions");
  const pairButton = make("button", "primary-button", companionState.paired ? "Paired" : "Pair");
  pairButton.type = "submit";
  pairButton.disabled = companionState.paired;
  actions.append(
    pairButton,
    button("Check", checkCompanionStatus, "ghost-button"),
    button("Disconnect", disconnectCompanion, "ghost-button"),
    button(companionState.screenshotRedaction ? "Show Screen" : "Redact Screen", toggleScreenshotRedaction, "ghost-button")
  );
  form.append(label, input, actions);
  form.addEventListener("submit", pairCompanion);
  section.append(form);

  const latest = latestAssistantCapture();
  const send = button("Send Latest Input", sendLatestAssistantToCompanion, "small-button");
  send.disabled = !latest || !companionState.paired;
  const sendRow = make("div", "item-actions");
  sendRow.append(send);
  if (latest) {
    sendRow.append(sensitive(make("span", "fine-print", latest.title || sourceLabel(captureSource(latest)))));
  } else {
    sendRow.append(make("span", "fine-print", "Add an assistant input first."));
  }
  section.append(sendRow);
  section.append(make("p", "fine-print", "Synthetic or low-risk input only. The browser session token stays in memory and workspace responses stay metadata-only."));
  return section;
}

function assistantBiblePanel() {
  const section = make("section", "section-panel bible-panel");
  const verse = getBibleVerse();
  section.append(make("p", "eyebrow", "Today Bible Verse"));
  section.append(make("h3", "", verse.reference));
  section.append(make("p", "", verse.text));
  section.append(make("p", "fine-print", "고정된 demo 말씀 목록에서 날짜별로 표시합니다."));
  return section;
}

function getBibleVerse() {
  if (window.PNHAssistantRules?.bibleVerseForToday) {
    return window.PNHAssistantRules.bibleVerseForToday(new Date());
  }
  return {
    reference: "Proverbs 16:3",
    text: "Commit your work to the Lord, and your plans will be established.",
  };
}

async function handleAssistantCapture(event) {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(event.currentTarget).entries());
  if (!String(data.title || "").trim() && !String(data.body || "").trim()) {
    toast("Assistant input is empty", "내용을 입력한 뒤 추가하세요.");
    return;
  }
  const normalizer = window.PNHAssistantImport?.normalizeManualCapture || fallbackNormalizeCapture;
  let capture;
  try {
    capture = normalizer({
      source: data.source,
      dispatchIntent: data.dispatchIntent,
      title: data.title,
      body: data.body,
      receivedAt: nowISO(),
    });
  } catch (error) {
    toast("Assistant input rejected", error?.message || "입력 형식을 확인하세요.");
    return;
  }
  if (!capture.body && !capture.title) {
    toast("Assistant input is empty", "내용을 입력한 뒤 추가하세요.");
    return;
  }
  await saveAssistantCapture(capture);
  event.currentTarget.reset();
}

function fallbackNormalizeCapture(input) {
  return {
    id: uid("capture"),
    source: input.source || "my_memo",
    dispatchIntent: normalizeAssistantDispatchIntent(input.dispatchIntent),
    title: String(input.title || "").trim() || sourceLabel(input.source || "my_memo"),
    body: String(input.body || "").trim(),
    receivedAt: input.receivedAt || nowISO(),
    priority: "medium",
    status: "inbox",
    tags: [],
    createdAt: nowISO(),
    updatedAt: nowISO(),
  };
}

function normalizeAssistantDispatchIntent(value) {
  const intent = String(value || "assistant_capture").trim();
  return ASSISTANT_DISPATCH_INTENTS.includes(intent) ? intent : "assistant_capture";
}

async function saveAssistantCapture(capture) {
  if (!window.PNHAssistantStorage?.addCapture) {
    assistantState.captures.unshift(capture);
  } else {
    await window.PNHAssistantStorage.addCapture(capture);
    assistantState.captures = await window.PNHAssistantStorage.listCaptures();
    const status = window.PNHAssistantStorage.getStatus?.();
    assistantState.ready = Boolean(status?.ready);
    assistantState.persistent = Boolean(status?.persistent);
    assistantState.error = status?.error || "";
  }
  render();
  toast(
    "Assistant input saved",
    assistantState.persistent ? "IndexedDB assistant inbox에 저장했습니다." : "현재 세션 fallback에 저장했습니다. 브라우저 저장소 권한을 확인하세요."
  );
}

async function refreshAssistant() {
  await loadAssistantCaptures();
  render();
  toast("Assistant refreshed");
}

async function loadAssistantCaptures() {
  try {
    if (!window.PNHAssistantStorage?.init) {
      assistantState.ready = false;
      assistantState.persistent = false;
      return;
    }
    const status = await window.PNHAssistantStorage.init();
    assistantState.captures = await window.PNHAssistantStorage.listCaptures();
    assistantState.ready = Boolean(status?.ready);
    assistantState.persistent = Boolean(status?.persistent);
    assistantState.error = status?.error || "";
  } catch (error) {
    assistantState.ready = false;
    assistantState.persistent = false;
    assistantState.error = error?.name || "AssistantStorageError";
  }
}

async function updateAssistantCapture(id, patch, message = "Assistant item updated") {
  const local = assistantState.captures.find((capture) => capture.id === id);
  if (local) Object.assign(local, patch, { updatedAt: nowISO() });
  if (window.PNHAssistantStorage?.updateCapture) {
    await window.PNHAssistantStorage.updateCapture(id, patch);
    assistantState.captures = await window.PNHAssistantStorage.listCaptures();
  }
  render();
  toast(message);
}

function buildAssistantSuggestions() {
  const rawSuggestions = window.PNHAssistantRules?.buildSuggestions
    ? window.PNHAssistantRules.buildSuggestions(assistantState.captures)
    : assistantState.captures.map((capture) => ({
    id: `suggestion-${capture.id}`,
    captureId: capture.id,
    suggestionType: "note",
    title: capture.title,
    body: capture.body,
    confidence: "low",
    status: "pending",
    payload: {},
  }));

  return rawSuggestions.map((suggestion, index) => ({
    id: suggestion.id || `suggestion-${index + 1}`,
    captureId: suggestion.captureId || "",
    suggestionType: suggestion.suggestionType || suggestion.type || "note",
    title: suggestion.title || "Assistant suggestion",
    body: suggestion.body || suggestion.reason || "",
    confidence: suggestion.confidence || "medium",
    status: suggestion.status || "pending",
    payload: {
      priority: suggestion.priority,
      dueDate: suggestion.dueDate,
      ...(suggestion.payload || {}),
    },
  }));
}

function buildAssistantBrief() {
  if (window.PNHAssistantRules?.buildDailyBrief) {
    const brief = window.PNHAssistantRules.buildDailyBrief(assistantState.captures, state.tasks);
    return {
      title: brief.title || brief.focus || "Assistant daily brief",
      body:
        brief.body ||
        [
          `${brief.counts?.captures || 0} assistant inputs`,
          `${brief.counts?.todayTasks || 0} today tasks`,
          ...(brief.reviewPrompts || []),
        ].join(" · "),
      cards: (brief.topSuggestions || []).map((suggestion) => ({
        title: suggestion.title,
        body: suggestion.reason || suggestion.body || "",
        type: suggestion.type || "assistant",
      })),
    };
  }
  return {
    title: "Start with assistant inbox",
    body: "오늘 들어온 입력을 assistant에 모으면 작업 기록, 할 일, 요약 초안으로 정리할 수 있습니다.",
    cards: [],
  };
}

function assistantBriefCards() {
  const brief = buildAssistantBrief();
  return [
    { title: brief.title, body: brief.body, type: "Daily" },
    ...(brief.cards || []),
  ];
}

function assistantBriefCard(item) {
  const card = itemShell(item.title);
  card.append(metaRow([item.type || "assistant"]));
  card.append(make("p", "", item.body || ""));
  return card;
}

function assistantCaptureCard(capture) {
  const card = itemShell(capture.title || sourceLabel(captureSource(capture)));
  card.append(metaRow([sourceLabel(captureSource(capture)), assistantDispatchIntentLabel(capture.dispatchIntent), captureStatus(capture), capture.priority, ...(capture.tags || [])], capture.priority));
  if (capture.body) card.append(sensitive(make("p", "", capture.body.slice(0, 220))));
  const actions = make("div", "item-actions");
  actions.append(button("Send to Workspace", () => sendAssistantCaptureToCompanion(capture), "small-button"));
  actions.append(button("Processed", () => updateAssistantCapture(capture.id, { status: "processed" }, "Marked processed"), "small-button"));
  actions.append(button("Archive", () => updateAssistantCapture(capture.id, { status: "archived" }, "Archived"), "small-button"));
  card.append(actions);
  return card;
}

function latestAssistantCapture() {
  return assistantState.captures
    .filter((capture) => captureStatus(capture) !== "archived")
    .slice()
    .sort((a, b) => String(b.updatedAt || b.receivedAt || b.createdAt || "").localeCompare(String(a.updatedAt || a.receivedAt || a.createdAt || "")))[0];
}

function companionPayloadForAssistantCapture(capture) {
  const title = String(capture.title || sourceLabel(captureSource(capture))).trim();
  const body = String(capture.body || title).trim();
  const dispatchIntent = normalizeAssistantDispatchIntent(capture.dispatchIntent);
  const commandIntent = isCommandDispatchIntent(dispatchIntent);
  return {
    id: `assistant-capture-${capture.id}`,
    source: "mobile_web",
    kind: commandIntent ? dispatchIntent : "assistant_capture",
    title: commandIntent ? `${commandTypeLabel(dispatchIntent)}: ${title}` : `Assistant input: ${title}`,
    body,
    sensitivity: capture.sensitivity || "internal",
    createdAt: capture.receivedAt || capture.createdAt || nowISO(),
    payloadType: commandIntent ? "pnh_mobile_command_packet" : "pnh_assistant_capture",
    commandType: commandIntent ? dispatchIntent : undefined,
    commandStatus: commandIntent ? "queued" : undefined,
    dispatchState: commandIntent ? "not_dispatched" : undefined,
    assistantSource: captureSource(capture),
    assistantStatus: captureStatus(capture),
    assistantDispatchIntent: dispatchIntent,
    tags: capture.tags || [],
  };
}

async function sendLatestAssistantToCompanion() {
  const capture = latestAssistantCapture();
  if (!capture) {
    toast("No assistant input", "먼저 Assistant 입력을 추가하세요.");
    return;
  }
  await sendAssistantCaptureToCompanion(capture);
}

async function sendAssistantCaptureToCompanion(capture) {
  const bridge = window.PNHCompanionBridge;
  if (!bridge?.sendAssistantCapture || !bridge.isPaired()) {
    toast("Companion not paired", "pairing code로 연결한 뒤 전송하세요.");
    return;
  }
  try {
    const payload = companionPayloadForAssistantCapture(capture);
    const sendCommand = isCommandDispatchIntent(payload.commandType)
      ? bridge.sendMobileCommandPacket || bridge.sendAssistantCapture
      : bridge.sendAssistantCapture;
    const result = await sendCommand(payload);
    companionState = {
      ...companionState,
      online: true,
      paired: true,
      lastResult: captureSendResultMessage(result, assistantDispatchIntentLabel(payload.commandType || payload.kind)),
    };
    await updateAssistantCapture(capture.id, { workspaceSentAt: nowISO(), workspaceCaptureId: result.captureId }, "Assistant input sent to workspace");
  } catch (error) {
    companionState = {
      ...companionState,
      lastResult: error?.message || "Assistant send failed.",
    };
    render();
    toast("Send failed", "companion 상태와 pairing을 확인하세요.");
  }
}

function assistantSuggestionCard(suggestion) {
  const card = itemShell(suggestion.title);
  card.append(metaRow([suggestion.suggestionType, suggestion.confidence]));
  if (suggestion.body) card.append(make("p", "", suggestion.body.slice(0, 240)));
  const actions = make("div", "item-actions");
  if (suggestion.suggestionType === "task") {
    actions.append(button("Create Task", () => acceptAssistantTask(suggestion), "small-button"));
  } else if (suggestion.suggestionType === "calendar_event") {
    actions.append(button("Copy Calendar Draft", () => copyAssistantText(suggestion.body || suggestion.title), "small-button"));
  } else {
    actions.append(button("Create Note", () => acceptAssistantNote(suggestion), "small-button"));
  }
  actions.append(button("Copy", () => copyAssistantText(`${suggestion.title}\n${suggestion.body || ""}`), "small-button"));
  card.append(actions);
  return card;
}

function acceptAssistantTask(suggestion) {
  state.tasks.unshift({
    id: uid("task"),
    title: suggestion.title,
    status: "inbox",
    priority: suggestion.payload?.priority || "medium",
    dueDate: suggestion.payload?.dueDate || "",
    projectId: "",
    notes: suggestion.body || "",
    tags: ["assistant", suggestion.suggestionType],
    createdAt: nowISO(),
    updatedAt: nowISO(),
  });
  persist("Task created from assistant");
}

function acceptAssistantNote(suggestion) {
  state.notes.unshift({
    id: uid("note"),
    title: suggestion.title,
    body: suggestion.body || "",
    tags: ["assistant", suggestion.suggestionType],
    projectId: "",
    createdAt: nowISO(),
    updatedAt: nowISO(),
  });
  persist("Note created from assistant");
}

async function copyAssistantText(text) {
  try {
    await navigator.clipboard.writeText(text);
    toast("Copied", "출력 초안을 clipboard에 복사했습니다.");
  } catch {
    toast("Copy unavailable", "브라우저 권한 때문에 복사하지 못했습니다.");
  }
}

async function loadAssistantFixture() {
  const samples = [
    { source: "slack", title: "배포 전 확인", body: "오늘 오후 5시까지 release checklist 확인하고 blocker 있으면 공유해야 함" },
    { source: "youtube", title: "자동화 참고 영상", body: "https://example.com/demo 자동화 시스템 구성 아이디어 정리" },
    { source: "bible", title: "오늘의 말씀", body: getBibleVerse().text },
  ];
  const normalizer = window.PNHAssistantImport?.normalizeManualCapture || fallbackNormalizeCapture;
  for (const sample of samples) {
    await saveAssistantCapture(normalizer({ ...sample, receivedAt: nowISO() }));
  }
}

function quickCaptureForm() {
  const form = make("form", "quick-capture");
  const input = document.createElement("input");
  input.type = "text";
  input.placeholder = "Capture task, note, project, link";
  input.id = "quickCaptureInput";
  const select = document.createElement("select");
  ["task", "note", "project", "link"].forEach((value) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = value;
    select.append(option);
  });
  const button = make("button", "primary-button", "Add");
  button.type = "submit";
  form.append(input, select, button);
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const title = input.value.trim();
    if (!title) {
      toast("Capture is empty", "내용을 입력한 뒤 추가하세요.");
      return;
    }
    createQuickItem(select.value, title);
    input.value = "";
  });
  return form;
}

function createQuickItem(type, title) {
  if (type === "task") {
    state.tasks.unshift({
      id: uid("task"),
      title,
      status: "inbox",
      priority: "medium",
      dueDate: "",
      projectId: "",
      notes: "",
      tags: [],
      createdAt: nowISO(),
      updatedAt: nowISO(),
    });
  }
  if (type === "note") {
    state.notes.unshift({
      id: uid("note"),
      title,
      body: "",
      tags: [],
      projectId: "",
      createdAt: nowISO(),
      updatedAt: nowISO(),
    });
  }
  if (type === "project") {
    state.projects.unshift({
      id: uid("project"),
      title,
      status: "active",
      priority: "medium",
      summary: "",
      nextAction: "",
      tags: [],
      createdAt: nowISO(),
      updatedAt: nowISO(),
    });
  }
  if (type === "link") {
    state.links.unshift({
      id: uid("link"),
      title,
      url: "https://",
      category: "inbox",
      notes: "",
      createdAt: nowISO(),
      updatedAt: nowISO(),
    });
  }
  persist("Captured", `${type} added`);
}

function panel(title, items, cardRenderer, emptyText) {
  const section = make("section", "section-panel");
  const header = make("div", "section-header");
  header.append(make("h3", "", title));
  section.append(header);
  const list = make("div", "item-list");
  if (!items.length) {
    list.append(make("p", "empty-state", emptyText));
  } else {
    items.forEach((item) => list.append(cardRenderer(item)));
  }
  section.append(list);
  return section;
}

function renderProjects() {
  appView.append(
    viewHeader(
      "Projects",
      "목표, status, priority, next action을 한곳에서 정리하고 task/note와 연결합니다.",
      "New Project",
      () => openEditor("project")
    )
  );
  const filtered = state.projects.filter(matchesQuery);
  const grid = make("section", "content-grid");
  if (!filtered.length) {
    appView.append(make("p", "empty-state", "검색 조건에 맞는 project가 없습니다."));
    return;
  }
  filtered.forEach((project) => grid.append(projectCard(project)));
  appView.append(grid);
}

function renderTasks() {
  appView.append(
    viewHeader(
      "Task board",
      "Inbox, Today, Upcoming, Done 단계로 실행 단위를 관리합니다.",
      "New Task",
      () => openEditor("task")
    )
  );
  const board = make("section", "board");
  const columns = [
    ["inbox", "Inbox"],
    ["today", "Today"],
    ["upcoming", "Upcoming"],
    ["done", "Done"],
  ];
  columns.forEach(([status, title]) => {
    const column = make("div", "board-column");
    column.append(make("h3", "", title));
    const list = make("div", "item-list");
    const tasks = state.tasks.filter((task) => task.status === status && matchesQuery(task));
    if (!tasks.length) list.append(make("p", "empty-state", "No tasks"));
    tasks.forEach((task) => list.append(taskCard(task)));
    column.append(list);
    board.append(column);
  });
  appView.append(board);
}

function renderNotes() {
  appView.append(
    viewHeader(
      "Notes",
      "운영 메모, 의사결정, 아이디어를 프로젝트와 연결해 누적합니다.",
      "New Note",
      () => openEditor("note")
    )
  );
  const filtered = state.notes.filter(matchesQuery).sort((a, b) => b.updatedAt.localeCompare(a.updatedAt));
  const grid = make("section", "content-grid");
  if (!filtered.length) {
    appView.append(make("p", "empty-state", "검색 조건에 맞는 note가 없습니다."));
    return;
  }
  filtered.forEach((note) => grid.append(noteCard(note)));
  appView.append(grid);
}

function renderRoutines() {
  appView.append(
    viewHeader(
      "Routines",
      "반복 점검과 운영 루틴을 checklist로 관리합니다.",
      "New Routine",
      () => openEditor("routine")
    )
  );
  const grid = make("section", "content-grid");
  const filtered = state.routines.filter(matchesQuery);
  if (!filtered.length) {
    appView.append(make("p", "empty-state", "검색 조건에 맞는 routine이 없습니다."));
    return;
  }
  filtered.forEach((routine) => grid.append(routineCard(routine)));
  appView.append(grid);
}

function renderLinks() {
  appView.append(
    viewHeader(
      "Links",
      "자주 쓰는 문서, repo, dashboard를 category별로 모읍니다.",
      "New Link",
      () => openEditor("link")
    )
  );
  const grid = make("section", "content-grid");
  const filtered = state.links.filter(matchesQuery);
  if (!filtered.length) {
    appView.append(make("p", "empty-state", "검색 조건에 맞는 link가 없습니다."));
    return;
  }
  filtered.forEach((link) => grid.append(linkCard(link)));
  appView.append(grid);
}

function renderSettings() {
  appView.append(
    viewHeader(
      "Settings",
      "데이터 백업, 복원, 초기화, theme을 관리합니다. 실제 데이터는 이 브라우저에만 저장됩니다.",
      "",
      null
    )
  );

  const stack = make("section", "settings-stack");
  stack.append(settingsRow("Theme", "밝은 화면과 어두운 화면을 전환합니다.", themeToggleButton()));
  stack.append(settingsRow("Export JSON", "현재 hub 데이터와 assistant capture를 JSON 파일로 백업합니다.", button("Export Data", exportState)));
  stack.append(settingsRow("Import JSON", "백업 파일을 불러와 현재 데이터를 교체합니다.", importControl()));
  stack.append(settingsRow("Reset Data", "현재 브라우저의 hub 데이터를 seed 상태로 되돌립니다.", button("Reset", resetState, "danger-button")));
  stack.append(settingsRow("Public data warning", "GitHub Pages에는 앱 코드와 더미 데이터만 올리세요. 실제 개인 데이터, 고객 정보, 민감한 키는 커밋하지 않습니다.", make("span", "badge", "Local only")));
  appView.append(stack);
}

function settingsRow(title, description, control) {
  const row = make("div", "settings-row");
  const copy = make("div", "");
  copy.append(make("h3", "", title));
  copy.append(make("p", "", description));
  row.append(copy, control);
  return row;
}

function button(label, handler, className = "ghost-button") {
  const el = make("button", className, label);
  el.type = "button";
  el.addEventListener("click", handler);
  return el;
}

function themeToggleButton() {
  return button(state.settings.theme === "dark" ? "Use Light" : "Use Dark", () => {
    state.settings.theme = state.settings.theme === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = state.settings.theme;
    persist("Theme updated");
  });
}

function importControl() {
  const label = make("label", "ghost-button", "Import Data");
  const input = document.createElement("input");
  input.type = "file";
  input.accept = "application/json,.json";
  input.className = "hidden";
  input.addEventListener("change", handleImport);
  label.append(input);
  return label;
}

function projectCard(project) {
  const card = itemShell(project.title);
  card.append(metaRow([project.status, project.priority, ...(project.tags || [])], project.priority));
  if (project.summary) card.append(make("p", "", project.summary));
  if (project.nextAction) card.append(make("p", "", `Next: ${project.nextAction}`));
  const actions = make("div", "item-actions");
  actions.append(button("Edit", () => openEditor("project", project), "small-button"));
  actions.append(button("Task", () => openEditor("task", { projectId: project.id }), "small-button"));
  card.append(actions);
  return card;
}

function taskCard(task) {
  const card = itemShell(task.title);
  card.append(metaRow([task.status, task.priority, task.dueDate, projectTitle(task.projectId), ...(task.tags || [])], task.priority));
  if (task.notes) card.append(make("p", "", task.notes));
  const actions = make("div", "item-actions");
  actions.append(button(task.status === "done" ? "Reopen" : "Done", () => updateTaskStatus(task.id, task.status === "done" ? "inbox" : "done"), "small-button"));
  actions.append(button("Edit", () => openEditor("task", task), "small-button"));
  card.append(actions);
  return card;
}

function noteCard(note) {
  const card = itemShell(note.title);
  card.append(metaRow([projectTitle(note.projectId), ...(note.tags || [])]));
  if (note.body) card.append(make("p", "", note.body.slice(0, 220)));
  const actions = make("div", "item-actions");
  actions.append(button("Edit", () => openEditor("note", note), "small-button"));
  card.append(actions);
  return card;
}

function routineCard(routine) {
  const card = itemShell(routine.title);
  card.append(metaRow([routine.frequency, routine.lastCompletedAt ? `last ${routine.lastCompletedAt.slice(0, 10)}` : "not completed"]));
  if (routine.checklist?.length) {
    const list = make("p", "", routine.checklist.join(" · "));
    card.append(list);
  }
  const actions = make("div", "item-actions");
  actions.append(button("Complete", () => completeRoutine(routine.id), "small-button"));
  actions.append(button("Edit", () => openEditor("routine", routine), "small-button"));
  card.append(actions);
  return card;
}

function linkCard(link) {
  const card = itemShell(link.title);
  card.append(metaRow([link.category]));
  if (link.notes) card.append(make("p", "", link.notes));
  const actions = make("div", "item-actions");
  const safeUrl = normalizeHttpUrl(link.url);
  if (safeUrl) {
    const anchor = make("a", "small-button", "Open");
    anchor.href = safeUrl;
    anchor.target = "_blank";
    anchor.rel = "noopener noreferrer";
    actions.append(anchor);
  } else {
    const disabled = make("button", "small-button", "Invalid URL");
    disabled.type = "button";
    disabled.disabled = true;
    actions.append(disabled);
  }
  actions.append(button("Edit", () => openEditor("link", link), "small-button"));
  card.append(actions);
  return card;
}

function itemShell(title) {
  const card = make("article", "item-card");
  const top = make("div", "item-top");
  top.append(make("h3", "item-title", title));
  card.append(top);
  return card;
}

function metaRow(values, priority) {
  const row = make("div", "item-meta");
  values.filter(Boolean).forEach((value) => {
    const normalized = String(value).toLowerCase();
    let extra = "";
    if (["high", "medium", "low"].includes(normalized)) extra = `priority-${normalized}`;
    if (["done", "archived"].includes(normalized)) extra = `status-${normalized}`;
    row.append(badge(String(value), extra));
  });
  return row;
}

function updateTaskStatus(id, status) {
  const task = state.tasks.find((item) => item.id === id);
  if (!task) return;
  task.status = status;
  task.updatedAt = nowISO();
  persist("Task updated");
}

function completeRoutine(id) {
  const routine = state.routines.find((item) => item.id === id);
  if (!routine) return;
  routine.lastCompletedAt = nowISO();
  routine.updatedAt = nowISO();
  persist("Routine completed");
}

function openEditor(type, item = {}) {
  const isExisting = Boolean(item.id);
  const label = isExisting ? `Edit ${type}` : `New ${type}`;
  inspectorTitle.textContent = label;
  inspectorType.textContent = type;
  editorForm.replaceChildren();
  const fields = editorFields(type, item);
  fields.forEach((field) => editorForm.append(field));
  const actions = make("div", "form-actions");
  actions.append(button(isExisting ? "Save" : "Create", () => saveEditor(type, item.id), "primary-button"));
  if (isExisting) {
    actions.append(button("Delete", () => deleteItem(type, item.id), "danger-button"));
  }
  editorForm.append(actions);
  inspector.classList.add("is-open");
  const firstInput = editorForm.querySelector("input, textarea, select");
  if (firstInput) firstInput.focus();
}

function editorFields(type, item) {
  const common = [];
  if (type === "project") {
    common.push(
      field("title", "Title", "text", item.title || ""),
      field("status", "Status", "select", item.status || "active", ["active", "paused", "done", "archived"]),
      field("priority", "Priority", "select", item.priority || "medium", ["high", "medium", "low"]),
      field("summary", "Summary", "textarea", item.summary || ""),
      field("nextAction", "Next action", "text", item.nextAction || ""),
      field("tags", "Tags", "text", tagsToInput(item.tags))
    );
  }
  if (type === "task") {
    common.push(
      field("title", "Title", "text", item.title || ""),
      field("status", "Status", "select", item.status || "inbox", ["inbox", "today", "upcoming", "done"]),
      field("priority", "Priority", "select", item.priority || "medium", ["high", "medium", "low"]),
      field("dueDate", "Due date", "date", item.dueDate || ""),
      field("projectId", "Project", "select", item.projectId || "", projectOptions()),
      field("notes", "Notes", "textarea", item.notes || ""),
      field("tags", "Tags", "text", tagsToInput(item.tags))
    );
  }
  if (type === "note") {
    common.push(
      field("title", "Title", "text", item.title || ""),
      field("projectId", "Project", "select", item.projectId || "", projectOptions()),
      field("body", "Body", "textarea", item.body || ""),
      field("tags", "Tags", "text", tagsToInput(item.tags))
    );
  }
  if (type === "routine") {
    common.push(
      field("title", "Title", "text", item.title || ""),
      field("frequency", "Frequency", "select", item.frequency || "weekly", ["daily", "weekly", "monthly", "ad hoc"]),
      field("checklist", "Checklist", "textarea", (item.checklist || []).join("\n"))
    );
  }
  if (type === "link") {
    common.push(
      field("title", "Title", "text", item.title || ""),
      field("url", "URL", "url", item.url || "https://"),
      field("category", "Category", "text", item.category || "inbox"),
      field("notes", "Notes", "textarea", item.notes || "")
    );
  }
  return common;
}

function field(name, labelText, type, value, options = []) {
  const wrap = make("div", "field");
  const label = document.createElement("label");
  label.htmlFor = `field-${name}`;
  label.textContent = labelText;
  let control;
  if (type === "textarea") {
    control = document.createElement("textarea");
    control.value = value;
  } else if (type === "select") {
    control = document.createElement("select");
    options.forEach((optionValue) => {
      const option = document.createElement("option");
      if (typeof optionValue === "object") {
        option.value = optionValue.value;
        option.textContent = optionValue.label;
      } else {
        option.value = optionValue;
        option.textContent = optionValue || "None";
      }
      control.append(option);
    });
    control.value = value;
  } else {
    control = document.createElement("input");
    control.type = type;
    control.value = value;
  }
  control.name = name;
  control.id = `field-${name}`;
  wrap.append(label, control);
  return wrap;
}

function projectOptions() {
  return [{ value: "", label: "None" }, ...state.projects.map((project) => ({ value: project.id, label: project.title }))];
}

function tagsToInput(tags) {
  return Array.isArray(tags) ? tags.join(", ") : "";
}

function inputToTags(value) {
  return value
    .split(",")
    .map((tag) => tag.trim())
    .filter(Boolean);
}

function saveEditor(type, id) {
  const data = Object.fromEntries(new FormData(editorForm).entries());
  if (!data.title?.trim()) {
    toast("Title required", "저장하려면 title을 입력하세요.");
    return;
  }
  if (type === "link" && !normalizeHttpUrl(data.url)) {
    toast("Invalid URL", "http 또는 https URL만 저장할 수 있습니다.");
    return;
  }
  const collectionName = `${type}s`;
  const collection = state[collectionName];
  if (!Array.isArray(collection)) return;
  const existing = collection.find((item) => item.id === id);
  const prepared = prepareItem(type, data, existing);
  if (existing) {
    Object.assign(existing, prepared, { updatedAt: nowISO() });
  } else {
    collection.unshift({
      ...prepared,
      id: uid(type),
      createdAt: nowISO(),
      updatedAt: nowISO(),
    });
  }
  inspector.classList.remove("is-open");
  persist(existing ? "Updated" : "Created");
}

function prepareItem(type, data, existing = {}) {
  if (type === "project") {
    return {
      title: data.title.trim(),
      status: data.status,
      priority: data.priority,
      summary: data.summary.trim(),
      nextAction: data.nextAction.trim(),
      tags: inputToTags(data.tags || ""),
    };
  }
  if (type === "task") {
    return {
      title: data.title.trim(),
      status: data.status,
      priority: data.priority,
      dueDate: data.dueDate,
      projectId: data.projectId,
      notes: data.notes.trim(),
      tags: inputToTags(data.tags || ""),
    };
  }
  if (type === "note") {
    return {
      title: data.title.trim(),
      projectId: data.projectId,
      body: data.body.trim(),
      tags: inputToTags(data.tags || ""),
    };
  }
  if (type === "routine") {
    return {
      title: data.title.trim(),
      frequency: data.frequency,
      checklist: data.checklist
        .split("\n")
        .map((line) => line.trim())
        .filter(Boolean),
      lastCompletedAt: existing.lastCompletedAt || "",
    };
  }
  return {
    title: data.title.trim(),
    url: normalizeHttpUrl(data.url),
    category: data.category.trim() || "inbox",
    notes: data.notes.trim(),
  };
}

function deleteItem(type, id) {
  let detail = "";
  if (type === "project") {
    const linkedTasks = state.tasks.filter((task) => task.projectId === id).length;
    const linkedNotes = state.notes.filter((note) => note.projectId === id).length;
    detail = linkedTasks || linkedNotes ? ` This will unlink ${linkedTasks} tasks and ${linkedNotes} notes.` : "";
  }
  const confirmed = window.confirm(`Delete this ${type}? This only affects this browser's local data.${detail}`);
  if (!confirmed) return;
  const collectionName = `${type}s`;
  state[collectionName] = state[collectionName].filter((item) => item.id !== id);
  if (type === "project") {
    state.tasks.forEach((task) => {
      if (task.projectId === id) task.projectId = "";
    });
    state.notes.forEach((note) => {
      if (note.projectId === id) note.projectId = "";
    });
  }
  inspector.classList.remove("is-open");
  persist("Deleted");
}

async function exportState(filenamePrefix = "personal-notion-hub") {
  const assistantExport = await exportAssistantCaptures();
  const payload = {
    ...state,
    assistantCaptures: assistantExport.captures,
    assistantExportedAt: assistantExport.exportedAt,
  };
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `${filenamePrefix}-${todayISO()}.json`;
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
  toast("Export ready", "JSON backup downloaded, including assistant captures.");
}

async function exportAssistantCaptures() {
  if (!window.PNHAssistantStorage?.exportCaptures) {
    return { exportedAt: nowISO(), captures: assistantState.captures };
  }
  return window.PNHAssistantStorage.exportCaptures();
}

async function handleImport(event) {
  const file = event.target.files?.[0];
  if (!file) return;
  const confirmed = window.confirm("Import will replace this browser's current hub data. A pre-import backup will be downloaded first. Continue?");
  if (!confirmed) {
    event.target.value = "";
    toast("Import cancelled");
    return;
  }
  await exportState("personal-notion-hub-pre-import-backup");
  const reader = new FileReader();
  reader.addEventListener("load", async () => {
    try {
      const parsed = JSON.parse(String(reader.result));
      validateImportedState(parsed);
      const imported = normalizeState(parsed);
      state = imported;
      await importAssistantCaptures(parsed);
      activeView = state.settings.activeView || "dashboard";
      document.documentElement.dataset.theme = state.settings.theme;
      persist("Import complete");
    } catch (error) {
      console.warn("Import failed", error?.name || "ImportError");
      toast("Import failed", "JSON 형식이나 schema를 확인하세요.");
    }
    event.target.value = "";
  });
  reader.readAsText(file);
}

async function importAssistantCaptures(parsed) {
  const captures = Array.isArray(parsed.assistantCaptures)
    ? parsed.assistantCaptures
    : Array.isArray(parsed.assistant?.captures)
      ? parsed.assistant.captures
      : [];
  if (!captures.length || !window.PNHAssistantStorage?.clearCaptures) {
    return;
  }
  await window.PNHAssistantStorage.clearCaptures();
  for (const capture of captures) {
    await window.PNHAssistantStorage.addCapture(capture);
  }
  assistantState.captures = await window.PNHAssistantStorage.listCaptures();
}

function validateImportedState(candidate) {
  if (!candidate || typeof candidate !== "object" || Array.isArray(candidate)) {
    throw new Error("Import root must be an object.");
  }
  const collections = ["projects", "tasks", "notes", "routines", "links"];
  const hasCollection = collections.some((name) => Array.isArray(candidate[name]));
  const hasAssistant = Array.isArray(candidate.assistantCaptures) || Array.isArray(candidate.assistant?.captures);
  if (!hasCollection && !hasAssistant) {
    throw new Error("Import must include at least one known collection.");
  }
  collections.forEach((name) => {
    if (candidate[name] !== undefined && !Array.isArray(candidate[name])) {
      throw new Error(`${name} must be an array.`);
    }
  });
}

function normalizeHttpUrl(value) {
  const raw = String(value || "").trim();
  if (!raw) return "";
  try {
    const parsed = new URL(raw);
    if (!["http:", "https:"].includes(parsed.protocol)) return "";
    return parsed.href;
  } catch {
    return "";
  }
}

async function resetState() {
  const confirmation = window.prompt("Type RESET to reset this browser's local hub data.");
  if (confirmation !== "RESET") {
    toast("Reset cancelled");
    return;
  }
  state = clone(seedState);
  activeView = "dashboard";
  document.documentElement.dataset.theme = state.settings.theme;
  if (window.PNHAssistantStorage?.clearCaptures) {
    await window.PNHAssistantStorage.clearCaptures().then(loadAssistantCaptures).catch(() => {
      assistantState.captures = [];
    });
  } else {
    assistantState.captures = [];
  }
  persist("Data reset");
}

function wireEvents() {
  document.querySelectorAll(".nav-item").forEach((button) => {
    button.addEventListener("click", () => {
      activeView = button.dataset.view;
      state.settings.activeView = activeView;
      sidebar.classList.remove("is-open");
      render();
      writeStoredState();
      appView.focus();
    });
  });

  globalSearch.addEventListener("input", (event) => {
    searchQuery = event.target.value.trim();
    render();
  });

  document.querySelector("#quickCaptureFocus").addEventListener("click", () => {
    activeView = "dashboard";
    render();
    window.setTimeout(() => document.querySelector("#quickCaptureInput")?.focus(), 0);
  });

  document.querySelector("#quickExportButton").addEventListener("click", exportState);
  document.querySelector("#closeInspector").addEventListener("click", () => inspector.classList.remove("is-open"));
  document.querySelector("#mobileMenuButton").addEventListener("click", () => sidebar.classList.toggle("is-open"));

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      inspector.classList.remove("is-open");
      sidebar.classList.remove("is-open");
    }
  });
}

async function boot() {
  await loadAssistantCaptures();
  wireEvents();
  render();
  if (state.system?.recoveredAt) {
    toast("Recovered default data", "손상된 localStorage 값을 감지해 기본 상태로 복구했습니다.");
  }
  if (!storageState.available) {
    toast("Local storage unavailable", "앱은 열렸지만 이 브라우저에 저장하지 못할 수 있습니다.");
  }
  if (assistantState.error) {
    toast("Assistant storage fallback", `IndexedDB를 초기화하지 못했습니다: ${assistantState.error}`);
  }
}

boot();
