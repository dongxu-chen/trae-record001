class MockBookmarkApi {
  constructor() {
    this.storageKey = 'mock_server_bookmarks'
  }
  
  delay(ms = 300) {
    return new Promise(resolve => setTimeout(resolve, ms))
  }
  
  async getBookmarks(deviceId) {
    await this.delay(200)
    
    const data = localStorage.getItem(this.storageKey)
    const serverData = data ? JSON.parse(data) : {}
    
    const bookmarks = serverData[deviceId] || []
    
    console.log('[Mock API] 获取书签:', bookmarks)
    return { bookmarks }
  }
  
  async saveBookmarks(deviceId, bookmarks) {
    await this.delay(300)
    
    const data = localStorage.getItem(this.storageKey)
    const serverData = data ? JSON.parse(data) : {}
    
    serverData[deviceId] = bookmarks
    localStorage.setItem(this.storageKey, JSON.stringify(serverData))
    
    console.log('[Mock API] 保存书签:', bookmarks)
    return { success: true }
  }
}

export const mockApi = new MockBookmarkApi()
export default mockApi
