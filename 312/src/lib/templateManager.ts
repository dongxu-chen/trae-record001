import { AnimationTemplate, AnimationTrackTemplate, Layer } from '@/types'
import { nanoid } from 'nanoid'

export const defaultTemplates: AnimationTemplate[] = [
  {
    id: 'template-bounce-1',
    name: '活泼弹跳',
    description: '经典的弹跳动画效果，让图标更有活力',
    author: '系统',
    createdAt: Date.now() - 86400000 * 30,
    updatedAt: Date.now() - 86400000 * 30,
    likes: 128,
    downloads: 1024,
    isPublic: true,
    tags: ['弹跳', '活泼', '通用'],
    category: '基础动画',
    animation: {
      duration: 1000,
      framerate: 60,
      targetElements: ['*'],
      tracks: [
        {
          property: 'position.y',
          keyframes: [
            { time: 0, value: 0, easing: 'easeOutCubic' },
            { time: 500, value: -30, easing: 'easeInCubic' },
            { time: 1000, value: 0, easing: 'easeOutBounce' },
          ],
        },
        {
          property: 'scale.y',
          keyframes: [
            { time: 0, value: 1, easing: 'easeOut' },
            { time: 450, value: 1.1, easing: 'easeIn' },
            { time: 550, value: 0.9, easing: 'easeOut' },
            { time: 1000, value: 1, easing: 'easeOut' },
          ],
        },
      ],
    },
  },
  {
    id: 'template-pulse-1',
    name: '呼吸脉冲',
    description: '柔和的缩放动画，模拟呼吸效果',
    author: '系统',
    createdAt: Date.now() - 86400000 * 25,
    updatedAt: Date.now() - 86400000 * 25,
    likes: 256,
    downloads: 2048,
    isPublic: true,
    tags: ['脉冲', '呼吸', '循环'],
    category: '基础动画',
    animation: {
      duration: 1500,
      framerate: 60,
      targetElements: ['*'],
      tracks: [
        {
          property: 'scale.x',
          keyframes: [
            { time: 0, value: 1, easing: 'easeInOutCubic' },
            { time: 750, value: 1.15, easing: 'easeInOutCubic' },
            { time: 1500, value: 1, easing: 'easeInOutCubic' },
          ],
        },
        {
          property: 'scale.y',
          keyframes: [
            { time: 0, value: 1, easing: 'easeInOutCubic' },
            { time: 750, value: 1.15, easing: 'easeInOutCubic' },
            { time: 1500, value: 1, easing: 'easeInOutCubic' },
          ],
        },
      ],
    },
  },
  {
    id: 'template-spin-1',
    name: '优雅旋转',
    description: '匀速旋转动画，适合加载状态',
    author: '系统',
    createdAt: Date.now() - 86400000 * 20,
    updatedAt: Date.now() - 86400000 * 20,
    likes: 89,
    downloads: 768,
    isPublic: true,
    tags: ['旋转', '加载', '循环'],
    category: '加载动画',
    animation: {
      duration: 1000,
      framerate: 60,
      targetElements: ['*'],
      tracks: [
        {
          property: 'rotation',
          keyframes: [
            { time: 0, value: 0, easing: 'linear' },
            { time: 1000, value: 360, easing: 'linear' },
          ],
        },
      ],
    },
  },
  {
    id: 'template-heartbeat-1',
    name: '心跳节奏',
    description: '模拟心跳的动画效果，适合收藏、喜欢按钮',
    author: '系统',
    createdAt: Date.now() - 86400000 * 15,
    updatedAt: Date.now() - 86400000 * 15,
    likes: 312,
    downloads: 1536,
    isPublic: true,
    tags: ['心跳', '喜欢', '收藏'],
    category: '情感动画',
    animation: {
      duration: 1000,
      framerate: 60,
      targetElements: ['*'],
      tracks: [
        {
          property: 'scale.x',
          keyframes: [
            { time: 0, value: 1, easing: 'easeOut' },
            { time: 150, value: 1.1, easing: 'easeIn' },
            { time: 300, value: 1, easing: 'easeOut' },
            { time: 450, value: 1.15, easing: 'easeIn' },
            { time: 600, value: 1, easing: 'easeOut' },
            { time: 1000, value: 1, easing: 'linear' },
          ],
        },
        {
          property: 'scale.y',
          keyframes: [
            { time: 0, value: 1, easing: 'easeOut' },
            { time: 150, value: 1.1, easing: 'easeIn' },
            { time: 300, value: 1, easing: 'easeOut' },
            { time: 450, value: 1.15, easing: 'easeIn' },
            { time: 600, value: 1, easing: 'easeOut' },
            { time: 1000, value: 1, easing: 'linear' },
          ],
        },
      ],
    },
  },
  {
    id: 'template-shake-1',
    name: '抖动提醒',
    description: '左右抖动效果，适合错误提示或提醒',
    author: '系统',
    createdAt: Date.now() - 86400000 * 10,
    updatedAt: Date.now() - 86400000 * 10,
    likes: 67,
    downloads: 512,
    isPublic: true,
    tags: ['抖动', '提醒', '错误'],
    category: '反馈动画',
    animation: {
      duration: 500,
      framerate: 60,
      targetElements: ['*'],
      tracks: [
        {
          property: 'position.x',
          keyframes: [
            { time: 0, value: 0, easing: 'easeInOut' },
            { time: 50, value: -5, easing: 'easeInOut' },
            { time: 100, value: 5, easing: 'easeInOut' },
            { time: 150, value: -5, easing: 'easeInOut' },
            { time: 200, value: 5, easing: 'easeInOut' },
            { time: 250, value: -2.5, easing: 'easeInOut' },
            { time: 300, value: 2.5, easing: 'easeInOut' },
            { time: 350, value: -1.25, easing: 'easeInOut' },
            { time: 400, value: 1.25, easing: 'easeInOut' },
            { time: 500, value: 0, easing: 'easeOut' },
          ],
        },
      ],
    },
  },
  {
    id: 'template-float-1',
    name: '轻盈漂浮',
    description: '上下漂浮效果，营造轻盈感',
    author: '系统',
    createdAt: Date.now() - 86400000 * 5,
    updatedAt: Date.now() - 86400000 * 5,
    likes: 178,
    downloads: 896,
    isPublic: true,
    tags: ['漂浮', '轻盈', '优雅'],
    category: '基础动画',
    animation: {
      duration: 2000,
      framerate: 60,
      targetElements: ['*'],
      tracks: [
        {
          property: 'position.y',
          keyframes: [
            { time: 0, value: 0, easing: 'easeInOutCubic' },
            { time: 1000, value: -15, easing: 'easeInOutCubic' },
            { time: 2000, value: 0, easing: 'easeInOutCubic' },
          ],
        },
      ],
    },
  },
  {
    id: 'template-wiggle-1',
    name: '趣味摇摆',
    description: '左右摇摆效果，增添趣味性',
    author: '系统',
    createdAt: Date.now() - 86400000 * 2,
    updatedAt: Date.now() - 86400000 * 2,
    likes: 95,
    downloads: 448,
    isPublic: true,
    tags: ['摇摆', '趣味', '活泼'],
    category: '趣味动画',
    animation: {
      duration: 1000,
      framerate: 60,
      targetElements: ['*'],
      tracks: [
        {
          property: 'rotation',
          keyframes: [
            { time: 0, value: 0, easing: 'easeInOut' },
            { time: 250, value: -10, easing: 'easeInOut' },
            { time: 500, value: 10, easing: 'easeInOut' },
            { time: 750, value: -5, easing: 'easeInOut' },
            { time: 1000, value: 0, easing: 'easeOut' },
          ],
        },
      ],
    },
  },
  {
    id: 'template-ripple-1',
    name: '涟漪扩散',
    description: '从中心向外扩散的涟漪效果',
    author: '系统',
    createdAt: Date.now() - 86400000,
    updatedAt: Date.now() - 86400000,
    likes: 156,
    downloads: 672,
    isPublic: true,
    tags: ['涟漪', '扩散', '特效'],
    category: '特效动画',
    animation: {
      duration: 1500,
      framerate: 60,
      targetElements: ['*'],
      tracks: [
        {
          property: 'scale.x',
          keyframes: [
            { time: 0, value: 0.8, easing: 'easeOut' },
            { time: 1500, value: 1.5, easing: 'easeOut' },
          ],
        },
        {
          property: 'scale.y',
          keyframes: [
            { time: 0, value: 0.8, easing: 'easeOut' },
            { time: 1500, value: 1.5, easing: 'easeOut' },
          ],
        },
        {
          property: 'opacity',
          keyframes: [
            { time: 0, value: 1, easing: 'linear' },
            { time: 1500, value: 0, easing: 'linear' },
          ],
        },
      ],
    },
  },
]

