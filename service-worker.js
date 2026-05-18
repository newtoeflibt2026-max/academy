// ╔══════════════════════════════════════════════════════════╗
// ║    أكاديمية يامن — Service Worker (Offline Mode)         ║
// ║  يخزّن الدروس والمفردات أوفلاين ويزامن الكويزات تلقائياً ║
// ╚══════════════════════════════════════════════════════════╝

const CACHE_NAME   = "yamen-academy-v3";
const STATIC_CACHE = "yamen-static-v3";
const API_CACHE    = "yamen-api-v3";
const IDB_NAME     = "YamenOfflineDB";
const IDB_VERSION  = 2;

// ── الموارد الثابتة للتخزين فوراً ──────────────────────────────
const STATIC_ASSETS = [
  "/",
  "/index.html",
  "/manifest.json",
  "/style.css",
  "/app.js",
  "/offline.js",
  "/config.js",
  "/favicon.ico",
  "/icons/icon-192.png",
  "/icons/icon-512.png",
];

// ── مسارات API التي تُخزَّن مؤقتاً ─────────────────────────────
const CACHEABLE_API = [
  "/api/student/profile",
  "/api/questions",
  "/api/leaderboard",
  "/api/errors/summary",
  "/api/student/tasks",
];

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// INSTALL — تثبيت وتخزين الموارد الثابتة
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
self.addEventListener("install", (event) => {
  console.log("[SW] Installing Yamen Academy v3...");
  event.waitUntil(
    caches.open(STATIC_CACHE).then((cache) => {
      // تخزين الموارد الثابتة مع تجاهل الأخطاء الفردية
      return Promise.allSettled(
        STATIC_ASSETS.map((url) =>
          cache.add(url).catch((e) =>
            console.warn(`[SW] لم يتم تخزين ${url}: ${e.message}`)
          )
        )
      );
    })
  );
  self.skipWaiting();
});

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// ACTIVATE — حذف الكاشات القديمة
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
self.addEventListener("activate", (event) => {
  console.log("[SW] Activating...");
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((k) => ![STATIC_CACHE, API_CACHE].includes(k))
          .map((k) => {
            console.log(`[SW] حذف كاش قديم: ${k}`);
            return caches.delete(k);
          })
      )
    )
  );
  self.clients.claim();
});

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// FETCH — استراتيجية التخزين الذكية
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
self.addEventListener("fetch", (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // تجاهل طلبات غير HTTP وطلبات المزامنة الخلفية
  if (!request.url.startsWith("http")) return;
  if (request.method !== "GET") {
    // للطلبات POST/PUT — حاول إرسالها، وإذا فشل خزّنها في IDB
    if (request.method === "POST" && isApiRequest(url)) {
      event.respondWith(fetchWithFallback(request));
    }
    return;
  }

  // موارد ثابتة → Cache First
  if (isStaticAsset(url)) {
    event.respondWith(cacheFirst(request, STATIC_CACHE));
    return;
  }

  // API calls → Network First مع Cache Fallback
  if (isApiRequest(url)) {
    event.respondWith(networkFirstWithCache(request));
    return;
  }

  // باقي الطلبات → Network مع Offline Fallback
  event.respondWith(networkWithOfflineFallback(request));
});

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// استراتيجيات التخزين
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

/** Cache First: ابحث في الكاش أولاً، إذا لم يوجد → الشبكة */
async function cacheFirst(request, cacheName) {
  const cached = await caches.match(request);
  if (cached) return cached;
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(cacheName);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    return offlinePage();
  }
}

/** Network First: جرب الشبكة، إذا فشل → الكاش */
async function networkFirstWithCache(request) {
  try {
    const response = await fetch(request.clone());
    if (response.ok) {
      const url = new URL(request.url);
      // خزّن فقط نقاط API المسموح بها
      if (CACHEABLE_API.some((p) => url.pathname.startsWith(p))) {
        const cache = await caches.open(API_CACHE);
        cache.put(request, response.clone());
      }
    }
    return response;
  } catch {
    const cached = await caches.match(request);
    if (cached) {
      console.log(`[SW] Offline — من الكاش: ${request.url}`);
      return cached;
    }
    return jsonOfflineResponse();
  }
}

/** Network with Offline Fallback */
async function networkWithOfflineFallback(request) {
  try {
    return await fetch(request);
  } catch {
    const cached = await caches.match(request);
    if (cached) return cached;
    return offlinePage();
  }
}

