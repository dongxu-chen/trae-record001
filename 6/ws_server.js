const http = require('http')
const { WebSocketServer } = require('ws')

const PORT = process.env.WS_PORT || 3002
const HEARTBEAT_INTERVAL = 30000

const server = http.createServer()
const wss = new WebSocketServer({ server })

const channels = new Map()

function heartbeat(ws) {
  ws.isAlive = true
}

function subscribe(ws, postId) {
  if (!channels.has(postId)) {
    channels.set(postId, new Set())
  }
  const subscribers = channels.get(postId)
  subscribers.add(ws)
  if (!ws.subscriptions) {
    ws.subscriptions = new Set()
  }
  ws.subscriptions.add(postId)
  console.log(`Client subscribed to post: ${postId}`)
}

function unsubscribe(ws, postId) {
  const subscribers = channels.get(postId)
  if (subscribers) {
    subscribers.delete(ws)
    if (subscribers.size === 0) {
      channels.delete(postId)
    }
  }
  if (ws.subscriptions) {
    ws.subscriptions.delete(postId)
  }
  console.log(`Client unsubscribed from post: ${postId}`)
}

function broadcastToChannel(postId, payload) {
  const subscribers = channels.get(postId)
  if (!subscribers) {
    return
  }
  const message = JSON.stringify(payload)
  subscribers.forEach((ws) => {
    if (ws.readyState === 1) {
      ws.send(message)
    }
  })
  console.log(`Broadcast to post ${postId}: ${subscribers.size} subscribers`)
}

function handleMessage(ws, rawData) {
  let data
  try {
    data = JSON.parse(rawData.toString())
  } catch (err) {
    console.warn('Invalid message:', rawData.toString())
    return
  }

  switch (data.type) {
    case 'subscribe':
      if (data.postId) {
        subscribe(ws, String(data.postId))
      }
      break
    case 'unsubscribe':
      if (data.postId) {
        unsubscribe(ws, String(data.postId))
      }
      break
    case 'ping':
      ws.send(JSON.stringify({ type: 'pong' }))
      break
    case 'comment':
      if (data.postId && data.comment) {
        broadcastToChannel(String(data.postId), {
          type: 'new_comment',
          postId: data.postId,
          comment: data.comment
        })
      }
      break
    default:
      console.warn('Unknown message type:', data.type)
  }
}

function cleanupConnection(ws) {
  if (ws.subscriptions) {
    ws.subscriptions.forEach((postId) => {
      const subscribers = channels.get(postId)
      if (subscribers) {
        subscribers.delete(ws)
        if (subscribers.size === 0) {
          channels.delete(postId)
        }
      }
    })
    ws.subscriptions.clear()
  }
}

wss.on('connection', (ws) => {
  ws.isAlive = true
  ws.subscriptions = new Set()

  ws.on('pong', () => heartbeat(ws))

  ws.on('message', (rawData) => {
    handleMessage(ws, rawData)
  })

  ws.on('close', () => {
    cleanupConnection(ws)
    console.log('Client disconnected')
  })

  ws.on('error', (err) => {
    console.error('WebSocket error:', err.message)
    cleanupConnection(ws)
  })
})

const heartbeatInterval = setInterval(() => {
  wss.clients.forEach((ws) => {
    if (ws.isAlive === false) {
      return ws.terminate()
    }
    ws.isAlive = false
    ws.ping()
  })
}, HEARTBEAT_INTERVAL)

wss.on('close', () => {
  clearInterval(heartbeatInterval)
})

server.listen(PORT, () => {
  console.log(`WebSocket server running on port ${PORT}`)
})
