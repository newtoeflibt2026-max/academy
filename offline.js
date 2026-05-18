// ╔══════════════════════════════════════════════════════════╗
// ║   أكاديمية يامن — Offline Manager (Client-Side)          ║
// ║   يدير Service Worker + IndexedDB + مزامنة الكويزات      ║
// ╚══════════════════════════════════════════════════════════╝

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// 1. تسجيل Service Worker
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
let _sw = null;

async function registerSW() {
  if (!("serviceWorker" in navigator)) {
    console.warn("[Offline] Service Worker غير مدعوم في هذا المتصفح");
    return;
  }
  try {
    const reg = await navigator.serviceWorker.register("/service-worker.js", {
      scope: "/",
    });
    _sw = reg;
    console.log("[Offline] ✅ Service Worker مسجّل:", reg.scope);

    // استمع لرسائل الـ SW
    navigator.serviceWorker.addEventListener("message", _onSWMessage);

    // تحديث تلقائي عند وجود نسخة جديدة
    reg.addEventListener("updatefound", () => {
      const newWorker = reg.installing;
      newWorker?.addEventListener("statechange", () => {
        if (newWorker.state === "installed" && navigator.serviceWorker.controller) {
          console.log("[Offline] 🔄 تحديث جديد متاح");
          _showUpdateBanner();
        }
      });
    });
  } catch (e) {
    console.error("[Offline] فشل تسجيل SW:", e);
  }
}

function _onSWMessage(event) {
  const { type, count } = event.data || {};
  switch (type) {
    case "SYNC_COMPLETE":
      console.log(`[Offline] ✅ تمت مزامنة ${count} طلب معلق`);
      _showSyncNotification(count);
      break;
    case "SYNC_DONE":
      console.log("[Offline] ✅ مزامنة يدوية اكتملت");
      break;
    case "LESSON_CACHED":
      console.log(`[Offline] 📚 درس محفوظ: ${event.data.key}`);
      break;
  }
}

function _showUpdateBanner() {
  const banner = document.createElement("div");
  banner.id = "sw-update-banner";
  banner.innerHTML = `
    <div style="position:fixed;bottom:20px;left:50%;transform:translateX(-50%);
    background:#1e293b;color:#f1f5f9;padding:12px 20px;border-radius:12px;
    z-index:9999;display:flex;gap:12px;align-items:center;box-shadow:0 4px 20px rgba(0,0,0,.4)">
      🔄 <span>تحديث جديد متاح</span>
      <button onclick="location.reload()" style="background:#f59e0b;color:#000;border:none;
      padding:6px 14px;border-radius:6px;cursor:pointer;font-weight:bold">تحديث</button>
    </div>`;
  document.body.appendChild(banner);
}

