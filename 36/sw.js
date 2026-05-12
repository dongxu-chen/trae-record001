const VERSION = 'v2';
const CACHE_PREFIX = 'offline-diary';
const STATIC_CACHE = `${CACHE_PREFIX}-static-${VERSION}`;
const RUNTIME_CACHE = `${CACHE_PREFIX}-runtime-${VERSION}`;
const API_CACHE_PREFIX = `${CACHE_PREFIX}-api`;

const STATIC_ASSETS = [
  './',
  './index.html',
  './styles.css',
  './app.js',
  './idb.js',
  './sync.js',
  './manifest.json'
];

const API_CACHE_PATTERNS = [
  { url: '/api/user', maxAge: 5 * 60 * 1000, strategy: 'cache-first' },
  { url: '/api/diaries', maxAge: 30 * 1000, strategy: 'network-first' }
];

function getAPICacheName(pattern) {
  return `${API_CACHE_PREFIX}-${pattern.url.replace(/\//g, '-')}-${VERSION}`;
}

self.addEventListener('install', (event) => {
  console.log('[SW] 安装中 - 版本:', VERSION);
  
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then((cache) => {
        console.log('[SW] 缓存静态资源');
        return cache.addAll(STATIC_ASSETS);
      })
      .then(() => {
        console.log('[SW] 静态资源缓存完成，强制激活');
        return self.skipWaiting();
      })
      .catch((error) => {
        console.error('[SW] 缓存失败:', error);
      })
  );
});

self.addEventListener('activate', (event) => {
  console.log('[SW] 激活中 - 清理旧缓存');
  
  const expectedCaches = [
    STATIC_CACHE,
    RUNTIME_CACHE,
    ...API_CACHE_PATTERNS.map(p => getAPICacheName(p))
  ];
  
  event.waitUntil(
    caches.keys()
      .then((cacheNames) => {
        return Promise.all(
          cacheNames
            .filter((cacheName) => {
              const isOldVersion = cacheName.startsWith(CACHE_PREFIX) && 
                                   !expectedCaches.includes(cacheName);
              if (isOldVersion) {
                console.log('[SW] 删除旧缓存:', cacheName);
              }
              return isOldVersion;
            })
            .map((cacheName) => caches.delete(cacheName))
        );
      })
      .then(() => {
        console.log('[SW] 激活完成，立即接管所有客户端');
        return self.clients.claim();
      })
      .then(() => {
        return notifyClientsAboutUpdate();
      })
  );
});

async function notifyClientsAboutUpdate() {
  const clients = await self.clients.matchAll();
  clients.forEach(client => {
    client.postMessage({
      type: 'SW_UPDATED',
      version: VERSION,
      message: '应用已更新，请刷新页面'
    });
  });
}

self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  if (url.origin !== self.location.origin) {
    return;
  }

  if (request.method !== 'GET') {
    event.respondWith(handleNonGetRequest(request));
    return;
  }

  if (url.pathname.includes('/api/')) {
    event.respondWith(handleAPIRequest(request));
    return;
  }

  if (isStaticAsset(url)) {
    event.respondWith(staleWhileRevalidate(request, STATIC_CACHE));
    return;
  }

  event.respondWith(cacheFirstWithFallback(request));
});

function isStaticAsset(url) {
  const staticExtensions = [
    '.html', '.css', '.js', '.json',
    '.svg', '.png', '.jpg', '.jpeg', '.gif', '.ico',
    '.woff', '.woff2', '.ttf', '.eot'
  ];
  
  const pathname = url.pathname;
  if (pathname === '/' || pathname === '/index.html') return true;
  
  return staticExtensions.some(ext => pathname.endsWith(ext));
}

async function staleWhileRevalidate(request, cacheName) {
  const cache = await caches.open(cacheName);
  const cachedResponse = await cache.match(request);

  const networkFetch = fetch(request)
    .then(async (networkResponse) => {
      if (networkResponse && networkResponse.status === 200) {
        const responseClone = networkResponse.clone();
        await cache.put(request, responseClone);
        
        if (cachedResponse) {
          const cachedEtag = cachedResponse.headers.get('etag');
          const networkEtag = networkResponse.headers.get('etag');
          const cachedLastMod = cachedResponse.headers.get('last-modified');
          const networkLastMod = networkResponse.headers.get('last-modified');
          
          if (cachedEtag !== networkEtag || cachedLastMod !== networkLastMod) {
            const clients = await self.clients.matchAll();
            clients.forEach(client => {
              client.postMessage({
                type: 'CONTENT_UPDATED',
                url: request.url
              });
            });
          }
        }
      }
      return networkResponse;
    })
    .catch(error => {
      console.log('[SW] 网络请求失败，使用缓存:', request.url);
      return null;
    });

  if (cachedResponse) {
    return cachedResponse;
  }

  return networkFetch;
}

async function cacheFirstWithFallback(request) {
  const cache = await caches.open(RUNTIME_CACHE);
  const cachedResponse = await cache.match(request);

  if (cachedResponse) {
    return cachedResponse;
  }

  try {
    const networkResponse = await fetch(request);
    
    if (networkResponse && networkResponse.status === 200) {
      const responseClone = networkResponse.clone();
      await cache.put(request, responseClone);
    }
    
    return networkResponse;
  } catch (error) {
    console.log('[SW] 离线模式，返回首页');
    return caches.match('./index.html');
  }
}

