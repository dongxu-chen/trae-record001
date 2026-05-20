import { mockApi } from './mockApi'

const USE_MOCK_API = true
const API_BASE_URL = 'https://api.example.com/comic-reader'
const STORAGE_KEY = 'comic_reader_bookmarks'
const SYNC_INTERVAL = 5 * 60 * 1000

class BookmarkService {
  constructor() {
    this.bookmarks = new Set()
    this.isSyncing = false
    this.lastSyncTime = 0
    this.deviceId = this.getOrCreateDeviceId()
  }

  getOrCreateDeviceId() {
    let deviceId = localStorage.getItem('comic_reader_device_id')
    if (!deviceId) {
      deviceId = 'device_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9)
      localStorage.setItem('comic_reader_device_id', deviceId)
    }
    return deviceId
  }

  async init() {
    try {
      const localBookmarks = this.loadFromLocalStorage()
      localBookmarks.forEach(page => this.bookmarks.add(page))
      
      await this.syncFromServer()
      
      this.startAutoSync()
      
      console.log('书签服务初始化完成，当前书签:', Array.from(this.bookmarks))
    } catch (error) {
      console.error('书签服务初始化失败:', error)
    }
  }

  loadFromLocalStorage() {
    try {
      const data = localStorage.getItem(STORAGE_KEY)
      return data ? JSON.parse(data) : []
    } catch (error) {
      console.error('从本地存储加载书签失败:', error)
      return []
    }
  }

  saveToLocalStorage() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(Array.from(this.bookmarks)))
    } catch (error) {
      console.error('保存书签到本地存储失败:', error)
    }
  }

  async syncFromServer() {
    if (this.isSyncing) return
    
    this.isSyncing = true
    try {
      let data
      
      if (USE_MOCK_API) {
        data = await mockApi.getBookmarks(this.deviceId)
      } else {
        const response = await fetch(`${API_BASE_URL}/bookmarks?deviceId=${this.deviceId}`, {
          method: 'GET',
          headers: { 'Content-Type': 'application/json' }
        })
        data = await response.json()
      }
      
      const serverBookmarks = data.bookmarks || []
      
      serverBookmarks.forEach(page => this.bookmarks.add(page))
      this.saveToLocalStorage()
      
      this.lastSyncTime = Date.now()
      console.log('从服务器同步书签成功:', serverBookmarks)
    } catch (error) {
      console.warn('从服务器同步书签失败，使用本地数据:', error)
    } finally {
      this.isSyncing = false
    }
  }

  async syncToServer() {
    if (this.isSyncing) return
    
    this.isSyncing = true
    try {
      if (USE_MOCK_API) {
        await mockApi.saveBookmarks(this.deviceId, Array.from(this.bookmarks))
      } else {
        await fetch(`${API_BASE_URL}/bookmarks`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            deviceId: this.deviceId,
            bookmarks: Array.from(this.bookmarks),
            timestamp: Date.now()
          })
        })
      }
      
      this.lastSyncTime = Date.now()
      console.log('书签到服务器同步成功')
    } catch (error) {
      console.warn('同步书签到服务器失败，将在下次重试:', error)
    } finally {
      this.isSyncing = false
    }
  }

  async addBookmark(page) {
    this.bookmarks.add(page)
    this.saveToLocalStorage()
    
    setTimeout(() => this.syncToServer(), 1000)
    
    return Array.from(this.bookmarks)
  }

  async removeBookmark(page) {
    this.bookmarks.delete(page)
    this.saveToLocalStorage()
    
    setTimeout(() => this.syncToServer(), 1000)
    
    return Array.from(this.bookmarks)
  }

  async toggleBookmark(page) {
    if (this.bookmarks.has(page)) {
      return await this.removeBookmark(page)
    } else {
      return await this.addBookmark(page)
    }
  }

  hasBookmark(page) {
    return this.bookmarks.has(page)
  }

  getAllBookmarks() {
    return Array.from(this.bookmarks).sort((a, b) => a - b)
  }

  startAutoSync() {
    setInterval(() => {
      if (Date.now() - this.lastSyncTime > SYNC_INTERVAL) {
        this.syncFromServer()
      }
    }, SYNC_INTERVAL)
  }

  async forceSync() {
    await this.syncFromServer()
    await this.syncToServer()
  }

  clearAll() {
    this.bookmarks.clear()
    this.saveToLocalStorage()
    this.syncToServer()
  }
}

export const bookmarkService = new BookmarkService()
export default bookmarkService
