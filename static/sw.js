const VERSION = 'v1';
const STATIC_CACHE = `timetrack-static-${VERSION}`;
const RUNTIME_CACHE = `timetrack-runtime-${VERSION}`;

const STATIC_ASSETS = [
    '/static/style.css',
    '/static/manifest.json',
    '/static/icons/icon-192x192.png',
    '/static/icons/icon-512x512.png',
    'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap',
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css'
];

self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(STATIC_CACHE).then(cache => cache.addAll(STATIC_ASSETS))
    );
    self.skipWaiting();
});

self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(keys =>
            Promise.all(
                keys.filter(k => ![STATIC_CACHE, RUNTIME_CACHE].includes(k))
                    .map(k => caches.delete(k))
            )
        ).then(() => self.clients.claim())
    );
});

self.addEventListener('message', event => {
    if (event.data && event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    }
});

self.addEventListener('fetch', event => {
    const req = event.request;
    const url = new URL(req.url);

    // Skip API calls – always go to network
    if (url.pathname.startsWith('/api/')) {
        event.respondWith(fetch(req));
        return;
    }

    // Network-first for navigation
    if (req.mode === 'navigate' || req.destination === 'document') {
        event.respondWith(
            fetch(req)
                .then(res => {
                    const copy = res.clone();
                    caches.open(RUNTIME_CACHE).then(cache => cache.put(req, copy));
                    return res;
                })
                .catch(() => caches.match(req))
        );
        return;
    }

    // Stale-while-revalidate for static assets
    if (STATIC_ASSETS.some(asset => url.href.includes(asset))) {
        event.respondWith(
            caches.match(req).then(cached => {
                const fetchPromise = fetch(req)
                    .then(networkRes => {
                        caches.open(STATIC_CACHE).then(cache => cache.put(req, networkRes.clone()));
                        return networkRes;
                    })
                    .catch(() => cached);
                return cached || fetchPromise;
            })
        );
        return;
    }

    // Default: cache fallback
    event.respondWith(
        caches.match(req).then(cached => cached || fetch(req))
    );
});
