import express from 'express'
import cors from 'cors'
import path from 'path'
import { fileURLToPath } from 'url'
import DOMPurify from 'dompurify'
import { JSDOM } from 'jsdom'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

const app = express()
const PORT = process.env.PORT || 3001

app.use(cors())
app.use(express.json())

const window = new JSDOM('').window
const purify = DOMPurify(window)

const SVG_COLOR_PROPERTIES = [
  'fill',
  'stroke',
  'stop-color',
  'flood-color',
  'lighting-color',
  'color',
]

function sanitizeSvgServer(svgContent: string): {
  clean: string
  warnings: string[]
  removedElements: string[]
} {
  const warnings: string[] = []
  const removedElements: string[] = []

  const dom = new JSDOM(svgContent)
  const svg = dom.window.document.querySelector('svg')

  if (svg) {
    const dangerousElements = svg.querySelectorAll('script, iframe, foreignObject')
    dangerousElements.forEach((el) => {
      removedElements.push(el.tagName.toLowerCase())
      el.remove()
    })

    const allElements = svg.querySelectorAll('*')
    allElements.forEach((el) => {
      Array.from(el.attributes).forEach((attr) => {
        if (attr.name.startsWith('on')) {
          el.removeAttribute(attr.name)
          warnings.push(`Removed event handler: ${attr.name}`)
        }
        if (attr.value.includes('javascript:')) {
          el.removeAttribute(attr.name)
          warnings.push(`Removed javascript URL in: ${attr.name}`)
        }
      })
    })
  }

  const clean = purify.sanitize(svgContent, {
    USE_PROFILES: { svg: true, svgFilters: true },
    ADD_TAGS: ['svg', 'path', 'g', 'circle', 'rect', 'ellipse', 'line', 'polyline', 'polygon', 'defs', 'filter', 'linearGradient', 'radialGradient', 'stop', 'clipPath', 'use', 'mask', 'pattern', 'symbol', 'marker', 'title', 'desc'],
    ADD_ATTR: ['viewBox', 'd', 'cx', 'cy', 'r', 'x', 'y', 'width', 'height', 'x1', 'y1', 'x2', 'y2', 'points', 'fill', 'stroke', 'stroke-width', 'stroke-linecap', 'stroke-linejoin', 'transform', 'opacity', 'fill-opacity', 'stroke-opacity', 'id', 'class', 'href', 'xlink:href', 'offset', 'stop-color', 'stop-opacity', 'clip-path', 'filter', 'mask', 'patternUnits', 'patternContentUnits', 'preserveAspectRatio', 'marker-end', 'marker-start', 'marker-mid'],
    FORBID_TAGS: ['script', 'iframe', 'foreignObject'],
    FORBID_ATTR: ['onload', 'onclick', 'onmouseover', 'onerror', 'style'],
  })

  if (removedElements.length > 0) {
    warnings.push(`Removed dangerous elements: ${removedElements.join(', ')}`)
  }

  return { clean, warnings, removedElements }
}

function extractOriginalColor(svgContent: string): string {
  const dom = new JSDOM(svgContent)
  const allElements = dom.window.document.querySelectorAll('*')
  
  for (const el of Array.from(allElements)) {
    for (const prop of SVG_COLOR_PROPERTIES) {
      const value = el.getAttribute(prop)
      if (value && value !== 'none' && value !== 'transparent') {
        if (value.startsWith('#') || value.startsWith('rgb') || value.startsWith('hsl')) {
          return value
        }
      }
    }
  }
  
  return '#000000'
}

interface User {
  id: string
  email: string
  name: string
  passwordHash: string
  role: 'admin' | 'editor' | 'viewer'
  createdAt: string
}

interface Category {
  id: string
  name: string
  parentId: string | null
  order: number
  createdAt: string
  _count: { icons: number }
}

interface IconVersion {
  id: string
  iconId: string
  version: number
  svgContent: string
  name: string
  tags: string[]
  createdAt: string
  createdBy: string
  note?: string
}

