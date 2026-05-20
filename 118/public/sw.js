importScripts('https://storage.googleapis.com/workbox-cdn/releases/7.0.0/workbox-sw.js')

const { registerRoute, setCatchHandler } = workbox.routing
const { CacheFirst, NetworkFirst, StaleWhileRevalidate, NetworkOnly } = workbox.strategies
const { CacheableResponsePlugin } = workbox.cacheableResponse
const { ExpirationPlugin } = workbox.expiration
const { precacheAndRoute } = workbox.precaching
const { warmStrategyCache } = workbox.recipes

const CACHE_NAMES = {
  static: 'epub-reader-static-v1',
  fonts: 'epub-reader-fonts-v1',
  images: 'epub-reader-images-v1',
  api: 'epub-reader-api-v1'
}

precacheAndRoute(self.__WB_MANIFEST || [])

// Static assets (CSS, JS, HTML)
registerRoute(
  ({ request }) => ['style', 'script', 'document'].includes(request.destination),
  new StaleWhileRevalidate({
    cacheName: CACHE_NAMES.static,
    plugins: [
      new CacheableResponsePlugin({ statuses: [200] }),
      new ExpirationPlugin({ maxEntries: 50, maxAgeSeconds: 30 * 24 * 60 * 60 })
    ]
  })
)

// Fonts
registerRoute(
  ({ request }) => request.destination === 'font',
  new CacheFirst({
    cacheName: CACHE_NAMES.fonts,
    plugins: [
      new CacheableResponsePlugin({ statuses: [200] }),
      new ExpirationPlugin({ maxEntries: 20, maxAgeSeconds: 365 * 24 * 60 * 60 })
    ]
  })
)

// Images
registerRoute(
  ({ request }) => request.destination === 'image',
  new CacheFirst({
    cacheName: CACHE_NAMES.images,
    plugins: [
      new CacheableResponsePlugin({ statuses: [200] }),
      new ExpirationPlugin({ maxEntries: 100, maxAgeSeconds: 30 * 24 * 60 * 60 })
    ]
  })
)

// API - Books list and metadata (network first, fallback to cache)
registerRoute(
  ({ url }) => url.pathname.startsWith('/api/books') && !url.pathname.includes('/file/'),
  new NetworkFirst({
    cacheName: CACHE_NAMES.api,
    plugins: [
      new CacheableResponsePlugin({ statuses: [200] }),
      new ExpirationPlugin({ maxEntries: 50, maxAgeSeconds: 24 * 60 * 60 })
    ]
  })
)

// API - Upload and other write operations (network only)
registerRoute(
  ({ url }) => url.pathname.startsWith('/api/upload') || url.pathname.startsWith('/api/decrypt'),
  new NetworkOnly()
)

// EPUB book files (cache first, store indefinitely)
registerRoute(
  ({ url }) => url.pathname.startsWith('/api/books/file/'),
  new CacheFirst({
    cacheName: 'epub-books',
    plugins: [
      new CacheableResponsePlugin({ statuses: [200] }),
      new ExpirationPlugin({ maxEntries: 20 })
    ]
  })
)

// Offline fallback
setCatchHandler(({ event }) => {
  switch (event.request.destination) {
    case 'document':
      return caches.match('/offline.html')
    case 'image':
      return new Response('', { status: 404, statusText: 'Image not available offline' })
    default:
      return Response.error()
  }
})

// Background sync for progress and annotations
const queue = new workbox.backgroundSync.BackgroundSyncPlugin('syncQueue', {
  maxRetentionTime: 24 * 60
})

registerRoute(
  ({ url }) => 
    url.pathname.startsWith('/api/progress') || 
    url.pathname.startsWith('/api/annotations') ||
    url.pathname.startsWith('/api/bookmarks'),
  new NetworkOnly({
    plugins: [queue]
  }),
  'POST'
)

// Push notifications
self.addEventListener('push', (event) => {
  const data = event.data?.json() || {}
  const options = {
    body: data.body || '继续你的阅读之旅！',
    icon: '/icons/icon-192x192.png',
    badge: '/icons/icon-96x96.png',
    vibrate: [100, 50, 100],
    data: {
      dateOfArrival: Date.now(),
      primaryKey: data.bookId || 1,
      url: data.url || '/'
    },
    actions: [
      { action: 'continue', title: '继续阅读', icon: '/icons/action-read.png' },
      { action: 'dismiss', title: '稍后', icon: '/icons/action-dismiss.png' }
    ],
    tag: data.tag || 'reading-reminder',
    renotify: true
  }

  event.waitUntil(
    self.registration.showNotification(data.title || '📚 阅读提醒', options)
  )
})

self.addEventListener('notificationclick', (event) => {
  event.notification.close()

  if (event.action === 'continue') {
    event.waitUntil(
      clients.openWindow(event.notification.data.url)
    )
  } else if (event.action === 'dismiss') {
    console.log('User dismissed notification')
  } else {
    event.waitUntil(
      clients.openWindow('/')
    )
  }
})

self.addEventListener('install', (event) => {
  self.skipWaiting()
  
  const urls = ['/', '/offline.html']
  event.waitUntil(
    warmStrategyCache({ urls, strategy: new CacheFirst() })
  )
})

self.addEventListener('activate', (event) => {
  const currentCaches = Object.values(CACHE_NAMES)
  
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return cacheNames.filter((cacheName) => !currentCaches.includes(cacheName))
        .map((cacheName) => caches.delete(cacheName))
    }).then(() => self.clients.claim())
  )
})

// Handle sync events
self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-progress') {
    event.waitUntil(syncReadingProgress())
  } else if (event.tag === 'sync-annotations') {
    event.waitUntil(syncAnnotations())
  }
})

async function syncReadingProgress() {
  const allClients = await clients.matchAll({ includeUncontrolled: true })
  for (const client of allClients) {
    client.postMessage({ type: 'SYNC_PROGRESS' })
  }
}

async function syncAnnotations() {
  const allClients = await clients.matchAll({ includeUncontrolled: true })
  for (const client of allClients) {
    client.postMessage({ type: 'SYNC_ANNOTATIONS' })
  }
}

// Periodic background sync
self.addEventListener('periodicsync', (event) => {
  if (event.tag === 'daily-reading-reminder') {
    event.waitUntil(
      self.registration.showNotification('📚 每日阅读提醒', {
        body: '今天还没阅读哦，来读几页吧！',
        icon: '/icons/icon-192x192.png',
        badge: '/icons/icon-96x96.png'
      })
    )
  }
})
