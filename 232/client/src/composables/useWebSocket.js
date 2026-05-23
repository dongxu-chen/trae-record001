import { ref, onUnmounted } from 'vue'

export function useWebSocket() {
  const ws = ref(null)
  const isConnected = ref(false)
  const clientId = ref(null)
  const sessionId = ref('default')
  const userCount = ref(0)
  const messageHandlers = new Map()

  function connect(sId = 'default', userName = '匿名用户') {
    sessionId.value = sId
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//localhost:8080`
    
    ws.value = new WebSocket(wsUrl)

    ws.value.onopen = () => {
      isConnected.value = true
      send({ type: 'join', sessionId: sId, userName })
    }

    ws.value.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data)
        handleMessage(message)
      } catch (e) {
        console.error('Failed to parse message:', e)
      }
    }

    ws.value.onclose = () => {
      isConnected.value = false
    }

    ws.value.onerror = (error) => {
      console.error('WebSocket error:', error)
    }
  }

  function handleMessage(message) {
    switch (message.type) {
      case 'init':
        clientId.value = message.clientId
        break
      case 'userJoined':
      case 'userLeft':
        userCount.value = message.userCount
        break
    }

    const handler = messageHandlers.get(message.type)
    if (handler) {
      handler(message)
    }
  }

  function on(type, handler) {
    messageHandlers.set(type, handler)
  }

  function off(type) {
    messageHandlers.delete(type)
  }

  function send(message) {
    if (ws.value && ws.value.readyState === WebSocket.OPEN) {
      ws.value.send(JSON.stringify(message))
    }
  }

  function disconnect() {
    if (ws.value) {
      ws.value.close()
      ws.value = null
    }
  }

  onUnmounted(() => {
    disconnect()
  })

  return {
    ws,
    isConnected,
    clientId,
    sessionId,
    userCount,
    connect,
    disconnect,
    send,
    on,
    off
  }
}
