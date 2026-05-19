export interface Book {
  id: number
  title: string
  author?: string
  description?: string
  summary?: string
  cover?: string
  filePath: string
  fileSize?: number
  isCompleted: boolean
  totalReadTime: number
  downloadedAt?: number
  lastReadAt?: number
  syncStatus: 'synced' | 'pending' | 'conflict'
  createdAt: number
  updatedAt: number
}

export interface Progress {
  id?: number
  bookId: number
  location: string
  percentage: number
  createdAt: number
  updatedAt: number
}

export interface Annotation {
  id?: number
  bookId: number
  cfi: string
  normalizedCfi?: string
  text: string
  note?: string
  color: string
  createdAt: number
  updatedAt: number
}

export interface Bookmark {
  id?: number
  bookId: number
  cfi: string
  chapter?: string
  note?: string
  createdAt: number
  updatedAt: number
}

export interface ReadingSession {
  id?: number
  bookId: number
  startTime: number
  endTime?: number
  duration: number
  startCfi?: string
  endCfi?: string
  pagesRead: number
  createdAt: number
}

export interface ChapterSummary {
  id?: number
  bookId: number
  chapterIndex: number
  chapterTitle: string
  summary: string
  createdAt: number
  updatedAt: number
}

export interface BookFile {
  bookId: number
  fileName: string
  fileType: string
  data: ArrayBuffer
  size: number
  createdAt: number
}

const DB_NAME = 'EPUBReaderDB'
const DB_VERSION = 1

const STORES = {
  books: 'books',
  progress: 'progress',
  annotations: 'annotations',
  bookmarks: 'bookmarks',
  readingSessions: 'readingSessions',
  chapterSummaries: 'chapterSummaries',
  bookFiles: 'bookFiles'
} as const

class IndexedDB {
  private db: IDBDatabase | null = null
  private initPromise: Promise<void> | null = null

  async init(): Promise<void> {
    if (this.initPromise) return this.initPromise
    if (this.db) return

    this.initPromise = new Promise((resolve, reject) => {
      const request = indexedDB.open(DB_NAME, DB_VERSION)

      request.onerror = () => reject(request.error)
      request.onsuccess = () => {
        this.db = request.result
        resolve()
      }

      request.onupgradeneeded = (event) => {
        const db = (event.target as IDBOpenDBRequest).result
        this.createStores(db)
      }
    })

    return this.initPromise
  }

  private createStores(db: IDBDatabase): void {
    // Books store
    if (!db.objectStoreNames.contains(STORES.books)) {
      const booksStore = db.createObjectStore(STORES.books, { keyPath: 'id', autoIncrement: true })
      booksStore.createIndex('title', 'title', { unique: false })
      booksStore.createIndex('downloadedAt', 'downloadedAt', { unique: false })
      booksStore.createIndex('lastReadAt', 'lastReadAt', { unique: false })
    }

    // Progress store
    if (!db.objectStoreNames.contains(STORES.progress)) {
      const progressStore = db.createObjectStore(STORES.progress, { keyPath: 'id', autoIncrement: true })
      progressStore.createIndex('bookId', 'bookId', { unique: true })
    }

    // Annotations store
    if (!db.objectStoreNames.contains(STORES.annotations)) {
      const annStore = db.createObjectStore(STORES.annotations, { keyPath: 'id', autoIncrement: true })
      annStore.createIndex('bookId', 'bookId', { unique: false })
      annStore.createIndex('cfi', 'cfi', { unique: false })
    }

    // Bookmarks store
    if (!db.objectStoreNames.contains(STORES.bookmarks)) {
      const bmStore = db.createObjectStore(STORES.bookmarks, { keyPath: 'id', autoIncrement: true })
      bmStore.createIndex('bookId', 'bookId', { unique: false })
    }

    // ReadingSessions store
    if (!db.objectStoreNames.contains(STORES.readingSessions)) {
      const sessionStore = db.createObjectStore(STORES.readingSessions, { keyPath: 'id', autoIncrement: true })
      sessionStore.createIndex('bookId', 'bookId', { unique: false })
    }

    // ChapterSummaries store
    if (!db.objectStoreNames.contains(STORES.chapterSummaries)) {
      const summaryStore = db.createObjectStore(STORES.chapterSummaries, { keyPath: 'id', autoIncrement: true })
      summaryStore.createIndex('bookId', 'bookId', { unique: false })
    }

    // BookFiles store (for storing EPUB files)
    if (!db.objectStoreNames.contains(STORES.bookFiles)) {
      const fileStore = db.createObjectStore(STORES.bookFiles, { keyPath: 'bookId' })
    }
  }

