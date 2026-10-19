// NoteFlow Service Worker
// Strategies:
//   - Static assets (_next/static/): cache-first
//   - API calls (/api/, backend origin): network-first, fall back to cache
//   - Pages / navigation: stale-while-revalidate
//   - Offline audio: stored in IndexedDB by the app; SW handles background sync
//   - Push notifications: display with icon + badge

const CACHE_VERSION = "v2";
const STATIC_CACHE = `noteflow-static-${CACHE_VERSION}`;
const DYNAMIC_CACHE = `noteflow-dynamic-${CACHE_VERSION}`;
const API_CACHE = `noteflow-api-${CACHE_VERSION}`;
const AUDIO_SYNC_TAG = "noteflow-audio-upload";

const STATIC_ASSETS = [
  "/",
  "/dashboard",
  "/notes/new",
  "/manifest.json",
  "/offline.html",
];

// Detect the API origin at registration time via a custom URL param injected
// by next.config (see NEXT_PUBLIC_API_URL in the app shell script tag), or
// fall back to same-origin /api proxy path.
const API_ORIGIN = self.__NF_API_ORIGIN__ || null;

// ---------------------------------------------------------------------------
// Install — pre-cache app shell
// ---------------------------------------------------------------------------

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(STATIC_CACHE)
      .then((cache) =>
        cache.addAll(STATIC_ASSETS).catch(() => {
          // Non-fatal: offline.html may not exist yet during initial build
        })
      )
      .then(() => self.skipWaiting())
  );
});

// ---------------------------------------------------------------------------
// Activate — purge stale caches
// ---------------------------------------------------------------------------

self.addEventListener("activate", (event) => {
  const allowed = new Set([STATIC_CACHE, DYNAMIC_CACHE, API_CACHE]);
  event.waitUntil(
    caches
      .keys()
      .then((names) =>
        Promise.all(
          names
            .filter((n) => !allowed.has(n))
            .map((n) => caches.delete(n))
        )
      )
      .then(() => self.clients.claim())
  );
});

// ---------------------------------------------------------------------------
// Fetch — route by request type
// ---------------------------------------------------------------------------

self.addEventListener("fetch", (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Ignore non-GET mutations to API — let them fail offline naturally
  if (request.method !== "GET" && isApiRequest(url)) {
    return;
  }

  // Cache-first for immutable Next.js compiled assets
  if (url.pathname.startsWith("/_next/static/")) {
    event.respondWith(cacheFirst(request, STATIC_CACHE));
    return;
  }

  // Network-first for API calls (GET only — mutations already filtered above)
  if (request.method === "GET" && isApiRequest(url)) {
    event.respondWith(networkFirst(request, API_CACHE));
    return;
  }

  // Network-first for Next.js data-fetching (_next/data/)
  if (url.pathname.startsWith("/_next/data/")) {
    event.respondWith(networkFirst(request, DYNAMIC_CACHE));
    return;
  }

  // Stale-while-revalidate for HTML pages and everything else
  event.respondWith(staleWhileRevalidate(request, DYNAMIC_CACHE));
});

function isApiRequest(url) {
  if (API_ORIGIN && url.origin === API_ORIGIN) return true;
  return url.pathname.startsWith("/api/");
}

// ---------------------------------------------------------------------------
// Caching strategies
// ---------------------------------------------------------------------------

async function networkFirst(request, cacheName) {
  try {
    const response = await fetch(request.clone());
    if (response.ok) {
      const cache = await caches.open(cacheName);
      // Do not await cache.put — fire-and-forget
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    const cached = await caches.match(request);
    if (cached) return cached;
    // Return a structured offline error for API requests
    return new Response(
      JSON.stringify({ detail: "You are offline and this request is not cached." }),
      {
        status: 503,
        headers: {
          "Content-Type": "application/json",
          "X-NoteFlow-Offline": "true",
        },
      }
    );
  }
}

async function cacheFirst(request, cacheName) {
  const cached = await caches.match(request);
  if (cached) return cached;
  try {
    const response = await fetch(request.clone());
    if (response.ok) {
      const cache = await caches.open(cacheName);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    return new Response("Asset unavailable offline.", { status: 503 });
  }
}

async function staleWhileRevalidate(request, cacheName) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request);

  const revalidate = fetch(request.clone())
    .then((response) => {
      if (response.ok) cache.put(request, response.clone());
      return response;
    })
    .catch(() => null);

  // Return cached immediately; revalidation happens in the background
  if (cached) return cached;
  const fresh = await revalidate;
  return (
    fresh ||
    new Response("Page unavailable offline.", {
      status: 503,
      headers: { "Content-Type": "text/plain" },
    })
  );
}

// ---------------------------------------------------------------------------
// Background sync — flush pending audio uploads from IndexedDB
// ---------------------------------------------------------------------------

self.addEventListener("sync", (event) => {
  if (event.tag === AUDIO_SYNC_TAG) {
    event.waitUntil(syncPendingAudioUploads());
  }
});

async function syncPendingAudioUploads() {
  // Instruct all open app windows to drain their pending upload queues.
  // The app holds the actual IndexedDB data and FormData blobs; the SW
  // signals it to retry, keeping the service worker lightweight.
  const clients = await self.clients.matchAll({ includeUncontrolled: true });
  clients.forEach((client) =>
    client.postMessage({ type: "SYNC_PENDING_UPLOADS" })
  );
}

// ---------------------------------------------------------------------------
// Offline audio storage helper messages from app
// ---------------------------------------------------------------------------

self.addEventListener("message", (event) => {
  if (!event.data) return;

  if (event.data.type === "SKIP_WAITING") {
    self.skipWaiting();
    return;
  }

  if (event.data.type === "REGISTER_AUDIO_SYNC") {
    // App requests a background sync tag when it goes offline mid-upload
    self.registration.sync
      .register(AUDIO_SYNC_TAG)
      .catch(() => {
        // Background Sync API not supported — app will poll via online event
      });
    return;
  }
});

// ---------------------------------------------------------------------------
// Push notifications
// ---------------------------------------------------------------------------

self.addEventListener("push", (event) => {
  if (!event.data) return;

  let data = {};
  try {
    data = event.data.json();
  } catch {
    data = { title: "NoteFlow", body: event.data.text() };
  }

  const title = data.title || "NoteFlow";
  const options = {
    body: data.body || "",
    icon: "/icons/icon-192x192.png",
    badge: "/icons/icon-72x72.png",
    tag: data.tag || "noteflow-notification",
    renotify: data.renotify || false,
    requireInteraction: data.requireInteraction || false,
    data: {
      url: data.url || "/dashboard",
    },
  };

  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();

  const targetUrl = event.notification.data?.url || "/dashboard";

  event.waitUntil(
    self.clients
      .matchAll({ type: "window", includeUncontrolled: true })
      .then((clientList) => {
        // Reuse an existing window if one is already open at the target URL
        for (const client of clientList) {
          if (client.url === targetUrl && "focus" in client) {
            return client.focus();
          }
        }
        return self.clients.openWindow(targetUrl);
      })
  );
});
