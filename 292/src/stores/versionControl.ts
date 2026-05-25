import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { FormVersion, VersionStatus } from '@/types/advanced'
import type { FormSchema } from '@/types/form'
import { cloneSchema } from '@/utils/schema'

function generateVersionId(): string {
  return 'v_' + Date.now().toString(36) + '_' + Math.random().toString(36).substr(2, 6)
}

function incrementVersion(version: string): string {
  const parts = version.split('.').map(Number)
  if (parts.length === 3) {
    parts[2]++
    return parts.join('.')
  }
  return '1.0.0'
}

export const useVersionStore = defineStore('version', () => {
  const versions = ref<FormVersion[]>([])
  const currentDraftSchema = ref<FormSchema | null>(null)
  const publishedVersionId = ref<string | null>(null)

  const publishedVersion = computed(() => {
    return versions.value.find(v => v.status === 'published') || null
  })

  const draftVersion = computed(() => {
    return versions.value.find(v => v.status === 'draft') || null
  })

  const versionHistory = computed(() => {
    return [...versions.value].sort((a, b) => 
      new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
    )
  })

  const hasPublished = computed(() => publishedVersion.value !== null)

  function initVersion(schema: FormSchema) {
    if (versions.value.length === 0) {
      const initialVersion: FormVersion = {
        id: generateVersionId(),
        version: '1.0.0',
        name: '初始版本',
        description: '创建表单',
        schema: cloneSchema(schema),
        status: 'draft',
        createdAt: new Date().toISOString(),
        createdBy: '当前用户',
        changelog: '创建表单',
        isCurrent: true
      }
      versions.value.push(initialVersion)
      currentDraftSchema.value = cloneSchema(schema)
    }
  }

  function updateDraft(schema: FormSchema) {
    currentDraftSchema.value = cloneSchema(schema)
    
    const draft = versions.value.find(v => v.status === 'draft')
    if (draft) {
      draft.schema = cloneSchema(schema)
      draft.updatedAt = new Date().toISOString()
    }
  }

  function publishVersion(changelog: string): FormVersion {
    const currentDraft = versions.value.find(v => v.status === 'draft')
    const currentPublished = versions.value.find(v => v.status === 'published')

    const newVersion: FormVersion = {
      id: generateVersionId(),
      version: currentPublished 
        ? incrementVersion(currentPublished.version)
        : '1.0.0',
      name: `版本 ${currentPublished ? incrementVersion(currentPublished.version) : '1.0.0'}`,
      description: changelog,
      schema: cloneSchema(currentDraftSchema.value!),
      status: 'published',
      createdAt: new Date().toISOString(),
      createdBy: '当前用户',
      changelog,
      isCurrent: true
    }

    if (currentPublished) {
      currentPublished.status = 'archived'
      currentPublished.isCurrent = false
    }

    if (currentDraft) {
      currentDraft.status = 'archived'
      currentDraft.isCurrent = false
    }

    versions.value.push(newVersion)
    publishedVersionId.value = newVersion.id

    const newDraft: FormVersion = {
      id: generateVersionId(),
      version: incrementVersion(newVersion.version),
      name: '草稿',
      description: '编辑中...',
      schema: cloneSchema(newVersion.schema),
      status: 'draft',
      createdAt: new Date().toISOString(),
      createdBy: '当前用户',
      changelog: '草稿',
      isCurrent: true
    }
    versions.value.push(newDraft)
    currentDraftSchema.value = cloneSchema(newVersion.schema)

    return newVersion
  }

  function rollbackToVersion(versionId: string, reason: string): boolean {
    const targetVersion = versions.value.find(v => v.id === versionId)
    if (!targetVersion) return false

    const draft = versions.value.find(v => v.status === 'draft')
    if (draft) {
      draft.schema = cloneSchema(targetVersion.schema)
      draft.description = `回滚到 ${targetVersion.version}`
      draft.changelog = reason
    }

    currentDraftSchema.value = cloneSchema(targetVersion.schema)
    return true
  }

  function getVersionById(versionId: string): FormVersion | undefined {
    return versions.value.find(v => v.id === versionId)
  }

  function compareVersions(versionId1: string, versionId2: string): {
    added: string[]
    removed: string[]
    modified: string[]
  } {
    const v1 = getVersionById(versionId1)
    const v2 = getVersionById(versionId2)

    if (!v1 || !v2) {
      return { added: [], removed: [], modified: [] }
    }

    const fields1 = new Map<string, any>()
    const fields2 = new Map<string, any>()

    v1.schema.tabs.forEach(tab => {
      tab.fields.forEach(f => fields1.set(f.id, f))
    })
    v2.schema.tabs.forEach(tab => {
      tab.fields.forEach(f => fields2.set(f.id, f))
    })

    const added: string[] = []
    const removed: string[] = []
    const modified: string[] = []

    fields1.forEach((field, id) => {
      if (!fields2.has(id)) {
        removed.push(field.label)
      }
    })

    fields2.forEach((field, id) => {
      if (!fields1.has(id)) {
        added.push(field.label)
      } else {
        const f1 = fields1.get(id)
        if (JSON.stringify(f1) !== JSON.stringify(field)) {
          modified.push(field.label)
        }
      }
    })

    return { added, removed, modified }
  }

  function deleteVersion(versionId: string): boolean {
    const index = versions.value.findIndex(v => v.id === versionId)
    if (index === -1) return false
    
    const version = versions.value[index]
    if (version.status === 'published') return false
    
    versions.value.splice(index, 1)
    return true
  }

  function clearAll() {
    versions.value = []
    currentDraftSchema.value = null
    publishedVersionId.value = null
  }

  function getDraftSchema(): FormSchema | null {
    return currentDraftSchema.value
  }

  function getPublishedSchema(): FormSchema | null {
    return publishedVersion.value?.schema || null
  }

  return {
    versions,
    currentDraftSchema,
    publishedVersionId,
    publishedVersion,
    draftVersion,
    versionHistory,
    hasPublished,
    initVersion,
    updateDraft,
    publishVersion,
    rollbackToVersion,
    getVersionById,
    compareVersions,
    deleteVersion,
    clearAll,
    getDraftSchema,
    getPublishedSchema
  }
})