/** محاولة POST مع حفظ في IDB عند الفشل */
async function fetchWithFallback(request) {
  try {
    const response = await fetch(request.clone());
    // عند نجاح الاتصال → حاول مزامنة الطلبات المعلقة
    syncPendingRequests();
    return response;
  } catch {
    // أوفلاين → خزّن في IndexedDB
    const body = await request.clone().text();
    await idbSaveRequest({
      url: request.url,
      method: request.method,
      body,
      timestamp: Date.now(),
    });
    return new Response(
      JSON.stringify({ offline: true, message: "سيتم المزامنة عند الاتصال" }),
      { status: 202, headers: { "Content-Type": "application/json" } }
    );
  }
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// IndexedDB — تخزين نتائج الكويزات ومزامنتها
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

/** فتح IndexedDB */
function openIDB() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(IDB_NAME, IDB_VERSION);
    req.onupgradeneeded = (e) => {
      const db = e.target.result;
      // مخزن الطلبات المعلقة (نتائج الكويزات أوفلاين)
      if (!db.objectStoreNames.contains("pending_requests")) {
        const store = db.createObjectStore("pending_requests", {
          keyPath: "id",
          autoIncrement: true,
        });
        store.createIndex("timestamp", "timestamp", { unique: false });
      }
      // مخزن الدروس والمفردات
      if (!db.objectStoreNames.contains("lessons_cache")) {
        db.createObjectStore("lessons_cache", { keyPath: "key" });
      }
      // مخزن نتائج الكويزات المحلية
      if (!db.objectStoreNames.contains("quiz_results")) {
        const qStore = db.createObjectStore("quiz_results", {
          keyPath: "id",
          autoIncrement: true,
        });
        qStore.createIndex("student_id", "student_id", { unique: false });
        qStore.createIndex("synced", "synced", { unique: false });
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror   = () => reject(req.error);
  });
}

/** حفظ طلب معلق في IDB */
async function idbSaveRequest(data) {
  try {
    const db = await openIDB();
    return new Promise((resolve, reject) => {
      const tx = db.transaction("pending_requests", "readwrite");
      tx.objectStore("pending_requests").add(data);
      tx.oncomplete = resolve;
      tx.onerror    = () => reject(tx.error);
    });
  } catch (e) {
    console.error("[SW] IDB Save Error:", e);
  }
}