export class TemplateManager {
  private templates: AnimationTemplate[] = []

  constructor() {
    this.templates = [...defaultTemplates]
    this.loadFromStorage()
  }

  private loadFromStorage(): void {
    try {
      const stored = localStorage.getItem('animationTemplates')
      if (stored) {
        const customTemplates = JSON.parse(stored)
        this.templates = [...this.templates, ...customTemplates]
      }
    } catch (e) {
      console.error('Failed to load templates:', e)
    }
  }

  private saveToStorage(): void {
    try {
      const customTemplates = this.templates.filter((t) => !t.id.startsWith('template-'))
      localStorage.setItem('animationTemplates', JSON.stringify(customTemplates))
    } catch (e) {
      console.error('Failed to save templates:', e)
    }
  }

  getAll(): AnimationTemplate[] {
    return this.templates.sort((a, b) => b.likes - a.likes)
  }

  getById(id: string): AnimationTemplate | undefined {
    return this.templates.find((t) => t.id === id)
  }

  search(query: string): AnimationTemplate[] {
    const lowerQuery = query.toLowerCase()
    return this.templates.filter(
      (t) =>
        t.name.toLowerCase().includes(lowerQuery) ||
        t.description.toLowerCase().includes(lowerQuery) ||
        t.tags.some((tag) => tag.toLowerCase().includes(lowerQuery)) ||
        t.category.toLowerCase().includes(lowerQuery)
    )
  }

