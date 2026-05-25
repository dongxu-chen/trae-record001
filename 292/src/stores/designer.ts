import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'
import type { FormSchema, FormField, FormTab, HistoryRecord } from '@/types/form'
import { createDefaultSchema, cloneSchema, generateTabId, createField } from '@/utils/schema'
import { useVersionStore } from './versionControl'

const MAX_HISTORY = 50

export const useDesignerStore = defineStore('designer', () => {
  const formSchema = ref<FormSchema>(createDefaultSchema())
  const selectedFieldId = ref<string | null>(null)
  const selectedTabId = ref<string>(formSchema.value.tabs[0].id)
  const history = ref<HistoryRecord[]>([])
  const historyIndex = ref<number>(-1)
  const tempPreviewSchema = ref<FormSchema | null>(null)

  const versionStore = useVersionStore()

  watch(formSchema, (newSchema) => {
    if (versionStore.versions.length === 0) {
      versionStore.initVersion(newSchema)
    } else {
      versionStore.updateDraft(newSchema)
    }
  }, { deep: true })

  const currentTab = computed(() => {
    return formSchema.value.tabs.find(t => t.id === selectedTabId.value) || null
  })

  const selectedField = computed(() => {
    if (!selectedFieldId.value) return null
    for (const tab of formSchema.value.tabs) {
      const field = tab.fields.find(f => f.id === selectedFieldId.value)
      if (field) return field
    }
    return null
  })

  const canUndo = computed(() => historyIndex.value > 0)
  const canRedo = computed(() => historyIndex.value < history.value.length - 1)

  function saveToHistory(type: HistoryRecord['type']) {
    const snapshot = cloneSchema(formSchema.value)
    const record: HistoryRecord = {
      type,
      snapshot,
      timestamp: Date.now()
    }
    
    history.value = history.value.slice(0, historyIndex.value + 1)
    history.value.push(record)
    
    if (history.value.length > MAX_HISTORY) {
      history.value.shift()
    } else {
      historyIndex.value++
    }
  }

  function undo() {
    if (!canUndo.value) return
    historyIndex.value--
    formSchema.value = cloneSchema(history.value[historyIndex.value].snapshot)
  }

  function redo() {
    if (!canRedo.value) return
    historyIndex.value++
    formSchema.value = cloneSchema(history.value[historyIndex.value].snapshot)
  }

  function selectField(fieldId: string | null) {
    selectedFieldId.value = fieldId
  }

  function selectTab(tabId: string) {
    selectedTabId.value = tabId
    selectedFieldId.value = null
  }

  function addField(type: string, label: string) {
    const tab = currentTab.value
    if (!tab) return
    
    const field = createField(type as any, label)
    tab.fields.push(field)
    selectedFieldId.value = field.id
    formSchema.value.updatedAt = new Date().toISOString()
    saveToHistory('add')
  }

  function updateField(fieldId: string, updates: Partial<FormField>) {
    for (const tab of formSchema.value.tabs) {
      const index = tab.fields.findIndex(f => f.id === fieldId)
      if (index !== -1) {
        tab.fields[index] = { ...tab.fields[index], ...updates }
        formSchema.value.updatedAt = new Date().toISOString()
        saveToHistory('update')
        return
      }
    }
  }

  function deleteField(fieldId: string) {
    for (const tab of formSchema.value.tabs) {
      const index = tab.fields.findIndex(f => f.id === fieldId)
      if (index !== -1) {
        tab.fields.splice(index, 1)
        if (selectedFieldId.value === fieldId) {
          selectedFieldId.value = null
        }
        formSchema.value.updatedAt = new Date().toISOString()
        saveToHistory('delete')
        return
      }
    }
  }

  function addTab(name: string) {
    const newTab: FormTab = {
      id: generateTabId(),
      name,
      icon: 'file-text',
      fields: []
    }
    formSchema.value.tabs.push(newTab)
    selectedTabId.value = newTab.id
    selectedFieldId.value = null
    formSchema.value.updatedAt = new Date().toISOString()
    saveToHistory('tab')
  }

  function deleteTab(tabId: string) {
    if (formSchema.value.tabs.length <= 1) return
    
    const index = formSchema.value.tabs.findIndex(t => t.id === tabId)
    if (index !== -1) {
      formSchema.value.tabs.splice(index, 1)
      if (selectedTabId.value === tabId) {
        selectedTabId.value = formSchema.value.tabs[Math.max(0, index - 1)].id
      }
      selectedFieldId.value = null
      formSchema.value.updatedAt = new Date().toISOString()
      saveToHistory('tab')
    }
  }

  function updateTab(tabId: string, updates: Partial<FormTab>) {
    const tab = formSchema.value.tabs.find(t => t.id === tabId)
    if (tab) {
      Object.assign(tab, updates)
      formSchema.value.updatedAt = new Date().toISOString()
      saveToHistory('tab')
    }
  }

  function clearAll() {
    const defaultSchema = createDefaultSchema()
    formSchema.value = defaultSchema
    selectedTabId.value = defaultSchema.tabs[0].id
    selectedFieldId.value = null
    history.value = []
    historyIndex.value = -1
  }

  function updateFormInfo(name: string, description: string) {
    formSchema.value.name = name
    formSchema.value.description = description
    formSchema.value.updatedAt = new Date().toISOString()
    saveToHistory('update')
  }

  function moveField(fromTabId: string, toTabId: string, fromIndex: number, toIndex: number) {
    const fromTab = formSchema.value.tabs.find(t => t.id === fromTabId)
    const toTab = formSchema.value.tabs.find(t => t.id === toTabId)
    
    if (!fromTab || !toTab) return
    
    const [field] = fromTab.fields.splice(fromIndex, 1)
    toTab.fields.splice(toIndex, 0, field)
    formSchema.value.updatedAt = new Date().toISOString()
    saveToHistory('move')
  }

  function loadSchema(schema: FormSchema) {
    formSchema.value = cloneSchema(schema)
    selectedTabId.value = formSchema.value.tabs[0]?.id || ''
    selectedFieldId.value = null
    history.value = []
    historyIndex.value = -1
  }

  return {
    formSchema,
    selectedFieldId,
    selectedTabId,
    currentTab,
    selectedField,
    canUndo,
    canRedo,
    history,
    historyIndex,
    tempPreviewSchema,
    selectField,
    selectTab,
    addField,
    updateField,
    deleteField,
    addTab,
    deleteTab,
    updateTab,
    undo,
    redo,
    clearAll,
    updateFormInfo,
    moveField,
    saveToHistory,
    loadSchema
  }
})
