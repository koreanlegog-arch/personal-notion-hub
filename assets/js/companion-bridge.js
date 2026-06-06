(function () {
  "use strict";

  const LOOPBACK_BASE_URL = "http://127.0.0.1:8765";
  const DEFAULT_COMPANION_PORT = "8765";
  const OWNER_DEVICE_STORAGE_KEY = "pnhOwnerDeviceCredential";
  let sessionToken = "";

  function defaultBaseUrl() {
    const page = new URL(window.location.href);
    if (page.protocol === "http:" && page.port && validCompanionOrigin(page.origin)) {
      return page.origin;
    }
    if (page.protocol === "https:" && page.hostname.endsWith(".ts.net")) {
      return page.origin;
    }
    return LOOPBACK_BASE_URL;
  }

  function validCompanionOrigin(origin) {
    const parsed = new URL(origin);
    if (parsed.protocol === "https:" && parsed.hostname.endsWith(".ts.net") && !parsed.port && parsed.pathname === "/") {
      return true;
    }
    if (parsed.protocol !== "http:" || !validCompanionPort(parsed.port) || parsed.pathname !== "/") {
      return false;
    }
    if (parsed.hostname.endsWith(".ts.net")) return true;
    if (/^100\.(6[4-9]|[7-9]\d|1[01]\d|12[0-7])\.\d{1,3}\.\d{1,3}$/.test(parsed.hostname)) return true;
    if (parsed.hostname === "127.0.0.1") return true;
    if (/^10\.\d{1,3}\.\d{1,3}\.\d{1,3}$/.test(parsed.hostname)) return true;
    if (/^192\.168\.\d{1,3}\.\d{1,3}$/.test(parsed.hostname)) return true;
    const match = parsed.hostname.match(/^172\.(\d{1,3})\.\d{1,3}\.\d{1,3}$/);
    return Boolean(match && Number(match[1]) >= 16 && Number(match[1]) <= 31);
  }

  function validCompanionPort(port) {
    if (port === DEFAULT_COMPANION_PORT) return true;
    const page = new URL(window.location.href);
    return Boolean(page.protocol === "http:" && page.port && port === page.port);
  }

  function validatedBaseUrl(value = defaultBaseUrl()) {
    const parsed = new URL(value);
    if (!validCompanionOrigin(parsed.origin) || parsed.search || parsed.hash) {
      throw new Error("Companion base URL must be loopback/private LAN http on the active companion port or Tailscale HTTPS/tailnet HTTP");
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
      body: { pairingCode: code, deviceLabel: ownerDeviceLabel() },
    });
    const token = String(result.headers?.get("X-PNH-Browser-Session") || "");
    if (!result.ok || token.length < 16) {
      sessionToken = "";
      throw new Error(result.data?.error || "Pairing failed");
    }
    sessionToken = token;
    const ownerDeviceCredential = String(result.headers?.get("X-PNH-Owner-Device-Credential") || "");
    if (ownerDeviceCredential) storeOwnerDeviceCredential(ownerDeviceCredential);
    return {
      paired: true,
      status: result.status,
      ownerDeviceIssued: Boolean(ownerDeviceCredential),
      ownerDevice: result.data?.ownerDevice || {},
    };
  }

  async function restoreOwnerDeviceSession() {
    const credential = readOwnerDeviceCredential();
    if (!credential) return { paired: false, restored: false, reason: "owner_device_credential_missing" };
    const result = await controlledFetch("/api/private/owner-device-session", {
      method: "POST",
      body: { ownerDeviceCredential: credential },
    });
    const token = String(result.headers?.get("X-PNH-Browser-Session") || "");
    if (!result.ok || token.length < 16) {
      clearOwnerDeviceCredential();
      sessionToken = "";
      return { paired: false, restored: false, reason: result.data?.error || "owner_device_restore_failed" };
    }
    sessionToken = token;
    return {
      paired: true,
      restored: true,
      status: result.status,
      ownerDevice: result.data?.ownerDevice || {},
    };
  }

  async function revokeOwnerDeviceSession() {
    const credential = readOwnerDeviceCredential();
    clearOwnerDeviceCredential();
    sessionToken = "";
    if (!credential) return { revoked: false, reason: "owner_device_credential_missing" };
    const result = await controlledFetch("/api/private/owner-device/revoke", {
      method: "POST",
      body: { ownerDeviceCredential: credential },
    });
    return { revoked: Boolean(result.data?.revoked), status: result.status };
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
      autoDispatch: result.data?.autoDispatch || { requested: false },
    };
  }

  async function sendLaunchPacket(packet) {
    return sendCapture(packet, "Launch packet");
  }

  async function sendMobileCommandPacket(packet) {
    return sendCapture(packet, "Mobile command packet");
  }

  async function sendAssistantCapture(packet) {
    return sendCapture(packet, "Assistant capture");
  }

  async function dispatchState() {
    const result = await controlledFetch("/api/private/dispatch-state", {
      authenticated: true,
    });
    if (!result.ok) {
      throw new Error(result.data?.error || "Dispatch state check failed");
    }
    return result.data?.dispatchState || {
      totalRecords: 0,
      githubLinked: 0,
      discordLinked: 0,
      records: [],
      privateValuesPrinted: false,
    };
  }

  async function commandPacketStatus() {
    const result = await controlledFetch("/api/private/command-packet-status", {
      authenticated: true,
    });
    if (!result.ok) {
      throw new Error(result.data?.error || "Command packet status check failed");
    }
    return result.data?.commandPacketStatus || {
      queueCount: 0,
      latestRun: {},
      latestDispatch: {},
      lastIssue: "",
      lastWorkerStatus: "",
      nextAction: "run_single_command_packet_wrapper",
      privateValuesPrinted: false,
      rawPrivateBodyRead: false,
      responsePolicy: "metadata-only",
    };
  }

  async function runSingleCommandPacket(mode = "dry-run", confirmApply = "") {
    const normalizedMode = String(mode || "dry-run");
    const result = await controlledFetch("/api/private/single-command-packet/run", {
      method: "POST",
      authenticated: true,
      body: {
        mode: normalizedMode,
        confirmApply: String(confirmApply || ""),
      },
    });
    if (!result.ok || !result.data?.ok) {
      throw new Error(result.data?.error || "Single command packet run failed");
    }
    return result.data?.singleCommandPacketRun || {
      ok: false,
      mode: normalizedMode,
      externalWritesPerformed: false,
      workerRunPerformed: false,
      privateValuesPrinted: false,
      rawPrivateBodyRead: false,
    };
  }

  window.PNHCompanionBridge = Object.freeze({
    baseUrl: defaultBaseUrl(),
    commandPacketStatus,
    disconnect,
    dispatchState,
    health,
    isPaired,
    pair,
    restoreOwnerDeviceSession,
    revokeOwnerDeviceSession,
    runSingleCommandPacket,
    sendAssistantCapture,
    sendCapture,
    sendLaunchPacket,
    sendMobileCommandPacket,
  });

  function ownerDeviceLabel() {
    const ua = window.navigator?.userAgent || "browser";
    return `owner-browser ${ua.slice(0, 48)}`;
  }

  function readOwnerDeviceCredential() {
    try {
      return String(window.localStorage.getItem(OWNER_DEVICE_STORAGE_KEY) || "");
    } catch {
      return "";
    }
  }

  function storeOwnerDeviceCredential(value) {
    try {
      window.localStorage.setItem(OWNER_DEVICE_STORAGE_KEY, value);
    } catch {
      // Persistent owner-device sessions are an enhancement. If localStorage is
      // unavailable, the normal one-time pairing session remains valid.
    }
  }

  function clearOwnerDeviceCredential() {
    try {
      window.localStorage.removeItem(OWNER_DEVICE_STORAGE_KEY);
    } catch {
      // No-op.
    }
  }
})();
