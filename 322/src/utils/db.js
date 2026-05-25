import { openDB } from 'idb'

const DB_NAME = 'chart-annotation-db'
const DB_VERSION = 1

const STORES = {
  IMAGES: 'images',
  ANNOTATIONS: 'annotations',
  HISTORY: 'history',
  PROJECTS: 'projects'
}

let dbPromise = null

const initDB = async () => {
  if (dbPromise) return dbPromise

  dbPromise = openDB(DB_NAME, DB_VERSION, {
    upgrade(db) {
      if (!db.objectStoreNames.contains(STORES.PROJECTS)) {
        const projectStore = db.createObjectStore(STORES.PROJECTS, {
          keyPath: 'id',
          autoIncrement: false
        })
        projectStore.createIndex('name', 'name', { unique: false })
        projectStore.createIndex('createdAt', 'createdAt', { unique: false })
      }

      if (!db.objectStoreNames.contains(STORES.IMAGES)) {
        const imageStore = db.createObjectStore(STORES.IMAGES, {
          keyPath: 'id',
          autoIncrement: false
        })
        imageStore.createIndex('projectId', 'projectId', { unique: false })
        imageStore.createIndex('name', 'name', { unique: false })
      }

      if (!db.objectStoreNames.contains(STORES.ANNOTATIONS)) {
        const annotationStore = db.createObjectStore(STORES.ANNOTATIONS, {
          keyPath: 'id',
          autoIncrement: false
        })
        annotationStore.createIndex('imageId', 'imageId', { unique: false })
        annotationStore.createIndex('projectId', 'projectId', { unique: false })
        annotationStore.createIndex('category', 'category', { unique: false })
        annotationStore.createIndex('type', 'type', { unique: false })
      }

      if (!db.objectStoreNames.contains(STORES.HISTORY)) {
        const historyStore = db.createObjectStore(STORES.HISTORY, {
          keyPath: 'id',
          autoIncrement: false
        })
        historyStore.createIndex('imageId', 'imageId', { unique: false })
        historyStore.createIndex('timestamp', 'timestamp', { unique: false })
      }
    }
  })

  return dbPromise
}

