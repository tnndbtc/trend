/**
 * Service Worker for Trend Intelligence Platform
 *
 * Provides offline caching for:
 * - Translation data
 * - Static assets (CSS, JS)
 * - API responses
 */

const CACHE_VERSION = 'v1.0.0';
const CACHE_NAME = `trend-intelligence-${CACHE_VERSION}`;

// Assets to cache on install
const STATIC_ASSETS = [
    '/',
    '/static/css/styles.css',
];

// Cache strategies
const CACHE_STRATEGIES = {
    // Network first, fallback to cache (for dynamic content)
    NETWORK_FIRST: 'network-first',
    // Cache first, fallback to network (for static assets)
    CACHE_FIRST: 'cache-first',
    // Network only (no caching)
    NETWORK_ONLY: 'network-only',
    // Cache only (offline-first)
    CACHE_ONLY: 'cache-only',
};

/**
 * Determine cache strategy based on request URL
 */
function getCacheStrategy(url) {
    // Translation API - cache first for speed
    if (url.includes('/api/translation/trends/')) {
        return CACHE_STRATEGIES.CACHE_FIRST;
    }

    // Static assets - cache first
    if (url.includes('/static/')) {
        return CACHE_STRATEGIES.CACHE_FIRST;
    }

    // Trend pages - network first for freshness
    if (url.includes('/trends/')) {
        return CACHE_STRATEGIES.NETWORK_FIRST;
    }

    // Default: network first
    return CACHE_STRATEGIES.NETWORK_FIRST;
}

/**
 * Install event - cache static assets
 */
self.addEventListener('install', (event) => {
    console.log('[ServiceWorker] Installing...');

    event.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => {
                console.log('[ServiceWorker] Caching static assets');
                return cache.addAll(STATIC_ASSETS);
            })
            .then(() => {
                console.log('[ServiceWorker] Installed successfully');
                // Activate immediately
                return self.skipWaiting();
            })
            .catch((error) => {
                console.error('[ServiceWorker] Installation failed:', error);
            })
    );
});

/**
 * Activate event - clean up old caches
 */
self.addEventListener('activate', (event) => {
    console.log('[ServiceWorker] Activating...');

    event.waitUntil(
        caches.keys()
            .then((cacheNames) => {
                return Promise.all(
                    cacheNames.map((cacheName) => {
                        // Delete old cache versions
                        if (cacheName !== CACHE_NAME && cacheName.startsWith('trend-intelligence-')) {
                            console.log('[ServiceWorker] Deleting old cache:', cacheName);
                            return caches.delete(cacheName);
                        }
                    })
                );
            })
            .then(() => {
                console.log('[ServiceWorker] Activated successfully');
                // Take control of all clients immediately
                return self.clients.claim();
            })
    );
});

/**
 * Fetch event - intercept network requests
 */
self.addEventListener('fetch', (event) => {
    const url = event.request.url;
    const strategy = getCacheStrategy(url);

    // Handle different cache strategies
    if (strategy === CACHE_STRATEGIES.CACHE_FIRST) {
        event.respondWith(cacheFirst(event.request));
    } else if (strategy === CACHE_STRATEGIES.NETWORK_FIRST) {
        event.respondWith(networkFirst(event.request));
    } else if (strategy === CACHE_STRATEGIES.CACHE_ONLY) {
        event.respondWith(cacheOnly(event.request));
    } else {
        // NETWORK_ONLY or default
        event.respondWith(fetch(event.request));
    }
});

/**
 * Cache first strategy
 * Try cache first, fallback to network
 */
async function cacheFirst(request) {
    const cachedResponse = await caches.match(request);

    if (cachedResponse) {
        console.log('[ServiceWorker] Cache hit:', request.url);
        return cachedResponse;
    }

    console.log('[ServiceWorker] Cache miss, fetching:', request.url);

    try {
        const networkResponse = await fetch(request);

        // Cache successful responses
        if (networkResponse && networkResponse.status === 200) {
            const cache = await caches.open(CACHE_NAME);
            cache.put(request, networkResponse.clone());
        }

        return networkResponse;
    } catch (error) {
        console.error('[ServiceWorker] Fetch failed:', error);
        // Return offline page or error response
        return new Response('Offline', {
            status: 503,
            statusText: 'Service Unavailable'
        });
    }
}

/**
 * Network first strategy
 * Try network first, fallback to cache
 */
async function networkFirst(request) {
    try {
        const networkResponse = await fetch(request);

        // Cache successful responses
        if (networkResponse && networkResponse.status === 200) {
            const cache = await caches.open(CACHE_NAME);
            cache.put(request, networkResponse.clone());
        }

        console.log('[ServiceWorker] Network response:', request.url);
        return networkResponse;
    } catch (error) {
        console.log('[ServiceWorker] Network failed, trying cache:', request.url);

        const cachedResponse = await caches.match(request);

        if (cachedResponse) {
            console.log('[ServiceWorker] Cache fallback hit:', request.url);
            return cachedResponse;
        }

        console.error('[ServiceWorker] No cache available:', error);
        return new Response('Offline', {
            status: 503,
            statusText: 'Service Unavailable'
        });
    }
}

/**
 * Cache only strategy
 * Only serve from cache
 */
async function cacheOnly(request) {
    const cachedResponse = await caches.match(request);

    if (cachedResponse) {
        return cachedResponse;
    }

    return new Response('Not in cache', {
        status: 404,
        statusText: 'Not Found'
    });
}

/**
 * Message event - handle messages from clients
 */
self.addEventListener('message', (event) => {
    if (event.data && event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    }

    if (event.data && event.data.type === 'CLEAR_CACHE') {
        event.waitUntil(
            caches.keys().then((cacheNames) => {
                return Promise.all(
                    cacheNames.map((cacheName) => caches.delete(cacheName))
                );
            })
        );
    }

    if (event.data && event.data.type === 'CACHE_URLS') {
        const urls = event.data.urls || [];
        event.waitUntil(
            caches.open(CACHE_NAME).then((cache) => {
                return cache.addAll(urls);
            })
        );
    }
});

/**
 * Sync event - background sync for offline actions
 */
self.addEventListener('sync', (event) => {
    console.log('[ServiceWorker] Background sync:', event.tag);

    if (event.tag === 'sync-translations') {
        event.waitUntil(syncTranslations());
    }
});

/**
 * Sync translations when back online
 */
async function syncTranslations() {
    console.log('[ServiceWorker] Syncing translations...');

    // Get pending translation requests from IndexedDB or Cache
    // This is a placeholder - implement based on your needs
    try {
        // Fetch latest translations
        const response = await fetch('/api/translation/trends/?sync=true');

        if (response.ok) {
            const data = await response.json();
            console.log('[ServiceWorker] Translations synced:', data);
        }
    } catch (error) {
        console.error('[ServiceWorker] Sync failed:', error);
    }
}

console.log('[ServiceWorker] Loaded');
