(function attachAssistantImport(window) {
  "use strict";

  const sourceTypes = Object.freeze(["slack", "email", "sms", "kakao", "call", "voice_memo", "my_memo", "youtube", "bible"]);
  const captureTypes = Object.freeze(["task", "note", "project", "link", "routine", "work_record", "calendar_event"]);
  const dispatchIntents = Object.freeze(["assistant_capture", "project_brief", "task_request", "daily_command", "urgent_approval"]);
  const piiPatterns = [
    /\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/i,
    /\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b/,
    /\b01[016789][-.\s]?\d{3,4}[-.\s]?\d{4}\b/,
    /-----BEGIN [A-Z ]*PRIVATE KEY-----/,
    /\b(?:api[_-]?key|access[_-]?token|oauth|secret)\b\s*[:=]/i,
  ];

  function normalizeManualCapture(input) {
    const raw = normalizeInput(input);
    const title = firstText(raw.title, raw.text, raw.body, raw.notes, raw.url);
    if (!title) {
      throw new Error("Manual capture requires a title or text value.");
    }

    const source = normalizeSourceType(raw.sourceType || raw.source || "my_memo");
    const type = normalizeCaptureType(raw.type || inferCaptureType(raw));
    const tags = normalizeTags(raw.tags);
    const receivedAt = normalizeDate(raw.receivedAt || raw.capturedAt || raw.createdAt) || new Date().toISOString();
    const now = new Date().toISOString();

    return removeEmpty({
      id: raw.id || makeId(),
      type,
      source,
      sourceType: source,
      dispatchIntent: normalizeDispatchIntent(raw.dispatchIntent || raw.commandType || raw.kind),
      title: compactLine(title),
      body: normalizeBody(raw.body || raw.text || raw.notes || ""),
      url: type === "link" ? normalizeUrl(raw.url || title) : "",
      priority: normalizePriority(raw.priority),
      dueDate: normalizeDateOnly(raw.dueDate || raw.date),
      project: compactLine(raw.project || raw.projectTitle || ""),
      status: normalizeStatus(raw.status),
      tags,
      receivedAt,
      capturedAt: receivedAt,
      createdAt: normalizeDate(raw.createdAt) || now,
      updatedAt: normalizeDate(raw.updatedAt) || now,
    });
  }

  function parseFixtureJson(text) {
    const rawText = String(text || "").trim();
    if (!rawText) {
      throw new Error("Fixture JSON is empty.");
    }
    if (containsSensitiveFixtureData(rawText)) {
      throw new Error("Fixture JSON must not include personal data, tokens, or secrets.");
    }

    let parsed;
    try {
      parsed = JSON.parse(rawText);
    } catch (error) {
      throw new Error(`Invalid fixture JSON: ${error.message}`);
    }

    const captures = Array.isArray(parsed) ? parsed : parsed && Array.isArray(parsed.captures) ? parsed.captures : null;
    if (!captures) {
      throw new Error("Fixture JSON must be an array or an object with a captures array.");
    }

    return captures.map((capture) =>
      normalizeManualCapture({
        ...normalizeInput(capture),
        sourceType: capture.sourceType || capture.source || "my_memo",
      })
    );
  }

  function makeId() {
    return `capture-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
  }

  function normalizeInput(input) {
    if (typeof input === "string") return { text: input };
    if (!input || typeof input !== "object" || Array.isArray(input)) {
      throw new Error("Capture input must be a string or plain object.");
    }
    return input;
  }

  function firstText() {
    for (const value of arguments) {
      const normalized = compactLine(value);
      if (normalized) return normalized;
    }
    return "";
  }

  function compactLine(value) {
    return String(value || "")
      .replace(/\s+/g, " ")
      .trim();
  }

  function normalizeBody(value) {
    return String(value || "")
      .replace(/\r\n/g, "\n")
      .trim();
  }

  function normalizeTags(value) {
    if (Array.isArray(value)) {
      return value.map(compactLine).filter(Boolean);
    }
    if (typeof value === "string") {
      return value
        .split(",")
        .map(compactLine)
        .filter(Boolean);
    }
    return [];
  }

  function normalizeSourceType(value) {
    const sourceType = compactLine(value).toLowerCase();
    return sourceTypes.includes(sourceType) ? sourceType : "manual";
  }

  function normalizeCaptureType(value) {
    const type = compactLine(value).toLowerCase();
    return captureTypes.includes(type) ? type : "note";
  }

  function inferCaptureType(raw) {
    const text = compactLine(`${raw.title || ""} ${raw.text || ""} ${raw.body || ""} ${raw.url || ""}`).toLowerCase();
    const source = compactLine(raw.sourceType || raw.source || "").toLowerCase();
    if (source === "bible") return "note";
    if (source === "call" || source === "voice_memo" || /\b(call|통화|전화|회의)\b/.test(text)) return "work_record";
    if (raw.dueDate || /\b(todo|task|please|action|due)\b/.test(text) || /(해야|할 일|액션|요청|마감|긴급|오늘|내일)/.test(text)) return "task";
    if (/\d{4}-\d{2}-\d{2}|\d{1,2}월\s*\d{1,2}일|\b\d{1,2}:\d{2}\b/.test(text)) return "calendar_event";
    if (normalizeUrl(raw.url || "") || /\bhttps?:\/\/\S+/.test(text)) return "link";
    if (/^(project|프로젝트)\b/.test(text)) return "project";
    if (/^(routine|habit|루틴|습관)\b/.test(text)) return "routine";
    return "note";
  }

  function normalizeUrl(value) {
    const raw = compactLine(value);
    if (!raw) return "";
    try {
      const url = new URL(raw);
      return ["http:", "https:"].includes(url.protocol) ? url.href : "";
    } catch {
      return "";
    }
  }

  function normalizePriority(value) {
    const priority = compactLine(value).toLowerCase();
    return ["high", "medium", "low"].includes(priority) ? priority : "medium";
  }

  function normalizeStatus(value) {
    const status = compactLine(value).toLowerCase();
    return ["inbox", "processed", "archived"].includes(status) ? status : "inbox";
  }

  function normalizeDispatchIntent(value) {
    const intent = compactLine(value).toLowerCase();
    return dispatchIntents.includes(intent) ? intent : "assistant_capture";
  }

  function normalizeDate(value) {
    const raw = compactLine(value);
    if (!raw) return "";
    const date = new Date(raw);
    return Number.isNaN(date.getTime()) ? "" : date.toISOString();
  }

  function normalizeDateOnly(value) {
    const raw = compactLine(value);
    if (!raw) return "";
    if (/^\d{4}-\d{2}-\d{2}$/.test(raw)) return raw;
    const date = new Date(raw);
    return Number.isNaN(date.getTime()) ? "" : date.toISOString().slice(0, 10);
  }

  function removeEmpty(record) {
    return Object.fromEntries(
      Object.entries(record).filter(([, value]) => {
        if (Array.isArray(value)) return value.length > 0;
        return value !== "";
      })
    );
  }

  function containsSensitiveFixtureData(text) {
    return piiPatterns.some((pattern) => pattern.test(text));
  }

  window.PNHAssistantImport = Object.freeze({
    dispatchIntents,
    sourceTypes,
    normalizeManualCapture,
    parseFixtureJson,
  });
})(window);
