/**
 * Vardiya Takvimi - Service Worker
 * Offline caching ve PWA desteği
 */

const CACHE_NAME = 'vardiya-takvimi-v3';
const STATIC_CACHE = 'vardiya-static-v3';

// Önbelleğe alınacak dosyalar
const STATIC_ASSETS = [
    '/',
    '/static/css/style.css',
    '/static/js/app.js',
    '/static/js/ics.js',
    '/static/js/activities.js',
    '/static/js/i18n.js',
    '/static/js/templates.js',
    '/static/manifest.json'
];

// CDN kaynakları (network-first stratejisi)
const CDN_ASSETS = [
    'https://fonts.googleapis.com',
    'https://fonts.gstatic.com',
    'https://cdnjs.cloudflare.com/ajax/libs/cropperjs',
    'https://cdn.jsdelivr.net/npm/tesseract.js'
];

// Install event - static assets'i önbelleğe al
self.addEventListener('install', (event) => {
    console.log('[SW] Installing Service Worker...');
    
    event.waitUntil(
        caches.open(STATIC_CACHE)
            .then((cache) => {
                console.log('[SW] Caching static assets');
                return cache.addAll(STATIC_ASSETS);
            })
            .then(() => {
                console.log('[SW] Static assets cached');
                return self.skipWaiting();
            })
            .catch((error) => {
                console.error('[SW] Cache error:', error);
            })
    );
});

// Activate event - eski cache'leri temizle
self.addEventListener('activate', (event) => {
    console.log('[SW] Activating Service Worker...');
    
    event.waitUntil(
        caches.keys()
            .then((cacheNames) => {
                return Promise.all(
                    cacheNames
                        .filter((name) => name !== STATIC_CACHE && name !== CACHE_NAME)
                        .map((name) => {
                            console.log('[SW] Deleting old cache:', name);
                            return caches.delete(name);
                        })
                );
            })
            .then(() => {
                console.log('[SW] Service Worker activated');
                return self.clients.claim();
            })
    );
});

// Fetch event - cache stratejisi
self.addEventListener('fetch', (event) => {
    const { request } = event;
    const url = new URL(request.url);
    
    // API istekleri için ağı kullan
    if (url.pathname.startsWith('/generate-plan') || url.pathname.startsWith('/api')) {
        event.respondWith(networkFirst(request));
        return;
    }
    
    // CDN kaynakları için ağ öncelikli
    if (CDN_ASSETS.some(cdn => request.url.includes(cdn))) {
        event.respondWith(networkFirst(request));
        return;
    }
    
    // Static assets için cache-first stratejisi
    if (request.destination === 'style' || 
        request.destination === 'script' || 
        request.destination === 'image' ||
        url.pathname.startsWith('/static/')) {
        event.respondWith(cacheFirst(request));
        return;
    }
    
    // HTML için stale-while-revalidate
    if (request.mode === 'navigate') {
        event.respondWith(staleWhileRevalidate(request));
        return;
    }
    
    // Diğer istekler için network-first
    event.respondWith(networkFirst(request));
});

// Cache-first stratejisi
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
        console.error('[SW] Fetch error:', error);
        return new Response('Offline', { status: 503 });
    }
}

// Network-first stratejisi
async function networkFirst(request) {
    try {
        const response = await fetch(request);
        if (response.ok) {
            const cache = await caches.open(CACHE_NAME);
            cache.put(request, response.clone());
        }
        return response;
    } catch (error) {
        const cached = await caches.match(request);
        if (cached) {
            return cached;
        }
        return new Response('Offline', { status: 503 });
    }
}

// Stale-while-revalidate stratejisi
async function staleWhileRevalidate(request) {
    const cached = await caches.match(request);
    
    const fetchPromise = fetch(request)
        .then((response) => {
            if (response.ok) {
                const cache = caches.open(CACHE_NAME);
                cache.then(c => c.put(request, response.clone()));
            }
            return response;
        })
        .catch(() => cached);
    
    return cached || fetchPromise;
}

// Push notification handler (gelecek için)
self.addEventListener('push', (event) => {
    if (event.data) {
        const data = event.data.json();
        
        const options = {
            body: data.body || 'Yeni bildirim',
            icon: '/static/icons/icon-192x192.png',
            badge: '/static/icons/icon-72x72.png',
            vibrate: [100, 50, 100],
            data: {
                url: data.url || '/'
            }
        };
        
        event.waitUntil(
            self.registration.showNotification(data.title || 'Vardiya Takvimi', options)
        );
    }
});

// Notification click handler
self.addEventListener('notificationclick', (event) => {
    event.notification.close();
    
    event.waitUntil(
        clients.openWindow(event.notification.data.url || '/')
    );
});

console.log('[SW] Service Worker loaded');
