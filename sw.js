self.addEventListener('install', (event) => {
    console.log('[sw] Installing...');
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    console.log('[sw] Activated');
    event.waitUntil(
        caches.keys().then(keys => Promise.all(keys.map(key => caches.delete(key))))
    );
});

self.addEventListener('fetch', (event) => {
    event.respondWith(fetch(event.request).catch(() => caches.match(event.request)));
});
