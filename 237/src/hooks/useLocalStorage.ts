import { useState, useEffect } from 'react'

export function useLocalStorage<T>(key: string, initialValue: T): [T, (value: T | ((val: T) => T)) => void] {
  const [storedValue, setStoredValue] = useState<T>(() => {
    if (typeof window === 'undefined') {
      return initialValue
    }
    try {
      const item = window.localStorage.getItem(key)
      return item ? JSON.parse(item) : initialValue
    } catch (error) {
      console.error('Error reading localStorage:', error)
      return initialValue
    }
  })

  const setValue = (value: T | ((val: T) => T)) => {
    try {
      const valueToStore = value instanceof Function ? value(storedValue) : value
      setStoredValue(valueToStore)
      if (typeof window !== 'undefined') {
        window.localStorage.setItem(key, JSON.stringify(valueToStore))
      }
    } catch (error) {
      console.error('Error writing to localStorage:', error)
    }
  }

  return [storedValue, setValue]
}

export function getFromLocalStorage<T>(key: string, defaultValue: T): T {
  if (typeof window === 'undefined') {
    return defaultValue
  }
  try {
    const item = window.localStorage.getItem(key)
    return item ? JSON.parse(item) : defaultValue
  } catch (error) {
    return defaultValue
  }
}

export function setToLocalStorage<T>(key: string, value: T): void {
  if (typeof window === 'undefined') {
    return
  }
  try {
    window.localStorage.setItem(key, JSON.stringify(value))
  } catch (error) {
    console.error('Error writing to localStorage:', error)
  }
}

export function removeFromLocalStorage(key: string): void {
  if (typeof window === 'undefined') {
    return
  }
  try {
    window.localStorage.removeItem(key)
  } catch (error) {
    console.error('Error removing from localStorage:', error)
  }
}

export const NOTE_CACHE_PREFIX = 'note_cache_'
export const NOTE_CACHE_TIMESTAMP_PREFIX = 'note_cache_ts_'

export function getNoteCache(noteId: string): { title: string; content: string; timestamp: number } | null {
  const cache = getFromLocalStorage<any>(NOTE_CACHE_PREFIX + noteId, null)
  if (!cache) return null
  
  const timestamp = getFromLocalStorage<number>(NOTE_CACHE_TIMESTAMP_PREFIX + noteId, 0)
  return { ...cache, timestamp }
}

export function setNoteCache(noteId: string, title: string, content: string): void {
  setToLocalStorage(NOTE_CACHE_PREFIX + noteId, { title, content })
  setToLocalStorage(NOTE_CACHE_TIMESTAMP_PREFIX + noteId, Date.now())
}

export function clearNoteCache(noteId: string): void {
  removeFromLocalStorage(NOTE_CACHE_PREFIX + noteId)
  removeFromLocalStorage(NOTE_CACHE_TIMESTAMP_PREFIX + noteId)
}

export function getAllCachedNotes(): { noteId: string; title: string; content: string; timestamp: number }[] {
  if (typeof window === 'undefined') {
    return []
  }
  
  const notes: { noteId: string; title: string; content: string; timestamp: number }[] = []
  
  for (let i = 0; i < window.localStorage.length; i++) {
    const key = window.localStorage.key(i)
    if (key && key.startsWith(NOTE_CACHE_PREFIX)) {
      const noteId = key.replace(NOTE_CACHE_PREFIX, '')
      const cache = getNoteCache(noteId)
      if (cache) {
        notes.push({ noteId, ...cache })
      }
    }
  }
  
  return notes.sort((a, b) => b.timestamp - a.timestamp)
}