export const db = {
  async init() {
    await initDB()
  },

  async createProject(project) {
    const db = await initDB()
    const id = project.id || `proj_${Date.now()}`
    const data = {
      id,
      name: project.name || '未命名项目',
      description: project.description || '',
      createdAt: Date.now(),
      updatedAt: Date.now()
    }
    await db.put(STORES.PROJECTS, data)
    return data
  },

  async getProjects() {
    const db = await initDB()
    const projects = await db.getAll(STORES.PROJECTS)
    return projects.sort((a, b) => b.updatedAt - a.updatedAt)
  },

  async getProject(projectId) {
    const db = await initDB()
    return await db.get(STORES.PROJECTS, projectId)
  },

  async updateProject(projectId, updates) {
    const db = await initDB()
    const project = await db.get(STORES.PROJECTS, projectId)
    if (project) {
      const updated = { ...project, ...updates, updatedAt: Date.now() }
      await db.put(STORES.PROJECTS, updated)
      return updated
    }
    return null
  },

  async deleteProject(projectId) {
    const db = await initDB()
    const tx = db.transaction(
      [STORES.PROJECTS, STORES.IMAGES, STORES.ANNOTATIONS, STORES.HISTORY],
      'readwrite'
    )

    await tx.store.delete(projectId)

    const images = await tx.objectStore(STORES.IMAGES).index('projectId').getAll(projectId)
    for (const img of images) {
      await tx.objectStore(STORES.IMAGES).delete(img.id)
      await tx.objectStore(STORES.ANNOTATIONS).index('imageId').getAllKeys(img.id).then(keys =>
        Promise.all(keys.map(key => tx.objectStore(STORES.ANNOTATIONS).delete(key)))
      )
      await tx.objectStore(STORES.HISTORY).index('imageId').getAllKeys(img.id).then(keys =>
        Promise.all(keys.map(key => tx.objectStore(STORES.HISTORY).delete(key)))
      )
    }

    await tx.done
  },

  async addImage(imageData) {
    const db = await initDB()
    const id = imageData.id || `img_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    const data = {
      id,
      projectId: imageData.projectId,
      name: imageData.name,
      dataUrl: imageData.dataUrl,
      width: imageData.width,
      height: imageData.height,
      createdAt: Date.now()
    }
    await db.put(STORES.IMAGES, data)
    return data
  },

  async getImages(projectId) {
    const db = await initDB()
    if (projectId) {
      return await db.getAllFromIndex(STORES.IMAGES, 'projectId', projectId)
    }
    return await db.getAll(STORES.IMAGES)
  },

  async getImage(imageId) {
    const db = await initDB()
    return await db.get(STORES.IMAGES, imageId)
  },

  async deleteImage(imageId) {
    const db = await initDB()
    const tx = db.transaction([STORES.IMAGES, STORES.ANNOTATIONS, STORES.HISTORY], 'readwrite')
    await tx.store.delete(imageId)
    const annotKeys = await tx.objectStore(STORES.ANNOTATIONS).index('imageId').getAllKeys(imageId)
    await Promise.all(annotKeys.map(key => tx.objectStore(STORES.ANNOTATIONS).delete(key)))
    const histKeys = await tx.objectStore(STORES.HISTORY).index('imageId').getAllKeys(imageId)
    await Promise.all(histKeys.map(key => tx.objectStore(STORES.HISTORY).delete(key)))
    await tx.done
  },

  async addAnnotation(annotation) {
    const db = await initDB()
    const id = annotation.id || `ann_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    const data = {
      id,
      ...annotation,
      createdAt: Date.now(),
      updatedAt: Date.now()
    }
    await db.put(STORES.ANNOTATIONS, data)
    return data
  },

  async addAnnotations(annotations) {
    const db = await initDB()
    const tx = db.transaction(STORES.ANNOTATIONS, 'readwrite')
    const results = []
    for (const ann of annotations) {
      const id = ann.id || `ann_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
      const data = {
        id,
        ...ann,
        createdAt: Date.now(),
        updatedAt: Date.now()
      }
      await tx.store.put(data)
      results.push(data)
    }
    await tx.done
    return results
  },

  async getAnnotations(imageId) {
    const db = await initDB()
    return await db.getAllFromIndex(STORES.ANNOTATIONS, 'imageId', imageId)
  },

  async updateAnnotation(annotationId, updates) {
    const db = await initDB()
    const annotation = await db.get(STORES.ANNOTATIONS, annotationId)
    if (annotation) {
      const updated = { ...annotation, ...updates, updatedAt: Date.now() }
      await db.put(STORES.ANNOTATIONS, updated)
      return updated
    }
    return null
  },

  async deleteAnnotation(annotationId) {
    const db = await initDB()
    await db.delete(STORES.ANNOTATIONS, annotationId)
  },

  async clearAnnotations(imageId) {
    const db = await initDB()
    const tx = db.transaction(STORES.ANNOTATIONS, 'readwrite')
    const keys = await tx.store.index('imageId').getAllKeys(imageId)
    await Promise.all(keys.map(key => tx.store.delete(key)))
    await tx.done
  },

  async saveHistory(imageId, action, data, snapshot) {
    const db = await initDB()
    const id = `hist_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    const history = {
      id,
      imageId,
      action,
      data,
      snapshot,
      timestamp: Date.now()
    }
    await db.put(STORES.HISTORY, history)
    return history
  },

  async getHistory(imageId, limit = 50) {
    const db = await initDB()
    const history = await db.getAllFromIndex(STORES.HISTORY, 'imageId', imageId)
    return history.sort((a, b) => b.timestamp - a.timestamp).slice(0, limit)
  },

  async clearOldHistory(imageId, keepCount = 100) {
    const db = await initDB()
    const history = await this.getHistory(imageId, keepCount + 1)
    if (history.length > keepCount) {
      const tx = db.transaction(STORES.HISTORY, 'readwrite')
      const toDelete = history.slice(keepCount)
      await Promise.all(toDelete.map(h => tx.store.delete(h.id)))
      await tx.done
    }
  },

  async exportAll(projectId) {
    const images = await this.getImages(projectId)
    const result = []
    for (const img of images) {
      const annotations = await this.getAnnotations(img.id)
      result.push({
        image: {
          id: img.id,
          name: img.name,
          width: img.width,
          height: img.height
        },
        annotations
      })
    }
    return result
  },

  async close() {
    if (dbPromise) {
      const db = await dbPromise
      db.close()
      dbPromise = null
    }
  }
}

export default db
