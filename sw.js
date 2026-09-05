/* Service worker: cache the shell so the app opens instantly and works
   offline, but never cache the data files — those must always be fresh. */

const SHELL = "hmh-shell-v5";
const SHELL_FILES = [
  "./",
  "./index.html",
  "./styles.css",
  "./app.js",
  "./manifest.webmanifest",
  "./home_photo.jpg",
  "./icon-192.png",
  "./icon-512.png"
];

self.addEventListener("install", (e) => {
  e.waitUntil(
    caches.open(SHELL)
      .then((c) => c.addAll(SHELL_FILES))
      .catch(() => {})           // a missing optional file must not block install
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== SHELL).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

/* Network first, cache as offline fallback. */
function networkFirst(req) {
  return fetch(req)
    .then((res) => {
      if (res && res.ok) {
        const copy = res.clone();
        caches.open(SHELL).then((c) => c.put(req, copy)).catch(() => {});
      }
      return res;
    })
    .catch(() => caches.match(req).then((hit) => hit || caches.match("./index.html")));
}

/* Cache first, refresh in the background. */
function cacheFirst(req) {
  return caches.match(req).then((hit) => {
    const net = fetch(req)
      .then((res) => {
        if (res && res.ok) {
          const copy = res.clone();
          caches.open(SHELL).then((c) => c.put(req, copy)).catch(() => {});
        }
        return res;
      })
      .catch(() => hit);
    return hit || net;
  });
}

self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET") return;

  const url = new URL(req.url);

  // Never intercept the GitHub API or anything cross-origin.
  if (url.origin !== self.location.origin) return;

  /* HTML, CSS and JS go network first. Serving these from cache meant a deploy
     didn't show up until the second launch, and worse, a cached index.html
     could be paired with a freshly fetched app.js — different generations of
     the same app, which breaks as soon as one adds an element the other
     doesn't know about. They must move together, so they come from the
     network whenever it's reachable. */
  if (req.mode === "navigate" ||
      url.pathname.includes("/data/") ||
      /\.(?:html|css|js|webmanifest)$/.test(url.pathname) ||
      url.pathname.endsWith("/")) {
    e.respondWith(networkFirst(req));
    return;
  }

  // Photos, icons: big and effectively immutable, so cache first is right.
  e.respondWith(cacheFirst(req));
});
