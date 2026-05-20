export const TemplateType = {
  INTRO: 'intro',
  OUTRO: 'outro',
  TRANSITION: 'transition',
  LOWER_THIRD: 'lower_third',
  FILTER: 'filter',
}

export const TemplateCategory = {
  BUSINESS: 'business',
  SOCIAL_MEDIA: 'social_media',
  EDUCATION: 'education',
  ENTERTAINMENT: 'entertainment',
  TECHNOLOGY: 'technology',
  PERSONAL: 'personal',
}

const defaultTemplates = [
  {
    id: 'intro_tech_01',
    name: '科技感片头',
    type: TemplateType.INTRO,
    category: TemplateCategory.TECHNOLOGY,
    duration: 3,
    thumbnail: '🎬',
    description: '现代科技风格，适合产品介绍和技术分享',
    effects: [
      { type: 'fade_in', duration: 0.5 },
      { type: 'text_animation', text: '科技片头', style: { fontSize: 72, color: '#00d4ff', fontFamily: 'Orbitron, sans-serif' } },
      { type: 'particle_effect', count: 50 },
      { type: 'fade_out', duration: 0.5 },
    ],
    colorScheme: { primary: '#00d4ff', secondary: '#0066ff', background: '#0a0a1a' },
  },
  {
    id: 'intro_business_01',
    name: '商务简洁片头',
    type: TemplateType.INTRO,
    category: TemplateCategory.BUSINESS,
    duration: 2.5,
    thumbnail: '💼',
    description: '简洁专业的商务风格，适合企业宣传片',
    effects: [
      { type: 'slide_in', direction: 'left', duration: 0.6 },
      { type: 'text_animation', text: '商务标题', style: { fontSize: 56, color: '#2c3e50', fontFamily: 'Montserrat, sans-serif' } },
      { type: 'line_animation', position: 'bottom' },
      { type: 'fade_out', duration: 0.3 },
    ],
    colorScheme: { primary: '#2c3e50', secondary: '#3498db', background: '#ffffff' },
  },
  {
    id: 'intro_social_01',
    name: '社交媒体片头',
    type: TemplateType.INTRO,
    category: TemplateCategory.SOCIAL_MEDIA,
    duration: 2,
    thumbnail: '📱',
    description: '活泼动感，适合短视频和社交平台',
    effects: [
      { type: 'zoom_in', duration: 0.4 },
      { type: 'text_animation', text: '精彩内容', style: { fontSize: 64, color: '#ff6b6b', fontFamily: 'Poppins, sans-serif' } },
      { type: 'sticker_effect', emoji: '✨' },
      { type: 'bounce_out', duration: 0.3 },
    ],
    colorScheme: { primary: '#ff6b6b', secondary: '#feca57', background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' },
  },
  {
    id: 'outro_tech_01',
    name: '科技感片尾',
    type: TemplateType.OUTRO,
    category: TemplateCategory.TECHNOLOGY,
    duration: 3,
    thumbnail: '🔚',
    description: '带有订阅按钮和关注提示的科技片尾',
    effects: [
      { type: 'fade_in', duration: 0.5 },
      { type: 'text_animation', text: '感谢观看', style: { fontSize: 64, color: '#00d4ff', fontFamily: 'Orbitron, sans-serif' } },
      { type: 'subscribe_button', text: '订阅关注' },
      { type: 'qr_code_placeholder' },
      { type: 'social_icons', platforms: ['youtube', 'twitter', 'github'] },
    ],
    colorScheme: { primary: '#00d4ff', secondary: '#00ff88', background: '#0a0a1a' },
  },
  {
    id: 'outro_business_01',
    name: '商务片尾',
    type: TemplateType.OUTRO,
    category: TemplateCategory.BUSINESS,
    duration: 2.5,
    thumbnail: '📋',
    description: '专业的结束画面，包含联系方式',
    effects: [
      { type: 'slide_in', direction: 'right', duration: 0.5 },
      { type: 'text_animation', text: '谢谢观看', style: { fontSize: 48, color: '#2c3e50', fontFamily: 'Montserrat, sans-serif' } },
      { type: 'contact_info', email: 'contact@example.com', website: 'www.example.com' },
      { type: 'fade_out', duration: 0.5 },
    ],
    colorScheme: { primary: '#2c3e50', secondary: '#27ae60', background: '#f8f9fa' },
  },
  {
    id: 'outro_social_01',
    name: '互动片尾',
    type: TemplateType.OUTRO,
    category: TemplateCategory.SOCIAL_MEDIA,
    duration: 2,
    thumbnail: '💬',
    description: '引导点赞评论的互动片尾',
    effects: [
      { type: 'bounce_in', duration: 0.4 },
      { type: 'text_animation', text: '点赞 收藏 关注', style: { fontSize: 48, color: '#ff6b6b', fontFamily: 'Poppins, sans-serif' } },
      { type: 'emoji_rain', emojis: ['👍', '❤️', '⭐', '🔔'] },
      { type: 'fade_out', duration: 0.3 },
    ],
    colorScheme: { primary: '#ff6b6b', secondary: '#48dbfb', background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)' },
  },
  {
    id: 'lower_third_news_01',
    name: '新闻字幕条',
    type: TemplateType.LOWER_THIRD,
    category: TemplateCategory.EDUCATION,
    duration: 5,
    thumbnail: '📰',
    description: '专业新闻风格的底部字幕条',
    effects: [
      { type: 'slide_in', direction: 'left', duration: 0.4 },
      { type: 'lower_third', title: '标题文字', subtitle: '副标题说明' },
      { type: 'logo_placeholder', position: 'left' },
      { type: 'slide_out', direction: 'left', duration: 0.3 },
    ],
    colorScheme: { primary: '#e74c3c', secondary: '#2c3e50', background: 'rgba(44, 62, 80, 0.9)' },
  },
  {
    id: 'transition_glitch_01',
    name: '故障转场',
    type: TemplateType.TRANSITION,
    category: TemplateCategory.ENTERTAINMENT,
    duration: 0.5,
    thumbnail: '⚡',
    description: '赛博朋克风格的故障艺术转场',
    effects: [
      { type: 'glitch_effect', intensity: 0.8 },
      { type: 'rgb_split', duration: 0.3 },
      { type: 'static_noise', amount: 0.3 },
    ],
    colorScheme: { primary: '#ff00ff', secondary: '#00ffff', background: '#000000' },
  },
  {
    id: 'filter_cinematic_01',
    name: '电影滤镜',
    type: TemplateType.FILTER,
    category: TemplateCategory.ENTERTAINMENT,
    duration: 0,
    thumbnail: '🎞️',
    description: '经典电影色调，增加胶片质感',
    effects: [
      { type: 'color_grading', contrast: 1.1, saturation: 0.9, brightness: 1.05 },
      { type: 'vignette', amount: 0.3 },
      { type: 'film_grain', amount: 0.1 },
    ],
    colorScheme: { primary: '#8b4513', secondary: '#daa520', background: null },
  },
  {
    id: 'filter_vintage_01',
    name: '复古滤镜',
    type: TemplateType.FILTER,
    category: TemplateCategory.PERSONAL,
    duration: 0,
    thumbnail: '📷',
    description: '80年代复古胶片效果',
    effects: [
      { type: 'color_grading', contrast: 0.9, saturation: 0.7, brightness: 1.0, sepia: 0.3 },
      { type: 'vignette', amount: 0.4 },
      { type: 'film_grain', amount: 0.15 },
      { type: 'flicker', speed: 0.1 },
    ],
    colorScheme: { primary: '#d4a574', secondary: '#8b7355', background: null },
  },
]

class TemplateLibrary {
  constructor() {
    this.templates = [...defaultTemplates]
    this.categories = Object.values(TemplateCategory)
    this.types = Object.values(TemplateType)
    this.favorites = new Set()
    this.recentlyUsed = []
  }

  getTemplates(options = {}) {
    let result = [...this.templates]
    
    if (options.type) {
      result = result.filter(t => t.type === options.type)
    }
    
    if (options.category) {
      result = result.filter(t => t.category === options.category)
    }
    
    if (options.search) {
      const keyword = options.search.toLowerCase()
      result = result.filter(t => 
        t.name.toLowerCase().includes(keyword) ||
        t.description.toLowerCase().includes(keyword)
      )
    }
    
    if (options.favoritesOnly) {
      result = result.filter(t => this.favorites.has(t.id))
    }
    
    if (options.recentOnly) {
      result = this.recentlyUsed
        .filter(id => result.some(t => t.id === id))
        .map(id => result.find(t => t.id === id))
    }
    
    return result
  }

  getTemplateById(id) {
    return this.templates.find(t => t.id === id)
  }

  getIntroTemplates(options = {}) {
    return this.getTemplates({ ...options, type: TemplateType.INTRO })
  }

  getOutroTemplates(options = {}) {
    return this.getTemplates({ ...options, type: TemplateType.OUTRO })
  }

  getTransitionTemplates(options = {}) {
    return this.getTemplates({ ...options, type: TemplateType.TRANSITION })
  }

  getLowerThirdTemplates(options = {}) {
    return this.getTemplates({ ...options, type: TemplateType.LOWER_THIRD })
  }

  getFilterTemplates(options = {}) {
    return this.getTemplates({ ...options, type: TemplateType.FILTER })
  }

  async applyTemplate(templateId, targetClip, position = 'start') {
    const template = this.getTemplateById(templateId)
    if (!template) {
      throw new Error(`模板不存在: ${templateId}`)
    }
    
    this._markAsUsed(templateId)
    
    return {
      template,
      targetClip,
      position,
      appliedAt: Date.now(),
    }
  }

  async applyIntro(templateId, clip) {
    const result = await this.applyTemplate(templateId, clip, 'start')
    
    return {
      ...result,
      generateFFmpegFilter: () => {
        const template = result.template
        const filters = []
        
        const bgColor = template.colorScheme.background.startsWith('linear-gradient') 
          ? '#000000' 
          : template.colorScheme.background
        
        filters.push(
          `color=c=${bgColor.replace('#', '')}:s=1920x1080:d=${template.duration}[bg]`
        )
        
        const textColor = template.colorScheme.primary.replace('#', '')
        filters.push(
          `[bg]drawtext=text='${template.name}':fontsize=72:fontcolor=${textColor}:` +
          `x=(w-text_w)/2:y=(h-text_h)/2:enable='between(t,0,${template.duration})'[intro]`
        )
        
        return filters
      },
    }
  }

  async applyOutro(templateId, clip) {
    const result = await this.applyTemplate(templateId, clip, 'end')
    
    return {
      ...result,
      generateFFmpegFilter: () => {
        const template = result.template
        const filters = []
        
        const bgColor = template.colorScheme.background.startsWith('linear-gradient') 
          ? '#000000' 
          : template.colorScheme.background
        
        filters.push(
          `color=c=${bgColor.replace('#', '')}:s=1920x1080:d=${template.duration}[outro_bg]`
        )
        
        const textColor = template.colorScheme.primary.replace('#', '')
        filters.push(
          `[outro_bg]drawtext=text='感谢观看':fontsize=64:fontcolor=${textColor}:` +
          `x=(w-text_w)/2:y=(h-text_h)/2-50[outro_text]`
        )
        
        filters.push(
          `[outro_text]drawtext=text='订阅关注':fontsize=36:fontcolor=${textColor}:` +
          `x=(w-text_w)/2:y=(h-text_h)/2+50[outro]`
        )
        
        return filters
      },
    }
  }

  async applyFilter(templateId, clips) {
    const template = this.getTemplateById(templateId)
    if (!template || template.type !== TemplateType.FILTER) {
      throw new Error(`滤镜模板不存在: ${templateId}`)
    }
    
    this._markAsUsed(templateId)
    
    return {
      template,
      clips,
      appliedAt: Date.now(),
      generateFFmpegFilter: () => {
        const effects = template.effects
        const filters = []
        
        for (const effect of effects) {
          if (effect.type === 'color_grading') {
            const params = []
            if (effect.contrast !== undefined) params.push(`contrast=${effect.contrast}`)
            if (effect.saturation !== undefined) params.push(`saturation=${effect.saturation}`)
            if (effect.brightness !== undefined) params.push(`brightness=${effect.brightness}`)
            if (effect.sepia !== undefined) params.push(`colorchannelmixer=.393:.769:.189:0:.349:.686:.168:0:.272:.534:.131`)
            
            if (params.length > 0) {
              filters.push(`eq=${params.join(':')}`)
            }
          }
          
          if (effect.type === 'vignette') {
            filters.push(`vignette=a=${effect.amount}`)
          }
        }
        
        return filters
      },
    }
  }

  addTemplate(template) {
    if (!template.id) {
      template.id = `custom_${Date.now().toString(36)}`
    }
    
    if (this.getTemplateById(template.id)) {
      throw new Error(`模板ID已存在: ${template.id}`)
    }
    
    this.templates.push(template)
    return template
  }

  updateTemplate(id, updates) {
    const index = this.templates.findIndex(t => t.id === id)
    if (index === -1) {
      throw new Error(`模板不存在: ${id}`)
    }
    
    this.templates[index] = { ...this.templates[index], ...updates }
    return this.templates[index]
  }

  deleteTemplate(id) {
    const index = this.templates.findIndex(t => t.id === id)
    if (index === -1) {
      throw new Error(`模板不存在: ${id}`)
    }
    
    this.templates.splice(index, 1)
    this.favorites.delete(id)
    this.recentlyUsed = this.recentlyUsed.filter(rid => rid !== id)
  }

  toggleFavorite(templateId) {
    if (this.favorites.has(templateId)) {
      this.favorites.delete(templateId)
      return false
    } else {
      this.favorites.add(templateId)
      return true
    }
  }

  isFavorite(templateId) {
    return this.favorites.has(templateId)
  }

  getFavorites() {
    return Array.from(this.favorites).map(id => this.getTemplateById(id)).filter(Boolean)
  }

  getRecentlyUsed(limit = 10) {
    return this.recentlyUsed
      .slice(0, limit)
      .map(id => this.getTemplateById(id))
      .filter(Boolean)
  }

  _markAsUsed(templateId) {
    this.recentlyUsed = this.recentlyUsed.filter(id => id !== templateId)
    this.recentlyUsed.unshift(templateId)
    if (this.recentlyUsed.length > 20) {
      this.recentlyUsed = this.recentlyUsed.slice(0, 20)
    }
  }

  exportTemplates(ids = null) {
    const templatesToExport = ids 
      ? ids.map(id => this.getTemplateById(id)).filter(Boolean)
      : this.templates
    
    return JSON.stringify(templatesToExport, null, 2)
  }

  importTemplates(jsonString) {
    try {
      const imported = JSON.parse(jsonString)
      
      if (!Array.isArray(imported)) {
        throw new Error('导入数据格式错误')
      }
      
      for (const template of imported) {
        try {
          this.addTemplate(template)
        } catch (e) {
          console.warn(`跳过已有模板: ${template.id}`)
        }
      }
      
      return imported.length
    } catch (error) {
      console.error('模板导入失败:', error)
      throw error
    }
  }

  getCategories() {
    return this.categories.map(cat => ({
      id: cat,
      name: this._getCategoryName(cat),
      count: this.templates.filter(t => t.category === cat).length,
    }))
  }

  getTypes() {
    return this.types.map(type => ({
      id: type,
      name: this._getTypeName(type),
      count: this.templates.filter(t => t.type === type).length,
    }))
  }

  _getCategoryName(category) {
    const names = {
      [TemplateCategory.BUSINESS]: '商务',
      [TemplateCategory.SOCIAL_MEDIA]: '社交媒体',
      [TemplateCategory.EDUCATION]: '教育',
      [TemplateCategory.ENTERTAINMENT]: '娱乐',
      [TemplateCategory.TECHNOLOGY]: '科技',
      [TemplateCategory.PERSONAL]: '个人',
    }
    return names[category] || category
  }

  _getTypeName(type) {
    const names = {
      [TemplateType.INTRO]: '片头',
      [TemplateType.OUTRO]: '片尾',
      [TemplateType.TRANSITION]: '转场',
      [TemplateType.LOWER_THIRD]: '字幕条',
      [TemplateType.FILTER]: '滤镜',
    }
    return names[type] || type
  }

  getStats() {
    return {
      total: this.templates.length,
      byType: this.types.reduce((acc, type) => {
        acc[type] = this.templates.filter(t => t.type === type).length
        return acc
      }, {}),
      byCategory: this.categories.reduce((acc, cat) => {
        acc[cat] = this.templates.filter(t => t.category === cat).length
        return acc
      }, {}),
      favorites: this.favorites.size,
      recentlyUsed: this.recentlyUsed.length,
    }
  }

  dispose() {
    this.templates = [...defaultTemplates]
    this.favorites.clear()
    this.recentlyUsed = []
  }
}

export default TemplateLibrary
