import { app } from 'electron'
import * as path from 'path'
import * as fs from 'fs'
import type { Database } from 'better-sqlite3'
import type { HistoryItem, ClipboardContent, ClipboardDataType, DataMigrationResult } from '@shared/types'
import { ClipboardDataType as DataType, DEFAULT_KDF_ITERATIONS, DATABASE_CIPHER } from '@shared/types'
import { deriveKeyFromPassword, generateId, verifyPassword } from '@shared/utils'

let Database: any
try {
  Database = require('@journeyapps/sqlcipher').verbose()
} catch (e) {
  try {
    Database = require('better-sqlite3')
  } catch (e2) {
    console.error('无法加载数据库模块:', e2)
  }
}

interface HistoryRecord {
  id: string
  content_id: string
  content_type: string
  content_data: string
  content_hash: string
  content_checksum: string
  device_id: string
  device_name: string
  timestamp: number
  created_at: number
  favorite: number
  synced: number
}

export class HistoryManager {
  private db: Database | null = null
  private dbPath: string
  private maxItems: number
  private encryptionKey: string = ''
  private isInitialized: boolean = false
  private isEncrypted: boolean = false

  constructor(maxItems: number = 100) {
    this.maxItems = maxItems
    this.dbPath = path.join(app.getPath('userData'), 'clipboard-history.db')
  }

  async initialize(password?: string, existingKey?: string): Promise<boolean> {
    try {
      if (!Database) {
        throw new Error('数据库模块未加载')
      }

      if (password) {
        const derived = await deriveKeyFromPassword(password)
        this.encryptionKey = derived.key
        this.isEncrypted = true
      } else if (existingKey) {
        this.encryptionKey = existingKey
        this.isEncrypted = true
      }

      this.db = new Database(this.dbPath)

      if (this.isEncrypted) {
        this.db.pragma(`key = '${this.encryptionKey}'`)
        this.db.pragma(`cipher = '${DATABASE_CIPHER}'`)
      }

      this.db.pragma('journal_mode = WAL')
      this.db.pragma('synchronous = NORMAL')

      this.createTables()

      try {
        const testStmt = this.db.prepare('SELECT COUNT(*) as count FROM history')
        testStmt.get()
        this.isInitialized = true
        return true
      } catch (e) {
        console.error('数据库密钥错误或损坏:', e)
        this.db.close()
        this.db = null
        this.isInitialized = false
        return false
      }
    } catch (e) {
      console.error('初始化数据库失败:', e)
      if (this.db) {
        try { this.db.close() } catch (_) {}
        this.db = null
      }
      this.isInitialized = false
      return false
    }
  }

  private createTables(): void {
    if (!this.db) return

    this.db.exec(`
      CREATE TABLE IF NOT EXISTS history (
        id TEXT PRIMARY KEY,
        content_id TEXT NOT NULL,
        content_type TEXT NOT NULL,
        content_data TEXT NOT NULL,
        content_hash TEXT NOT NULL,
        content_checksum TEXT,
        device_id TEXT NOT NULL,
        device_name TEXT NOT NULL,
        timestamp INTEGER NOT NULL,
        created_at INTEGER NOT NULL,
        favorite INTEGER DEFAULT 0,
        synced INTEGER DEFAULT 1
      );
      
      CREATE INDEX IF NOT EXISTS idx_history_type ON history(content_type);
      CREATE INDEX IF NOT EXISTS idx_history_favorite ON history(favorite);
      CREATE INDEX IF NOT EXISTS idx_history_created ON history(created_at DESC);
      CREATE INDEX IF NOT EXISTS idx_history_hash ON history(content_hash);
      
      CREATE TABLE IF NOT EXISTS metadata (
        key TEXT PRIMARY KEY,
        value TEXT
      );
    `)

    const checkTable = this.db.prepare("SELECT name FROM sqlite_master WHERE type='table' AND name='metadata'")
    if (checkTable.get()) {
      const initStmt = this.db.prepare('INSERT OR IGNORE INTO metadata (key, value) VALUES (?, ?)')
      initStmt.run('schema_version', '1')
      initStmt.run('created_at', Date.now().toString())
    }
  }