/** مزامنة الطلبات المعلقة مع الخادم */
async function syncPendingRequests() {
  try {
    const db = await openIDB();
    const pending = await new Promise((resolve, reject) => {
      const tx = db.transaction("pending_requests", "readonly");
      const req = tx.objectStore("pending_requests").getAll();
      req.onsuccess = () => resolve(req.result);
      req.onerror   = () => reject(req.error);
    });

    if (pending.length === 0) return;
    console.log(`[SW] مزامنة ${pending.length} طلب معلق…`);

    for (const item of pending) {
      try {
        const response = await fetch(item.url, {
          method: item.method,
          body: item.body,
          headers: { "Content-Type": "application/json" },
        });
        if (response.ok) {
          // حذف من IDB بعد المزامنة الناجحة
          const delTx = db.transaction("pending_requests", "readwrite");
          delTx.objectStore("pending_requests").delete(item.id);
          console.log(`[SW] ✅ مزامنة: ${item.url}`);
        }
      } catch {
        // لا يزال أوفلاين، سنحاول لاحقاً
      }
    }

    // أخبر العملاء بنجاح المزامنة
    const clients = await self.clients.matchAll();
    clients.forEach((c) =>
      c.postMessage({ type: "SYNC_COMPLETE", count: pending.length })
    );
  } catch (e) {
    console.error("[SW] Sync Error:", e);
  }
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// Background Sync — مزامنة تلقائية عند عودة الإنترنت
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
self.addEventListener("sync", (event) => {
  if (event.tag === "yamen-sync-quiz") {
    console.log("[SW] Background Sync: مزامنة نتائج الكويزات…");
    event.waitUntil(syncPendingRequests());
  }
});

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// Push Notifications
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
self.addEventListener("push", (event) => {
  const data = event.data ? event.data.json() : {};
  const title = data.title || "أكاديمية يامن";
  const options = {
    body:  data.body  || "لديك رسالة جديدة",
    icon:  "/icons/icon-192.png",
    badge: "/icons/icon-192.png",
    data:  { url: data.url || "/" },
    vibrate: [200, 100, 200],
    requireInteraction: false,
    actions: [
      { action: "open",    title: "📚 افتح الأكاديمية" },
      { action: "dismiss", title: "❌ تجاهل" },
    ],
  };
  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  if (event.action === "dismiss") return;
  const targetUrl = event.notification.data?.url || "/";
  event.waitUntil(
    self.clients.matchAll({ type: "window" }).then((clients) => {
      for (const c of clients) {
        if (c.url === targetUrl && "focus" in c) return c.focus();
      }
      return self.clients.openWindow(targetUrl);
    })
  );
});

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// رسائل من الصفحة → Service Worker
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
self.addEventListener("message", (event) => {
  const { type, payload } = event.data || {};

  switch (type) {
    case "CACHE_LESSON":
      // تخزين نص درس من الصفحة
      cacheLesson(payload).then(() =>
        event.source?.postMessage({ type: "LESSON_CACHED", key: payload.key })
      );
      break;

    case "SAVE_QUIZ_RESULT":
      // حفظ نتيجة كويز أوفلاين
      saveQuizResult(payload).then(() => {
        event.source?.postMessage({ type: "QUIZ_SAVED" });
        // حاول المزامنة فوراً
        syncPendingRequests();
      });
      break;

    case "FORCE_SYNC":
      // مزامنة يدوية من الصفحة
      syncPendingRequests().then(() =>
        event.source?.postMessage({ type: "SYNC_DONE" })
      );
      break;

    case "SKIP_WAITING":
      self.skipWaiting();
      break;
  }
});

/** تخزين درس في IDB */
async function cacheLesson(lesson) {
  try {
    const db = await openIDB();
    return new Promise((resolve, reject) => {
      const tx = db.transaction("lessons_cache", "readwrite");
      tx.objectStore("lessons_cache").put({
        key:       lesson.key,
        title:     lesson.title,
        content:   lesson.content,
        vocab:     lesson.vocab || [],
        cached_at: Date.now(),
      });
      tx.oncomplete = resolve;
      tx.onerror    = () => reject(tx.error);
    });
  } catch (e) {
    console.error("[SW] Cache Lesson Error:", e);
  }
}

/** حفظ نتيجة كويز */
async function saveQuizResult(result) {
  try {
    const db = await openIDB();
    // حفظ في quiz_results
    await new Promise((resolve, reject) => {
      const tx = db.transaction("quiz_results", "readwrite");
      tx.objectStore("quiz_results").add({
        ...result,
        synced:     false,
        created_at: Date.now(),
      });
      tx.oncomplete = resolve;
      tx.onerror    = () => reject(tx.error);
    });
    // إضافة لقائمة الطلبات المعلقة للمزامنة
    await idbSaveRequest({
      url:       "/api/questions/check",
      method:    "POST",
      body:      JSON.stringify(result),
      timestamp: Date.now(),
    });
  } catch (e) {
    console.error("[SW] Save Quiz Error:", e);
  }
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// Helper Functions
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
function isStaticAsset(url) {
  return (
    url.pathname.match(/\.(html|css|js|png|jpg|ico|webp|svg|woff2?)$/) ||
    url.pathname === "/" ||
    STATIC_ASSETS.includes(url.pathname)
  );
}

function isApiRequest(url) {
  return url.pathname.startsWith("/api/");
}

function offlinePage() {
  return caches.match("/index.html").then(
    (r) =>
      r ||
      new Response(
        `<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="UTF-8">
  <title>أوفلاين — أكاديمية يامن</title>
  <style>
    body { font-family: sans-serif; text-align: center; padding: 40px;
           background: #0f172a; color: #e2e8f0; }
    h1 { color: #f59e0b; font-size: 2rem; }
    p  { color: #94a3b8; }
    button { background: #f59e0b; color: #000; border: none;
             padding: 12px 24px; border-radius: 8px; font-size: 1rem;
             cursor: pointer; margin-top: 20px; }
  </style>
</head>
<body>
  <h1>📶 أنت أوفلاين</h1>
  <p>الدروس المحفوظة متاحة. ستتم المزامنة عند الاتصال.</p>
  <button onclick="location.reload()">🔄 إعادة المحاولة</button>
</body>
</html>`,
        { status: 200, headers: { "Content-Type": "text/html; charset=utf-8" } }
      )
  );
}

function jsonOfflineResponse() {
  return new Response(
    JSON.stringify({
      offline: true,
      error:   "أنت أوفلاين — البيانات محفوظة محلياً",
    }),
    {
      status:  200,
      headers: { "Content-Type": "application/json; charset=utf-8" },
    }
  );
}
