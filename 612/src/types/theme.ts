export interface ThemeColors {
  primary: string
  secondary: string
  background: string
  surface: string
  text: string
  textSecondary: string
  border: string
  accent: string
  success: string
  warning: string
  error: string
}

export interface ThemeFonts {
  heading: string
  body: string
  mono: string
  headingSize: number
  bodySize: number
  headingWeight: number
  bodyWeight: number
  lineHeight: number
}

export interface ThemeCharts {
  colorPalette: string[]
  curveType: 'linear' | 'monotone' | 'natural'
  barRadius: number
  legendPosition: 'top' | 'bottom' | 'left' | 'right'
  showDataLabel: boolean
  lineWidth: number
  dotSize: number
}

export interface ThemeSpacing {
  cardGap: number
  cardPadding: number
  moduleGap: number
  gridColumns: number
  borderRadius: number
}

export interface ThemeConfig {
  id: string
  name: string
  createdAt: string
  updatedAt: string
  colors: ThemeColors
  fonts: ThemeFonts
  charts: ThemeCharts
  spacing: ThemeSpacing
}
