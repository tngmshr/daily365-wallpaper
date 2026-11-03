// Offline shell for the Pages web app (iPhone home-screen use).
// tools/package_web.py replaces __PRECACHE_VERSION__ with a hash of precache-manifest.json, so the
// browser sees a changed worker on every deploy that changes app files and installs a fresh cache.
// Files whose revision did not change are copied from the previous cache instead of downloaded again.
// The iPhone Shortcut fetches wallpapers/MM-DD.jpg directly and never goes through this worker.
const CACHE_PREFIX = 'daily365-shell-';
const CACHE_NAME = CACHE_PREFIX + '__PRECACHE_VERSION__';
// Flutter web downloads fallback fonts (Japanese glyphs) from Google Fonts at runtime.
const FONT_CACHE = 'daily365-fonts-v1';
const FONT_ORIGIN = 'https://fonts.gstatic.com';
const MANIFEST = 'precache-manifest.json';

async function previousRevisions(cacheName) {
  const cache = await caches.open(cacheName);
  const stored = await cache.match(new URL(MANIFEST, self.registration.scope).href);
  if (!stored) return null;
  try {
    return { cache, revisions: (await stored.json()).revisions || {} };
  } catch (_) {
    return null;
  }
}

self.addEventListener('install', (event) => {
  event.waitUntil((async () => {
    const manifestUrl = new URL(MANIFEST, self.registration.scope).href;
    const response = await fetch(manifestUrl, { cache: 'no-store' });
    if (!response.ok) throw new Error('Could not load offline asset list.');
    const manifest = await response.json();
    const revisions = manifest.revisions || {};
    const cache = await caches.open(CACHE_NAME);

    const previous = [];
    for (const name of await caches.keys()) {
      if (name.startsWith(CACHE_PREFIX) && name !== CACHE_NAME) {
        const found = await previousRevisions(name);
        if (found) previous.push(found);
      }
    }

    const toFetch = [];
    for (const path of manifest.files) {
      const url = new URL(path, self.registration.scope).href;
      if (await cache.match(url)) continue; // resumed install
      let reused = false;
      for (const old of previous) {
        if (revisions[path] && old.revisions[path] === revisions[path]) {
          const hit = await old.cache.match(url);
          if (hit) {
            await cache.put(url, hit);
            reused = true;
            break;
          }
        }
      }
      // cache: 'reload' skips the HTTP cache so a deploy is not mixed with stale files.
      if (!reused) toFetch.push(new Request(url, { cache: 'reload' }));
    }
    for (let index = 0; index < toFetch.length; index += 12) {
      await cache.addAll(toFetch.slice(index, index + 12));
    }
    // Store the manifest last: a cache without it is never used as a source for reuse.
    await cache.put(manifestUrl, new Response(JSON.stringify(manifest), {
      headers: { 'Content-Type': 'application/json' },
    }));
    await self.skipWaiting();
  })());
});

self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    const names = await caches.keys();
    await Promise.all(names
      .filter((name) => name.startsWith('daily365-') && name !== CACHE_NAME && name !== FONT_CACHE)
      .map((name) => caches.delete(name)));
    await self.clients.claim();
  })());
});

async function fromNetwork(request, cacheName) {
  const response = await fetch(request);
  if (response.ok && (response.type === 'basic' || response.type === 'cors')) {
    const cache = await caches.open(cacheName);
    await cache.put(request, response.clone());
  }
  return response;
}

self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') return;
  const requestUrl = new URL(event.request.url);

  if (requestUrl.origin === FONT_ORIGIN) {
    event.respondWith((async () => {
      const cached = await caches.match(event.request, { cacheName: FONT_CACHE });
      return cached || fromNetwork(event.request, FONT_CACHE);
    })());
    return;
  }
  if (requestUrl.origin !== self.location.origin) return;
  // The Android app's update check and the Shortcut images must always come from the network.
  const scopePath = new URL(self.registration.scope).pathname;
  const relative = requestUrl.pathname.startsWith(scopePath) ? requestUrl.pathname.slice(scopePath.length) : '';
  if (relative === 'version.json' || relative.startsWith('wallpapers/')) return;

  event.respondWith((async () => {
    const cache = await caches.open(CACHE_NAME);
    const cached = await cache.match(event.request);
    if (cached) return cached;
    try {
      return await fromNetwork(event.request, CACHE_NAME);
    } catch (_) {
      if (event.request.mode === 'navigate') {
        return (await cache.match(new URL('index.html', self.registration.scope).href)) || Response.error();
      }
      return Response.error();
    }
  })());
});
