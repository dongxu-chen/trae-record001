import { db } from '~/utils/indexedDB'

export default defineNuxtPlugin(async () => {
  await db.init()

  if ('serviceWorker' in navigator) {
    const { registration } = usePWA()
    try {
      const reg = await navigator.serviceWorker.register('/sw.js')
      registration.value = reg
    } catch (error) {
      console.error('Service Worker registration failed:', error)
    }
  }
})
