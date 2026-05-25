import { WebSocketServer } from 'ws'
import crypto from 'crypto'

const generateId = () => {
  return crypto.randomUUID ? crypto.randomUUID() : 
    `${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
}

const PORT = process.env.PORT || 8080
const wss = new WebSocketServer({ port: PORT })

const rooms = new Map()

const WS_MESSAGE_TYPES = {
  JOIN: 'join',
  LEAVE: 'leave',
  USERS_UPDATE: 'users_update',
  ANNOTATION_ADD: 'annotation_add',
  ANNOTATION_UPDATE: 'annotation_update',
  ANNOTATION_DELETE: 'annotation_delete',
  IMAGE_LOAD: 'image_load',
  CURSOR_MOVE: 'cursor_move',
  UNDO: 'undo',
  REDO: 'redo',
  OT_OPERATION: 'ot_operation',
  OT_ACK: 'ot_ack',
  OT_SYNC: 'ot_sync'
}

console.log(`WebSocket Server running on ws://localhost:${PORT}`)

wss.on('connection', (ws, req) => {
  const clientId = generateId()
  let currentRoom = null
  let currentUser = null

  console.log(`Client connected: ${clientId}`)

  ws.on('message', (message) => {
    try {
      const data = JSON.parse(message.toString())
      handleMessage(ws, data)
    } catch (error) {
      console.error('Message parse error:', error)
    }
  })

  ws.on('close', () => {
    console.log(`Client disconnected: ${clientId}`)
    handleLeave()
  })

  ws.on('error', (error) => {
    console.error(`WebSocket error for ${clientId}:`, error)
  })

  function handleMessage(ws, message) {
    const { type, data, roomId } = message

    switch (type) {
      case 'join':
        handleJoin(ws, data)
        break
      case 'leave':
        handleLeave()
        break
      case 'annotation_add':
      case 'annotation_update':
      case 'annotation_delete':
      case 'image_load':
      case 'cursor_move':
      case 'undo':
      case 'redo':
        broadcast(type, data)
        break
      case WS_MESSAGE_TYPES.OT_OPERATION:
        handleOTOperation(data)
        break
      case WS_MESSAGE_TYPES.OT_ACK:
        handleOTAck(data)
        break
      case WS_MESSAGE_TYPES.OT_SYNC:
        handleOTSync(ws, data)
        break
      case 'ping':
        ws.send(JSON.stringify({ type: 'pong', timestamp: Date.now() }))
        break
      default:
        console.log(`Unknown message type: ${type}`)
    }
  }

  function handleOTOperation(data) {
    if (!currentRoom || !rooms.has(currentRoom)) return

    const room = rooms.get(currentRoom)
    const operation = data.operation

    if (!operation || !operation.id) return

    const existingOp = room.otHistory.find(op => op.id === operation.id)
    if (existingOp) {
      sendAck(operation.id, room.currentVersion)
      return
    }

    if (operation.version < room.currentVersion) {
      const operationsSince = room.otHistory.filter(op => op.version > operation.version)
      operationsSince.forEach(op => {
        const transformed = transformOperation(operation, op)
        operation.data = transformed.data
        operation.version = op.version
      })
    }

    operation.version = room.currentVersion + 1
    operation.serverTimestamp = Date.now()

    room.otHistory.push(operation)
    if (room.otHistory.length > room.maxHistory) {
      room.otHistory.shift()
    }
    room.currentVersion = operation.version

    broadcast(WS_MESSAGE_TYPES.OT_OPERATION, { operation })

    setTimeout(() => sendAck(operation.id, room.currentVersion), 10)
  }

  function handleOTAck(data) {
    console.log('Received OT ack:', data)
  }

  function handleOTSync(ws, data) {
    if (!currentRoom || !rooms.has(currentRoom)) return

    const room = rooms.get(currentRoom)

    if (data && data.requestSync) {
      const operationsSince = room.otHistory.filter(op => op.version > (data.currentVersion || 0))
      ws.send(JSON.stringify({
        type: WS_MESSAGE_TYPES.OT_SYNC,
        data: {
          operations: operationsSince,
          version: room.currentVersion
        },
        senderId: 'server',
        timestamp: Date.now()
      }))
    }
  }

  function sendAck(operationId, version) {
    if (!currentRoom || !rooms.has(currentRoom)) return

    const room = rooms.get(currentRoom)
    const client = room.users.get(clientId)
    if (client && client.ws.readyState === 1) {
      client.ws.send(JSON.stringify({
        type: WS_MESSAGE_TYPES.OT_ACK,
        data: { operationId, version },
        senderId: 'server',
        timestamp: Date.now()
      }))
    }
  }

  function transformOperation(op1, op2) {
    if (op1.annotationId !== op2.annotationId) {
      return op1
    }

    const transformed = JSON.parse(JSON.stringify(op1))

    if (op1.type === 'move' && op2.type === 'resize') {
      if (op1.data.canvasCoords && op2.data.canvasCoords) {
        const deltaX = (op2.data.canvasCoords.left || 0) - (op2.data.prevLeft || 0)
        const deltaY = (op2.data.canvasCoords.top || 0) - (op2.data.prevTop || 0)
        
        transformed.data.canvasCoords = {
          ...op1.data.canvasCoords,
          left: (op1.data.canvasCoords.left || 0) + deltaX * 0.5,
          top: (op1.data.canvasCoords.top || 0) + deltaY * 0.5
        }
      }
    }

    if (op1.type === 'resize' && op2.type === 'resize') {
      if (op1.data.canvasCoords && op2.data.canvasCoords) {
        const prevRight = (op2.data.prevLeft || 0) + (op2.data.prevWidth || 0)
        const prevBottom = (op2.data.prevTop || 0) + (op2.data.prevHeight || 0)
        const newRight = (op2.data.canvasCoords.left || 0) + (op2.data.canvasCoords.width || 0)
        const newBottom = (op2.data.canvasCoords.top || 0) + (op2.data.canvasCoords.height || 0)
        
        const rightDelta = newRight - prevRight
        const bottomDelta = newBottom - prevBottom

        transformed.data.canvasCoords = {
          ...op1.data.canvasCoords,
          width: Math.max(20, (op1.data.canvasCoords.width || 0) + rightDelta * 0.3),
          height: Math.max(20, (op1.data.canvasCoords.height || 0) + bottomDelta * 0.3)
        }
      }
    }

    return transformed
  }

  function handleJoin(ws, data) {
    const { user, roomId } = data

    if (!rooms.has(roomId)) {
      rooms.set(roomId, {
        id: roomId,
        users: new Map(),
        createdAt: Date.now(),
        otHistory: [],
        currentVersion: 0,
        maxHistory: 1000
      })
    }

    const room = rooms.get(roomId)
    currentRoom = roomId
    currentUser = { ...user, clientId }

    room.users.set(clientId, {
      user: currentUser,
      ws,
      joinedAt: Date.now()
    })

    const usersList = Array.from(room.users.values()).map(u => u.user)

    ws.send(JSON.stringify({
      type: 'join_success',
      data: {
        user: currentUser,
        users: usersList
      }
    }))

    broadcast('users_update', { users: usersList })

    console.log(`User ${currentUser.name} joined room ${roomId}`)
  }

  function handleLeave() {
    if (!currentRoom || !rooms.has(currentRoom)) return

    const room = rooms.get(currentRoom)
    room.users.delete(clientId)

    if (room.users.size === 0) {
      rooms.delete(currentRoom)
      console.log(`Room ${currentRoom} deleted (empty)`)
    } else {
      const usersList = Array.from(room.users.values()).map(u => u.user)
      broadcast('users_update', { users: usersList })
      broadcast('leave', { userId: currentUser?.id })
    }

    if (currentUser) {
      console.log(`User ${currentUser.name} left room ${currentRoom}`)
    }

    currentRoom = null
    currentUser = null
  }

  function broadcast(type, data) {
    if (!currentRoom || !rooms.has(currentRoom)) return

    const room = rooms.get(currentRoom)
    const message = JSON.stringify({
      type,
      data,
      senderId: currentUser?.id,
      timestamp: Date.now()
    })

    room.users.forEach((client, id) => {
      if (id !== clientId && client.ws.readyState === 1) {
        client.ws.send(message)
      }
    })
  }
})

wss.on('error', (error) => {
  console.error('WebSocket Server error:', error)
})

process.on('SIGINT', () => {
  console.log('\nShutting down WebSocket server...')
  wss.close(() => {
    console.log('WebSocket server closed')
    process.exit(0)
  })
})