function _showSyncNotification(count) {
  const el = document.getElementById("sync-toast");
  if (el) {
    el.textContent = `✅ تمت مزامنة ${count} إجابة محفوظة`;
    el.style.display = "block";
    setTimeout(() => (el.style.display = "none"), 3000);
  }
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// 2. IndexedDB Manager
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
const IDB_NAME    = "YamenOfflineDB";
const IDB_VERSION = 2;

const OfflineDB = {
  db: null,

  async init() {
    if (this.db) return this.db;
    return new Promise((resolve, reject) => {
      const req = indexedDB.open(IDB_NAME, IDB_VERSION);

      req.onupgradeneeded = (e) => {
        const db = e.target.result;

        // مخزن الدروس والمفردات
        if (!db.objectStoreNames.contains("lessons")) {
          db.createObjectStore("lessons", { keyPath: "key" });
        }
        // مخزن نتائج الكويزات المعلقة
        if (!db.objectStoreNames.contains("pending_quiz")) {
          const s = db.createObjectStore("pending_quiz", {
            keyPath: "id",
            autoIncrement: true,
          });
          s.createIndex("synced", "synced", { unique: false });
        }
        // كاش ميديا (صور/صوت)
        if (!db.objectStoreNames.contains("media_cache")) {
          db.createObjectStore("media_cache", { keyPath: "url" });
        }
        // إعدادات محلية
        if (!db.objectStoreNames.contains("settings")) {
          db.createObjectStore("settings", { keyPath: "key" });
        }
      };

      req.onsuccess = () => {
        this.db = req.result;
        resolve(this.db);
      };
      req.onerror = () => reject(req.error);
    });
  },

  // ── دروس ───────────────────────────────────────────────────
  async saveLesson(lesson) {
    await this.init();
    return this._put("lessons", {
      key:       lesson.id || lesson.key || String(Date.now()),
      title:     lesson.title || "",
      content:   lesson.content || "",
      vocab:     lesson.vocab || [],
      cached_at: Date.now(),
    });
  },

  async getLesson(key) {
    await this.init();
    return this._get("lessons", String(key));
  },

  async getAllLessons() {
    await this.init();
    return this._getAll("lessons");
  },

  // ── كويزات معلقة ───────────────────────────────────────────
  async saveQuizAnswer(answer) {
    await this.init();
    const item = { ...answer, synced: false, saved_at: Date.now() };
    await this._add("pending_quiz", item);
    // أخبر الـ SW بالحفظ
    this._postToSW({ type: "SAVE_QUIZ_RESULT", payload: answer });
    // تسجيل Background Sync إن كان مدعوماً
    if (_sw && "sync" in _sw) {
      await _sw.sync.register("yamen-sync-quiz").catch(() => {});
    }
  },

  async getPendingAnswers() {
    await this.init();
    return this._getAll("pending_quiz");
  },

  async clearPendingAnswers() {
    await this.init();
    return this._clear("pending_quiz");
  },

  // ── ميديا ──────────────────────────────────────────────────
  async cacheMedia(url, blob) {
    await this.init();
    return this._put("media_cache", {
      url,
      blob,
      cached_at: Date.now(),
    });
  },

  async getCachedMedia(url) {
    await this.init();
    const item = await this._get("media_cache", url);
    if (!item) return null;
    // انتهاء صلاحية بعد 7 أيام
    if (Date.now() - item.cached_at > 7 * 24 * 3600 * 1000) return null;
    return item.blob;
  },

  // ── إعدادات ────────────────────────────────────────────────
  async setSetting(key, value) {
    await this.init();
    return this._put("settings", { key, value });
  },

  async getSetting(key) {
    await this.init();
    const item = await this._get("settings", key);
    return item ? item.value : null;
  },

  // ── helpers ────────────────────────────────────────────────
  _put(store, data) {
    return new Promise((res, rej) => {
      const tx = this.db.transaction(store, "readwrite");
      tx.objectStore(store).put(data);
      tx.oncomplete = () => res(data);
      tx.onerror    = () => rej(tx.error);
    });
  },
  _add(store, data) {
    return new Promise((res, rej) => {
      const tx  = this.db.transaction(store, "readwrite");
      const req = tx.objectStore(store).add(data);
      req.onsuccess = () => res(req.result);
      tx.onerror    = () => rej(tx.error);
    });
  },
  _get(store, key) {
    return new Promise((res, rej) => {
      const tx  = this.db.transaction(store, "readonly");
      const req = tx.objectStore(store).get(key);
      req.onsuccess = () => res(req.result || null);
      req.onerror   = () => rej(req.error);
    });
  },
  _getAll(store) {
    return new Promise((res, rej) => {
      const tx  = this.db.transaction(store, "readonly");
      const req = tx.objectStore(store).getAll();
      req.onsuccess = () => res(req.result || []);
      req.onerror   = () => rej(req.error);
    });
  },
  _clear(store) {
    return new Promise((res, rej) => {
      const tx = this.db.transaction(store, "readwrite");
      tx.objectStore(store).clear();
      tx.oncomplete = res;
      tx.onerror    = () => rej(tx.error);
    });
  },
  _postToSW(msg) {
    if (navigator.serviceWorker?.controller) {
      navigator.serviceWorker.controller.postMessage(msg);
    }
  },
};

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// 3. مزامنة تلقائية عند عودة الإنترنت
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
async function syncPendingAnswers() {
  if (!navigator.onLine) return;
  const pending = await OfflineDB.getPendingAnswers().catch(() => []);
  if (!pending.length) return;

  console.log(`[Offline] مزامنة ${pending.length} إجابة معلقة…`);
  let synced = 0;

  for (const answer of pending) {
    try {
      const API = window.CONFIG?.API_BASE || "";
      const res = await fetch(`${API}/api/questions/check`, {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify(answer),
      });
      if (res.ok) synced++;
    } catch {
      break; // لا يزال أوفلاين
    }
  }

  if (synced > 0) {
    await OfflineDB.clearPendingAnswers();
    _showSyncNotification(synced);
    console.log(`[Offline] ✅ تمت مزامنة ${synced} إجابة`);
  }
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// 4. مستمعو الاتصال + حالة الشبكة
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
window.addEventListener("online", () => {
  console.log("[Offline] 🌐 عاد الإنترنت — بدء المزامنة");
  syncPendingAnswers();
  // أخبر SW بالمزامنة أيضاً
  if (navigator.serviceWorker?.controller) {
    navigator.serviceWorker.controller.postMessage({ type: "FORCE_SYNC" });
  }
  _updateStatusBar(true);
});

window.addEventListener("offline", () => {
  console.log("[Offline] 📵 وضع أوفلاين — الدروس المحفوظة متاحة");
  _updateStatusBar(false);
});

function _updateStatusBar(online) {
  const bar = document.getElementById("connection-status");
  if (!bar) return;
  bar.style.display = online ? "none" : "flex";
  bar.textContent   = online ? "" : "📵 أنت أوفلاين — الدروس المحفوظة متاحة";
}

function isOnline() {
  return navigator.onLine;
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// 5. Helper: تخزين درس من الصفحة → SW + IDB
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
async function cacheLesson(lesson) {
  await OfflineDB.saveLesson(lesson);
  if (navigator.serviceWorker?.controller) {
    navigator.serviceWorker.controller.postMessage({
      type:    "CACHE_LESSON",
      payload: { key: String(lesson.id || lesson.key), ...lesson },
    });
  }
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// 6. تهيئة عند تحميل الصفحة
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
(async () => {
  await OfflineDB.init();
  await registerSW();

  // مزامنة فورية إذا كان هناك طلبات معلقة
  if (navigator.onLine) {
    setTimeout(syncPendingAnswers, 2000);
  }

  // تحديث حالة شريط الشبكة
  _updateStatusBar(navigator.onLine);

  console.log("[Offline] ✅ Yamen Academy Offline System جاهز");
})();
