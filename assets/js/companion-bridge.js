(function () {
  "use strict";

  const LOOPBACK_BASE_URL = "http://127.0.0.1:8765";
  const COMPANION_PORT = "8765";
  let sessionToken = "";

  function defaultBaseUrl() {
    const page = new URL(window.location.href);
    if (page.protocol === "http:" && page.port === COMPANION_PORT && page.hostname) {
      return page.origin;
    }
    return LOOPBACK_BASE_URL;
  }

  function validCompanionOrigin(origin) {
    const parsed = new URL(origin);
    if (parsed.protocol !== "http:" || parsed.port !== COMPANION_PORT || parsed.pathname !== "/") {
      return false;
    }
    if (parsed.hostname === "127.0.0.1") return true;
    if (/^10\.\d{1,3}\.\d{1,3}\.\d{1,3}$/.test(parsed.hostname)) return true;
    if (/^192\.168\.\d{1,3}\.\d{1,3}$/.test(parsed.hostname)) return true;
    const match = parsed.hostname.match(/^172\.(\d{1,3})\.\d{1,3}\.\d{1,3}$/);
    return Boolean(match && Number(match[1]) >= 16 && Number(match[1]) <= 31);
  }

  function validatedBaseUrl(value = defaultBaseUrl()) {
    const parsed = new URL(value);
    if (!validCompanionOrigin(parsed.origin) || parsed.search || parsed.hash) {
      throw new Error("Companion base URL must be loopback or private LAN http on port 8765");
    }
    return parsed.origin;
  }

  async function controlledFetch(path, options = {}) {
    const baseUrl = validatedBaseUrl();
    const target = new URL(path, baseUrl);
    if (target.origin !== baseUrl) {
      throw new Error("Companion request blocked by allowed origin policy");
    }
    const headers = new Headers(options.headers || {});
    headers.set("Accept", "application/json");
    if (options.body !== undefined) headers.set("Content-Type", "application/json");
    if (options.authenticated) {
      if (!sessionToken) throw new Error("Companion session is not paired");
      headers.set("Authorization", `Bearer ${sessionToken}`);
    }

    const response = await fetch(target.href, {
      method: options.method || "GET",
      headers,
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
      cache: "no-store",
    });
    let data = {};
    try {
      data = await response.json();
    } catch {
      data = {};
    }
    return { ok: response.ok, status: response.status, data, headers: response.headers };
  }

  async function health() {
    const result = await controlledFetch("/api/health");
    return {
      ok: result.ok && Boolean(result.data?.ok),
      status: result.status,
      mode: result.data?.mode || "unknown",
      writesEnabled: Boolean(result.data?.writesEnabled),
      authRequired: Boolean(result.data?.authRequired),
      browserBridgeEnabled: Boolean(result.data?.browserBridge?.enabled),
    };
  }

  async function pair(pairingCode) {
    const code = String(pairingCode || "").trim();
    if (!code) throw new Error("Pairing code is required");
    const result = await controlledFetch("/api/private/pair", {
      method: "POST",
      body: { pairingCode: code },
    });
    const token = String(result.headers?.get("X-PNH-Browser-Session") || "");
    if (!result.ok || token.length < 16) {
      sessionToken = "";
      throw new Error(result.data?.error || "Pairing failed");
    }
    sessionToken = token;
    return { paired: true, status: result.status };
  }

  function disconnect() {
    sessionToken = "";
    return { paired: false };
  }

  function isPaired() {
    return Boolean(sessionToken);
  }

  async function sendCapture(packet, label = "Capture") {
    if (!packet || typeof packet !== "object") {
      throw new Error(`${label} payload is required`);
    }
    const result = await controlledFetch("/api/private/mobile-captures", {
      method: "POST",
      authenticated: true,
      body: packet,
    });
    if (!result.ok) {
      throw new Error(result.data?.error || `${label} send failed`);
    }
    return {
      ok: true,
      status: result.status,
      writesPerformed: Boolean(result.data?.writesPerformed),
      captureId: result.data?.capture?.id || "",
    };
  }

  async function sendLaunchPacket(packet) {
    return sendCapture(packet, "Launch packet");
  }

  async function sendAssistantCapture(packet) {
    return sendCapture(packet, "Assistant capture");
  }

  window.PNHCompanionBridge = Object.freeze({
    baseUrl: defaultBaseUrl(),
    disconnect,
    health,
    isPaired,
    pair,
    sendAssistantCapture,
    sendCapture,
    sendLaunchPacket,
  });
})();