interface IconAnalytics {
  iconId: string
  downloadCount: number
  viewCount: number
  exportCount: number
  lastDownloadedAt?: string
  lastViewedAt?: string
}

interface Icon {
  id: string
  name: string
  svgContent: string
  categoryId: string | null
  tags: string[]
  originalColor: string
  filePath: string
  createdById: string
  createdAt: string
  updatedAt: string
  version: number
  versions: IconVersion[]
  analytics: IconAnalytics
}

const mockUsers: User[] = [
  {
    id: 'user-1',
    email: 'admin@example.com',
    name: '管理员',
    passwordHash: 'password123',
    role: 'admin',
    createdAt: '2024-01-01T00:00:00.000Z',
  },
]

const sampleIcons: Icon[] = [
  {
    id: 'icon-1',
    name: 'home',
    svgContent: '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>',
    categoryId: 'cat-1',
    tags: ['navigation', 'home', 'house'],
    originalColor: '#000000',
    filePath: '/icons/home.svg',
    createdById: 'user-1',
    createdAt: '2024-01-15T10:00:00.000Z',
    updatedAt: '2024-01-15T10:00:00.000Z',
    version: 1,
    versions: [{
      id: 'ver-1-1',
      iconId: 'icon-1',
      version: 1,
      svgContent: '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>',
      name: 'home',
      tags: ['navigation', 'home', 'house'],
      createdAt: '2024-01-15T10:00:00.000Z',
      createdBy: 'user-1',
      note: '初始版本',
    }],
    analytics: {
      iconId: 'icon-1',
      downloadCount: 156,
      viewCount: 423,
      exportCount: 45,
      lastDownloadedAt: '2024-01-20T10:00:00.000Z',
      lastViewedAt: '2024-01-21T08:00:00.000Z',
    },
  },
  {
    id: 'icon-2',
    name: 'settings',
    svgContent: '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/></svg>',
    categoryId: 'cat-1',
    tags: ['settings', 'gear', 'configuration'],
    originalColor: '#000000',
    filePath: '/icons/settings.svg',
    createdById: 'user-1',
    createdAt: '2024-01-16T11:00:00.000Z',
    updatedAt: '2024-01-16T11:00:00.000Z',
    version: 1,
    versions: [{
      id: 'ver-2-1',
      iconId: 'icon-2',
      version: 1,
      svgContent: '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/></svg>',
      name: 'settings',
      tags: ['settings', 'gear', 'configuration'],
      createdAt: '2024-01-16T11:00:00.000Z',
      createdBy: 'user-1',
      note: '初始版本',
    }],
    analytics: {
      iconId: 'icon-2',
      downloadCount: 89,
      viewCount: 267,
      exportCount: 23,
      lastDownloadedAt: '2024-01-19T15:00:00.000Z',
      lastViewedAt: '2024-01-20T12:00:00.000Z',
    },
  },
  {
    id: 'icon-3',
    name: 'user',
    svgContent: '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>',
    categoryId: 'cat-2',
    tags: ['user', 'profile', 'person'],
    originalColor: '#000000',
    filePath: '/icons/user.svg',
    createdById: 'user-1',
    createdAt: '2024-01-17T12:00:00.000Z',
    updatedAt: '2024-01-17T12:00:00.000Z',
    version: 1,
    versions: [{
      id: 'ver-3-1',
      iconId: 'icon-3',
      version: 1,
      svgContent: '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>',
      name: 'user',
      tags: ['user', 'profile', 'person'],
      createdAt: '2024-01-17T12:00:00.000Z',
      createdBy: 'user-1',
      note: '初始版本',
    }],
    analytics: {
      iconId: 'icon-3',
      downloadCount: 234,
      viewCount: 512,
      exportCount: 67,
      lastDownloadedAt: '2024-01-21T09:00:00.000Z',
      lastViewedAt: '2024-01-21T14:00:00.000Z',
    },
  },
  {
    id: 'icon-4',
    name: 'search',
    svgContent: '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>',
    categoryId: 'cat-2',
    tags: ['search', 'find', 'magnifying'],
    originalColor: '#000000',
    filePath: '/icons/search.svg',
    createdById: 'user-1',
    createdAt: '2024-01-18T13:00:00.000Z',
    updatedAt: '2024-01-18T13:00:00.000Z',
    version: 1,
    versions: [{
      id: 'ver-4-1',
      iconId: 'icon-4',
      version: 1,
      svgContent: '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>',
      name: 'search',
      tags: ['search', 'find', 'magnifying'],
      createdAt: '2024-01-18T13:00:00.000Z',
      createdBy: 'user-1',
      note: '初始版本',
    }],
    analytics: {
      iconId: 'icon-4',
      downloadCount: 178,
      viewCount: 389,
      exportCount: 52,
      lastDownloadedAt: '2024-01-20T18:00:00.000Z',
      lastViewedAt: '2024-01-21T11:00:00.000Z',
    },
  },
  {
    id: 'icon-5',
    name: 'heart',
    svgContent: '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"/></svg>',
    categoryId: 'cat-3',
    tags: ['heart', 'love', 'favorite'],
    originalColor: '#DC2626',
    filePath: '/icons/heart.svg',
    createdById: 'user-1',
    createdAt: '2024-01-19T14:00:00.000Z',
    updatedAt: '2024-01-19T14:00:00.000Z',
    version: 1,
    versions: [{
      id: 'ver-5-1',
      iconId: 'icon-5',
      version: 1,
      svgContent: '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"/></svg>',
      name: 'heart',
      tags: ['heart', 'love', 'favorite'],
      createdAt: '2024-01-19T14:00:00.000Z',
      createdBy: 'user-1',
      note: '初始版本',
    }],
    analytics: {
      iconId: 'icon-5',
      downloadCount: 312,
      viewCount: 678,
      exportCount: 89,
      lastDownloadedAt: '2024-01-21T07:00:00.000Z',
      lastViewedAt: '2024-01-21T15:00:00.000Z',
    },
  },
  {
    id: 'icon-6',
    name: 'star',
    svgContent: '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>',
    categoryId: 'cat-3',
    tags: ['star', 'favorite', 'rating'],
    originalColor: '#F59E0B',
    filePath: '/icons/star.svg',
    createdById: 'user-1',
    createdAt: '2024-01-20T15:00:00.000Z',
    updatedAt: '2024-01-20T15:00:00.000Z',
    version: 1,
    versions: [{
      id: 'ver-6-1',
      iconId: 'icon-6',
      version: 1,
      svgContent: '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>',
      name: 'star',
      tags: ['star', 'favorite', 'rating'],
      createdAt: '2024-01-20T15:00:00.000Z',
      createdBy: 'user-1',
      note: '初始版本',
    }],
    analytics: {
      iconId: 'icon-6',
      downloadCount: 267,
      viewCount: 534,
      exportCount: 71,
      lastDownloadedAt: '2024-01-20T20:00:00.000Z',
      lastViewedAt: '2024-01-21T13:00:00.000Z',
    },
  },
]

