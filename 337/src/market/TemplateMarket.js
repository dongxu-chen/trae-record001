import { exportConfig, importConfig, downloadConfig, loadConfigFromFile } from '../utils/ConfigManager.js'

const STORAGE_KEY = 'particle_templates_market'
const USER_TEMPLATES_KEY = 'particle_user_templates'

const communityTemplates = [
  {
    id: 'community-001',
    name: '炫酷火焰爆炸',
    author: 'Community',
    category: 'fire',
    icon: '🔥',
    description: '高强度火焰爆炸效果，适合游戏特效',
    downloads: 1245,
    likes: 892,
    config: {
      particleCount: 200000,
      emissionRate: 50000,
      speed: { min: 3, max: 8 },
      life: { min: 0.3, max: 1 },
      size: { min: 0.3, max: 1.2 },
      color: { start: '#ffff00', end: '#ff0000' },
      direction: { x: 0, y: 1, z: 0 },
      spread: 1.2,
      gravity: { x: 0, y: -2, z: 0 },
      emitterShape: 'sphere',
      emitterRadius: 0.3,
      blending: 'additive'
    }
  },
  {
    id: 'community-002',
    name: '梦幻紫色烟雾',
    author: 'Community',
    category: 'smoke',
    icon: '💜',
    description: '优雅的紫色烟雾，适合魔法效果',
    downloads: 876,
    likes: 654,
    config: {
      particleCount: 100000,
      emissionRate: 5000,
      speed: { min: 0.3, max: 1 },
      life: { min: 3, max: 6 },
      size: { min: 0.8, max: 2 },
      color: { start: '#cc88ff', end: '#440088' },
      direction: { x: 0, y: 1, z: 0 },
      spread: 0.4,
      gravity: { x: 0, y: 0.1, z: 0 },
      emitterShape: 'circle',
      emitterRadius: 0.5,
      blending: 'normal'
    }
  },
  {
    id: 'community-003',
    name: '极光星空',
    author: 'Community',
    category: 'stars',
    icon: '🌌',
    description: '美丽的极光粒子效果',
    downloads: 1567,
    likes: 1123,
    config: {
      particleCount: 300000,
      emissionRate: 30000,
      speed: { min: 0.02, max: 0.1 },
      life: { min: 5, max: 12 },
      size: { min: 0.05, max: 0.15 },
      color: { start: '#00ff88', end: '#0088ff' },
      direction: { x: 0, y: 0, z: 0 },
      spread: 0.1,
      gravity: { x: 0, y: 0, z: 0 },
      emitterShape: 'sphere',
      emitterRadius: 25,
      blending: 'additive'
    }
  },
  {
    id: 'community-004',
    name: '金色雪花',
    author: 'Community',
    category: 'snow',
    icon: '🌟',
    description: '闪闪发光的金色雪花',
    downloads: 789,
    likes: 567,
    config: {
      particleCount: 150000,
      emissionRate: 10000,
      speed: { min: 0.2, max: 0.8 },
      life: { min: 4, max: 8 },
      size: { min: 0.15, max: 0.35 },
      color: { start: '#ffdd00', end: '#ffaa00' },
      direction: { x: 0, y: -1, z: 0 },
      spread: 0.2,
      gravity: { x: 0, y: -0.05, z: 0 },
      emitterShape: 'box',
      emitterRadius: 18,
      blending: 'additive'
    }
  },
  {
    id: 'community-005',
    name: '绿色火焰',
    author: 'Community',
    category: 'fire',
    icon: '💚',
    description: '神秘的绿色火焰',
    downloads: 654,
    likes: 432,
    config: {
      particleCount: 120000,
      emissionRate: 25000,
      speed: { min: 2, max: 6 },
      life: { min: 0.4, max: 1.2 },
      size: { min: 0.2, max: 0.9 },
      color: { start: '#00ff00', end: '#004400' },
      direction: { x: 0, y: 1, z: 0 },
      spread: 0.7,
      gravity: { x: 0, y: -1.5, z: 0 },
      emitterShape: 'circle',
      emitterRadius: 0.4,
      blending: 'additive'
    }
  },
  {
    id: 'community-006',
    name: '彩虹粒子',
    author: 'Community',
    category: 'special',
    icon: '🌈',
    description: '七彩流动粒子效果',
    downloads: 2134,
    likes: 1876,
    config: {
      particleCount: 250000,
      emissionRate: 40000,
      speed: { min: 1, max: 3 },
      life: { min: 1, max: 4 },
      size: { min: 0.15, max: 0.5 },
      color: { start: '#ffffff', end: '#ffffff' },
      direction: { x: 0, y: 1, z: 0 },
      spread: 0.8,
      gravity: { x: 0, y: -0.5, z: 0 },
      emitterShape: 'sphere',
      emitterRadius: 0.5,
      blending: 'additive'
    }
  }
]

