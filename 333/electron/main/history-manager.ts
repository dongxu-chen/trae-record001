import Store from 'electron-store'
import type { HistoryItem, ClipboardContent, ClipboardDataType } from '@shared/types'
import { ClipboardDataType as DataType } from '@shared/types'

export class HistoryManager {
  private store: Store<{ history: HistoryItem[] }>
  private maxItems: number

  constructor(maxItems: number = 100) {
    this.maxItems = maxItems
    this.store = new Store({
      name: 'clipboard-history',
      defaults: {
        history: []
      }
    })
  }

  async addItem(item: HistoryItem): Promise<void> {
    const history = this.store.get('history', [])
    
    const existingIndex = history.findIndex(
      h => h.content.hash === item.content.hash && Date.now() - h.createdAt < 60000
    )
    
    if (existingIndex !== -1) {
      history.splice(existingIndex, 1)
    }
    
    history.unshift(item)
    
    if (history.length > this.maxItems) {
      history.length = this.maxItems
    }
    
    this.store.set('history', history)
  }

  getHistory(): HistoryItem[] {
    return this.store.get('history', [])
  }

  getItem(id: string): HistoryItem | undefined {
    const history = this.store.get('history', [])
    return history.find(item => item.id === id)
  }

  search(query: string): HistoryItem[] {
    const history = this.store.get('history', [])
    const lowerQuery = query.toLowerCase()
    
    return history.filter(item => {
      const content = item.content
      
      if (content.deviceName.toLowerCase().includes(lowerQuery)) return true
      
      switch (content.type) {
        case DataType.TEXT:
          return (content.data as string).toLowerCase().includes(lowerQuery)
        case DataType.IMAGE:
        case DataType.FILE:
        case DataType.FILES:
          const files = Array.isArray(content.data) ? content.data as any[] : [content.data]
          return files.some(f => f.name.toLowerCase().includes(lowerQuery))
        default:
          return false
      }
    })
  }

  deleteItem(id: string): boolean {
    const history = this.store.get('history', [])
    const index = history.findIndex(item => item.id === id)
    if (index !== -1) {
      history.splice(index, 1)
      this.store.set('history', history)
      return true
    }
    return false
  }

  clear(): boolean {
    this.store.set('history', [])
    return true
  }

  toggleFavorite(id: string): boolean {
    const history = this.store.get('history', [])
    const item = history.find(item => item.id === id)
    if (item) {
      item.favorite = !item.favorite
      this.store.set('history', history)
      return true
    }
    return false
  }

  setMaxItems(maxItems: number): void {
    this.maxItems = maxItems
    const history = this.store.get('history', [])
    if (history.length > maxItems) {
      history.length = maxItems
      this.store.set('history', history)
    }
  }

  getFavorites(): HistoryItem[] {
    return this.getHistory().filter(item => item.favorite)
  }

  getByType(type: ClipboardDataType): HistoryItem[] {
    return this.getHistory().filter(item => item.content.type === type)
  }

  getByDateRange(startDate: number, endDate: number): HistoryItem[] {
    return this.getHistory().filter(
      item => item.createdAt >= startDate && item.createdAt <= endDate
    )
  }

  exportHistory(): string {
    const history = this.getHistory()
    return JSON.stringify(history, null, 2)
  }

  importHistory(json: string): boolean {
    try {
      const imported = JSON.parse(json) as HistoryItem[]
      if (!Array.isArray(imported)) return false
      
      const existing = this.getHistory()
      const merged = [...imported, ...existing]
      
      const seen = new Set<string>()
      const unique = merged.filter(item => {
        const key = `${item.content.hash}-${item.createdAt}`
        if (seen.has(key)) return false
        seen.add(key)
        return true
      })
      
      unique.sort((a, b) => b.createdAt - a.createdAt)
      if (unique.length > this.maxItems) {
        unique.length = this.maxItems
      }
      
      this.store.set('history', unique)
      return true
    } catch (e) {
      console.error('导入历史记录失败:', e)
      return false
    }
  }
}
