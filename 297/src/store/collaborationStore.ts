import { create } from 'zustand'
import { OnlineUser, RegionLock, Point3D } from '@/types'

interface CollaborationState {
  onlineUsers: OnlineUser[]
  regionLocks: RegionLock[]
  setOnlineUsers: (users: OnlineUser[]) => void
  addOnlineUser: (user: OnlineUser) => void
  removeOnlineUser: (userId: string) => void
  updateUserPosition: (userId: string, position: Point3D) => void
  clearOnlineUsers: () => void
  setRegionLocks: (locks: RegionLock[]) => void
  addRegionLock: (lock: RegionLock) => void
  removeRegionLock: (lockId: string) => void
  clearRegionLocks: () => void
  isRegionLocked: (center: Point3D, radius: number) => RegionLock | null
  isRegionLockedByUser: (center: Point3D, radius: number, userId: string) => boolean
  getLocksByUser: (userId: string) => RegionLock[]
  clearExpiredLocks: () => void
}

export const useCollaborationStore = create<CollaborationState>((set, get) => ({
  onlineUsers: [],
  regionLocks: [],
  setOnlineUsers: (users) => set({ onlineUsers: users }),
  addOnlineUser: (user) =>
    set((state) => ({
      onlineUsers: [...state.onlineUsers, user],
    })),
  removeOnlineUser: (userId) =>
    set((state) => ({
      onlineUsers: state.onlineUsers.filter((u) => u.id !== userId),
    })),
  updateUserPosition: (userId, position) =>
    set((state) => ({
      onlineUsers: state.onlineUsers.map((u) =>
        u.id === userId ? { ...u, position } : u,
      ),
    })),
  clearOnlineUsers: () => set({ onlineUsers: [] }),
  setRegionLocks: (locks) => set({ regionLocks: locks }),
  addRegionLock: (lock) =>
    set((state) => ({
      regionLocks: [...state.regionLocks.filter(l => l.id !== lock.id), lock],
    })),
  removeRegionLock: (lockId) =>
    set((state) => ({
      regionLocks: state.regionLocks.filter((l) => l.id !== lockId),
    })),
  clearRegionLocks: () => set({ regionLocks: [] }),
  isRegionLocked: (center, radius) => {
    const state = get()
    for (const lock of state.regionLocks) {
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
  },
  isRegionLockedByUser: (center, radius, userId) => {
    const lock = get().isRegionLocked(center, radius)
    return lock !== null && lock.userId === userId
  },
  getLocksByUser: (userId) => {
    return get().regionLocks.filter(l => l.userId === userId)
  },
  clearExpiredLocks: () => {
    const now = new Date()
    set((state) => ({
      regionLocks: state.regionLocks.filter(l => new Date(l.expiresAt) > now),
    }))
  },
}))
