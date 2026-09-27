const CACHE_NAME = 'daily365-shell-v2';

self.addEventListener('install', (event) => {
  event.waitUntil((async () => {
    const manifestUrl = new URL('precache-manifest.json', self.registration.scope);
    const response = await fetch(manifestUrl, { cache: 'no-store' });
    if (!response.ok) throw new Error('Could not load offline asset list.');
    const manifest = await response.json();
    const assets = manifest.files.map((path) => new URL(path, self.registration.scope).href);
    const cache = await caches.open(CACHE_NAME);
    for (let index = 0; index < assets.length; index += 12) {
      await cache.addAll(assets.slice(index, index + 12));
    }
    await self.skipWaiting();
  })());
});

self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    const names = await caches.keys();
    await Promise.all(names.filter((name) => name.startsWith('daily365-') && name !== CACHE_NAME)
      .map((name) => caches.delete(name)));
    await self.clients.claim();
  })());
});

self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') return;
  const requestUrl = new URL(event.request.url);
  if (requestUrl.origin !== self.location.origin) return;

  event.respondWith((async () => {
    const cached = await caches.match(event.request);
    if (cached) return cached;
    try {
      const response = await fetch(event.request);
      if (response.ok && response.type === 'basic') {
        const cache = await caches.open(CACHE_NAME);
        await cache.put(event.request, response.clone());
      }
      return response;
    } catch (_) {
      if (event.request.mode === 'navigate') {
        return (await caches.match(new URL('index.html', self.registration.scope))) || Response.error();
      }
      return Response.error();
    }
  })());
});
