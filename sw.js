// Yamen Academy Service Worker v7
self.addEventListener("install", function(event) {
    console.log("[SW] Install");
    self.skipWaiting();
    event.waitUntil(
        caches.open("yamen-v7").then(function(cache) {
            return cache.addAll([
                "/",
                "/index.html",
                "/style.css",
                "/app.js",
                "/config.js",
                "/manifest.json"
            ]);
        })
    );
});

self.addEventListener("activate", function(event) {
    console.log("[SW] Activate");
    event.waitUntil(
        caches.keys().then(function(keys) {
            return Promise.all(
                keys.filter(function(k) { return k !== "yamen-v7"; })
                    .map(function(k) { return caches.delete(k); })
            );
        }).then(function() {
            return self.clients.claim();
        })
    );
});

self.addEventListener("fetch", function(event) {
    if (event.request.url.includes("/api/")) {
        return fetch(event.request);
    }
    event.respondWith(
        caches.match(event.request).then(function(cached) {
            return cached || fetch(event.request).catch(function() {
                return caches.match("/index.html");
            });
        })
    );
});
