'use client'

import { useEffect, useState, useCallback } from 'react'
import { Note, Folder } from '@/types'
import {
  isOnline,
  onOnline,
  onOffline,
  getAllNotesOffline,
  getAllFoldersOffline,
  saveNotesOffline,
  saveFoldersOffline,
  addToSyncQueue,
  getSyncQueue,
  clearSyncQueue,
  saveNoteOffline,
  deleteNoteOffline,
} from '@/lib/offlineDB'

interface UseOfflineSyncProps {
  notes: Note[]
  folders: Folder[]
  onUpdateNote: (noteId: string, updates: Partial<Note>) => Promise<Note>
  onCreateNote: (note: Partial<Note>) => Promise<Note>
  onDeleteNote: (noteId: string) => Promise<void>
  onUpdateFolder: (folderId: string, updates: Partial<Folder>) => Promise<Folder>
  onCreateFolder: (folder: Partial<Folder>) => Promise<Folder>
  onDeleteFolder: (folderId: string) => Promise<void>
}

export function useOfflineSync({
  notes,
  folders,
  onUpdateNote,
  onCreateNote,
  onDeleteNote,
  onUpdateFolder,
  onCreateFolder,
  onDeleteFolder,
}: UseOfflineSyncProps) {
  const [isOfflineMode, setIsOfflineMode] = useState(!isOnline())
  const [isSyncing, setIsSyncing] = useState(false)
  const [syncError, setSyncError] = useState<string | null>(null)
  const [pendingChanges, setPendingChanges] = useState(0)

  useEffect(() => {
    const updateOnlineStatus = () => {
      const offline = !isOnline()
      setIsOfflineMode(offline)
      if (!offline) {
        syncPendingChanges()
      }
    }

    const cleanupOnline = onOnline(updateOnlineStatus)
    const cleanupOffline = onOffline(updateOnlineStatus)

    updateOnlineStatus()

    return () => {
      cleanupOnline()
      cleanupOffline()
    }
  }, [])

  useEffect(() => {
    if (notes.length > 0) {
      saveNotesOffline(notes)
    }
  }, [notes])

  useEffect(() => {
    if (folders.length > 0) {
      saveFoldersOffline(folders)
    }
  }, [folders])

  useEffect(() => {
    const checkQueue = async () => {
      const queue = await getSyncQueue()
      setPendingChanges(queue.length)
    }
    checkQueue()
  }, [])

  const syncPendingChanges = useCallback(async () => {
    if (!isOnline() || isSyncing) return

    setIsSyncing(true)
    setSyncError(null)

    try {
      const queue = await getSyncQueue()
      const processedIds: string[] = []

      for (const item of queue) {
        try {
          if (item.entity === 'note') {
            switch (item.type) {
              case 'create':
                await onCreateNote(item.data)
                break
              case 'update':
                await onUpdateNote(item.data._id, item.data)
                break
              case 'delete':
                await onDeleteNote(item.data._id)
                break
            }
          } else if (item.entity === 'folder') {
            switch (item.type) {
              case 'create':
                await onCreateFolder(item.data)
                break
              case 'update':
                await onUpdateFolder(item.data._id, item.data)
                break
              case 'delete':
                await onDeleteFolder(item.data._id)
                break
            }
          }
          processedIds.push(item.id)
        } catch (error) {
          console.error(`Failed to sync ${item.type} ${item.entity}:`, error)
        }
      }

      if (processedIds.length > 0) {
        await clearSyncQueue(processedIds)
      }

      const remaining = await getSyncQueue()
      setPendingChanges(remaining.length)
    } catch (error) {
      setSyncError(error instanceof Error ? error.message : '同步失败')
    } finally {
      setIsSyncing(false)
    }
  }, [isSyncing, onCreateNote, onUpdateNote, onDeleteNote, onCreateFolder, onUpdateFolder, onDeleteFolder])

  const createNoteOffline = useCallback(async (note: Partial<Note>): Promise<Note> => {
    const tempId = `local-${Date.now()}`
    const newNote: Note = {
      _id: tempId,
      title: note.title || '无标题',
      content: note.content || '',
      tags: note.tags || [],
      folderId: note.folderId || null,
      createdAt: new Date(),
      updatedAt: new Date(),
      userId: '',
      isLocal: true,
    } as any

    if (isOfflineMode) {
      await saveNoteOffline(newNote)
      await addToSyncQueue('create', 'note', newNote)
    }

    return newNote
  }, [isOfflineMode])

  const updateNoteOffline = useCallback(async (noteId: string, updates: Partial<Note>): Promise<void> => {
    if (isOfflineMode) {
      const currentNote = await getAllNotesOffline().then(notes => notes.find(n => n._id === noteId))
      if (currentNote) {
        const updatedNote = { ...currentNote, ...updates, updatedAt: new Date() }
        await saveNoteOffline(updatedNote)
        await addToSyncQueue('update', 'note', updatedNote)
      }
    }
  }, [isOfflineMode])

  const deleteNoteOffline = useCallback(async (noteId: string): Promise<void> => {
    if (isOfflineMode) {
      await deleteNoteOffline(noteId)
      await addToSyncQueue('delete', 'note', { _id: noteId })
    }
  }, [isOfflineMode])

  const getOfflineNotes = useCallback(async (): Promise<Note[]> => {
    return await getAllNotesOffline()
  }, [])

  const getOfflineFolders = useCallback(async (): Promise<Folder[]> => {
    return await getAllFoldersOffline()
  }, [])

  return {
    isOfflineMode,
    isSyncing,
    syncError,
    pendingChanges,
    syncPendingChanges,
    createNoteOffline,
    updateNoteOffline,
    deleteNoteOffline,
    getOfflineNotes,
    getOfflineFolders,
  }
}
