import type { FormSchema, FormField, FormTab, FieldType } from '@/types/form'

export function generateId(): string {
  return 'field_' + Date.now().toString(36) + '_' + Math.random().toString(36).substr(2, 9)
}

export function generateTabId(): string {
  return 'tab_' + Date.now().toString(36) + '_' + Math.random().toString(36).substr(2, 9)
}

export function createDefaultSchema(): FormSchema {
  const tabId = generateTabId()
  return {
    id: generateId(),
    name: '新建表单',
    description: '',
    version: '1.0.0',
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    tabs: [
      {
        id: tabId,
        name: '基本信息',
        icon: 'file-text',
        fields: []
      }
    ]
  }
}

export function createField(type: FieldType, label: string): FormField {
  const id = generateId()
  return {
    id,
    type,
    name: `field_${id.slice(-6)}`,
    label,
    placeholder: `请输入${label}`,
    defaultValue: undefined,
    required: false,
    validation: [],
    props: {}
  }
}

export function cloneSchema(schema: FormSchema): FormSchema {
  return JSON.parse(JSON.stringify(schema))
}

export function exportSchema(schema: FormSchema): string {
  return JSON.stringify(schema, null, 2)
}

export function importSchema(json: string): FormSchema {
  return JSON.parse(json)
}

export function getFieldById(schema: FormSchema, fieldId: string): FormField | null {
  for (const tab of schema.tabs) {
    const field = tab.fields.find(f => f.id === fieldId)
    if (field) return field
  }
  return null
}

export function getTabById(schema: FormSchema, tabId: string): FormTab | null {
  return schema.tabs.find(t => t.id === tabId) || null
}
