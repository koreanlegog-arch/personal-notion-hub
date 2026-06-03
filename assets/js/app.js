const STORAGE_KEY = "personalNotionHubState";

const todayISO = () => new Date().toISOString().slice(0, 10);
const nowISO = () => new Date().toISOString();

const uid = (prefix) => `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;

let storageState = {
  available: true,
  lastError: "",
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
  updateActiveNav();
  updateStorageMeter();
  clearView();
  const renderers = {
    dashboard: renderDashboard,
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

  const hero = make("section", "hero-strip");
  const focus = make("div", "focus-panel");
  focus.append(make("p", "eyebrow", "Today"));
  focus.append(make("h3", "", todayTasks[0]?.title || "Start with a clear capture"));
  focus.append(
    make(
      "p",
      "",
      todayTasks[0]?.notes || "Quick Capture로 생각을 inbox에 넣고, 프로젝트와 task board에서 실행 단위로 정리하세요."
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
    ["Notes", state.notes.length],
    ["Routines", state.routines.length],
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
    panel("Active Projects", activeProjects.slice(0, 5), (project) => projectCard(project), "진행 중 프로젝트가 없습니다."),
    panel("Recent Notes", notes.slice(0, 5), (note) => noteCard(note), "최근 note가 없습니다.")
  );
  appView.append(grid);
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
  stack.append(settingsRow("Export JSON", "현재 localStorage 데이터를 파일로 백업합니다.", button("Export Data", exportState)));
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

function exportState(filenamePrefix = "personal-notion-hub") {
  const blob = new Blob([JSON.stringify(state, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `${filenamePrefix}-${todayISO()}.json`;
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
  toast("Export ready", "JSON backup downloaded.");
}

function handleImport(event) {
  const file = event.target.files?.[0];
  if (!file) return;
  const confirmed = window.confirm("Import will replace this browser's current hub data. A pre-import backup will be downloaded first. Continue?");
  if (!confirmed) {
    event.target.value = "";
    toast("Import cancelled");
    return;
  }
  exportState("personal-notion-hub-pre-import-backup");
  const reader = new FileReader();
  reader.addEventListener("load", () => {
    try {
      const parsed = JSON.parse(String(reader.result));
      validateImportedState(parsed);
      const imported = normalizeState(parsed);
      state = imported;
      activeView = state.settings.activeView || "dashboard";
      document.documentElement.dataset.theme = state.settings.theme;
      persist("Import complete");
    } catch (error) {
      console.error(error);
      toast("Import failed", "JSON 형식이나 schema를 확인하세요.");
    }
    event.target.value = "";
  });
  reader.readAsText(file);
}

function validateImportedState(candidate) {
  if (!candidate || typeof candidate !== "object" || Array.isArray(candidate)) {
    throw new Error("Import root must be an object.");
  }
  const collections = ["projects", "tasks", "notes", "routines", "links"];
  const hasCollection = collections.some((name) => Array.isArray(candidate[name]));
  if (!hasCollection) {
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

function resetState() {
  const confirmation = window.prompt("Type RESET to reset this browser's local hub data.");
  if (confirmation !== "RESET") {
    toast("Reset cancelled");
    return;
  }
  state = clone(seedState);
  activeView = "dashboard";
  document.documentElement.dataset.theme = state.settings.theme;
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

wireEvents();
render();
if (state.system?.recoveredAt) {
  toast("Recovered default data", "손상된 localStorage 값을 감지해 기본 상태로 복구했습니다.");
}
if (!storageState.available) {
  toast("Local storage unavailable", "앱은 열렸지만 이 브라우저에 저장하지 못할 수 있습니다.");
}