  private async transaction<T>(
    storeName: string,
    mode: IDBTransactionMode,
    callback: (store: IDBObjectStore) => IDBRequest<T>
  ): Promise<T> {
    await this.init()
    if (!this.db) throw new Error('Database not initialized')

    return new Promise((resolve, reject) => {
      const tx = this.db!.transaction(storeName, mode)
      const store = tx.objectStore(storeName)
      const request = callback(store)

      request.onsuccess = () => resolve(request.result)
      request.onerror = () => reject(request.error)
    })
  }

  // Books operations
  async addBook(book: Omit<Book, 'id' | 'createdAt' | 'updatedAt'>): Promise<number> {
    const now = Date.now()
    return this.transaction(STORES.books, 'readwrite', (store) =>
      store.add({ ...book, createdAt: now, updatedAt: now })
    )
  }

  async updateBook(id: number, updates: Partial<Book>): Promise<void> {
    const book = await this.getBook(id)
    if (!book) throw new Error('Book not found')

    await this.transaction(STORES.books, 'readwrite', (store) =>
      store.put({ ...book, ...updates, updatedAt: Date.now() })
    )
  }

  async getBook(id: number): Promise<Book | undefined> {
    return this.transaction(STORES.books, 'readonly', (store) => store.get(id))
  }

  async getAllBooks(): Promise<Book[]> {
    return this.transaction(STORES.books, 'readonly', (store) => store.getAll())
  }

  async deleteBook(id: number): Promise<void> {
    await this.transaction(STORES.books, 'readwrite', (store) => store.delete(id))
    await this.deleteBookFile(id)
  }

  // Book File operations (for storing EPUB files)
  async saveBookFile(bookId: number, fileName: string, data: ArrayBuffer): Promise<void> {
    await this.transaction(STORES.bookFiles, 'readwrite', (store) =>
      store.put({
        bookId,
        fileName,
        fileType: 'application/epub+zip',
        data,
        size: data.byteLength,
        createdAt: Date.now()
      })
    )
  }

  async getBookFile(bookId: number): Promise<BookFile | undefined> {
    return this.transaction(STORES.bookFiles, 'readonly', (store) => store.get(bookId))
  }

  async getAnnotationsByBookId(bookId: number): Promise<Annotation[]> {
    return this.transaction(STORES.annotations, 'readonly', (store) =>
      store.index('bookId').getAll(bookId)
    )
  }

  async deleteBookFile(bookId: number): Promise<void> {
    await this.transaction(STORES.bookFiles, 'readwrite', (store) => store.delete(bookId))
  }

  // Progress operations
  async saveProgress(progress: Omit<Progress, 'id' | 'createdAt' | 'updatedAt'>): Promise<number> {
    const existing = await this.getProgressByBookId(progress.bookId)
    const now = Date.now()

    if (existing) {
      await this.transaction(STORES.progress, 'readwrite', (store) =>
        store.put({ ...existing, ...progress, updatedAt: now })
      )
      return existing.id!
    }

    return this.transaction(STORES.progress, 'readwrite', (store) =>
      store.add({ ...progress, createdAt: now, updatedAt: now })
    )
  }

  async getProgressByBookId(bookId: number): Promise<Progress | undefined> {
    return this.transaction(STORES.progress, 'readonly', (store) =>
      store.index('bookId').get(bookId)
    )
  }

  // Annotation operations
  async addAnnotation(annotation: Omit<Annotation, 'id' | 'createdAt' | 'updatedAt'>): Promise<number> {
    const now = Date.now()
    return this.transaction(STORES.annotations, 'readwrite', (store) =>
      store.add({ ...annotation, createdAt: now, updatedAt: now })
    )
  }

  async getAnnotationsByBookId(bookId: number): Promise<Annotation[]> {
    return this.transaction(STORES.annotations, 'readonly', (store) =>
      store.index('bookId').getAll(bookId)
    )
  }

