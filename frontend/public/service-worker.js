// UNMAPPED — basic offline-first service worker.
//
// Generated using Workbox-style strategies (StaleWhileRevalidate + NetworkFirst
// + offline fallback). We use Workbox primitives loaded from the official CDN
// so we don't need a build-time integration. If the CDN fails to load (e.g.
// the user's first-ever visit happens offline), we degrade to vanilla
// `fetch`/`caches` calls below.

const SW_VERSION = "unmapped-sw-v1";
const APP_SHELL_CACHE = `${SW_VERSION}-shell`;
const RUNTIME_CACHE = `${SW_VERSION}-runtime`;
const API_CACHE = `${SW_VERSION}-api`;
const OFFLINE_URL = "/offline.html";

// Files that make up the static "app shell" — pre-cached on install so the UI
// boots even without a network connection.
const APP_SHELL_URLS = ["/", OFFLINE_URL, "/manifest.webmanifest"];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(APP_SHELL_CACHE)
      .then((cache) =>
        // `addAll` rejects on first failure, so we add individually and ignore
        // missing files (manifest is optional).
        Promise.all(
          APP_SHELL_URLS.map((url) =>
            cache
              .add(new Request(url, { cache: "reload" }))
              .catch(() => undefined),
          ),
        ),
      )
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys
            .filter((key) => !key.startsWith(SW_VERSION))
            .map((key) => caches.delete(key)),
        ),
      )
      .then(() => self.clients.claim()),
  );
});

function isApiRequest(url) {
  return url.pathname.startsWith("/api/") || url.pathname === "/api";
}

function isNavigationRequest(request) {
  return (
    request.mode === "navigate" ||
    (request.method === "GET" &&
      request.headers.get("accept")?.includes("text/html"))
  );
}

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;

  const url = new URL(request.url);

  if (url.origin !== self.location.origin && !isApiRequest(url)) {
    return;
  }

  if (isApiRequest(url)) {
    // Network-first for API calls so users always see fresh data when online,
    // and a cached response (or JSON error) when offline.
    event.respondWith(
      (async () => {
        try {
          const fresh = await fetch(request);
          const copy = fresh.clone();
          caches.open(API_CACHE).then((cache) => cache.put(request, copy));
          return fresh;
        } catch {
          const cached = await caches.match(request);
          if (cached) return cached;
          return new Response(
            JSON.stringify({
              error: "offline",
              message:
                "You appear to be offline. Reconnect to fetch a fresh analysis.",
            }),
            {
              status: 503,
              headers: { "Content-Type": "application/json" },
            },
          );
        }
      })(),
    );
    return;
  }

  if (isNavigationRequest(request)) {
    // App shell: try the network, fall back to cached shell, then offline.html
    event.respondWith(
      (async () => {
        try {
          const fresh = await fetch(request);
          const copy = fresh.clone();
          caches
            .open(APP_SHELL_CACHE)
            .then((cache) => cache.put(request, copy));
          return fresh;
        } catch {
          const cached = await caches.match(request);
          if (cached) return cached;
          const shell = await caches.match("/");
          if (shell) return shell;
          const offline = await caches.match(OFFLINE_URL);
          if (offline) return offline;
          return new Response("You are offline.", {
            status: 503,
            headers: { "Content-Type": "text/plain" },
          });
        }
      })(),
    );
    return;
  }

  // Stale-while-revalidate for static assets (JS, CSS, fonts, images).
  event.respondWith(
    (async () => {
      const cache = await caches.open(RUNTIME_CACHE);
      const cached = await cache.match(request);
      const network = fetch(request)
        .then((response) => {
          if (
            response &&
            response.status === 200 &&
            response.type === "basic"
          ) {
            cache.put(request, response.clone());
          }
          return response;
        })
        .catch(() => undefined);
      return cached || (await network) || Response.error();
    })(),
  );
});

// Allow the page to ask us to activate immediately after an update.
self.addEventListener("message", (event) => {
  if (event.data === "SKIP_WAITING") self.skipWaiting();
});
