import { create } from 'zustand'
import type { CompareMode, DiffEditorLayout, DiffStats, DiffTreeNode, FileTreeNode } from '@/types'

interface DiffStore {
  mode: CompareMode
  language: string
  oldCode: string
  newCode: string
  editorLayout: DiffEditorLayout
  oldTree: FileTreeNode | null
  newTree: FileTreeNode | null
  diffTree: DiffTreeNode[] | null
  oldFiles: Record<string, string>
  newFiles: Record<string, string>
  selectedFile: string | null
  diffStats: DiffStats | null
  currentDiffIndex: number
  totalDiffs: number
  sidebarOpen: boolean
  isComparing: boolean

  setMode: (mode: CompareMode) => void
  setLanguage: (language: string) => void
  setOldCode: (code: string) => void
  setNewCode: (code: string) => void
  setEditorLayout: (layout: DiffEditorLayout) => void
  setOldTree: (tree: FileTreeNode | null) => void
  setNewTree: (tree: FileTreeNode | null) => void
  setDiffTree: (tree: DiffTreeNode[] | null) => void
  setOldFiles: (files: Record<string, string>) => void
  setNewFiles: (files: Record<string, string>) => void
  setSelectedFile: (file: string | null) => void
  setDiffStats: (stats: DiffStats | null) => void
  setCurrentDiffIndex: (index: number) => void
  setTotalDiffs: (total: number) => void
  toggleSidebar: () => void
  setIsComparing: (value: boolean) => void
  navigateDiff: (direction: 'prev' | 'next') => void
  reset: () => void
}

const initialState = {
  mode: 'code' as CompareMode,
  language: 'javascript',
  oldCode: '',
  newCode: '',
  editorLayout: 'side-by-side' as DiffEditorLayout,
  oldTree: null,
  newTree: null,
  diffTree: null,
  oldFiles: {},
  newFiles: {},
  selectedFile: null,
  diffStats: null,
  currentDiffIndex: 0,
  totalDiffs: 0,
  sidebarOpen: true,
  isComparing: false,
}

export const useDiffStore = create<DiffStore>((set, get) => ({
  ...initialState,

  setMode: (mode) => set({ mode }),
  setLanguage: (language) => set({ language }),
  setOldCode: (oldCode) => set({ oldCode }),
  setNewCode: (newCode) => set({ newCode }),
  setEditorLayout: (editorLayout) => set({ editorLayout }),
  setOldTree: (oldTree) => set({ oldTree }),
  setNewTree: (newTree) => set({ newTree }),
  setDiffTree: (diffTree) => set({ diffTree }),
  setOldFiles: (oldFiles) => set({ oldFiles }),
  setNewFiles: (newFiles) => set({ newFiles }),
  setSelectedFile: (selectedFile) => set({ selectedFile }),
  setDiffStats: (diffStats) => set({ diffStats }),
  setCurrentDiffIndex: (currentDiffIndex) => set({ currentDiffIndex }),
  setTotalDiffs: (totalDiffs) => set({ totalDiffs }),
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
  setIsComparing: (isComparing) => set({ isComparing }),

  navigateDiff: (direction) => {
    const { currentDiffIndex, totalDiffs } = get()
    if (direction === 'prev') {
      set({ currentDiffIndex: Math.max(0, currentDiffIndex - 1) })
    } else {
      set({ currentDiffIndex: Math.min(totalDiffs - 1, currentDiffIndex + 1) })
    }
  },

  reset: () => set(initialState),
}))