const mockCategories: Category[] = [
  {
    id: 'cat-1',
    name: '导航',
    parentId: null,
    order: 0,
    createdAt: '2024-01-01T00:00:00.000Z',
    _count: { icons: 2 },
  },
  {
    id: 'cat-2',
    name: '用户界面',
    parentId: null,
    order: 1,
    createdAt: '2024-01-02T00:00:00.000Z',
    _count: { icons: 2 },
  },
  {
    id: 'cat-3',
    name: '社交',
    parentId: null,
    order: 2,
    createdAt: '2024-01-03T00:00:00.000Z',
    _count: { icons: 2 },
  },
]

let iconsDb = [...sampleIcons]
let categoriesDb = [...mockCategories]

app.post('/api/auth/login', (req, res) => {
  const { email, password } = req.body
  const user = mockUsers.find((u) => u.email === email)

  if (!user || password !== 'password123') {
    return res.status(401).json({ error: '邮箱或密码错误' })
  }

  res.json({
    success: true,
    user: {
      id: user.id,
      email: user.email,
      name: user.name,
      role: user.role,
    },
    token: 'mock-jwt-token',
  })
})

app.get('/api/icons', (req, res) => {
  const { search, categoryId } = req.query
  let result = [...iconsDb]

  if (search) {
    const searchTerm = (search as string).toLowerCase()
    result = result.filter(
      (icon) =>
        icon.name.toLowerCase().includes(searchTerm) ||
        icon.tags.some((tag) => tag.toLowerCase().includes(searchTerm))
    )
  }

  if (categoryId) {
    result = result.filter((icon) => icon.categoryId === categoryId)
  }

  res.json({ success: true, data: result })
})

