import express from 'express'
import http from 'http'
import { Server } from 'socket.io'
import cors from 'cors'
import path from 'path'
import { fileURLToPath } from 'url'
import authRoutes from './routes/auth'
import projectRoutes from './routes/projects'
import annotationRoutes from './routes/annotations'
import statisticsRoutes from './routes/statistics'
import { initDatabase } from './database'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

const app = express()
const server = http.createServer(app)

const io = new Server(server, {
  cors: {
    origin: 'http://localhost:3000',
    methods: ['GET', 'POST'],
  },
})

app.use(cors())
app.use(express.json())

initDatabase()

app.use('/api/auth', authRoutes)
app.use('/api/projects', projectRoutes)
app.use('/api/annotations', annotationRoutes)
app.use('/api/statistics', statisticsRoutes)

interface ProjectRoom {
  users: Set<string>
  regionLocks: Map<string, RegionLock>
}

interface RegionLock {
  id: string
  userId: string
  userName: string
  projectId: string
  boundingBox: {
    min: { x: number; y: number; z: number }
    max: { x: number; y: number; z: number }
  }
  center: { x: number; y: number; z: number }
  createdAt: string
  expiresAt: string
}

const projectRooms = new Map<string, ProjectRoom>()
const userColors = new Map<string, string>()
const userNames = new Map<string, string>()

const colors = ['#165DFF', '#00B42A', '#F53F3F', '#FF7D00', '#722ED1', '#86909C']

function getOrCreateRoom(projectId: string): ProjectRoom {
  if (!projectRooms.has(projectId)) {
    projectRooms.set(projectId, {
      users: new Set(),
      regionLocks: new Map(),
    })
  }
  return projectRooms.get(projectId)!
}

function checkLockConflict(
  room: ProjectRoom,
  center: { x: number; y: number; z: number },
  radius: number,
  excludeUserId?: string
): RegionLock | null {
  for (const lock of room.regionLocks.values()) {
    if (excludeUserId && lock.userId === excludeUserId) continue
    if (new Date(lock.expiresAt) < new Date()) continue

    const distance = Math.sqrt(
      Math.pow(center.x - lock.center.x, 2) +
      Math.pow(center.y - lock.center.y, 2) +
      Math.pow(center.z - lock.center.z, 2)
    )

    const lockRadius = Math.max(
      (lock.boundingBox.max.x - lock.boundingBox.min.x) / 2,
      (lock.boundingBox.max.y - lock.boundingBox.min.y) / 2,
      (lock.boundingBox.max.z - lock.boundingBox.min.z) / 2
    )

    if (distance < radius + lockRadius) {
      return lock
    }
  }
  return null
}

io.on('connection', (socket) => {
  console.log('User connected:', socket.id)

  socket.on('join-project', ({ projectId, userId, userName }) => {
    socket.join(projectId)
    
    const room = getOrCreateRoom(projectId)
    room.users.add(userId)
    
    const color = colors[Array.from(room.users).indexOf(userId) % colors.length]
    userColors.set(userId, color)
    userNames.set(userId, userName)

    const users = Array.from(room.users).map(id => ({
      id,
      username: userNames.get(id) || 'Unknown',
      color: userColors.get(id) || '#165DFF',
    }))

    const locks = Array.from(room.regionLocks.values())

    socket.to(projectId).emit('user-joined', {
      userId,
      userName,
      color,
    })

    socket.emit('online-users', { users })
    socket.emit('region-locks', { locks })
  })

  socket.on('leave-project', ({ projectId, userId }) => {
    socket.leave(projectId)
    const room = projectRooms.get(projectId)
    if (room) {
      room.users.delete(userId)
      
      for (const [lockId, lock] of room.regionLocks) {
        if (lock.userId === userId) {
          room.regionLocks.delete(lockId)
        }
      }
    }
    
    socket.to(projectId).emit('user-left', { userId })
  })

  socket.on('acquire-region-lock', ({ projectId, userId, userName, center, boundingBox }) => {
    const room = getOrCreateRoom(projectId)
    const radius = Math.max(
      (boundingBox.max.x - boundingBox.min.x) / 2,
      (boundingBox.max.y - boundingBox.min.y) / 2,
      (boundingBox.max.z - boundingBox.min.z) / 2
    )

    const conflict = checkLockConflict(room, center, radius, userId)
    if (conflict) {
      socket.emit('region-lock-denied', {
        reason: '区域已被锁定',
        conflictedLock: conflict,
      })
      return
    }

    const lockId = `lock_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    const lock: RegionLock = {
      id: lockId,
      userId,
      userName,
      projectId,
      boundingBox,
      center,
      createdAt: new Date().toISOString(),
      expiresAt: new Date(Date.now() + 5 * 60 * 1000).toISOString(),
    }

    room.regionLocks.set(lockId, lock)

    io.to(projectId).emit('region-lock-acquired', { lock })

    setTimeout(() => {
      if (room.regionLocks.has(lockId)) {
        room.regionLocks.delete(lockId)
        io.to(projectId).emit('region-lock-released', { lockId, userId })
      }
    }, 5 * 60 * 1000)
  })

  socket.on('release-region-lock', ({ projectId, lockId, userId }) => {
    const room = projectRooms.get(projectId)
    if (room) {
      const lock = room.regionLocks.get(lockId)
      if (lock && lock.userId === userId) {
        room.regionLocks.delete(lockId)
        io.to(projectId).emit('region-lock-released', { lockId, userId })
      }
    }
  })

  socket.on('update-region-lock', ({ projectId, lockId, userId, boundingBox }) => {
    const room = projectRooms.get(projectId)
    if (room) {
      const lock = room.regionLocks.get(lockId)
      if (lock && lock.userId === userId) {
        lock.boundingBox = boundingBox
        lock.center = {
          x: (boundingBox.min.x + boundingBox.max.x) / 2,
          y: (boundingBox.min.y + boundingBox.max.y) / 2,
          z: (boundingBox.min.z + boundingBox.max.z) / 2,
        }
        lock.expiresAt = new Date(Date.now() + 5 * 60 * 1000).toISOString()
        io.to(projectId).emit('region-lock-updated', { lock })
      }
    }
  })

  socket.on('annotation-created', ({ projectId, annotation, userId }) => {
    socket.to(projectId).emit('annotation-created', { annotation, userId })
    
    const room = projectRooms.get(projectId)
    if (room && annotation.geometry) {
      let center
      if (annotation.type === 'box') {
        center = (annotation.geometry as any).center
      } else {
        const points = (annotation.geometry as any).points || []
        center = points.length > 0 ? points[0] : { x: 0, y: 0, z: 0 }
      }
      
      for (const [lockId, lock] of room.regionLocks) {
        if (lock.userId === userId) {
          room.regionLocks.delete(lockId)
          io.to(projectId).emit('region-lock-released', { lockId, userId })
        }
      }
    }
  })

  socket.on('annotation-deleted', ({ projectId, annotationId, userId }) => {
    socket.to(projectId).emit('annotation-deleted', { annotationId, userId })
  })

  socket.on('cursor-position', ({ projectId, userId, position, rotation }) => {
    socket.to(projectId).emit('cursor-update', { userId, position, rotation })
  })

  socket.on('disconnect', () => {
    console.log('User disconnected:', socket.id)
  })
})

const PORT = 3001
server.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`)
})