export class TemplateMarket {
  constructor() {
    this.templates = [...communityTemplates]
    this.userTemplates = this.loadUserTemplates()
    this.categories = [
      { id: 'all', name: '全部', icon: '🌐' },
      { id: 'fire', name: '火焰', icon: '🔥' },
      { id: 'smoke', name: '烟雾', icon: '💨' },
      { id: 'stars', name: '星空', icon: '✨' },
      { id: 'snow', name: '雪花', icon: '❄️' },
      { id: 'special', name: '特殊', icon: '💫' },
      { id: 'user', name: '我的', icon: '👤' }
    ]
    this.currentCategory = 'all'
    this.searchQuery = ''
    this.sortBy = 'popular'
  }
  
  loadUserTemplates() {
    try {
      const stored = localStorage.getItem(USER_TEMPLATES_KEY)
      return stored ? JSON.parse(stored) : []
    } catch (error) {
      console.error('Failed to load user templates:', error)
      return []
    }
  }
  
  saveUserTemplates() {
    try {
      localStorage.setItem(USER_TEMPLATES_KEY, JSON.stringify(this.userTemplates))
    } catch (error) {
      console.error('Failed to save user templates:', error)
    }
  }
  
  getTemplates() {
    let templates = [...this.templates]
    
    if (this.currentCategory === 'user') {
      templates = [...this.userTemplates]
    } else if (this.currentCategory !== 'all') {
      templates = templates.filter(t => t.category === this.currentCategory)
    }
    
    if (this.searchQuery) {
      const query = this.searchQuery.toLowerCase()
      templates = templates.filter(t => 
        t.name.toLowerCase().includes(query) ||
        t.description.toLowerCase().includes(query)
      )
    }
    
    switch (this.sortBy) {
      case 'popular':
        templates.sort((a, b) => (b.downloads || 0) - (a.downloads || 0))
        break
      case 'latest':
        templates.sort((a, b) => new Date(b.createdAt || 0) - new Date(a.createdAt || 0))
        break
      case 'likes':
        templates.sort((a, b) => (b.likes || 0) - (a.likes || 0))
        break
    }
    
    return templates
  }
  
  getTemplateById(id) {
    return this.templates.find(t => t.id === id) || 
           this.userTemplates.find(t => t.id === id)
  }
  
  getCategories() {
    return this.categories
  }
  
  setCategory(category) {
    this.currentCategory = category
  }
  
  setSearchQuery(query) {
    this.searchQuery = query
  }
  
  setSortBy(sortBy) {
    this.sortBy = sortBy
  }
  
  saveUserTemplate(name, config, description = '') {
    const template = {
      id: `user-${Date.now()}`,
      name,
      author: 'Me',
      category: 'user',
      icon: '🎨',
      description,
      downloads: 0,
      likes: 0,
      createdAt: new Date().toISOString(),
      config: JSON.parse(JSON.stringify(config))
    }
    
    this.userTemplates.unshift(template)
    this.saveUserTemplates()
    
    return template
  }
  
  deleteUserTemplate(id) {
    const index = this.userTemplates.findIndex(t => t.id === id)
    if (index !== -1) {
      this.userTemplates.splice(index, 1)
      this.saveUserTemplates()
      return true
    }
    return false
  }
  
  downloadTemplate(template) {
    const filename = `template-${template.name.toLowerCase().replace(/\s+/g, '-')}-${Date.now()}.json`
    downloadConfig(template.config, filename, {
      name: template.name,
      author: template.author,
      description: template.description
    })
    
    if (!template.id.startsWith('user-')) {
      template.downloads = (template.downloads || 0) + 1
    }
  }
  
  likeTemplate(template) {
    if (!template.id.startsWith('user-')) {
      template.likes = (template.likes || 0) + 1
    }
  }
  
  async importTemplateFromFile(file) {
    try {
      const result = await loadConfigFromFile(file)
      return {
        id: `user-${Date.now()}`,
        name: file.name.replace('.json', ''),
        author: 'Imported',
        category: 'user',
        icon: '📁',
        description: '从文件导入',
        createdAt: new Date().toISOString(),
        config: result.data
      }
    } catch (error) {
      throw new Error('导入失败: ' + error.message)
    }
  }
  
  exportTemplate(template) {
    return exportConfig(template.config, {
      name: template.name,
      author: template.author,
      description: template.description,
      templateId: template.id
    })
  }
  
  shareTemplate(template) {
    const shareData = {
      title: template.name,
      text: template.description,
      url: `https://particle-editor.app/template/${template.id}`
    }
    
    if (navigator.share) {
      return navigator.share(shareData)
    }
    
    return Promise.resolve({ ...shareData, shared: true })
  }
}
