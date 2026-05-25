export type FieldType =
  | 'input'
  | 'textarea'
  | 'number'
  | 'select'
  | 'radio'
  | 'checkbox'
  | 'switch'
  | 'date'
  | 'time'
  | 'rate'
  | 'slider'
  | 'divider'
  | 'text'

export interface ValidationRule {
  type: 'required' | 'min' | 'max' | 'pattern' | 'email' | 'custom'
  value?: any
  message: string
}

export interface FormulaConfig {
  expression: string
  dependencies: string[]
}

export interface ConditionalExpression {
  field: string
  operator: '==' | '!=' | '>' | '<' | '>=' | '<=' | 'contains'
  value: any
}

export interface ConditionalConfig {
  show?: ConditionalExpression
  disable?: ConditionalExpression
}

export interface FormField {
  id: string
  type: FieldType
  name: string
  label: string
  placeholder?: string
  defaultValue?: any
  required?: boolean
  validation?: ValidationRule[]
  formula?: FormulaConfig
  conditional?: ConditionalConfig
  props?: Record<string, any>
}

export interface FormTab {
  id: string
  name: string
  icon?: string
  fields: FormField[]
}

export interface FormSchema {
  id: string
  name: string
  description: string
  tabs: FormTab[]
  version: string
  createdAt: string
  updatedAt: string
}

export interface HistoryRecord {
  type: 'add' | 'update' | 'delete' | 'move' | 'tab'
  snapshot: FormSchema
  timestamp: number
}

export interface ComponentConfig {
  type: FieldType
  label: string
  icon: string
  category: 'basic' | 'advanced' | 'layout'
  defaultProps: Partial<FormField>
}

export interface DesignerState {
  formSchema: FormSchema
  selectedFieldId: string | null
  selectedTabId: string
  history: HistoryRecord[]
  historyIndex: number
}