async function handleAPIRequest(request) {
  const url = new URL(request.url);
  const pattern = API_CACHE_PATTERNS.find(p => url.pathname.includes(p.url));
  
  if (!pattern) {
    try {
      return await fetch(request);
    } catch (error) {
      return new Response(
        JSON.stringify({ error: '网络不可用' }),
        { status: 503, headers: { 'Content-Type': 'application/json' } }
      );
    }
  }

  const cacheName = getAPICacheName(pattern);
  const cache = await caches.open(cacheName);
  const cachedResponse = await cache.match(request);
  
  if (pattern.strategy === 'network-first') {
    try {
      const networkResponse = await fetch(request);
      
      if (networkResponse && networkResponse.status === 200) {
        const responseClone = networkResponse.clone();
        const headers = new Headers(networkResponse.headers);
        headers.set('sw-cache-time', Date.now().toString());
        
        const responseToCache = new Response(responseClone.body, {
          status: networkResponse.status,
          statusText: networkResponse.statusText,
          headers: headers
        });
        
        await cache.put(request, responseToCache);
      }
      
      return networkResponse;
    } catch (error) {
      if (cachedResponse) {
        return cachedResponse;
      }
      return new Response(
        JSON.stringify({ error: '网络不可用' }),
        { status: 503, headers: { 'Content-Type': 'application/json' } }
      );
    }
  }
  
  if (cachedResponse) {
    const cacheTime = parseInt(cachedResponse.headers.get('sw-cache-time') || '0');
    const isExpired = Date.now() - cacheTime > pattern.maxAge;
    
    if (!isExpired) {
      fetch(request)
        .then(async (networkResponse) => {
          if (networkResponse && networkResponse.status === 200) {
            const responseClone = networkResponse.clone();
            const headers = new Headers(networkResponse.headers);
            headers.set('sw-cache-time', Date.now().toString());
            
            const responseToCache = new Response(responseClone.body, {
              status: networkResponse.status,
              statusText: networkResponse.statusText,
              headers: headers
            });
            
            await cache.put(request, responseToCache);
          }
        })
        .catch(() => {});
      
      return cachedResponse;
    }
  }
  
  try {
    const networkResponse = await fetch(request);
    
    if (networkResponse && networkResponse.status === 200) {
      const responseClone = networkResponse.clone();
      const headers = new Headers(networkResponse.headers);
      headers.set('sw-cache-time', Date.now().toString());
      
      const responseToCache = new Response(responseClone.body, {
        status: networkResponse.status,
        statusText: networkResponse.statusText,
        headers: headers
      });
      
      await cache.put(request, responseToCache);
    }
    
    return networkResponse;
  } catch (error) {
    if (cachedResponse) {
      return cachedResponse;
    }
    return new Response(
      JSON.stringify({ error: '网络不可用' }),
      { status: 503, headers: { 'Content-Type': 'application/json' } }
    );
  }
}

async function handleNonGetRequest(request) {
  try {
    return await fetch(request);
  } catch (error) {
    console.log('[SW] 非 GET 请求失败，添加到同步队列');
    
    try {
      const payload = await request.clone().json();
      await addToSyncQueue(request, payload);
    } catch (e) {
      console.log('[SW] 无法解析请求体');
    }

    return new Response(
      JSON.stringify({ 
        success: true, 
        pendingSync: true,
        message: '操作已保存，将在恢复网络后同步'
      }),
      { status: 202, headers: { 'Content-Type': 'application/json' } }
    );
  }
}

async function addToSyncQueue(request, payload) {
  const url = new URL(request.url);
  
  const syncItem = {
    id: `sync_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
    method: request.method,
    url: url.pathname,
    payload,
    createdAt: new Date().toISOString()
  };

  const allClients = await self.clients.matchAll();
  if (allClients.length > 0) {
    allClients[0].postMessage({
      type: 'SYNC_ITEM_ADDED',
      data: syncItem
    });
  }
}

self.addEventListener('sync', (event) => {
  console.log('[SW] 后台同步事件:', event.tag);
  
  if (event.tag === 'sync-diaries') {
    event.waitUntil(syncAllPendingDiaries());
  }
});

async function syncAllPendingDiaries() {
  const allClients = await self.clients.matchAll();
  
  if (allClients.length > 0) {
    allClients[0].postMessage({
      type: 'TRIGGER_SYNC'
    });
  }
}

self.addEventListener('message', (event) => {
  const { data } = event;
  
  switch (data.type) {
    case 'GET_VERSION':
      event.source.postMessage({
        type: 'VERSION',
        version: VERSION
      });
      break;
      
    case 'CLEAR_CACHE':
      caches.keys().then(names => {
        names.forEach(name => caches.delete(name));
      });
      break;
      
    case 'SKIP_WAITING':
      self.skipWaiting();
      break;
  }
});

self.addEventListener('push', (event) => {
  const data = event.data?.json() || { title: '离线日记本', body: '新消息' };
  
  event.waitUntil(
    self.registration.showNotification(data.title, {
      body: data.body,
      icon: data.icon || '/icon.png',
      badge: data.badge || '/icon.png',
      data: data.data || {}
    })
  );
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  
  event.waitUntil(
    self.clients.openWindow('/')
  );
});
