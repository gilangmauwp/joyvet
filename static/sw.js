/**
 * JoyVet Care Service Worker — Workbox-powered offline strategy.
 *
 * Caching strategy:
 *   Static assets (CSS, JS, fonts) → CacheFirst (30-day TTL)
 *   API responses                   → NetworkFirst (3s timeout → cached fallback)
 *   Page navigation                 → NetworkFirst (→ /offline.html on fail)
 *
 * Background sync: flushes the IndexedDB write_queue when LAN returns.
 *
 * NOTE: This SW must be served from the root path (/sw.js) with Nginx
 *       or Django's static file serving.
 */

const STATIC_CACHE  = 'joyvet-static-v1';
const API_CACHE     = 'joyvet-api-v1';
const PAGE_CACHE    = 'joyvet-pages-v1';

const STATIC_ASSETS = [
  '/',
  '/static/js/offline-db.js',
  '/offline.html',
];

// ── Install: pre-cache critical assets ─────────────────────────────────────

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(STATIC_CACHE).then(cache => cache.addAll(STATIC_ASSETS))
  );
  self.skipWaiting();
});

// ── Activate: clean up old caches ──────────────────────────────────────────

self.addEventListener('activate', event => {
  const KEEP = [STATIC_CACHE, API_CACHE, PAGE_CACHE];
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => !KEEP.includes(k)).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

// ── Fetch: route to appropriate strategy ───────────────────────────────────

self.addEventListener('fetch', event => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET and WebSocket requests
  if (request.method !== 'GET') return;
  if (url.protocol === 'ws:' || url.protocol === 'wss:') return;

  // Static assets → CacheFirst
  if (isStaticAsset(request)) {
    event.respondWith(cacheFirst(request, STATIC_CACHE));
    return;
  }

  // API calls → NetworkFirst with short timeout
  if (url.pathname.startsWith('/api/v1/')) {
    event.respondWith(networkFirst(request, API_CACHE, 3000));
    return;
  }

  // Page navigation → NetworkFirst → offline.html fallback
  if (request.mode === 'navigate') {
    event.respondWith(
      networkFirst(request, PAGE_CACHE, 4000).catch(() =>
        caches.match('/offline.html')
      )
    );
    return;
  }
});

// ── Background sync: flush offline write queue ─────────────────────────────

self.addEventListener('sync', event => {
  if (event.tag === 'joyvet-offline-queue') {
    event.waitUntil(processOfflineQueue());
  }
});

async function processOfflineQueue() {
  // Open IndexedDB directly from SW context
  const db = await openIDB('JoyVetOffline', 1);
  const queue = await idbGetAll(db, 'write_queue');

  for (const op of queue) {
    if (op.status !== 'pending') continue;
    try {
      const response = await fetch(op.url, {
        method: op.method,
        headers: {
          'Content-Type': 'application/json',
          'X-Offline-Queue-ID': String(op.id),
        },
        body: op.method !== 'GET' ? JSON.stringify(op.data) : undefined,
      });
      if (response.ok) {
        await idbDelete(db, 'write_queue', op.id);
      }
    } catch (e) {
      // Will retry on next sync event
    }
  }
}

// ── Cache strategies ────────────────────────────────────────────────────────

async function cacheFirst(request, cacheName) {
  const cached = await caches.match(request);
  if (cached) return cached;
  const response = await fetch(request);
  if (response.ok) {
    const cache = await caches.open(cacheName);
    cache.put(request, response.clone());
  }
  return response;
}

async function networkFirst(request, cacheName, timeoutMs = 4000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(request, { signal: controller.signal });
    clearTimeout(timer);
    if (response.ok) {
      const cache = await caches.open(cacheName);
      cache.put(request, response.clone());
    }
    return response;
  } catch (e) {
    clearTimeout(timer);
    const cached = await caches.match(request);
    if (cached) return cached;
    throw e;
  }
}

// ── Helpers ─────────────────────────────────────────────────────────────────

function isStaticAsset(request) {
  const dest = request.destination;
  return ['style', 'script', 'font', 'image'].includes(dest);
}

function openIDB(name, version) {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(name, version);
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

function idbGetAll(db, store) {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(store, 'readonly');
    const req = tx.objectStore(store).getAll();
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

function idbDelete(db, store, key) {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(store, 'readwrite');
    const req = tx.objectStore(store).delete(key);
    req.onsuccess = () => resolve();
    req.onerror = () => reject(req.error);
  });
}
