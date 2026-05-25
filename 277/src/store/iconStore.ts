import { create } from 'zustand'

export interface IconVersion {
  id: string
  iconId: string
  version: number
  svgContent: string
  name: string
  tags: string[]
  createdAt: string
  createdBy: string
  note?: string
}

export interface IconAnalytics {
  iconId: string
  downloadCount: number
  viewCount: number
  exportCount: number
  lastDownloadedAt?: string
  lastViewedAt?: string
}

export interface Icon {
  id: string
  name: string
  svgContent: string
  categoryId: string | null
  tags: string[]
  originalColor: string
  filePath: string
  createdById: string
  createdAt: string
  updatedAt: string
  version: number
  versions: IconVersion[]
  analytics: IconAnalytics
}

export interface Category {
  id: string
  name: string
  parentId: string | null
  order: number
  createdAt: string
  _count?: { icons: number }
}

interface IconState {
  icons: Icon[]
  categories: Category[]
  selectedIcons: string[]
  searchQuery: string
  selectedCategory: string | null
  loading: boolean
  fetchIcons: () => Promise<void>
  fetchCategories: () => Promise<void>
  uploadIcon: (formData: FormData) => Promise<void>
  deleteIcon: (id: string) => Promise<void>
  updateIcon: (id: string, data: Partial<Icon>) => Promise<void>
  rollbackVersion: (iconId: string, versionId: string) => Promise<void>
  incrementView: (iconId: string) => void
  incrementDownload: (iconId: string) => void
  incrementExport: (iconId: string) => void
  toggleSelect: (id: string) => void
  clearSelection: () => void
  setSearchQuery: (query: string) => void
  setSelectedCategory: (categoryId: string | null) => void
}

export const useIconStore = create<IconState>((set, get) => ({
  icons: [],
  categories: [],
  selectedIcons: [],
  searchQuery: '',
  selectedCategory: null,
  loading: false,

  fetchIcons: async () => {
    set({ loading: true })
    try {
      const { searchQuery, selectedCategory } = get()
      const params = new URLSearchParams()
      if (searchQuery) params.append('search', searchQuery)
      if (selectedCategory) params.append('categoryId', selectedCategory)
      
      const response = await fetch(`/api/icons?${params}`)
      const data = await response.json()
      set({ icons: data.data || [], loading: false })
    } catch {
      set({ loading: false })
    }
  },

  fetchCategories: async () => {
    try {
      const response = await fetch('/api/categories')
      const data = await response.json()
      set({ categories: data.data || [] })
    } catch {
      // silent fail
    }
  },

  uploadIcon: async (formData: FormData) => {
    const response = await fetch('/api/icons', {
      method: 'POST',
      body: formData,
    })
    
    if (!response.ok) {
      const data = await response.json()
      throw new Error(data.error || '上传失败')
    }
    
    await get().fetchIcons()
  },

  deleteIcon: async (id: string) => {
    await fetch(`/api/icons/${id}`, { method: 'DELETE' })
    set((state) => ({
      icons: state.icons.filter((icon) => icon.id !== id),
      selectedIcons: state.selectedIcons.filter((selectedId) => selectedId !== id),
    }))
  },

  updateIcon: async (id: string, data: Partial<Icon>) => {
    const response = await fetch(`/api/icons/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    
    if (!response.ok) {
      const errorData = await response.json()
      throw new Error(errorData.error || '更新失败')
    }
    
    const updatedIcon = await response.json()
    set((state) => ({
      icons: state.icons.map((icon) =>
        icon.id === id ? { ...icon, ...updatedIcon.data } : icon
      ),
    }))
  },

  rollbackVersion: async (iconId: string, versionId: string) => {
    const response = await fetch(`/api/icons/${iconId}/rollback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ versionId }),
    })
    
    if (!response.ok) {
      const errorData = await response.json()
      throw new Error(errorData.error || '回滚失败')
    }
    
    await get().fetchIcons()
  },

  incrementView: (iconId: string) => {
    set((state) => ({
      icons: state.icons.map((icon) =>
        icon.id === iconId
          ? {
              ...icon,
              analytics: {
                ...icon.analytics,
                viewCount: icon.analytics.viewCount + 1,
                lastViewedAt: new Date().toISOString(),
              },
            }
          : icon
      ),
    }))
    fetch(`/api/icons/${iconId}/analytics/view`, { method: 'POST' })
  },

  incrementDownload: (iconId: string) => {
    set((state) => ({
      icons: state.icons.map((icon) =>
        icon.id === iconId
          ? {
              ...icon,
              analytics: {
                ...icon.analytics,
                downloadCount: icon.analytics.downloadCount + 1,
                lastDownloadedAt: new Date().toISOString(),
              },
            }
          : icon
      ),
    }))
    fetch(`/api/icons/${iconId}/analytics/download`, { method: 'POST' })
  },

  incrementExport: (iconId: string) => {
    set((state) => ({
      icons: state.icons.map((icon) =>
        icon.id === iconId
          ? {
              ...icon,
              analytics: {
                ...icon.analytics,
                exportCount: icon.analytics.exportCount + 1,
              },
            }
          : icon
      ),
    }))
    fetch(`/api/icons/${iconId}/analytics/export`, { method: 'POST' })
  },

  toggleSelect: (id: string) => {
    set((state) => ({
      selectedIcons: state.selectedIcons.includes(id)
        ? state.selectedIcons.filter((selectedId) => selectedId !== id)
        : [...state.selectedIcons, id],
    }))
  },

  clearSelection: () => {
    set({ selectedIcons: [] })
  },

  setSearchQuery: (query: string) => {
    set({ searchQuery: query })
  },

  setSelectedCategory: (categoryId: string | null) => {
    set({ selectedCategory: categoryId })
  },
}))
