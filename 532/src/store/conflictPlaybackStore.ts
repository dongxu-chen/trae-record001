import { create } from 'zustand'
import type { ConflictRegion, CodeVersion, PlaybackState } from '@/types'

interface ConflictStore {
  conflictRegions: ConflictRegion[]
  hasConflicts: boolean
  resolvedCode: string

  parseConflicts: (code: string) => void
  resolveConflict: (index: number, resolution: 'current' | 'incoming' | 'both') => void
  resolveAll: (resolution: 'current' | 'incoming' | 'both') => void
  getResolvedCode: (originalCode: string) => string
  resetConflicts: () => void
}

export const useConflictStore = create<ConflictStore>((set, get) => ({
  conflictRegions: [],
  hasConflicts: false,
  resolvedCode: '',

  parseConflicts: (code: string) => {
    const regions: ConflictRegion[] = []
    const lines = code.split('\n')
    let i = 0

    while (i < lines.length) {
      if (lines[i].startsWith('<<<<<<<')) {
        const startLine = i + 1
        const currentLabel = lines[i].replace('<<<<<<<', '').trim() || '当前更改'
        let currentContent = ''
        let incomingContent = ''
        let incomingLabel = ''
        let inCurrent = true
        i++

        while (i < lines.length && !lines[i].startsWith('>>>>>>>')) {
          if (lines[i].startsWith('=======')) {
            inCurrent = false
            i++
            continue
          }
          if (inCurrent) {
            currentContent += (currentContent ? '\n' : '') + lines[i]
          } else {
            if (!incomingLabel && lines[i].trim()) {
            }
            incomingContent += (incomingContent ? '\n' : '') + lines[i]
          }
          i++
        }

        if (i < lines.length) {
          incomingLabel = lines[i].replace('>>>>>>>', '').trim() || '传入更改'
          i++
        }

        const endLine = i

        regions.push({
          startLine,
          endLine,
          currentContent,
          incomingContent,
          currentLabel,
          incomingLabel,
          resolved: false,
          resolution: null,
        })
      } else {
        i++
      }
    }

    set({
      conflictRegions: regions,
      hasConflicts: regions.length > 0,
    })
  },

  resolveConflict: (index, resolution) => {
    set((s) => ({
      conflictRegions: s.conflictRegions.map((r, i) =>
        i === index ? { ...r, resolved: true, resolution } : r
      ),
    }))
  },

  resolveAll: (resolution) => {
    set((s) => ({
      conflictRegions: s.conflictRegions.map((r) => ({
        ...r,
        resolved: true,
        resolution,
      })),
    }))
  },

  getResolvedCode: (originalCode: string) => {
    const { conflictRegions } = get()
    if (conflictRegions.length === 0) return originalCode

    const lines = originalCode.split('\n')
    const result: string[] = []
    let skipUntil = -1

    for (let i = 0; i < lines.length; i++) {
      if (i < skipUntil) continue

      const region = conflictRegions.find((r) => r.startLine === i + 1)
      if (region) {
        if (region.resolved && region.resolution) {
          if (region.resolution === 'current') {
            result.push(...region.currentContent.split('\n'))
          } else if (region.resolution === 'incoming') {
            result.push(...region.incomingContent.split('\n'))
          } else if (region.resolution === 'both') {
            result.push(...region.currentContent.split('\n'))
            result.push(...region.incomingContent.split('\n'))
          }
        } else {
          result.push(...lines.slice(i, region.endLine))
        }
        skipUntil = region.endLine
        continue
      }

      if (lines[i].startsWith('<<<<<<<') || lines[i].startsWith('=======') || lines[i].startsWith('>>>>>>>')) {
        continue
      }

      result.push(lines[i])
    }

    return result.join('\n')
  },

  resetConflicts: () => set({ conflictRegions: [], hasConflicts: false, resolvedCode: '' }),
}))

interface PlaybackStore {
  versions: CodeVersion[]
  currentIndex: number
  playbackState: PlaybackState
  playbackSpeed: number
  autoPlayInterval: ReturnType<typeof setInterval> | null

  setVersions: (versions: CodeVersion[]) => void
  addVersion: (version: Omit<CodeVersion, 'id'>) => void
  removeVersion: (id: string) => void
  setCurrentIndex: (index: number) => void
  play: () => void
  pause: () => void
  stop: () => void
  nextStep: () => void
  prevStep: () => void
  setPlaybackSpeed: (speed: number) => void
  getCurrentVersion: () => CodeVersion | null
  getPreviousVersion: () => CodeVersion | null
  reset: () => void
}

export const usePlaybackStore = create<PlaybackStore>((set, get) => ({
  versions: [],
  currentIndex: 0,
  playbackState: 'idle',
  playbackSpeed: 2000,
  autoPlayInterval: null,

  setVersions: (versions) => set({ versions, currentIndex: 0, playbackState: 'idle' }),

  addVersion: (version) => {
    const id = `ver_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`
    set((s) => ({
      versions: [...s.versions, { ...version, id }],
    }))
  },

  removeVersion: (id) => {
    set((s) => {
      const newVersions = s.versions.filter((v) => v.id !== id)
      return {
        versions: newVersions,
        currentIndex: Math.min(s.currentIndex, newVersions.length - 1),
      }
    })
  },

  setCurrentIndex: (currentIndex) => set({ currentIndex }),

  play: () => {
    const { versions, currentIndex, playbackSpeed } = get()
    if (versions.length <= 1) return

    set({ playbackState: 'playing' })

    const interval = setInterval(() => {
      const { currentIndex: ci, versions: vs } = get()
      if (ci >= vs.length - 1) {
        get().pause()
        return
      }
      set({ currentIndex: ci + 1 })
    }, playbackSpeed)

    set({ autoPlayInterval: interval })
  },

  pause: () => {
    const { autoPlayInterval } = get()
    if (autoPlayInterval) {
      clearInterval(autoPlayInterval)
    }
    set({ playbackState: 'paused', autoPlayInterval: null })
  },

  stop: () => {
    const { autoPlayInterval } = get()
    if (autoPlayInterval) {
      clearInterval(autoPlayInterval)
    }
    set({ playbackState: 'idle', currentIndex: 0, autoPlayInterval: null })
  },

  nextStep: () => {
    const { currentIndex, versions } = get()
    if (currentIndex < versions.length - 1) {
      set({ currentIndex: currentIndex + 1, playbackState: 'paused' })
    }
  },

  prevStep: () => {
    const { currentIndex } = get()
    if (currentIndex > 0) {
      set({ currentIndex: currentIndex - 1, playbackState: 'paused' })
    }
  },

  setPlaybackSpeed: (playbackSpeed) => {
    const { playbackState } = get()
    set({ playbackSpeed })
    if (playbackState === 'playing') {
      get().pause()
      get().play()
    }
  },

  getCurrentVersion: () => {
    const { versions, currentIndex } = get()
    return versions[currentIndex] || null
  },

  getPreviousVersion: () => {
    const { versions, currentIndex } = get()
    if (currentIndex > 0) return versions[currentIndex - 1]
    return null
  },

  reset: () => {
    const { autoPlayInterval } = get()
    if (autoPlayInterval) clearInterval(autoPlayInterval)
    set({ versions: [], currentIndex: 0, playbackState: 'idle', autoPlayInterval: null })
  },
}))