  getByCategory(category: string): AnimationTemplate[] {
    return this.templates.filter((t) => t.category === category)
  }

  getCategories(): string[] {
    return [...new Set(this.templates.map((t) => t.category))]
  }

  createTemplate(
    name: string,
    description: string,
    layers: Layer[],
    duration: number,
    framerate: number,
    tags: string[],
    category: string
  ): AnimationTemplate {
    const targetElements: string[] = []
    const allTracks: AnimationTrackTemplate[] = []

    layers.forEach((layer) => {
      targetElements.push(layer.name)
      layer.tracks.forEach((track) => {
        const existingTrack = allTracks.find((t) => t.property === track.property)
        if (!existingTrack) {
          allTracks.push({
            property: track.property,
            keyframes: track.keyframes.map((kf) => ({
              time: kf.time,
              value: kf.value as number | { x: number; y: number },
              easing: kf.easing,
            })),
          })
        }
      })
    })

    const template: AnimationTemplate = {
      id: `custom-${nanoid()}`,
      name,
      description,
      author: '我',
      createdAt: Date.now(),
      updatedAt: Date.now(),
      likes: 0,
      downloads: 0,
      isPublic: false,
      tags,
      category,
      animation: {
        duration,
        framerate,
        targetElements,
        tracks: allTracks,
      },
    }

    this.templates.push(template)
    this.saveToStorage()
    return template
  }

  likeTemplate(id: string): void {
    const template = this.templates.find((t) => t.id === id)
    if (template) {
      template.likes++
      this.saveToStorage()
    }
  }

  incrementDownload(id: string): void {
    const template = this.templates.find((t) => t.id === id)
    if (template) {
      template.downloads++
      this.saveToStorage()
    }
  }

  deleteTemplate(id: string): boolean {
    const index = this.templates.findIndex((t) => t.id === id)
    if (index > -1 && !id.startsWith('template-')) {
      this.templates.splice(index, 1)
      this.saveToStorage()
      return true
    }
    return false
  }

  exportTemplate(id: string): string | null {
    const template = this.getById(id)
    if (!template) return null
    return JSON.stringify(template, null, 2)
  }

  importTemplate(json: string): AnimationTemplate | null {
    try {
      const template = JSON.parse(json) as AnimationTemplate
      template.id = `imported-${nanoid()}`
      template.author = '导入'
      template.createdAt = Date.now()
      template.updatedAt = Date.now()
      template.likes = 0
      template.downloads = 0
      this.templates.push(template)
      this.saveToStorage()
      return template
    } catch (e) {
      console.error('Failed to import template:', e)
      return null
    }
  }
}

export const templateManager = new TemplateManager()
