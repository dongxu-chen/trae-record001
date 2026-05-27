import type { MappingTemplate } from '@/types';

const DB_NAME = 'DataMapperDB';
const DB_VERSION = 2;
const STORE_PROJECTS = 'mappingProjects';
const STORE_TEMPLATES = 'mappingTemplates';

export interface StoredProject {
  id?: number;
  name: string;
  createdAt: number;
  updatedAt: number;
  sourceFileName: string | null;
  sourceFields: any[];
  targetFields: any[];
  mappings: any[];
}

class IndexedDBService {
  private db: IDBDatabase | null = null;
  private initPromise: Promise<void> | null = null;

  async init(): Promise<void> {
    if (this.db) return;
    if (this.initPromise) return this.initPromise;

    this.initPromise = new Promise((resolve, reject) => {
      const request = indexedDB.open(DB_NAME, DB_VERSION);

      request.onerror = () => reject(request.error);
      request.onsuccess = () => {
        this.db = request.result;
        resolve();
      };

      request.onupgradeneeded = (event) => {
        const db = (event.target as IDBOpenDBRequest).result;
        const oldVersion = event.oldVersion || 0;

        if (oldVersion < 1) {
          if (!db.objectStoreNames.contains(STORE_PROJECTS)) {
            const store = db.createObjectStore(STORE_PROJECTS, {
              keyPath: 'id',
              autoIncrement: true,
            });
            store.createIndex('name', 'name', { unique: false });
            store.createIndex('updatedAt', 'updatedAt', { unique: false });
          }
        }

        if (oldVersion < 2) {
          if (!db.objectStoreNames.contains(STORE_TEMPLATES)) {
            const templateStore = db.createObjectStore(STORE_TEMPLATES, {
              keyPath: 'id',
              autoIncrement: true,
            });
            templateStore.createIndex('name', 'name', { unique: false });
            templateStore.createIndex('category', 'category', { unique: false });
            templateStore.createIndex('updatedAt', 'updatedAt', { unique: false });
          }
        }
      };
    });

    return this.initPromise;
  }

  async saveProject(project: Omit<StoredProject, 'id' | 'createdAt' | 'updatedAt'> & { id?: number }): Promise<number> {
    await this.init();
    return new Promise((resolve, reject) => {
      if (!this.db) {
        reject(new Error('Database not initialized'));
        return;
      }

      const transaction = this.db.transaction(STORE_PROJECTS, 'readwrite');
      const store = transaction.objectStore(STORE_PROJECTS);
      const now = Date.now();

      const data: StoredProject = {
        ...project,
        createdAt: project.id ? project.createdAt || now : now,
        updatedAt: now,
      };

      const request = project.id ? store.put(data) : store.add(data);

      request.onsuccess = () => resolve(request.result as number);
      request.onerror = () => reject(request.error);
    });
  }

  async getProject(id: number): Promise<StoredProject | null> {
    await this.init();
    return new Promise((resolve, reject) => {
      if (!this.db) {
        reject(new Error('Database not initialized'));
        return;
      }

      const transaction = this.db.transaction(STORE_PROJECTS, 'readonly');
      const store = transaction.objectStore(STORE_PROJECTS);
      const request = store.get(id);

      request.onsuccess = () => resolve(request.result || null);
      request.onerror = () => reject(request.error);
    });
  }

  async getLatestProject(): Promise<StoredProject | null> {
    await this.init();
    return new Promise((resolve, reject) => {
      if (!this.db) {
        reject(new Error('Database not initialized'));
        return;
      }

      const transaction = this.db.transaction(STORE_PROJECTS, 'readonly');
      const store = transaction.objectStore(STORE_PROJECTS);
      const index = store.index('updatedAt');
      const request = index.openCursor(null, 'prev');

      request.onsuccess = () => {
        const cursor = request.result;
        if (cursor) {
          resolve(cursor.value);
        } else {
          resolve(null);
        }
      };
      request.onerror = () => reject(request.error);
    });
  }

