(function () {
  "use strict";

  const BASE_URL = "http://127.0.0.1:8765";
  const EXPECTED_ORIGIN = "http://127.0.0.1:8765";
  let sessionToken = "";

  function validatedBaseUrl(value = BASE_URL) {
    const parsed = new URL(value);
    if (parsed.origin !== EXPECTED_ORIGIN || parsed.pathname !== "/" || parsed.search || parsed.hash) {
      throw new Error("Companion base URL must be exactly http://127.0.0.1:8765");
    }
    return parsed.origin;
  }

  async function controlledFetch(path, options = {}) {
    const baseUrl = validatedBaseUrl();
    const target = new URL(path, baseUrl);
    if (target.origin !== EXPECTED_ORIGIN) {
      throw new Error("Companion request blocked by loopback origin policy");
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

  async function sendLaunchPacket(packet) {
    if (!packet || typeof packet !== "object") {
      throw new Error("Launch packet payload is required");
    }
    const result = await controlledFetch("/api/private/mobile-captures", {
      method: "POST",
      authenticated: true,
      body: packet,
    });
    if (!result.ok) {
      throw new Error(result.data?.error || "Launch packet send failed");
    }
    return {
      ok: true,
      status: result.status,
      writesPerformed: Boolean(result.data?.writesPerformed),
      captureId: result.data?.capture?.id || "",
    };
  }

  window.PNHCompanionBridge = Object.freeze({
    baseUrl: BASE_URL,
    disconnect,
    health,
    isPaired,
    pair,
    sendLaunchPacket,
  });
})();
