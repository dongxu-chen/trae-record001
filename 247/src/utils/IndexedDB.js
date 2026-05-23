class IndexedDBManager {
  constructor(dbName = 'FormBuilderDB', version = 1) {
    this.dbName = dbName
    this.version = version
    this.db = null
  }

  async init() {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(this.dbName, this.version)

      request.onerror = () => reject(request.error)
      request.onsuccess = () => {
        this.db = request.result
        resolve(this.db)
      }

      request.onupgradeneeded = (event) => {
        const db = event.target.result

        if (!db.objectStoreNames.contains('formData')) {
          const formDataStore = db.createObjectStore('formData', { keyPath: 'id' })
          formDataStore.createIndex('formId', 'formId', { unique: false })
          formDataStore.createIndex('version', 'version', { unique: false })
          formDataStore.createIndex('updatedAt', 'updatedAt', { unique: false })
        }

        if (!db.objectStoreNames.contains('formVersions')) {
          const versionStore = db.createObjectStore('formVersions', { keyPath: 'id' })
          versionStore.createIndex('formId', 'formId', { unique: false })
          versionStore.createIndex('version', 'version', { unique: false })
          versionStore.createIndex('createdAt', 'createdAt', { unique: false })
        }

        if (!db.objectStoreNames.contains('formStatistics')) {
          const statsStore = db.createObjectStore('formStatistics', { keyPath: 'id' })
          statsStore.createIndex('formId', 'formId', { unique: false })
          statsStore.createIndex('fieldName', 'fieldName', { unique: false })
        }

        if (!db.objectStoreNames.contains('offlineSubmissions')) {
          const offlineStore = db.createObjectStore('offlineSubmissions', { keyPath: 'id', autoIncrement: true })
          offlineStore.createIndex('formId', 'formId', { unique: false })
          offlineStore.createIndex('status', 'status', { unique: false })
          offlineStore.createIndex('createdAt', 'createdAt', { unique: false })
        }
      }
    })
  }

  async getStore(storeName, mode = 'readonly') {
    if (!this.db) await this.init()
    const transaction = this.db.transaction(storeName, mode)
    return transaction.objectStore(storeName)
  }

  async add(storeName, data) {
    return new Promise(async (resolve, reject) => {
      const store = await this.getStore(storeName, 'readwrite')
      const request = store.add(data)
      request.onsuccess = () => resolve(request.result)
      request.onerror = () => reject(request.error)
    })
  }

  async put(storeName, data) {
    return new Promise(async (resolve, reject) => {
      const store = await this.getStore(storeName, 'readwrite')
      const request = store.put(data)
      request.onsuccess = () => resolve(request.result)
      request.onerror = () => reject(request.error)
    })
  }

  async get(storeName, key) {
    return new Promise(async (resolve, reject) => {
      const store = await this.getStore(storeName, 'readonly')
      const request = store.get(key)
      request.onsuccess = () => resolve(request.result)
      request.onerror = () => reject(request.error)
    })
  }

  async getAll(storeName) {
    return new Promise(async (resolve, reject) => {
      const store = await this.getStore(storeName, 'readonly')
      const request = store.getAll()
      request.onsuccess = () => resolve(request.result)
      request.onerror = () => reject(request.error)
    })
  }

  async getByIndex(storeName, indexName, value) {
    return new Promise(async (resolve, reject) => {
      const store = await this.getStore(storeName, 'readonly')
      const index = store.index(indexName)
      const request = index.getAll(value)
      request.onsuccess = () => resolve(request.result)
      request.onerror = () => reject(request.error)
    })
  }

  async delete(storeName, key) {
    return new Promise(async (resolve, reject) => {
      const store = await this.getStore(storeName, 'readwrite')
      const request = store.delete(key)
      request.onsuccess = () => resolve()
      request.onerror = () => reject(request.error)
    })
  }

  async clear(storeName) {
    return new Promise(async (resolve, reject) => {
      const store = await this.getStore(storeName, 'readwrite')
      const request = store.clear()
      request.onsuccess = () => resolve()
      request.onerror = () => reject(request.error)
    })
  }

  async count(storeName) {
    return new Promise(async (resolve, reject) => {
      const store = await this.getStore(storeName, 'readonly')
      const request = store.count()
      request.onsuccess = () => resolve(request.result)
      request.onerror = () => reject(request.error)
    })
  }
}

const dbManager = new IndexedDBManager()

export const FormDataStorage = {
  async saveFormData(formId, version, data) {
    const id = `${formId}_${version}`
    const record = {
      id,
      formId,
      version,
      data,
      updatedAt: new Date().toISOString()
    }
    await dbManager.put('formData', record)
    return record
  },

  async getFormData(formId, version) {
    const id = `${formId}_${version}`
    return await dbManager.get('formData', id)
  },

  async getLatestFormData(formId) {
    const allData = await dbManager.getByIndex('formData', 'formId', formId)
    if (allData.length === 0) return null
    return allData.sort((a, b) => new Date(b.updatedAt) - new Date(a.updatedAt))[0]
  }
}

