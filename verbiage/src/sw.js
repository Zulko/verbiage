import { clientsClaim } from 'workbox-core'
import { cleanupOutdatedCaches, precacheAndRoute } from 'workbox-precaching'
import { registerRoute, NavigationRoute } from 'workbox-routing'
import { CacheFirst } from 'workbox-strategies'
import { CacheableResponsePlugin } from 'workbox-cacheable-response'

const manifest = self.__WB_MANIFEST

const shellEntry = manifest.find((entry) => {
  const url = typeof entry === 'string' ? entry : entry.url
  return url === 'index.html'
})
const shellRevision =
  shellEntry && typeof shellEntry === 'object' && shellEntry.revision
    ? shellEntry.revision
    : 'current'
const SHELL_CACHE = `shell-${shellRevision}`
const SHELL_PATH = 'index.html'

// Cloudflare injects the analytics beacon only for document requests.
// Workbox's precache fetch sends Accept: */*, so the cached shell would never include it.
function shellRequest() {
  return new Request(SHELL_PATH, {
    cache: 'reload',
    headers: {
      Accept: 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    },
  })
}

self.skipWaiting()
clientsClaim()

precacheAndRoute(
  manifest.filter((entry) => {
    const url = typeof entry === 'string' ? entry : entry.url
    return url !== SHELL_PATH
  }),
)
cleanupOutdatedCaches()

async function cacheShell() {
  const response = await fetch(shellRequest())
  if (!response.ok) {
    throw new Error(`shell fetch failed: ${response.status}`)
  }
  const cache = await caches.open(SHELL_CACHE)
  await cache.put(SHELL_PATH, response.clone())
  return response
}

self.addEventListener('install', (event) => {
  event.waitUntil(cacheShell())
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((names) =>
      Promise.all(
        names
          .filter((name) => name.startsWith('shell-') && name !== SHELL_CACHE)
          .map((name) => caches.delete(name)),
      ),
    ),
  )
})

registerRoute(
  new NavigationRoute(async () => {
    const cache = await caches.open(SHELL_CACHE)
    const cached = await cache.match(SHELL_PATH)
    if (cached) return cached
    return cacheShell()
  }),
)

registerRoute(
  /\/puzzles\/.*\.json\.gz$/i,
  new CacheFirst({
    cacheName: 'puzzles',
    plugins: [
      new CacheableResponsePlugin({
        statuses: [0, 200],
      }),
    ],
  }),
  'GET',
)
