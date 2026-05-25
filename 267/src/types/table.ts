import type { ColumnDef } from '@tanstack/react-table'

export interface DataRow {
  id: number
  name: string
  email: string
  department: string
  position: string
  salary: number
  hireDate: string
  status: 'active' | 'inactive' | 'pending'
  performance: number
  projects: number
  region: string
  team: string
}

export type RendererType = 'text' | 'number' | 'date' | 'status' | 'progress' | 'action'

export interface ValidationRule {
  required?: boolean
  min?: number
  max?: number
  minLength?: number
  maxLength?: number
  pattern?: RegExp
  custom?: (value: unknown) => boolean | string
}

export interface ColumnMeta {
  renderer?: RendererType
  editable?: boolean
  mergeKey?: string
  width?: number
  minWidth?: number
  maxWidth?: number
  validation?: ValidationRule
}

export interface TableColumnDef<TData> extends ColumnDef<TData> {
  meta?: ColumnMeta
}

export interface CellPosition {
  rowIndex: number
  columnId: string
}

export interface CellSelection {
  start: CellPosition
  end: CellPosition
}

export interface EditState {
  rowIndex: number
  columnId: string
  value: unknown
  originalValue: unknown
  error?: string
}

export interface ExportOptions {
  format?: 'xlsx' | 'csv'
  filename?: string
  includeHeaders?: boolean
  selectedOnly?: boolean
}

export interface MergedCell {
  rowSpan: number
  colSpan: number
  startRow: number
  startCol: string
}

export interface ClipboardCell {
  value: string
  rowSpan: number
  colSpan: number
  isEmpty: boolean
}

export interface ValidationResult {
  isValid: boolean
  error?: string
}

export interface PivotConfig {
  rows: string[]
  columns: string[]
  values: PivotValue[]
  filters: Record<string, string[]>
}

export interface PivotValue {
  field: string
  aggregator: 'sum' | 'avg' | 'count' | 'min' | 'max'
  label?: string
}

export interface PivotData {
  rowHeaders: string[]
  colHeaders: string[]
  values: (number | string)[][]
  grandTotalRow: (number | string)[]
  grandTotalCol: (number | string)[]
}

export interface ChartConfig {
  type: 'bar' | 'line' | 'pie' | 'area' | 'scatter'
  title: string
  xField: string
  yField: string
  seriesField?: string
}

export interface ChartRecommendation {
  type: ChartConfig['type']
  confidence: number
  reason: string
  config: ChartConfig
}

export interface AIAnalysisResult {
  query: string
  result: string
  data?: Record<string, unknown>
  chartType?: ChartConfig['type']
  confidence: number
}

export interface CellRange {
  startRow: number
  endRow: number
  startCol: string
  endCol: string
}
