import { create } from 'zustand'
import type { TranscriptSegment } from '../utils/SpeechToText'
import type { CopyrightInfo } from '../utils/AudioFingerprint'

export interface Clip {
  id: string
  trackId: string
  startTime: number
  endTime: number
  offset: number
  volume: number
  fadeIn: number
  fadeOut: number
  name: string
}

export interface Track {
  id: string
  name: string
  color: string
  volume: number
  muted: boolean
  solo: boolean
  clips: Clip[]
}

export interface SubtitleTrack {
  id: string
  name: string
  visible: boolean
  segments: TranscriptSegment[]
}

export interface AudioFile {
  id: string
  name: string
  file: File
  url: string
  duration: number
  copyrightInfo?: CopyrightInfo | null
}

export interface HistoryState {
  tracks: Track[]
  selectedClipId: string | null
  selectedTrackId: string | null
}

interface EditorState extends HistoryState {
  files: AudioFile[]
  subtitleTracks: SubtitleTrack[]
  isPlaying: boolean
  currentTime: number
  totalDuration: number
  undoStack: HistoryState[]
  redoStack: HistoryState[]
  zoom: number

  addFile: (file: AudioFile) => void
  removeFile: (id: string) => void
  updateFileCopyright: (id: string, copyrightInfo: CopyrightInfo | null) => void

  addTrack: () => void
  removeTrack: (id: string) => void
  updateTrack: (id: string, updates: Partial<Track>) => void
  setTrackVolume: (id: string, volume: number) => void
  toggleMute: (id: string) => void
  toggleSolo: (id: string) => void

  addClip: (trackId: string, clip: Omit<Clip, 'trackId'>) => void
  removeClip: (clipId: string) => void
  updateClip: (clipId: string, updates: Partial<Clip>) => void
  selectClip: (clipId: string | null) => void
  selectTrack: (trackId: string | null) => void

  addSubtitleTrack: () => void
  removeSubtitleTrack: (id: string) => void
  updateSubtitleTrack: (id: string, updates: Partial<SubtitleTrack>) => void
  addSubtitleSegment: (trackId: string, segment: TranscriptSegment) => void
  removeSubtitleSegment: (trackId: string, segmentId: string) => void
  toggleSubtitleVisible: (id: string) => void

  setPlaying: (playing: boolean) => void
  setCurrentTime: (time: number) => void
  setTotalDuration: (duration: number) => void

  setZoom: (zoom: number) => void

  saveHistory: () => void
  undo: () => void
  redo: () => void
  canUndo: () => boolean
  canRedo: () => boolean

  getCurrentState: () => HistoryState
  restoreState: (state: HistoryState) => void
}

let trackCounter = 0
let clipCounter = 0
let subtitleTrackCounter = 0

const generateId = (prefix: string, counter: number) => `${prefix}_${counter}_${Date.now()}`