app.get('/api/icons/:id', (req, res) => {
  const icon = iconsDb.find((i) => i.id === req.params.id)
  
  if (!icon) {
    return res.status(404).json({ error: '图标不存在' })
  }

  res.json({ success: true, data: icon })
})

app.post('/api/icons', (req, res) => {
  const rawSvg = req.body.svgContent || '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/></svg>'
  
  const { clean: sanitizedSvg, warnings } = sanitizeSvgServer(rawSvg)
  const originalColor = extractOriginalColor(sanitizedSvg)
  const iconId = `icon-${Date.now()}`

  const newIcon: Icon = {
    id: iconId,
    name: req.body.name || 'new-icon',
    svgContent: sanitizedSvg,
    categoryId: req.body.categoryId || null,
    tags: req.body.tags || [],
    originalColor,
    filePath: `/icons/${Date.now()}.svg`,
    createdById: 'user-1',
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    version: 1,
    versions: [{
      id: `ver-${Date.now()}`,
      iconId,
      version: 1,
      svgContent: sanitizedSvg,
      name: req.body.name || 'new-icon',
      tags: req.body.tags || [],
      createdAt: new Date().toISOString(),
      createdBy: 'user-1',
      note: req.body.note || '初始版本',
    }],
    analytics: {
      iconId,
      downloadCount: 0,
      viewCount: 0,
      exportCount: 0,
    },
  }

  iconsDb.push(newIcon)

  res.json({ 
    success: true, 
    data: newIcon,
    warnings: warnings.length > 0 ? warnings : undefined,
  })
})

app.put('/api/icons/:id', (req, res) => {
  const index = iconsDb.findIndex((i) => i.id === req.params.id)
  
  if (index === -1) {
    return res.status(404).json({ error: '图标不存在' })
  }

  const currentIcon = iconsDb[index]
  const newVersion = currentIcon.version + 1
  const versionEntry: IconVersion = {
    id: `ver-${Date.now()}`,
    iconId: currentIcon.id,
    version: newVersion,
    svgContent: currentIcon.svgContent,
    name: currentIcon.name,
    tags: [...currentIcon.tags],
    createdAt: new Date().toISOString(),
    createdBy: 'user-1',
    note: req.body.note || `版本 ${newVersion}`,
  }

  let svgContent = req.body.svgContent || currentIcon.svgContent
  if (req.body.svgContent) {
    const { clean } = sanitizeSvgServer(req.body.svgContent)
    svgContent = clean
  }

  iconsDb[index] = {
    ...currentIcon,
    ...req.body,
    svgContent,
    version: newVersion,
    versions: [...currentIcon.versions, versionEntry],
    updatedAt: new Date().toISOString(),
  }

  res.json({ success: true, data: iconsDb[index] })
})

