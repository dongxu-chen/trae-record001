import { create } from 'zustand'
import { Project, Layer, SvgElement, Keyframe, Version, Point } from '@/types'
import { db } from './database'
import { nanoid } from 'nanoid'

interface EditorState {
  project: Project | null
  selectedLayerId: string | null
  currentTime: number
  isPlaying: boolean
  projects: Project[]
  isLoading: boolean

  init: () => Promise<void>
  loadProjects: () => Promise<void>
  createProject: (name: string, svgContent: string) => Promise<void>
  loadProject: (id: string) => Promise<void>
  saveProject: () => Promise<void>
  deleteProject: (id: string) => Promise<void>

  selectLayer: (layerId: string | null) => void
  setCurrentTime: (time: number) => void
  setPlaying: (playing: boolean) => void
  updateElementTransform: (elementId: string, transform: Partial<SvgElement['transform']>) => void
  addKeyframe: (layerId: string, property: string, time: number, value: any) => void
  removeKeyframe: (layerId: string, trackId: string, keyframeId: string) => void
  updateKeyframe: (layerId: string, trackId: string, keyframeId: string, updates: Partial<Keyframe>) => void

  createVersion: (name: string, description: string) => Promise<void>
  restoreVersion: (versionId: string) => Promise<void>
}

export const useEditorStore = create<EditorState>((set, get) => ({
  project: null,
  selectedLayerId: null,
  currentTime: 0,
  isPlaying: false,
  projects: [],
  isLoading: true,

  init: async () => {
    await db.init()
    await get().loadProjects()
    set({ isLoading: false })
  },

  loadProjects: async () => {
    const projects = await db.getProjects()
    set({ projects })
  },

  createProject: async (name: string, svgContent: string) => {
    const project: Project = {
      id: nanoid(),
      name,
      createdAt: Date.now(),
      updatedAt: Date.now(),
      duration: 3000,
      framerate: 60,
      width: 400,
      height: 400,
      svgContent,
      elements: {},
      layers: [],
      versions: [],
    }
    await db.saveProject(project)
    await get().loadProjects()
    set({ project })
  },

  loadProject: async (id: string) => {
    const project = await db.getProject(id)
    if (project) {
      set({ project, currentTime: 0, selectedLayerId: null })
    }
  },

  saveProject: async () => {
    const { project } = get()
    if (project) {
      await db.saveProject(project)
      await get().loadProjects()
    }
  },

  deleteProject: async (id: string) => {
    await db.deleteProject(id)
    await get().loadProjects()
    if (get().project?.id === id) {
      set({ project: null })
    }
  },

  selectLayer: (layerId) => set({ selectedLayerId: layerId }),

  setCurrentTime: (time) => set({ currentTime: time }),

  setPlaying: (playing) => set({ isPlaying: playing }),

  updateElementTransform: (elementId, transform) => {
    set((state) => {
      if (!state.project) return {}
      const element = state.project.elements[elementId]
      if (!element) return {}
      return {
        project: {
          ...state.project,
          elements: {
            ...state.project.elements,
            [elementId]: {
              ...element,
              transform: { ...element.transform, ...transform },
            },
          },
        },
      }
    })
  },

  addKeyframe: (layerId, property, time, value) => {
    set((state) => {
      if (!state.project) return {}
      const layer = state.project.layers.find((l) => l.id === layerId)
      if (!layer) return {}

      let track = layer.tracks.find((t) => t.property === property)
      if (!track) {
        track = {
          id: nanoid(),
          property,
          keyframes: [],
        }
      }

      const keyframe: Keyframe = {
        id: nanoid(),
        time,
        value,
        easing: 'easeInOutCubic',
        property,
      }

      const newKeyframes = [...track.keyframes, keyframe].sort((a, b) => a.time - b.time)

      return {
        project: {
          ...state.project,
          layers: state.project.layers.map((l) =>
            l.id === layerId
              ? {
                  ...l,
                  tracks: layer.tracks.find((t) => t.property === property)
                    ? l.tracks.map((t) => (t.property === property ? { ...t, keyframes: newKeyframes } : t))
                    : [...l.tracks, { ...track!, keyframes: newKeyframes }],
                }
              : l
          ),
        },
      }
    })
  },

  removeKeyframe: (layerId, trackId, keyframeId) => {
    set((state) => {
      if (!state.project) return {}
      return {
        project: {
          ...state.project,
          layers: state.project.layers.map((l) =>
            l.id === layerId
              ? {
                  ...l,
                  tracks: l.tracks.map((t) =>
                    t.id === trackId
                      ? { ...t, keyframes: t.keyframes.filter((k) => k.id !== keyframeId) }
                      : t
                  ).filter((t) => t.keyframes.length > 0),
                }
              : l
          ),
        },
      }
    })
  },

  updateKeyframe: (layerId, trackId, keyframeId, updates) => {
    set((state) => {
      if (!state.project) return {}
      return {
        project: {
          ...state.project,
          layers: state.project.layers.map((l) =>
            l.id === layerId
              ? {
                  ...l,
                  tracks: l.tracks.map((t) =>
                    t.id === trackId
                      ? {
                          ...t,
                          keyframes: t.keyframes
                            .map((k) => (k.id === keyframeId ? { ...k, ...updates } : k))
                            .sort((a, b) => a.time - b.time),
                        }
                      : t
                  ),
                }
              : l
          ),
        },
      }
    })
  },

  createVersion: async (name, description) => {
    const { project } = get()
    if (!project) return

    const snapshot = {
      elements: JSON.parse(JSON.stringify(project.elements)),
      layers: JSON.parse(JSON.stringify(project.layers)),
      duration: project.duration,
    }

    await db.createVersion(project.id, name, description, snapshot)
    await get().loadProject(project.id)
  },

  restoreVersion: async (versionId) => {
    const { project } = get()
    if (!project) return

    await db.restoreVersion(project.id, versionId)
    await get().loadProject(project.id)
  },
}))
