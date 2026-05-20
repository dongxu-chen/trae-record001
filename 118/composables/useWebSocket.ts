import { ref, onUnmounted } from 'vue'

export interface ProgressMessage {
  userId: string
  cfi: string
  percentage: number
  timestamp: number
}

export function useWebSocket(bookId: number) {
  const ws = ref<WebSocket | null>(null)
  const isConnected = ref(false)
  const userId = ref(`user_${Math.random().toString(36).substr(2, 9)}`)
  const remoteProgress = ref<ProgressMessage | null>(null)
  const syncProgress = ref<{ cfi: string; percentage: number } | null>(null)

  const connect = () => {
    if (typeof window === 'undefined') return

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsPort = process.env.WS_PORT || '3001'
    const wsUrl = `${protocol}//${window.location.hostname}:${wsPort}`

    ws.value = new WebSocket(wsUrl)

    ws.value.onopen = () => {
      isConnected.value = true
      send('join', { bookId, userId: userId.value })
    }

    ws.value.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data)
        handleMessage(message)
      } catch (e) {
        console.error('Failed to parse WebSocket message:', e)
      }
    }

    ws.value.onclose = () => {
      isConnected.value = false
      setTimeout(connect, 3000)
    }

    ws.value.onerror = (error) => {
      console.error('WebSocket error:', error)
    }
  }

  const handleMessage = (message: any) => {
    const { type, payload } = message

    switch (type) {
      case 'progress':
        if (payload.userId !== userId.value) {
          remoteProgress.value = payload
        }
        break
      case 'sync':
        syncProgress.value = payload
        break
    }
  }

  const send = (type: string, payload: any) => {
    if (ws.value && ws.value.readyState === WebSocket.OPEN) {
      ws.value.send(JSON.stringify({ type, payload }))
    }
  }

  const updateProgress = (cfi: string, percentage: number) => {
    send('progress', {
      bookId,
      userId: userId.value,
      cfi,
      percentage
    })
  }

  const disconnect = () => {
    send('leave', { bookId, userId: userId.value })
    ws.value?.close()
  }

  onUnmounted(() => {
    disconnect()
  })

  return {
    isConnected,
    userId,
    remoteProgress,
    syncProgress,
    connect,
    updateProgress,
    disconnect
  }
}