  async getAllProjects(): Promise<StoredProject[]> {
    await this.init();
    return new Promise((resolve, reject) => {
      if (!this.db) {
        reject(new Error('Database not initialized'));
        return;
      }

      const transaction = this.db.transaction(STORE_PROJECTS, 'readonly');
      const store = transaction.objectStore(STORE_PROJECTS);
      const request = store.getAll();

      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }

  async deleteProject(id: number): Promise<void> {
    await this.init();
    return new Promise((resolve, reject) => {
      if (!this.db) {
        reject(new Error('Database not initialized'));
        return;
      }

      const transaction = this.db.transaction(STORE_PROJECTS, 'readwrite');
      const store = transaction.objectStore(STORE_PROJECTS);
      const request = store.delete(id);

      request.onsuccess = () => resolve();
      request.onerror = () => reject(request.error);
    });
  }

  async saveTemplate(template: Omit<MappingTemplate, 'id' | 'createdAt' | 'updatedAt'> & { id?: number }): Promise<number> {
    await this.init();
    return new Promise((resolve, reject) => {
      if (!this.db) {
        reject(new Error('Database not initialized'));
        return;
      }

      const transaction = this.db.transaction(STORE_TEMPLATES, 'readwrite');
      const store = transaction.objectStore(STORE_TEMPLATES);
      const now = Date.now();

      const data: MappingTemplate = {
        ...template,
        id: template.id,
        createdAt: template.id ? template.createdAt || now : now,
        updatedAt: now,
      } as MappingTemplate;

      const request = template.id ? store.put(data) : store.add(data);

      request.onsuccess = () => resolve(request.result as number);
      request.onerror = () => reject(request.error);
    });
  }

  async getTemplate(id: number): Promise<MappingTemplate | null> {
    await this.init();
    return new Promise((resolve, reject) => {
      if (!this.db) {
        reject(new Error('Database not initialized'));
        return;
      }

      const transaction = this.db.transaction(STORE_TEMPLATES, 'readonly');
      const store = transaction.objectStore(STORE_TEMPLATES);
      const request = store.get(id);

      request.onsuccess = () => resolve(request.result || null);
      request.onerror = () => reject(request.error);
    });
  }

  async getAllTemplates(): Promise<MappingTemplate[]> {
    await this.init();
    return new Promise((resolve, reject) => {
      if (!this.db) {
        reject(new Error('Database not initialized'));
        return;
      }

      const transaction = this.db.transaction(STORE_TEMPLATES, 'readonly');
      const store = transaction.objectStore(STORE_TEMPLATES);
      const request = store.getAll();

      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }

  async getTemplatesByCategory(category: string): Promise<MappingTemplate[]> {
    await this.init();
    return new Promise((resolve, reject) => {
      if (!this.db) {
        reject(new Error('Database not initialized'));
        return;
      }

      const transaction = this.db.transaction(STORE_TEMPLATES, 'readonly');
      const store = transaction.objectStore(STORE_TEMPLATES);
      const index = store.index('category');
      const request = index.getAll(category);

      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }

  async deleteTemplate(id: number): Promise<void> {
    await this.init();
    return new Promise((resolve, reject) => {
      if (!this.db) {
        reject(new Error('Database not initialized'));
        return;
      }

      const transaction = this.db.transaction(STORE_TEMPLATES, 'readwrite');
      const store = transaction.objectStore(STORE_TEMPLATES);
      const request = store.delete(id);

      request.onsuccess = () => resolve();
      request.onerror = () => reject(request.error);
    });
  }

  async clearAll(): Promise<void> {
    await this.init();
    return new Promise((resolve, reject) => {
      if (!this.db) {
        reject(new Error('Database not initialized'));
        return;
      }

      const transaction = this.db.transaction([STORE_PROJECTS, STORE_TEMPLATES], 'readwrite');
      transaction.objectStore(STORE_PROJECTS).clear();
      transaction.objectStore(STORE_TEMPLATES).clear();

      transaction.oncomplete = () => resolve();
      transaction.onerror = () => reject(transaction.error);
    });
  }
}

export const indexedDBService = new IndexedDBService();

export const saveToLocalStorage = (key: string, data: any): void => {
  try {
    localStorage.setItem(key, JSON.stringify(data));
  } catch (e) {
    console.warn('localStorage save failed:', e);
  }
};

export const loadFromLocalStorage = <T>(key: string, defaultValue: T): T => {
  try {
    const stored = localStorage.getItem(key);
    return stored ? JSON.parse(stored) : defaultValue;
  } catch (e) {
    console.warn('localStorage load failed:', e);
    return defaultValue;
  }
};
