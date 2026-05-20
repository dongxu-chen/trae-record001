import { WebSocketServer, WebSocket } from 'ws'
import prisma from '../utils/prisma'

interface ReadingSession {
  bookId: number
  userId: string
  cfi: string
  percentage: number
  timestamp: number
}

const sessions = new Map<string, ReadingSession>()
const connections = new Map<WebSocket, { bookId: number; userId: string }>()

export default defineNitroPlugin((nitroApp) => {
  if (process.server && !globalThis.wss) {
    const port = parseInt(process.env.WS_PORT || '3001')
    const wss = new WebSocketServer({ port })
    globalThis.wss = wss

    console.log(`WebSocket server running on port ${port}`)

    wss.on('connection', (ws: WebSocket) => {
      ws.on('message', async (data) => {
        try {
          const message = JSON.parse(data.toString())
          handleMessage(ws, message)
        } catch (e) {
          console.error('WebSocket message error:', e)
        }
      })

      ws.on('close', () => {
        connections.delete(ws)
      })

      ws.on('error', (error) => {
        console.error('WebSocket error:', error)
        connections.delete(ws)
      })
    })
  }
})

async function handleMessage(ws: WebSocket, message: any) {
  const { type, payload } = message

  switch (type) {
    case 'join':
      handleJoin(ws, payload)
      break
    case 'progress':
      await handleProgress(ws, payload)
      break
    case 'leave':
      handleLeave(ws)
      break
  }
}

function handleJoin(ws: WebSocket, payload: any) {
  const { bookId, userId } = payload
  connections.set(ws, { bookId, userId })

  const sessionKey = `${bookId}-${userId}`
  const session = sessions.get(sessionKey)
  
  if (session) {
    ws.send(JSON.stringify({
      type: 'sync',
      payload: {
        cfi: session.cfi,
        percentage: session.percentage
      }
    }))
  }
}

async function handleProgress(ws: WebSocket, payload: any) {
  const { bookId, userId, cfi, percentage } = payload
  const conn = connections.get(ws)
  
  if (!conn) return

  const sessionKey = `${bookId}-${userId}`
  sessions.set(sessionKey, {
    bookId,
    userId,
    cfi,
    percentage,
    timestamp: Date.now()
  })

  try {
    let progress = await prisma.progress.findFirst({
      where: { bookId }
    })

    if (progress) {
      await prisma.progress.update({
        where: { id: progress.id },
        data: { location: cfi, percentage }
      })
    } else {
      await prisma.progress.create({
        data: { bookId, location: cfi, percentage }
      })
    }
  } catch (e) {
    console.error('Failed to save progress:', e)
  }

  broadcastProgress(bookId, userId, cfi, percentage, ws)
}

function handleLeave(ws: WebSocket) {
  connections.delete(ws)
}

function broadcastProgress(
  bookId: number, 
  userId: string, 
  cfi: string, 
  percentage: number, 
  sender: WebSocket
) {
  connections.forEach((conn, ws) => {
    if (ws !== sender && conn.bookId === bookId) {
      ws.send(JSON.stringify({
        type: 'progress',
        payload: {
          userId,
          cfi,
          percentage,
          timestamp: Date.now()
        }
      }))
    }
  })
}

declare global {
  var wss: WebSocketServer | undefined
}