export const VersionManager = {
  async createVersion(formId, version, schema, description = '') {
    const id = `${formId}_v${version}`
    const record = {
      id,
      formId,
      version,
      schema,
      description,
      createdAt: new Date().toISOString(),
      fieldMapping: {}
    }
    await dbManager.add('formVersions', record)
    return record
  },

  async getVersions(formId) {
    const versions = await dbManager.getByIndex('formVersions', 'formId', formId)
    return versions.sort((a, b) => b.version - a.version)
  },

  async getLatestVersion(formId) {
    const versions = await this.getVersions(formId)
    return versions.length > 0 ? versions[0] : null
  },

  async setFieldMapping(formId, version, mapping) {
    const id = `${formId}_v${version}`
    const versionRecord = await dbManager.get('formVersions', id)
    if (versionRecord) {
      versionRecord.fieldMapping = mapping
      await dbManager.put('formVersions', versionRecord)
    }
  },

  async migrateData(oldData, oldVersion, newSchema) {
    const newData = {}
    
    for (const [oldField, value] of Object.entries(oldData)) {
      const newField = newSchema.fieldMapping?.[oldField] || oldField
      if (newSchema.properties?.[newField]) {
        newData[newField] = value
      }
    }

    for (const [field, config] of Object.entries(newSchema.properties || {})) {
      if (newData[field] === undefined && config.default !== undefined) {
        newData[field] = config.default
      }
    }

    return newData
  }
}

export const StatisticsCollector = {
  stats: {},

  init(formId, fields) {
    this.stats[formId] = {}
    fields.forEach(field => {
      this.stats[formId][field] = {
        fillCount: 0,
        changeCount: 0,
        lastModified: null
      }
    })
  },

  trackChange(formId, fieldName, oldValue, newValue) {
    if (!this.stats[formId]) {
      this.stats[formId] = {}
    }
    if (!this.stats[formId][fieldName]) {
      this.stats[formId][fieldName] = { fillCount: 0, changeCount: 0, lastModified: null }
    }

    const stat = this.stats[formId][fieldName]

    if (oldValue === '' || oldValue === null || oldValue === undefined) {
      if (newValue !== '' && newValue !== null && newValue !== undefined) {
        stat.fillCount++
      }
    }

    stat.changeCount++
    stat.lastModified = new Date().toISOString()

    this.saveToDB(formId, fieldName, stat)
  },

  async saveToDB(formId, fieldName, stat) {
    const id = `${formId}_${fieldName}`
    const record = {
      id,
      formId,
      fieldName,
      ...stat
    }
    await dbManager.put('formStatistics', record)
  },

  async getStatistics(formId) {
    return await dbManager.getByIndex('formStatistics', 'formId', formId)
  },

  async calculateFillRate(formId, totalSubmissions = 1) {
    const stats = await this.getStatistics(formId)
    return stats.map(stat => ({
      fieldName: stat.fieldName,
      fillRate: totalSubmissions > 0 ? (stat.fillCount / totalSubmissions * 100).toFixed(1) + '%' : '0%',
      changeCount: stat.changeCount,
      lastModified: stat.lastModified
    }))
  },

  getOptimizationSuggestions(stats) {
    const suggestions = []
    const sortedByChanges = [...stats].sort((a, b) => b.changeCount - a.changeCount)
    
    if (sortedByChanges.length > 0 && sortedByChanges[0].changeCount > 10) {
      suggestions.push({
        type: 'warning',
        field: sortedByChanges[0].fieldName,
        message: `字段 "${sortedByChanges[0].fieldName}" 修改次数较多，建议优化提示文案`
      })
    }

    const lowFillRate = stats.filter(s => parseFloat(s.fillRate) < 30)
    lowFillRate.forEach(s => {
      suggestions.push({
        type: 'info',
        field: s.fieldName,
        message: `字段 "${s.fieldName}" 填写率较低 (${s.fillRate})，建议设为非必填或优化说明`
      })
    })

    return suggestions
  }
}

export const OfflineSubmission = {
  async saveSubmission(formId, data) {
    const record = {
      formId,
      data,
      status: 'pending',
      createdAt: new Date().toISOString(),
      syncedAt: null
    }
    return await dbManager.add('offlineSubmissions', record)
  },

  async getPendingSubmissions(formId) {
    const all = await dbManager.getByIndex('offlineSubmissions', 'formId', formId)
    return all.filter(s => s.status === 'pending')
  },

  async markAsSynced(id) {
    const submission = await dbManager.get('offlineSubmissions', id)
    if (submission) {
      submission.status = 'synced'
      submission.syncedAt = new Date().toISOString()
      await dbManager.put('offlineSubmissions', submission)
    }
  },

  async syncPending(formId, submitFn) {
    const pending = await this.getPendingSubmissions(formId)
    const results = []

    for (const submission of pending) {
      try {
        await submitFn(submission.data)
        await this.markAsSynced(submission.id)
        results.push({ id: submission.id, success: true })
      } catch (error) {
        results.push({ id: submission.id, success: false, error: error.message })
      }
    }

    return results
  }
}

export const setupAutoSave = (formId, version, formDataRef, debounceMs = 1000) => {
  let timeoutId = null

  const save = async () => {
    await FormDataStorage.saveFormData(formId, version, { ...formDataRef.value })
  }

  const scheduleSave = () => {
    if (timeoutId) clearTimeout(timeoutId)
    timeoutId = setTimeout(save, debounceMs)
  }

  const cancel = () => {
    if (timeoutId) clearTimeout(timeoutId)
  }

  return { scheduleSave, cancel, save }
}

export default dbManager
