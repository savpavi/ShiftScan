/**
 * ShiftScan - Service Worker
 *
 * Bu dosya /sw.js olarak sunucudan servis edilir; __SW_VERSION__ yerine
 * sunucu her deploy'da yeni bir surum yazar (SOURCE_COMMIT ya da static
 * icerik hash'i). Boylece cache adi elle yukseltilmez: yeni surum yeni
 * cache acar, activate eski cache'leri siler.
 *
 * Yalnizca GET istekleri ele alinir. /generate-plan ve /ocr POST'lari
 * (ve diger tum GET-disi istekler) hic yakalanmaz - Cache API POST'u
 * saklayamaz, eski surum bunu deniyordu.
 */

const VERSION = '__SW_VERSION__';
const STATIC_CACHE = `shiftscan-static-${VERSION}`;
const RUNTIME_CACHE = `shiftscan-runtime-${VERSION}`;

// Onbellege alinacak dosyalar (index.html'in yukledigi her yerel dosya)
const STATIC_ASSETS = [
    '/',
    '/static/css/style.css',
    '/static/js/i18n.js',
    '/static/js/templates.js',
    '/static/js/export.js',
    '/static/js/ics.js',
    '/static/js/activities.js',
    '/static/js/ocrparse.js',
    '/static/js/app.js',
    '/static/manifest.json',
    '/static/icons/icon.svg'
];

// CDN kaynaklari (ag oncelikli)
const CDN_HOSTS = [
    'https://fonts.googleapis.com',
    'https://fonts.gstatic.com',
    'https://cdnjs.cloudflare.com/ajax/libs/cropperjs',
    'https://cdn.jsdelivr.net/npm/tesseract.js'
];

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(STATIC_CACHE)
            .then((cache) => cache.addAll(STATIC_ASSETS))
            .then(() => self.skipWaiting())
            .catch((error) => console.error('[SW] Cache error:', error))
    );
});

self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys()
            .then((names) => Promise.all(
                names
                    .filter((name) => name !== STATIC_CACHE && name !== RUNTIME_CACHE)
                    .map((name) => caches.delete(name))
            ))
            .then(() => self.clients.claim())
    );
});

self.addEventListener('fetch', (event) => {
    const { request } = event;

    // GET disi hicbir istek SW'den gecmez (POST /ocr, POST /generate-plan)
    if (request.method !== 'GET') {
        return;
    }

    const url = new URL(request.url);

    if (url.pathname.startsWith('/api') || url.pathname === '/health') {
        event.respondWith(networkFirst(request));
        return;
    }

    if (CDN_HOSTS.some((host) => request.url.startsWith(host))) {
        event.respondWith(networkFirst(request));
        return;
    }

    if (url.origin === self.location.origin && url.pathname.startsWith('/static/')) {
        event.respondWith(cacheFirst(request));
        return;
    }

    if (request.mode === 'navigate') {
        event.respondWith(staleWhileRevalidate(request));
        return;
    }

    event.respondWith(networkFirst(request));
});

async function cacheFirst(request) {
    const cached = await caches.match(request);
    if (cached) {
        return cached;
    }
    try {
        const response = await fetch(request);
        if (response.ok) {
            const cache = await caches.open(STATIC_CACHE);
            cache.put(request, response.clone());
        }
        return response;
    } catch (error) {
        return new Response('Offline', { status: 503 });
    }
}

async function networkFirst(request) {
    try {
        const response = await fetch(request);
        if (response.ok) {
            const cache = await caches.open(RUNTIME_CACHE);
            cache.put(request, response.clone());
        }
        return response;
    } catch (error) {
        const cached = await caches.match(request);
        return cached || new Response('Offline', { status: 503 });
    }
}

async function staleWhileRevalidate(request) {
    const cached = await caches.match(request);
    const fetchPromise = fetch(request)
        .then((response) => {
            if (response.ok) {
                caches.open(RUNTIME_CACHE).then((cache) => cache.put(request, response.clone()));
            }
            return response;
        })
        .catch(() => cached);
    return cached || fetchPromise;
}
