import { create } from 'zustand'
import type { ThemeConfig } from '@/types/theme'

const defaultColors = {
  primary: '#6366f1',
  secondary: '#8b5cf6',
  background: '#0f0f23',
  surface: '#1a1a2e',
  text: '#e2e8f0',
  textSecondary: '#94a3b8',
  border: '#2d2d44',
  accent: '#f472b6',
  success: '#22c55e',
  warning: '#f59e0b',
  error: '#ef4444',
}

const defaultFonts = {
  heading: 'Outfit',
  body: 'DM Sans',
  mono: 'JetBrains Mono',
  headingSize: 24,
  bodySize: 14,
  headingWeight: 700,
  bodyWeight: 400,
  lineHeight: 1.6,
}

const defaultCharts = {
  colorPalette: [
    '#6366f1',
    '#8b5cf6',
    '#f472b6',
    '#22c55e',
    '#f59e0b',
    '#06b6d4',
    '#ef4444',
    '#a78bfa',
  ],
  curveType: 'monotone' as const,
  barRadius: 4,
  legendPosition: 'bottom' as const,
  showDataLabel: false,
  lineWidth: 2,
  dotSize: 4,
}

const defaultSpacing = {
  cardGap: 16,
  cardPadding: 20,
  moduleGap: 24,
  gridColumns: 12,
  borderRadius: 8,
}

function createDefaultTheme(name: string): ThemeConfig {
  const now = new Date().toISOString()
  return {
    id: crypto.randomUUID(),
    name,
    createdAt: now,
    updatedAt: now,
    colors: { ...defaultColors },
    fonts: { ...defaultFonts },
    charts: { ...defaultCharts, colorPalette: [...defaultCharts.colorPalette] },
    spacing: { ...defaultSpacing },
  }
}

interface ThemeState {
  themes: ThemeConfig[]
  currentThemeId: string | null
  loading: boolean
  currentTheme: () => ThemeConfig | undefined
  fetchThemes: () => Promise<void>
  createTheme: (name: string) => Promise<void>
  updateTheme: (partial: Partial<ThemeConfig>) => Promise<void>
  deleteTheme: (id: string) => Promise<void>
  switchTheme: (id: string) => void
  duplicateTheme: (id: string) => Promise<void>
  importTheme: (theme: ThemeConfig) => Promise<void>
  exportTheme: (id: string) => ThemeConfig | undefined
}

export const useThemeStore = create<ThemeState>((set, get) => ({
  themes: [],
  currentThemeId: null,
  loading: false,

  currentTheme: () => {
    const { themes, currentThemeId } = get()
    return themes.find((t) => t.id === currentThemeId)
  },

  fetchThemes: async () => {
    set({ loading: true })
    try {
      const res = await fetch('/api/themes')
      const data: ThemeConfig[] = await res.json()
      set({
        themes: data,
        currentThemeId: data.length > 0 ? data[0].id : null,
        loading: false,
      })
    } catch {
      set({ loading: false })
    }
  },

  createTheme: async (name: string) => {
    const theme = createDefaultTheme(name)
    set({ loading: true })
    try {
      const res = await fetch('/api/themes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(theme),
      })
      const created: ThemeConfig = await res.json()
      set((state) => ({
        themes: [...state.themes, created],
        currentThemeId: created.id,
        loading: false,
      }))
    } catch {
      set({ loading: false })
    }
  },

  updateTheme: async (partial: Partial<ThemeConfig>) => {
    const { currentThemeId, themes } = get()
    if (!currentThemeId) return
    const existing = themes.find((t) => t.id === currentThemeId)
    if (!existing) return
    const merged: ThemeConfig = {
      ...existing,
      ...partial,
      id: existing.id,
      createdAt: existing.createdAt,
      updatedAt: new Date().toISOString(),
    }
    set((state) => ({
      themes: state.themes.map((t) => (t.id === currentThemeId ? merged : t)),
    }))
    try {
      await fetch(`/api/themes/${currentThemeId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(merged),
      })
    } catch {
      set((state) => ({
        themes: state.themes.map((t) => (t.id === currentThemeId ? existing : t)),
      }))
    }
  },

  deleteTheme: async (id: string) => {
    const { themes } = get()
    const previous = [...themes]
    set((state) => ({
      themes: state.themes.filter((t) => t.id !== id),
      currentThemeId: state.currentThemeId === id
        ? state.themes.find((t) => t.id !== id)?.id ?? null
        : state.currentThemeId,
    }))
    try {
      await fetch(`/api/themes/${id}`, { method: 'DELETE' })
    } catch {
      set({ themes: previous })
    }
  },

  switchTheme: (id: string) => {
    set({ currentThemeId: id })
  },

  duplicateTheme: async (id: string) => {
    const { themes } = get()
    const source = themes.find((t) => t.id === id)
    if (!source) return
    const now = new Date().toISOString()
    const copy: ThemeConfig = {
      ...source,
      ...JSON.parse(JSON.stringify(source)),
      id: crypto.randomUUID(),
      name: `${source.name} (Copy)`,
      createdAt: now,
      updatedAt: now,
    }
    set({ loading: true })
    try {
      const res = await fetch('/api/themes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(copy),
      })
      const created: ThemeConfig = await res.json()
      set((state) => ({
        themes: [...state.themes, created],
        currentThemeId: created.id,
        loading: false,
      }))
    } catch {
      set({ loading: false })
    }
  },

  importTheme: async (theme: ThemeConfig) => {
    set({ loading: true })
    try {
      const res = await fetch('/api/themes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(theme),
      })
      const created: ThemeConfig = await res.json()
      set((state) => ({
        themes: [...state.themes, created],
        currentThemeId: created.id,
        loading: false,
      }))
    } catch {
      set({ loading: false })
    }
  },

  exportTheme: (id: string) => {
    const { themes } = get()
    return themes.find((t) => t.id === id)
  },
}))