export const useEditorStore = create<EditorState>((set, get) => ({
  files: [],
  tracks: [],
  subtitleTracks: [],
  selectedClipId: null,
  selectedTrackId: null,
  isPlaying: false,
  currentTime: 0,
  totalDuration: 60,
  undoStack: [],
  redoStack: [],
  zoom: 50,

  addFile: (file) => set((state) => ({ files: [...state.files, file] })),
  removeFile: (id) =>
    set((state) => ({ files: state.files.filter((f) => f.id !== id) })),
  updateFileCopyright: (id, copyrightInfo) =>
    set((state) => ({
      files: state.files.map((f) => (f.id === id ? { ...f, copyrightInfo } : f)),
    })),

  addTrack: () => {
    trackCounter++
    const colors = ['#4ade80', '#60a5fa', '#f472b6', '#fbbf24', '#a78bfa', '#fb923c', '#34d399', '#818cf8']
    const newTrack: Track = {
      id: generateId('track', trackCounter),
      name: `轨道 ${trackCounter}`,
      color: colors[(trackCounter - 1) % colors.length],
      volume: 1,
      muted: false,
      solo: false,
      clips: [],
    }
    set((state) => ({ tracks: [...state.tracks, newTrack] }))
  },

  removeTrack: (id) =>
    set((state) => ({
      tracks: state.tracks.filter((t) => t.id !== id),
      selectedTrackId: state.selectedTrackId === id ? null : state.selectedTrackId,
      selectedClipId: state.tracks
        .find((t) => t.id === id)
        ?.clips.some((c) => c.id === state.selectedClipId)
        ? null
        : state.selectedClipId,
    })),

  updateTrack: (id, updates) =>
    set((state) => ({
      tracks: state.tracks.map((t) => (t.id === id ? { ...t, ...updates } : t)),
    })),

  setTrackVolume: (id, volume) =>
    set((state) => ({
      tracks: state.tracks.map((t) => (t.id === id ? { ...t, volume } : t)),
    })),

  toggleMute: (id) =>
    set((state) => ({
      tracks: state.tracks.map((t) => (t.id === id ? { ...t, muted: !t.muted } : t)),
    })),

  toggleSolo: (id) =>
    set((state) => ({
      tracks: state.tracks.map((t) => (t.id === id ? { ...t, solo: !t.solo } : t)),
    })),

  addClip: (trackId, clip) =>
    set((state) => ({
      tracks: state.tracks.map((t) =>
        t.id === trackId ? { ...t, clips: [...t.clips, { ...clip, trackId }] } : t
      ),
    })),

  removeClip: (clipId) =>
    set((state) => ({
      tracks: state.tracks.map((t) => ({
        ...t,
        clips: t.clips.filter((c) => c.id !== clipId),
      })),
      selectedClipId: state.selectedClipId === clipId ? null : state.selectedClipId,
    })),

  updateClip: (clipId, updates) =>
    set((state) => ({
      tracks: state.tracks.map((t) => ({
        ...t,
        clips: t.clips.map((c) => (c.id === clipId ? { ...c, ...updates } : c)),
      })),
    })),

  selectClip: (clipId) => set({ selectedClipId: clipId }),
  selectTrack: (trackId) => set({ selectedTrackId: trackId }),

  addSubtitleTrack: () => {
    subtitleTrackCounter++
    const newTrack: SubtitleTrack = {
      id: generateId('subtitle', subtitleTrackCounter),
      name: `字幕 ${subtitleTrackCounter}`,
      visible: true,
      segments: [],
    }
    set((state) => ({ subtitleTracks: [...state.subtitleTracks, newTrack] }))
  },

  removeSubtitleTrack: (id) =>
    set((state) => ({
      subtitleTracks: state.subtitleTracks.filter((t) => t.id !== id),
    })),

  updateSubtitleTrack: (id, updates) =>
    set((state) => ({
      subtitleTracks: state.subtitleTracks.map((t) =>
        t.id === id ? { ...t, ...updates } : t
      ),
    })),

  addSubtitleSegment: (trackId, segment) =>
    set((state) => ({
      subtitleTracks: state.subtitleTracks.map((t) =>
        t.id === trackId ? { ...t, segments: [...t.segments, segment] } : t
      ),
    })),

  removeSubtitleSegment: (trackId, segmentId) =>
    set((state) => ({
      subtitleTracks: state.subtitleTracks.map((t) =>
        t.id === trackId
          ? { ...t, segments: t.segments.filter((s) => s.id !== segmentId) }
          : t
      ),
    })),

  toggleSubtitleVisible: (id) =>
    set((state) => ({
      subtitleTracks: state.subtitleTracks.map((t) =>
        t.id === id ? { ...t, visible: !t.visible } : t
      ),
    })),

  setPlaying: (playing) => set({ isPlaying: playing }),
  setCurrentTime: (time) => set({ currentTime: time }),
  setTotalDuration: (duration) => set({ totalDuration: duration }),

  setZoom: (zoom) => set({ zoom: Math.max(10, Math.min(200, zoom)) }),

  saveHistory: () => {
    const state = get()
    const historyState: HistoryState = {
      tracks: JSON.parse(JSON.stringify(state.tracks)),
      selectedClipId: state.selectedClipId,
      selectedTrackId: state.selectedTrackId,
    }
    set((s) => ({
      undoStack: [...s.undoStack, historyState],
      redoStack: [],
    }))
  },

  undo: () => {
    const state = get()
    if (state.undoStack.length === 0) return
    const previous = state.undoStack[state.undoStack.length - 1]
    const current: HistoryState = {
      tracks: JSON.parse(JSON.stringify(state.tracks)),
      selectedClipId: state.selectedClipId,
      selectedTrackId: state.selectedTrackId,
    }
    set({
      tracks: previous.tracks,
      selectedClipId: previous.selectedClipId,
      selectedTrackId: previous.selectedTrackId,
      undoStack: state.undoStack.slice(0, -1),
      redoStack: [...state.redoStack, current],
    })
  },

  redo: () => {
    const state = get()
    if (state.redoStack.length === 0) return
    const next = state.redoStack[state.redoStack.length - 1]
    const current: HistoryState = {
      tracks: JSON.parse(JSON.stringify(state.tracks)),
      selectedClipId: state.selectedClipId,
      selectedTrackId: state.selectedTrackId,
    }
    set({
      tracks: next.tracks,
      selectedClipId: next.selectedClipId,
      selectedTrackId: next.selectedTrackId,
      undoStack: [...state.undoStack, current],
      redoStack: state.redoStack.slice(0, -1),
    })
  },

  canUndo: () => get().undoStack.length > 0,
  canRedo: () => get().redoStack.length > 0,

  getCurrentState: () => {
    const state = get()
    return {
      tracks: state.tracks,
      selectedClipId: state.selectedClipId,
      selectedTrackId: state.selectedTrackId,
    }
  },

  restoreState: (state) => {
    set({
      tracks: state.tracks,
      selectedClipId: state.selectedClipId,
      selectedTrackId: state.selectedTrackId,
    })
  },
}))

export const generateClipId = () => {
  clipCounter++
  return generateId('clip', clipCounter)
}