  async setPassword(password: string): Promise<boolean> {
    try {
      const derived = await deriveKeyFromPassword(password)
      this.encryptionKey = derived.key
      this.isEncrypted = true

      if (this.db) {
        this.db.pragma(`rekey = '${this.encryptionKey}'`)
        this.db.pragma(`cipher = '${DATABASE_CIPHER}'`)
      }

      return true
    } catch (e) {
      console.error('设置密码失败:', e)
      return false
    }
  }

  async changePassword(oldPassword: string, newPassword: string): Promise<boolean> {
    try {
      if (!this.isEncrypted) {
        return this.setPassword(newPassword)
      }

      const metaStmt = this.db?.prepare('SELECT value FROM metadata WHERE key = ?')
      const salt = metaStmt?.get('password_salt')?.value
      const hash = metaStmt?.get('password_hash')?.value
      const iterations = parseInt(metaStmt?.get('kdf_iterations')?.value || DEFAULT_KDF_ITERATIONS.toString())

      if (salt && hash) {
        const isValid = await verifyPassword(oldPassword, hash, salt, iterations)
        if (!isValid) {
          return false
        }
      }

      return this.setPassword(newPassword)
    } catch (e) {
      console.error('修改密码失败:', e)
      return false
    }
  }

  async addItem(item: HistoryItem): Promise<void> {
    if (!this.db || !this.isInitialized) {
      throw new Error('数据库未初始化')
    }

    const content = item.content
    const contentData = typeof content.data === 'string' 
      ? content.data 
      : JSON.stringify(content.data)

    const checkStmt = this.db.prepare(
      'SELECT id FROM history WHERE content_hash = ? AND created_at > ? ORDER BY created_at DESC LIMIT 1'
    )
    const existing = checkStmt.get(content.hash, Date.now() - 60000)
    
    if (existing) {
      const deleteStmt = this.db.prepare('DELETE FROM history WHERE id = ?')
      deleteStmt.run((existing as any).id)
    }

    const insertStmt = this.db.prepare(`
      INSERT INTO history (
        id, content_id, content_type, content_data, content_hash, content_checksum,
        device_id, device_name, timestamp, created_at, favorite, synced
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `)

    insertStmt.run(
      item.id,
      content.id,
      content.type,
      contentData,
      content.hash,
      content.checksum || '',
      content.deviceId,
      content.deviceName,
      content.timestamp,
      item.createdAt,
      item.favorite ? 1 : 0,
      item.synced ? 1 : 0
    )

    this.enforceLimit()
  }

  private enforceLimit(): void {
    if (!this.db) return

    const countStmt = this.db.prepare('SELECT COUNT(*) as count FROM history')
    const result = countStmt.get() as { count: number }
    
    if (result.count > this.maxItems) {
      const deleteStmt = this.db.prepare(`
        DELETE FROM history 
        WHERE id IN (
          SELECT id FROM history 
          ORDER BY created_at ASC 
          LIMIT ?
        )
      `)
      deleteStmt.run(result.count - this.maxItems)
    }
  }

  getHistory(): HistoryItem[] {
    if (!this.db || !this.isInitialized) return []

    const stmt = this.db.prepare('SELECT * FROM history ORDER BY created_at DESC LIMIT ?')
    const rows = stmt.all(this.maxItems) as HistoryRecord[]
    
    return rows.map(row => this.recordToHistoryItem(row))
  }

  getItem(id: string): HistoryItem | undefined {
    if (!this.db || !this.isInitialized) return undefined

    const stmt = this.db.prepare('SELECT * FROM history WHERE id = ?')
    const row = stmt.get(id) as HistoryRecord | undefined
    
    return row ? this.recordToHistoryItem(row) : undefined
  }