app.post('/api/icons/:id/rollback', (req, res) => {
  const { versionId } = req.body
  const index = iconsDb.findIndex((i) => i.id === req.params.id)
  
  if (index === -1) {
    return res.status(404).json({ error: '图标不存在' })
  }

  const currentIcon = iconsDb[index]
  const targetVersion = currentIcon.versions.find((v) => v.id === versionId)

  if (!targetVersion) {
    return res.status(404).json({ error: '版本不存在' })
  }

  const newVersion = currentIcon.version + 1
  const rollbackEntry: IconVersion = {
    id: `ver-${Date.now()}`,
    iconId: currentIcon.id,
    version: newVersion,
    svgContent: currentIcon.svgContent,
    name: currentIcon.name,
    tags: [...currentIcon.tags],
    createdAt: new Date().toISOString(),
    createdBy: 'user-1',
    note: `回滚到版本 ${targetVersion.version}`,
  }

  iconsDb[index] = {
    ...currentIcon,
    svgContent: targetVersion.svgContent,
    name: targetVersion.name,
    tags: targetVersion.tags,
    version: newVersion,
    versions: [...currentIcon.versions, rollbackEntry],
    updatedAt: new Date().toISOString(),
  }

  res.json({ success: true, data: iconsDb[index] })
})

app.get('/api/icons/:id/versions', (req, res) => {
  const icon = iconsDb.find((i) => i.id === req.params.id)
  
  if (!icon) {
    return res.status(404).json({ error: '图标不存在' })
  }

  res.json({ success: true, data: icon.versions })
})

app.post('/api/icons/:id/analytics/view', (req, res) => {
  const index = iconsDb.findIndex((i) => i.id === req.params.id)
  
  if (index === -1) {
    return res.status(404).json({ error: '图标不存在' })
  }

  iconsDb[index].analytics.viewCount++
  iconsDb[index].analytics.lastViewedAt = new Date().toISOString()

  res.json({ success: true, data: iconsDb[index].analytics })
})

app.post('/api/icons/:id/analytics/download', (req, res) => {
  const index = iconsDb.findIndex((i) => i.id === req.params.id)
  
  if (index === -1) {
    return res.status(404).json({ error: '图标不存在' })
  }

  iconsDb[index].analytics.downloadCount++
  iconsDb[index].analytics.lastDownloadedAt = new Date().toISOString()

  res.json({ success: true, data: iconsDb[index].analytics })
})

app.post('/api/icons/:id/analytics/export', (req, res) => {
  const index = iconsDb.findIndex((i) => i.id === req.params.id)
  
  if (index === -1) {
    return res.status(404).json({ error: '图标不存在' })
  }

  iconsDb[index].analytics.exportCount++

  res.json({ success: true, data: iconsDb[index].analytics })
})

app.delete('/api/icons/:id', (req, res) => {
  iconsDb = iconsDb.filter((i) => i.id !== req.params.id)
  res.json({ success: true })
})

app.get('/api/categories', (req, res) => {
  res.json({ success: true, data: categoriesDb })
})

app.post('/api/categories', (req, res) => {
  const newCategory: Category = {
    id: `cat-${Date.now()}`,
    name: req.body.name,
    parentId: req.body.parentId || null,
    order: categoriesDb.length,
    createdAt: new Date().toISOString(),
    _count: { icons: 0 },
  }

  categoriesDb.push(newCategory)
  res.json({ success: true, data: newCategory })
})

app.put('/api/categories/:id', (req, res) => {
  const index = categoriesDb.findIndex((c) => c.id === req.params.id)
  
  if (index === -1) {
    return res.status(404).json({ error: '分类不存在' })
  }

  categoriesDb[index] = {
    ...categoriesDb[index],
    ...req.body,
  }

  res.json({ success: true, data: categoriesDb[index] })
})

app.delete('/api/categories/:id', (req, res) => {
  categoriesDb = categoriesDb.filter((c) => c.id !== req.params.id)
  res.json({ success: true })
})

app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() })
})

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`)
})

export default app