  async deleteAnnotation(id: number): Promise<void> {
    await this.transaction(STORES.annotations, 'readwrite', (store) => store.delete(id))
  }

  // Bookmark operations
  async addBookmark(bookmark: Omit<Bookmark, 'id' | 'createdAt' | 'updatedAt'>): Promise<number> {
    const now = Date.now()
    return this.transaction(STORES.bookmarks, 'readwrite', (store) =>
      store.add({ ...bookmark, createdAt: now, updatedAt: now })
    )
  }

  async getBookmarksByBookId(bookId: number): Promise<Bookmark[]> {
    return this.transaction(STORES.bookmarks, 'readonly', (store) =>
      store.index('bookId').getAll(bookId)
    )
  }

  async deleteBookmark(id: number): Promise<void> {
    await this.transaction(STORES.bookmarks, 'readwrite', (store) => store.delete(id))
  }

  // ReadingSession operations
  async startSession(bookId: number, startCfi?: string): Promise<number> {
    return this.transaction(STORES.readingSessions, 'readwrite', (store) =>
      store.add({
        bookId,
        startTime: Date.now(),
        duration: 0,
        startCfi,
        pagesRead: 0,
        createdAt: Date.now()
      })
    )
  }

  async endSession(sessionId: number, endCfi?: string, pagesRead: number = 0): Promise<void> {
    const session = await this.transaction(STORES.readingSessions, 'readonly', (store) =>
      store.get(sessionId)
    )

    if (!session) return

    const now = Date.now()
    const duration = Math.floor((now - session.startTime) / 1000)

    await this.transaction(STORES.readingSessions, 'readwrite', (store) =>
      store.put({
        ...session,
        endTime: now,
        duration,
        endCfi,
        pagesRead: session.pagesRead + pagesRead
      })
    )
  }

  async getReadingStats(): Promise<{ totalTime: number; booksRead: number }> {
    const sessions = await this.transaction(STORES.readingSessions, 'readonly', (store) =>
      store.getAll()
    )

    const books = await this.getAllBooks()
    const totalTime = sessions.reduce((sum, s) => sum + s.duration, 0)
    const booksRead = books.filter(b => b.isCompleted).length

    return { totalTime, booksRead }
  }

  // ChapterSummary operations
  async saveChapterSummary(summary: Omit<ChapterSummary, 'id' | 'createdAt' | 'updatedAt'>): Promise<number> {
    const now = Date.now()
    return this.transaction(STORES.chapterSummaries, 'readwrite', (store) =>
      store.add({ ...summary, createdAt: now, updatedAt: now })
    )
  }

  async getChapterSummaries(bookId: number): Promise<ChapterSummary[]> {
    return this.transaction(STORES.chapterSummaries, 'readonly', (store) =>
      store.index('bookId').getAll(bookId)
    )
  }

  // Sync operations
  async getAllPendingSync(): Promise<{
    books: Book[]
    progress: Progress[]
    annotations: Annotation[]
    bookmarks: Bookmark[]
  }> {
    const [books, progress, annotations, bookmarks] = await Promise.all([
      this.getAllBooks(),
      this.transaction(STORES.progress, 'readonly', (store) => store.getAll()),
      this.transaction(STORES.annotations, 'readonly', (store) => store.getAll()),
      this.transaction(STORES.bookmarks, 'readonly', (store) => store.getAll())
    ])

    return {
      books: books.filter(b => b.syncStatus === 'pending'),
      progress,
      annotations,
      bookmarks
    }
  }

  async clear(): Promise<void> {
    await this.init()
    if (!this.db) return

    for (const storeName of Object.values(STORES)) {
      await this.transaction(storeName, 'readwrite', (store) => store.clear())
    }
  }
}

export const db = new IndexedDB()

// Composables for Vue
export function useIndexedDB() {
  const isSupported = typeof window !== 'undefined' && 'indexedDB' in window
  const isOnline = ref(true)

  if (typeof window !== 'undefined') {
    window.addEventListener('online', () => { isOnline.value = true })
    window.addEventListener('offline', () => { isOnline.value = false })
  }

  return {
    db,
    isSupported,
    isOnline,
    initDB: () => db.init()
  }
}