  search(query: string): HistoryItem[] {
    if (!this.db || !this.isInitialized) return []

    const searchPattern = `%${query.toLowerCase()}%`
    const stmt = this.db.prepare(`
      SELECT * FROM history 
      WHERE LOWER(device_name) LIKE ?
         OR LOWER(content_data) LIKE ?
         OR content_type = ?
      ORDER BY created_at DESC 
      LIMIT ?
    `)
    
    const rows = stmt.all(
      searchPattern, 
      searchPattern, 
      'text',
      this.maxItems
    ) as HistoryRecord[]
    
    return rows
      .map(row => this.recordToHistoryItem(row))
      .filter(item => {
        if (query && item.content.type !== DataType.TEXT) {
          const lowerQuery = query.toLowerCase()
          if (item.content.deviceName.toLowerCase().includes(lowerQuery)) return true
          const data = item.content.data as any
          if (Array.isArray(data)) {
            return data.some((f: any) => f.name?.toLowerCase().includes(lowerQuery))
          } else if (data?.name) {
            return data.name.toLowerCase().includes(lowerQuery)
          }
          return false
        }
        return true
      })
  }

  deleteItem(id: string): boolean {
    if (!this.db || !this.isInitialized) return false

    try {
      const stmt = this.db.prepare('DELETE FROM history WHERE id = ?')
      const result = stmt.run(id)
      return result.changes > 0
    } catch (e) {
      console.error('删除记录失败:', e)
      return false
    }
  }

  clear(): boolean {
    if (!this.db || !this.isInitialized) return false

    try {
      const stmt = this.db.prepare('DELETE FROM history')
      stmt.run()
      return true
    } catch (e) {
      console.error('清空历史记录失败:', e)
      return false
    }
  }

  toggleFavorite(id: string): boolean {
    if (!this.db || !this.isInitialized) return false

    try {
      const selectStmt = this.db.prepare('SELECT favorite FROM history WHERE id = ?')
      const row = selectStmt.get(id) as { favorite: number } | undefined
      
      if (!row) return false

      const updateStmt = this.db.prepare('UPDATE history SET favorite = ? WHERE id = ?')
      const result = updateStmt.run(row.favorite ? 0 : 1, id)
      return result.changes > 0
    } catch (e) {
      console.error('切换收藏失败:', e)
      return false
    }
  }

  setMaxItems(maxItems: number): void {
    this.maxItems = maxItems
    this.enforceLimit()
  }

  getFavorites(): HistoryItem[] {
    if (!this.db || !this.isInitialized) return []

    const stmt = this.db.prepare('SELECT * FROM history WHERE favorite = 1 ORDER BY created_at DESC')
    const rows = stmt.all() as HistoryRecord[]
    return rows.map(row => this.recordToHistoryItem(row))
  }

  getByType(type: ClipboardDataType): HistoryItem[] {
    if (!this.db || !this.isInitialized) return []

    let types: string[]
    if (type === DataType.FILE) {
      types = [DataType.FILE, DataType.FILES]
    } else {
      types = [type]
    }

    const placeholders = types.map(() => '?').join(', ')
    const stmt = this.db.prepare(`
      SELECT * FROM history 
      WHERE content_type IN (${placeholders}) 
      ORDER BY created_at DESC 
      LIMIT ?
    `)
    
    const rows = stmt.all([...types, this.maxItems]) as HistoryRecord[]
    return rows.map(row => this.recordToHistoryItem(row))
  }

  getByDateRange(startDate: number, endDate: number): HistoryItem[] {
    if (!this.db || !this.isInitialized) return []

    const stmt = this.db.prepare(`
      SELECT * FROM history 
      WHERE created_at BETWEEN ? AND ? 
      ORDER BY created_at DESC 
      LIMIT ?
    `)
    
    const rows = stmt.all(startDate, endDate, this.maxItems) as HistoryRecord[]
    return rows.map(row => this.recordToHistoryItem(row))
  }

