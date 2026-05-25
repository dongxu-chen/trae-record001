import { io, Socket } from 'socket.io-client'
import { Annotation, Point3D, RegionLock } from '@/types'

class WebSocketService {
  private socket: Socket | null = null

  connect() {
    if (this.socket?.connected) return

    this.socket = io({
      transports: ['websocket'],
    })

    return new Promise<void>((resolve) => {
      this.socket?.on('connect', () => {
        console.log('WebSocket connected')
        resolve()
      })
    })
  }

  disconnect() {
    this.socket?.disconnect()
    this.socket = null
  }

  joinProject(projectId: string, userId: string, userName: string) {
    this.socket?.emit('join-project', { projectId, userId, userName })
  }

  leaveProject(projectId: string) {
    this.socket?.emit('leave-project', { projectId })
  }

  sendAnnotationCreated(projectId: string, annotation: Annotation) {
    this.socket?.emit('annotation-created', { projectId, annotation })
  }

  sendAnnotationDeleted(projectId: string, annotationId: string) {
    this.socket?.emit('annotation-deleted', { projectId, annotationId })
  }

  sendCursorPosition(projectId: string, position: Point3D, rotation: Point3D) {
    this.socket?.emit('cursor-position', { projectId, position, rotation })
  }

  acquireRegionLock(projectId: string, center: Point3D, radius: number, boundingBox: { min: Point3D; max: Point3D }) {
    this.socket?.emit('acquire-region-lock', { 
      projectId, 
      center, 
      radius, 
      boundingBox 
    })
  }

  releaseRegionLock(projectId: string, lockId: string) {
    this.socket?.emit('release-region-lock', { projectId, lockId })
  }

  updateRegionLock(projectId: string, lockId: string, boundingBox: { min: Point3D; max: Point3D }) {
    this.socket?.emit('update-region-lock', { projectId, lockId, boundingBox })
  }

  on(event: string, callback: (...args: unknown[]) => void) {
    this.socket?.on(event, callback)
  }

  off(event: string, callback: (...args: unknown[]) => void) {
    this.socket?.off(event, callback)
  }
}

export const wsService = new WebSocketService()
