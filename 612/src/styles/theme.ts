import type { ThemeConfig } from '@/types/theme'

export interface StyledTheme {
  colors: ThemeConfig['colors']
  fonts: ThemeConfig['fonts']
  charts: ThemeConfig['charts']
  spacing: ThemeConfig['spacing']
}

export function createStyledTheme(config: ThemeConfig): StyledTheme {
  return {
    colors: { ...config.colors },
    fonts: { ...config.fonts },
    charts: { ...config.charts, colorPalette: [...config.charts.colorPalette] },
    spacing: { ...config.spacing },
  }
}

export const defaultTheme: StyledTheme = createStyledTheme({
  id: 'default-dark',
  name: 'Default Dark',
  createdAt: new Date().toISOString(),
  updatedAt: new Date().toISOString(),
  colors: {
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
  },
  fonts: {
    heading: 'Outfit',
    body: 'DM Sans',
    mono: 'JetBrains Mono',
    headingSize: 24,
    bodySize: 14,
    headingWeight: 700,
    bodyWeight: 400,
    lineHeight: 1.6,
  },
  charts: {
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
    curveType: 'monotone',
    barRadius: 4,
    legendPosition: 'bottom',
    showDataLabel: false,
    lineWidth: 2,
    dotSize: 4,
  },
  spacing: {
    cardGap: 16,
    cardPadding: 20,
    moduleGap: 24,
    gridColumns: 12,
    borderRadius: 8,
  },
})