  private recordToHistoryItem(row: HistoryRecord): HistoryItem {
    let contentData: any
    try {
      contentData = JSON.parse(row.content_data)
    } catch {
      contentData = row.content_data
    }

    const content: ClipboardContent = {
      id: row.content_id,
      type: row.content_type as ClipboardDataType,
      data: contentData,
      timestamp: row.timestamp,
      deviceId: row.device_id,
      deviceName: row.device_name,
      hash: row.content_hash,
      checksum: row.content_checksum || undefined
    }

    return {
      id: row.id,
      content,
      createdAt: row.created_at,
      favorite: row.favorite === 1,
      synced: row.synced === 1
    }
  }

  async migrateFromLegacy(legacyData: HistoryItem[]): Promise<DataMigrationResult> {
    if (!this.db || !this.isInitialized) {
      return {
        success: false,
        migratedCount: 0,
        failedCount: legacyData.length,
        error: '数据库未初始化'
      }
    }

    let migratedCount = 0
    let failedCount = 0

    const tx = this.db.transaction(() => {
      for (const item of legacyData) {
        try {
          const content = item.content
          const contentData = typeof content.data === 'string' 
            ? content.data 
            : JSON.stringify(content.data)

          const insertStmt = this.db!.prepare(`
            INSERT OR REPLACE INTO history (
              id, content_id, content_type, content_data, content_hash, content_checksum,
              device_id, device_name, timestamp, created_at, favorite, synced
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
          `)

          insertStmt.run(
            item.id,
            content.id,
            content.type,
            contentData,
            content.hash,
            content.checksum || '',
            content.deviceId,
            content.deviceName,
            content.timestamp,
            item.createdAt,
            item.favorite ? 1 : 0,
            item.synced ? 1 : 0
          )
          
          migratedCount++
        } catch (e) {
          console.error('迁移记录失败:', item.id, e)
          failedCount++
        }
      }
    })

    try {
      tx()
      this.enforceLimit()
      return {
        success: true,
        migratedCount,
        failedCount
      }
    } catch (e) {
      return {
        success: false,
        migratedCount,
        failedCount: legacyData.length - migratedCount,
        error: (e as Error).message
      }
    }
  }

  exportHistory(): string {
    const history = this.getHistory()
    return JSON.stringify(history, null, 2)
  }

  importHistory(json: string): boolean {
    try {
      const imported = JSON.parse(json) as HistoryItem[]
      if (!Array.isArray(imported)) return false

      const tx = this.db!.transaction(() => {
        for (const item of imported) {
          const content = item.content
          const contentData = typeof content.data === 'string' 
            ? content.data 
            : JSON.stringify(content.data)

          const insertStmt = this.db!.prepare(`
            INSERT OR IGNORE INTO history (
              id, content_id, content_type, content_data, content_hash, content_checksum,
              device_id, device_name, timestamp, created_at, favorite, synced
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
          `)

          insertStmt.run(
            item.id,
            content.id,
            content.type,
            contentData,
            content.hash,
            content.checksum || '',
            content.deviceId,
            content.deviceName,
            content.timestamp,
            item.createdAt,
            item.favorite ? 1 : 0,
            item.synced ? 1 : 0
          )
        }
      })

      tx()
      this.enforceLimit()
      return true
    } catch (e) {
      console.error('导入历史记录失败:', e)
      return false
    }
  }

  close(): void {
    if (this.db) {
      try {
        this.db.close()
      } catch (e) {
        console.error('关闭数据库失败:', e)
      }
      this.db = null
      this.isInitialized = false
    }
  }

  getDatabasePath(): string {
    return this.dbPath
  }

  getDatabaseSize(): number {
    try {
      const stats = fs.statSync(this.dbPath)
      return stats.size
    } catch {
      return 0
    }
  }

  vacuum(): void {
    if (this.db) {
      this.db.exec('VACUUM')
    }
  }

  isReady(): boolean {
    return this.isInitialized && this.db !== null
  }
}
