import { db } from '~/utils/indexedDB'

export function usePWA() {
  const isPWA = ref(false)
  const isInstallPromptAvailable = ref(false)
  const deferredPrompt = ref<any>(null)
  const isOnline = ref(true)
  const isServiceWorkerReady = ref(false)
  const registration = ref<ServiceWorkerRegistration | null>(null)
  const pushSubscription = ref<PushSubscription | null>(null)
  const notificationPermission = ref<NotificationPermission>('default')

  const isDownloading = ref(false)
  const downloadProgress = ref(0)
  const currentDownload = ref<string | null>(null)

  onMounted(() => {
    isPWA.value = window.matchMedia('(display-mode: standalone)').matches ||
                   (window.navigator as any).standalone === true

    isOnline.value = navigator.onLine
    window.addEventListener('online', () => { isOnline.value = true })
    window.addEventListener('offline', () => { isOnline.value = false })

    window.addEventListener('beforeinstallprompt', (e: Event) => {
      e.preventDefault()
      deferredPrompt.value = e
      isInstallPromptAvailable.value = true
    })

    if ('Notification' in window) {
      notificationPermission.value = Notification.permission
    }

    registerServiceWorker()
  })

  const registerServiceWorker = async () => {
    if ('serviceWorker' in navigator) {
      try {
        registration.value = await navigator.serviceWorker.register('/sw.js')
        isServiceWorkerReady.value = true
        
        registration.value.addEventListener('updatefound', () => {
          const newWorker = registration.value?.installing
          if (newWorker) {
            newWorker.addEventListener('statechange', () => {
              if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                console.log('New version available')
              }
            })
          }
        })

        navigator.serviceWorker.addEventListener('message', handleSWMessage)
      } catch (error) {
        console.error('Service Worker registration failed:', error)
      }
    }
  }

  const handleSWMessage = (event: MessageEvent) => {
    const { type } = event.data
    
    switch (type) {
      case 'SYNC_PROGRESS':
        syncProgressToServer()
        break
      case 'SYNC_ANNOTATIONS':
        syncAnnotationsToServer()
        break
    }
  }

  const installPWA = async (): Promise<boolean> => {
    if (!deferredPrompt.value) return false

    deferredPrompt.value.prompt()
    const { outcome } = await deferredPrompt.value.userChoice
    deferredPrompt.value = null
    isInstallPromptAvailable.value = false

    return outcome === 'accepted'
  }

  const requestNotificationPermission = async (): Promise<boolean> => {
    if (!('Notification' in window)) return false

    const permission = await Notification.requestPermission()
    notificationPermission.value = permission
    return permission === 'granted'
  }

  const subscribePushNotifications = async (vapidPublicKey: string): Promise<boolean> => {
    if (!registration.value || !('PushManager' in window)) return false

    try {
      const subscription = await registration.value.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(vapidPublicKey)
      })
      
      pushSubscription.value = subscription
      
      await fetch('/api/push/subscribe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(subscription.toJSON())
      })

      return true
    } catch (error) {
      console.error('Push subscription failed:', error)
      return false
    }
  }

  const sendLocalNotification = (title: string, options: NotificationOptions = {}) => {
    if (Notification.permission === 'granted' && registration.value) {
      registration.value.showNotification(title, {
        icon: '/icons/icon-192x192.png',
        badge: '/icons/icon-96x96.png',
        vibrate: [100, 50, 100],
        ...options
      })
    }
  }

  const scheduleReadingReminder = (hours: number = 24) => {
    if (Notification.permission !== 'granted') return

    const now = Date.now()
    const reminderTime = now + hours * 60 * 60 * 1000
    
    localStorage.setItem('nextReadingReminder', String(reminderTime))
  }

  const checkReadingReminder = () => {
    const nextReminder = localStorage.getItem('nextReadingReminder')
    if (!nextReminder) return

    if (Date.now() > parseInt(nextReminder)) {
      sendLocalNotification('📚 阅读时间到！', {
        body: '继续你的阅读之旅吧，哪怕只读几页！',
        data: { url: '/' }
      })
      localStorage.removeItem('nextReadingReminder')
    }
  }

  const syncProgressToServer = async () => {
    if (!isOnline.value) return

    try {
      const allBooks = await db.getAllBooks()
      for (const book of allBooks) {
        const progress = await db.getProgressByBookId(book.id)
        if (progress) {
          await fetch('/api/progress', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(progress)
          })
        }
      }
    } catch (e) {
      console.error('Failed to sync progress:', e)
    }
  }

  const syncAnnotationsToServer = async () => {
    if (!isOnline.value) return

    try {
      const allBooks = await db.getAllBooks()
      for (const book of allBooks) {
        const annotations = await db.getAnnotationsByBookId(book.id)
        for (const annotation of annotations) {
          if ('_dirty' in annotation && annotation._dirty) {
            await fetch('/api/annotations', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(annotation)
            })
          }
        }
      }
    } catch (e) {
      console.error('Failed to sync annotations:', e)
    }
  }

  const downloadBook = async (bookId: number, bookUrl: string, fileName: string): Promise<boolean> => {
    isDownloading.value = true
    currentDownload.value = fileName
    downloadProgress.value = 0

    try {
      const response = await fetch(bookUrl)
      const reader = response.body?.getReader()
      const contentLength = parseInt(response.headers.get('Content-Length') || '0')
      
      if (!reader) throw new Error('No reader available')

      let receivedLength = 0
      const chunks: Uint8Array[] = []

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        chunks.push(value)
        receivedLength += value.length
        downloadProgress.value = Math.round((receivedLength / contentLength) * 100)
      }

      const fileData = new Uint8Array(receivedLength)
      let position = 0
      for (const chunk of chunks) {
        fileData.set(chunk, position)
        position += chunk.length
      }

      await db.saveBookFile(bookId, fileName, fileData.buffer)
      return true
    } catch (error) {
      console.error('Download failed:', error)
      return false
    } finally {
      isDownloading.value = false
      currentDownload.value = null
      downloadProgress.value = 0
    }
  }

  const urlBase64ToUint8Array = (base64String: string): Uint8Array => {
    const padding = '='.repeat((4 - base64String.length % 4) % 4)
    const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/')
    const rawData = window.atob(base64)
    return Uint8Array.from([...rawData].map(char => char.charCodeAt(0)))
  }

  return {
    isPWA,
    isInstallPromptAvailable,
    isOnline,
    isServiceWorkerReady,
    pushSubscription,
    notificationPermission,
    isDownloading,
    downloadProgress,
    currentDownload,
    installPWA,
    requestNotificationPermission,
    subscribePushNotifications,
    sendLocalNotification,
    scheduleReadingReminder,
    checkReadingReminder,
    syncProgressToServer,
    syncAnnotationsToServer,
    downloadBook
  }
}

export function useOfflineBooks() {
  const { db, isOnline } = useIndexedDB()
  const books = ref<any[]>([])
  const isDownloading = ref(false)
  const downloadProgress = ref(0)
  const currentDownload = ref<string | null>(null)

  const loadBooks = async () => {
    books.value = await db.getAllBooks()
  }

  const deleteOfflineBook = async (bookId: number) => {
    await db.deleteBook(bookId)
    await loadBooks()
  }

  const getBookForReading = async (bookId: number): Promise<Blob | null> => {
    const bookFile = await db.getBookFile(bookId)
    if (bookFile) {
      return new Blob([bookFile.data], { type: 'application/epub+zip' })
    }
    return null
  }

  const isBookOffline = (bookId: number): boolean => {
    return books.value.some(b => b.id === bookId && b.downloadedAt)
  }

  onMounted(() => {
    loadBooks()
  })

  return {
    books,
    isDownloading,
    downloadProgress,
    currentDownload,
    isOnline,
    loadBooks,
    deleteOfflineBook,
    getBookForReading,
    isBookOffline
  }
}
