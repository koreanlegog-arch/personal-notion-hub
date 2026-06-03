(function () {
  "use strict";

  const DB_NAME = "personalNotionHubAssistant";
  const STORE_NAME = "captures";
  const DB_VERSION = 1;

  let db = null;
  let useMemory = false;
  let fallbackError = "";
  const memoryCaptures = new Map();

  function clone(value) {
    if (typeof structuredClone === "function") {
      return structuredClone(value);
    }
    return JSON.parse(JSON.stringify(value));
  }

  function makeId() {
    return `capture-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
  }

  function assertCapture(value) {
    if (!value || typeof value !== "object" || Array.isArray(value)) {
      throw new TypeError("capture must be an object");
    }
  }

  function assertPatch(value) {
    if (!value || typeof value !== "object" || Array.isArray(value)) {
      throw new TypeError("patch must be an object");
    }
  }

  function enableMemoryFallback(error) {
    useMemory = true;
    db = null;
    fallbackError = error?.name || error?.message || "IndexedDBFallback";
    if (error) {
      console.warn("PNHAssistantStorage using memory fallback", fallbackError);
    }
  }

  function openDatabase() {
    return new Promise((resolve, reject) => {
      if (!window.indexedDB) {
        reject(new Error("IndexedDB unavailable"));
        return;
      }

      const request = window.indexedDB.open(DB_NAME, DB_VERSION);

      request.onupgradeneeded = () => {
        const database = request.result;
        if (!database.objectStoreNames.contains(STORE_NAME)) {
          database.createObjectStore(STORE_NAME, { keyPath: "id" });
        }
      };

      request.onsuccess = () => {
        const database = request.result;
        database.onversionchange = () => database.close();
        resolve(database);
      };

      request.onerror = () => reject(request.error || new Error("IndexedDB open failed"));
      request.onblocked = () => reject(new Error("IndexedDB open blocked"));
    });
  }

  function runStore(mode, operation) {
    return new Promise((resolve, reject) => {
      if (!db) {
        reject(new Error("storage is not initialized"));
        return;
      }

      const transaction = db.transaction(STORE_NAME, mode);
      const store = transaction.objectStore(STORE_NAME);
      const request = operation(store);

      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error || new Error("IndexedDB request failed"));
      transaction.onerror = () => reject(transaction.error || new Error("IndexedDB transaction failed"));
    });
  }

  async function withFallback(operation, memoryOperation) {
    if (useMemory) {
      return memoryOperation();
    }

    try {
      return await operation();
    } catch (error) {
      enableMemoryFallback(error);
      return memoryOperation();
    }
  }

  const memoryAdapter = {
    add(capture) {
      memoryCaptures.set(capture.id, clone(capture));
      return clone(capture);
    },
    list() {
      return Array.from(memoryCaptures.values()).map(clone);
    },
    update(id, patch) {
      const current = memoryCaptures.get(id);
      if (!current) return null;
      const next = { ...current, ...clone(patch), id };
      memoryCaptures.set(id, clone(next));
      return clone(next);
    },
    delete(id) {
      return memoryCaptures.delete(id);
    },
    clear() {
      memoryCaptures.clear();
      return true;
    },
  };

  const storage = {
    async init() {
      if (db || useMemory) return this.getStatus();

      try {
        db = await openDatabase();
      } catch (error) {
        enableMemoryFallback(error);
      }

      return this.getStatus();
    },

    getStatus() {
      return {
        ready: Boolean(db || useMemory),
        persistent: Boolean(db && !useMemory),
        fallback: useMemory,
        error: fallbackError,
      };
    },

    async addCapture(capture) {
      assertCapture(capture);
      await this.init();

      const record = clone(capture);
      record.id = record.id || makeId();

      return withFallback(
        async () => {
          await runStore("readwrite", (store) => store.put(record));
          return clone(record);
        },
        () => memoryAdapter.add(record)
      );
    },

    async listCaptures() {
      await this.init();

      return withFallback(
        () => runStore("readonly", (store) => store.getAll()).then((captures) => captures.map(clone).sort(sortNewestFirst)),
        () => memoryAdapter.list()
      );
    },

    async updateCapture(id, patch) {
      if (!id) throw new TypeError("id is required");
      assertPatch(patch);
      await this.init();

      return withFallback(
        async () => {
          const current = await runStore("readonly", (store) => store.get(id));
          if (!current) return null;
          const next = { ...current, ...clone(patch), id };
          await runStore("readwrite", (store) => store.put(next));
          return clone(next);
        },
        () => memoryAdapter.update(id, patch)
      );
    },

    async deleteCapture(id) {
      if (!id) throw new TypeError("id is required");
      await this.init();

      return withFallback(
        async () => {
          const existing = await runStore("readonly", (store) => store.get(id));
          if (!existing) return false;
          await runStore("readwrite", (store) => store.delete(id));
          return true;
        },
        () => memoryAdapter.delete(id)
      );
    },

    async clearCaptures() {
      await this.init();

      return withFallback(
        async () => {
          await runStore("readwrite", (store) => store.clear());
          return true;
        },
        () => memoryAdapter.clear()
      );
    },

    async exportCaptures() {
      const captures = await this.listCaptures();
      return {
        schemaVersion: 1,
        exportedAt: new Date().toISOString(),
        captures,
      };
    },
  };

  function sortNewestFirst(a, b) {
    const left = Date.parse(a.updatedAt || a.createdAt || a.receivedAt || a.capturedAt || "");
    const right = Date.parse(b.updatedAt || b.createdAt || b.receivedAt || b.capturedAt || "");
    return (Number.isNaN(right) ? 0 : right) - (Number.isNaN(left) ? 0 : left);
  }

  window.PNHAssistantStorage = storage;
})();
