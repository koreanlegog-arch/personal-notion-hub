(function attachAssistantRules(window) {
  "use strict";

  const verseRotation = Object.freeze([
    { reference: "Proverbs 16:3", text: "Commit your work to the Lord, and your plans will be established." },
    { reference: "James 1:5", text: "If any of you lacks wisdom, let him ask God." },
    { reference: "Psalm 90:12", text: "Teach us to number our days that we may get a heart of wisdom." },
    { reference: "Matthew 6:34", text: "Do not be anxious about tomorrow." },
    { reference: "Colossians 3:23", text: "Whatever you do, work heartily, as for the Lord." },
    { reference: "Philippians 4:6", text: "Do not be anxious about anything, but in everything by prayer let your requests be made known." },
    { reference: "Isaiah 41:10", text: "Fear not, for I am with you." },
  ]);

  function buildSuggestions(captures) {
    return normalizeCaptures(captures).map((capture, index) => {
      const type = inferSuggestionType(capture);
      const priority = capture.priority || inferPriority(capture);

      return removeEmpty({
        id: `suggestion-${index + 1}`,
        captureId: capture.id || "",
        action: actionForType(type),
        type,
        suggestionType: type,
        title: capture.title,
        body: buildSuggestionBody(capture, type),
        confidence: confidenceForType(type, capture),
        priority,
        dueDate: capture.dueDate || "",
        project: capture.project || "",
        tags: capture.tags || [],
        payload: {
          priority,
          dueDate: capture.dueDate || "",
          source: capture.source || capture.sourceType || "",
        },
        reason: reasonForCapture(capture, priority),
      });
    });
  }

  function buildDailyBrief(captures, existingTasks) {
    const normalizedCaptures = normalizeCaptures(captures);
    const tasks = Array.isArray(existingTasks) ? existingTasks : [];
    const openTasks = tasks.filter((task) => task && task.status !== "done");
    const today = todayISO();
    const todayTasks = openTasks.filter((task) => task.status === "today" || task.dueDate === today);
    const highPriorityCaptures = normalizedCaptures.filter((capture) => inferPriority(capture) === "high");
    const suggestions = buildSuggestions(normalizedCaptures);

    return {
      date: today,
      focus: chooseFocus(todayTasks, highPriorityCaptures, suggestions),
      verse: bibleVerseForToday(today),
      counts: {
        captures: normalizedCaptures.length,
        suggestions: suggestions.length,
        openTasks: openTasks.length,
        todayTasks: todayTasks.length,
      },
      topSuggestions: suggestions.slice(0, 3),
      reviewPrompts: buildReviewPrompts(normalizedCaptures, openTasks),
    };
  }

  function bibleVerseForToday(date) {
    const dayIndex = dayNumber(date || new Date());
    return verseRotation[dayIndex % verseRotation.length];
  }

  function normalizeCaptures(captures) {
    if (!Array.isArray(captures)) return [];
    return captures
      .filter((capture) => capture && typeof capture === "object" && !Array.isArray(capture))
      .map((capture) => ({
        ...capture,
        title: compactLine(capture.title || capture.text || capture.body || "Untitled capture"),
        tags: Array.isArray(capture.tags) ? capture.tags.map(compactLine).filter(Boolean) : [],
      }));
  }

  function normalizeType(value) {
    const type = compactLine(value).toLowerCase();
    return ["task", "note", "project", "link", "routine", "work_record", "calendar_event"].includes(type) ? type : "note";
  }

  function inferSuggestionType(capture) {
    const explicit = normalizeType(capture.type);
    if (explicit !== "note") return explicit;
    const source = compactLine(capture.source || capture.sourceType).toLowerCase();
    const text = compactLine(`${capture.title || ""} ${capture.body || ""}`).toLowerCase();
    if (source === "bible") return "note";
    if (source === "call" || source === "voice_memo" || /\b(call|통화|전화|회의)\b/.test(text)) return "work_record";
    if (/\b(todo|task|please|action|due)\b/.test(text) || /(해야|할 일|액션|요청|마감|긴급|오늘|내일)/.test(text)) return "task";
    if (capture.dueDate || /\d{4}-\d{2}-\d{2}|\d{1,2}월\s*\d{1,2}일|\b\d{1,2}:\d{2}\b/.test(text)) return "calendar_event";
    if (/\bhttps?:\/\/\S+/.test(text)) return "link";
    return "note";
  }

  function actionForType(type) {
    return {
      task: "create_task",
      note: "create_note",
      project: "create_project",
      link: "save_link",
      routine: "create_routine",
      work_record: "create_work_record",
      calendar_event: "draft_calendar_event",
    }[type];
  }

  function buildSuggestionBody(capture, type) {
    const body = compactLine(capture.body || capture.title || "");
    if (type === "calendar_event") return `Calendar draft: ${body}`;
    if (type === "work_record") return `Work log draft: ${body}`;
    return body;
  }

  function confidenceForType(type, capture) {
    if (type === "task" && (capture.dueDate || inferPriority(capture) === "high")) return "high";
    if (type === "calendar_event" || type === "work_record") return "medium";
    return "medium";
  }

  function inferPriority(capture) {
    const text = compactLine(`${capture.title || ""} ${capture.body || ""} ${(capture.tags || []).join(" ")}`).toLowerCase();
    if (capture.priority === "high" || /\b(urgent|today|blocked|critical)\b/.test(text) || /(마감|긴급|오늘)/.test(text)) return "high";
    if (capture.priority === "low" || /\b(later|someday)\b/.test(text) || /(언젠가|낮음)/.test(text)) return "low";
    return "medium";
  }

  function reasonForCapture(capture, priority) {
    if (priority === "high") return "긴급도나 오늘 처리 신호가 있어 우선 정리합니다.";
    if (capture.dueDate) return "기한 정보가 있어 실행 항목으로 전환하기 좋습니다.";
    if ((capture.tags || []).length) return "태그가 있어 기존 hub 분류에 바로 연결할 수 있습니다.";
    return "수동 capture를 inbox에서 잃지 않도록 정리합니다.";
  }

  function chooseFocus(todayTasks, highPriorityCaptures, suggestions) {
    if (todayTasks.length) return compactLine(todayTasks[0].title || "오늘 task 정리");
    if (highPriorityCaptures.length) return compactLine(highPriorityCaptures[0].title || "긴급 capture 정리");
    if (suggestions.length) return compactLine(suggestions[0].title || "새 capture 정리");
    return "오늘의 핵심 task 하나를 정하고 시작";
  }

  function buildReviewPrompts(captures, openTasks) {
    const prompts = [];
    if (captures.length) prompts.push("새 capture를 task, note, link 중 하나로 분류하세요.");
    if (openTasks.length > 5) prompts.push("열린 task가 많습니다. 오늘 처리할 항목 3개만 고르세요.");
    if (!captures.length && !openTasks.length) prompts.push("오늘 기록할 생각이나 실행 항목을 하나 capture하세요.");
    return prompts;
  }

  function todayISO() {
    return new Date().toISOString().slice(0, 10);
  }

  function dayNumber(value) {
    const date = value instanceof Date ? value : new Date(value);
    const safeDate = Number.isNaN(date.getTime()) ? new Date() : date;
    return Math.floor(Date.UTC(safeDate.getUTCFullYear(), safeDate.getUTCMonth(), safeDate.getUTCDate()) / 86400000);
  }

  function compactLine(value) {
    return String(value || "")
      .replace(/\s+/g, " ")
      .trim();
  }

  function removeEmpty(record) {
    return Object.fromEntries(
      Object.entries(record).filter(([, value]) => {
        if (Array.isArray(value)) return value.length > 0;
        return value !== "";
      })
    );
  }

  window.PNHAssistantRules = Object.freeze({
    buildSuggestions,
    buildDailyBrief,
    bibleVerseForToday,
  });
})(window);
