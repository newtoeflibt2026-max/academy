// Yamen Academy — Service Worker v3 (offline lessons)
const CACHE_VERSION = 'yamen-v1781223601';
const STATIC_CACHE  = CACHE_VERSION + '-static';
const PAGES_CACHE   = CACHE_VERSION + '-pages';
const RUNTIME_CACHE = CACHE_VERSION + '-runtime';

// أصول ثابتة تُحمّل عند التثبيت
const STATIC_ASSETS = [
  '/static/style.css',
  '/static/app.js',
  '/static/manifest.json',
  '/static/offline.html',
  '/static/icon-192.svg',
  '/static/icon-512.svg'
];

// مسارات التمارين التفاعلية (تحتاج إنترنت دائماً)
const ONLINE_ONLY = [
  '/reading/cw/exam/',
  '/reading/cw/submit',
  '/foundation/quiz/',
  '/api/',
  '/admin/',
  '/webhook',
  '/student'
];

// مسارات الدروس النظرية (تُحفظ للعرض بلا نت)
const CACHEABLE_PAGES = [
  '/foundation',
  '/foundation/stage/',
  '/foundation/lesson/',
  '/reading/cw/learn',
  '/mistakes'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE).then((cache) =>
      cache.addAll(STATIC_ASSETS).catch(() => null)
    ).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys.filter((k) => !k.startsWith(CACHE_VERSION))
            .map((k) => caches.delete(k))
      )
    ).then(() => self.clients.claim())
  );
});

function isOnlineOnly(url) {
  return ONLINE_ONLY.some((p) => url.pathname.startsWith(p) || url.pathname.includes(p));
}

function isCacheablePage(url) {
  return CACHEABLE_PAGES.some((p) => url.pathname === p || url.pathname.startsWith(p));
}

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;

  const url = new URL(req.url);
  if (url.origin !== location.origin) return;

  // 1) المسارات التي تحتاج إنترنت → network-only مع fallback لصفحة offline
  if (isOnlineOnly(url)) {
    event.respondWith(
      fetch(req).catch(() => caches.match('/static/offline.html'))
    );
    return;
  }

  // 2) الأصول الثابتة (CSS/JS/IMG) → cache-first
  if (url.pathname.startsWith('/static/')) {
    event.respondWith(
      caches.match(req).then((cached) =>
        cached || fetch(req).then((res) => {
          const copy = res.clone();
          caches.open(RUNTIME_CACHE).then((c) => c.put(req, copy));
          return res;
        }).catch(() => cached)
      )
    );
    return;
  }

  // 3) صفحات الدروس النظرية → stale-while-revalidate
  if (isCacheablePage(url)) {
    event.respondWith(
      caches.open(PAGES_CACHE).then((cache) =>
        cache.match(req).then((cached) => {
          const fetchPromise = fetch(req).then((res) => {
            if (res && res.status === 200) cache.put(req, res.clone());
            return res;
          }).catch(() => cached || caches.match('/static/offline.html'));
          return cached || fetchPromise;
        })
      )
    );
    return;
  }

  // 4) باقي الطلبات → network-first مع fallback من الكاش
  event.respondWith(
    fetch(req).then((res) => {
      if (res && res.status === 200) {
        const copy = res.clone();
        caches.open(RUNTIME_CACHE).then((c) => c.put(req, copy));
      }
      return res;
    }).catch(() => caches.match(req).then((c) => c || caches.match('/static/offline.html')))
  );
});
