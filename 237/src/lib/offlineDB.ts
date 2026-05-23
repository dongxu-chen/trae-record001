import { openDB, IDBPDatabase } from 'idb'
import { Note, Folder } from '@/types'

const DB_NAME = 'markdown-notes-db'
const DB_VERSION = 1

export interface OfflineNote extends Note {
  isLocal?: boolean
  lastSyncedAt?: Date
}

export interface SyncQueueItem {
  id: string
  type: 'create' | 'update' | 'delete'
  entity: 'note' | 'folder'
  data: any
  timestamp: number
}

let dbPromise: Promise<IDBPDatabase> | null = null

export function initDB(): Promise<IDBPDatabase> {
  if (!dbPromise) {
    dbPromise = openDB(DB_NAME, DB_VERSION, {
      upgrade(db) {
        if (!db.objectStoreNames.contains('notes')) {
          const notesStore = db.createObjectStore('notes', { keyPath: '_id' })
          notesStore.createIndex('updatedAt', 'updatedAt')
          notesStore.createIndex('folderId', 'folderId')
        }

        if (!db.objectStoreNames.contains('folders')) {
          db.createObjectStore('folders', { keyPath: '_id' })
        }

        if (!db.objectStoreNames.contains('syncQueue')) {
          const syncStore = db.createObjectStore('syncQueue', { keyPath: 'id' })
          syncStore.createIndex('timestamp', 'timestamp')
        }

        if (!db.objectStoreNames.contains('images')) {
          db.createObjectStore('images', { keyPath: 'id' })
        }
      },
    })
  }
  return dbPromise
}

export async function saveNotesOffline(notes: Note[]): Promise<void> {
  const db = await initDB()
  const tx = db.transaction('notes', 'readwrite')
  for (const note of notes) {
    await tx.store.put({
      ...note,
      lastSyncedAt: new Date(),
    })
  }
  await tx.done
}

export async function saveNoteOffline(note: Note): Promise<void> {
  const db = await initDB()
  await db.put('notes', {
    ...note,
    lastSyncedAt: new Date(),
  })
}

export async function getNoteOffline(noteId: string): Promise<OfflineNote | undefined> {
  const db = await initDB()
  return await db.get('notes', noteId)
}

export async function getAllNotesOffline(): Promise<OfflineNote[]> {
  const db = await initDB()
  return await db.getAll('notes')
}

export async function deleteNoteOffline(noteId: string): Promise<void> {
  const db = await initDB()
  await db.delete('notes', noteId)
}

export async function saveFoldersOffline(folders: Folder[]): Promise<void> {
  const db = await initDB()
  const tx = db.transaction('folders', 'readwrite')
  for (const folder of folders) {
    await tx.store.put(folder)
  }
  await tx.done
}

export async function getAllFoldersOffline(): Promise<Folder[]> {
  const db = await initDB()
  return await db.getAll('folders')
}

export async function addToSyncQueue(
  type: 'create' | 'update' | 'delete',
  entity: 'note' | 'folder',
  data: any
): Promise<void> {
  const db = await initDB()
  const item: SyncQueueItem = {
    id: `${type}-${entity}-${data._id || Date.now()}`,
    type,
    entity,
    data,
    timestamp: Date.now(),
  }
  await db.put('syncQueue', item)
}

export async function getSyncQueue(): Promise<SyncQueueItem[]> {
  const db = await initDB()
  return await db.getAllFromIndex('syncQueue', 'timestamp')
}

export async function clearSyncQueue(ids: string[]): Promise<void> {
  const db = await initDB()
  const tx = db.transaction('syncQueue', 'readwrite')
  for (const id of ids) {
    await tx.store.delete(id)
  }
  await tx.done
}

export async function clearAllSyncQueue(): Promise<void> {
  const db = await initDB()
  await db.clear('syncQueue')
}

export async function saveImageOffline(
  imageId: string,
  imageData: Blob,
  ocrText?: string
): Promise<void> {
  const db = await initDB()
  await db.put('images', {
    id: imageId,
    blob: imageData,
    ocrText: ocrText || '',
    createdAt: new Date(),
  })
}

export async function getImageOffline(imageId: string): Promise<{ blob: Blob; ocrText: string } | undefined> {
  const db = await initDB()
  return await db.get('images', imageId)
}

export function isOnline(): boolean {
  return typeof navigator !== 'undefined' && navigator.onLine
}

export function onOnline(callback: () => void): () => void {
  if (typeof window === 'undefined') return () => {}
  window.addEventListener('online', callback)
  return () => window.removeEventListener('online', callback)
}

export function onOffline(callback: () => void): () => void {
  if (typeof window === 'undefined') return () => {}
  window.addEventListener('offline', callback)
  return () => window.removeEventListener('offline', callback)
}

export async function clearOfflineData(): Promise<void> {
  const db = await initDB()
  const tx = db.transaction(['notes', 'folders', 'syncQueue', 'images'], 'readwrite')
  await tx.objectStore('notes').clear()
  await tx.objectStore('folders').clear()
  await tx.objectStore('syncQueue').clear()
  await tx.objectStore('images').clear()
  await tx.done
}
