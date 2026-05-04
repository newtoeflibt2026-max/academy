// Yamen Academy — Service Worker for Offline Support
const CACHE_NAME = 'yamen-academy-v1';
const STATIC_ASSETS = [
    '/',
    '/index.html',
    '/style.css',
    '/app.js',
    '/config.js',
    '/manifest.json',
    '/icons/icon-192.png',
    '/icons/icon-512.png',
    'https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800&family=Inter:wght@400;500;600&display=swap'
];

// Install — cache static assets
self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => cache.addAll(STATIC_ASSETS))
            .then(() => self.skipWaiting())
    );
});

// Activate — clean old caches
self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(keys =>
            Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
        ).then(() => self.clients.claim())
    );
});

// Fetch — Network First, fallback to Cache
self.addEventListener('fetch', event => {
    const url = new URL(event.request.url);

    // API calls: Network only (don't cache live data)
    if (url.pathname.startsWith('/api/')) {
        event.respondWith(fetch(event.request).catch(() =>
            new Response(JSON.stringify({ offline: true, error: 'No connection' }), {
                status: 503,
                headers: { 'Content-Type': 'application/json' }
            })
        ));
        return;
    }

    // Static assets & Telegram file downloads: Network first, then cache
    if (url.hostname === 'api.telegram.org') {
        event.respondWith(
            caches.open('yamen-media').then(cache =>
                fetch(event.request)
                    .then(response => {
                        if (response.ok) {
                            cache.put(event.request, response.clone());
                        }
                        return response;
                    })
                    .catch(() => cache.match(event.request))
            )
        );
        return;
    }

    // All other: Cache falling back to network
    event.respondWith(
        caches.match(event.request).then(cached =>
            cached || fetch(event.request).then(response => {
                if (response.ok) {
                    const clone = response.clone();
                    caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
                }
                return response;
            })
        )
    );
});

// Background Sync — queue offline actions
self.addEventListener('sync', event => {
    if (event.tag === 'sync-quiz-answers') {
        event.waitUntil(syncQuizAnswers());
    }
});

async function syncQuizAnswers() {
    const db = await openIDB();
    const pending = await db.getAll('pendingAnswers');
    for (const item of pending) {
        try {
            await fetch('/api/quizzes/answer', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(item)
            });
            await db.delete('pendingAnswers', item.id);
        } catch (e) {
            console.log('Sync failed, will retry:', e);
        }
    }
}

function openIDB() {
    return new Promise((resolve, reject) => {
        const req = indexedDB.open('yamen-offline', 1);
        req.onupgradeneeded = () => {
            req.result.createObjectStore('pendingAnswers', { keyPath: 'id', autoIncrement: true });
            req.result.createObjectStore('lessons', { keyPath: 'id' });
            req.result.createObjectStore('mediaCache', { keyPath: 'url' });
        };
        req.onsuccess = () => resolve({
            getAll: (store) => new Promise((rs, rj) => {
                const tx = req.result.transaction(store, 'readonly');
                const r = tx.objectStore(store).getAll();
                r.onsuccess = () => rs(r.result);
                r.onerror = rj;
            }),
            delete: (store, id) => new Promise((rs, rj) => {
                const tx = req.result.transaction(store, 'readwrite');
                const r = tx.objectStore(store).delete(id);
                r.onsuccess = rs;
                r.onerror = rj;
            })
        });
        req.onerror = reject;
    });
}
