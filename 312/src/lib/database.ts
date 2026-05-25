import { Project, Version, ProjectSnapshot } from '@/types'
import { nanoid } from 'nanoid'

const DB_NAME = 'IconAnimationEditor'
const DB_VERSION = 1
const STORE_PROJECTS = 'projects'

export class Database {
  private db: IDBDatabase | null = null

  async init(): Promise<void> {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(DB_NAME, DB_VERSION)

      request.onerror = () => reject(request.error)
      request.onsuccess = () => {
        this.db = request.result
        resolve()
      }

      request.onupgradeneeded = (event) => {
        const db = (event.target as IDBOpenDBRequest).result

        if (!db.objectStoreNames.contains(STORE_PROJECTS)) {
          const store = db.createObjectStore(STORE_PROJECTS, { keyPath: 'id' })
          store.createIndex('name', 'name', { unique: false })
          store.createIndex('updatedAt', 'updatedAt', { unique: false })
        }
      }
    })
  }

  async getProjects(): Promise<Project[]> {
    if (!this.db) throw new Error('Database not initialized')

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction(STORE_PROJECTS, 'readonly')
      const store = transaction.objectStore(STORE_PROJECTS)
      const request = store.getAll()

      request.onsuccess = () => resolve(request.result)
      request.onerror = () => reject(request.error)
    })
  }

  async getProject(id: string): Promise<Project | undefined> {
    if (!this.db) throw new Error('Database not initialized')

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction(STORE_PROJECTS, 'readonly')
      const store = transaction.objectStore(STORE_PROJECTS)
      const request = store.get(id)

      request.onsuccess = () => resolve(request.result)
      request.onerror = () => reject(request.error)
    })
  }

  async saveProject(project: Project): Promise<void> {
    if (!this.db) throw new Error('Database not initialized')

    project.updatedAt = Date.now()

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction(STORE_PROJECTS, 'readwrite')
      const store = transaction.objectStore(STORE_PROJECTS)
      const request = store.put(project)

      request.onsuccess = () => resolve()
      request.onerror = () => reject(request.error)
    })
  }

  async deleteProject(id: string): Promise<void> {
    if (!this.db) throw new Error('Database not initialized')

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction(STORE_PROJECTS, 'readwrite')
      const store = transaction.objectStore(STORE_PROJECTS)
      const request = store.delete(id)

      request.onsuccess = () => resolve()
      request.onerror = () => reject(request.error)
    })
  }

  async createVersion(projectId: string, name: string, description: string, snapshot: ProjectSnapshot): Promise<Version> {
    const version: Version = {
      id: nanoid(),
      name,
      description,
      createdAt: Date.now(),
      snapshot,
    }

    const project = await this.getProject(projectId)
    if (!project) throw new Error('Project not found')

    project.versions.unshift(version)
    await this.saveProject(project)

    return version
  }

  async restoreVersion(projectId: string, versionId: string): Promise<void> {
    const project = await this.getProject(projectId)
    if (!project) throw new Error('Project not found')

    const version = project.versions.find(v => v.id === versionId)
    if (!version) throw new Error('Version not found')

    project.elements = version.snapshot.elements
    project.layers = version.snapshot.layers
    project.duration = version.snapshot.duration

    await this.saveProject(project)
  }

  close(): void {
    if (this.db) {
      this.db.close()
      this.db = null
    }
  }
}

export const db = new Database()
