import { get, set, del, keys, clear } from 'idb-keyval'

const STORAGE_PREFIX = 'mindmap_'

export const storage = {
  async saveMindMap(id, data) {
    const key = `${STORAGE_PREFIX}${id}`
    await set(key, {
      ...data,
      updatedAt: Date.now()
    })
    return id
  },

  async getMindMap(id) {
    const key = `${STORAGE_PREFIX}${id}`
    return await get(key)
  },

  async deleteMindMap(id) {
    const key = `${STORAGE_PREFIX}${id}`
    await del(key)
  },

  async getAllMindMaps() {
    const allKeys = await keys()
    const mindmapKeys = allKeys.filter(key => key.startsWith(STORAGE_PREFIX))
    const mindmaps = []
    for (const key of mindmapKeys) {
      const data = await get(key)
      mindmaps.push({
        id: key.replace(STORAGE_PREFIX, ''),
        title: data.title || '未命名思维导图',
        updatedAt: data.updatedAt || Date.now(),
        createdAt: data.createdAt || Date.now()
      })
    }
    return mindmaps.sort((a, b) => b.updatedAt - a.updatedAt)
  },

  async saveSettings(settings) {
    await set('mindmap_settings', settings)
  },

  async getSettings() {
    return await get('mindmap_settings') || { theme: 'light' }
  },

  async clearAll() {
    await clear()
  },

  generateId() {
    return `${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  }
}
