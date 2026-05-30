import { Router, type Request, type Response } from 'express'
import { v4 as uuidv4 } from 'uuid'
import db from '../db/init.js'

const router = Router()

interface MarketplacePreset {
  id: string
  name: string
  description: string
  author: string
  filterType: string
  intensity: number
  customParams: string
  thumbnailData: string | null
  tags: string
  downloads: number
  rating: number
  ratingCount: number
  createdAt: string
}

const parsePreset = (row: MarketplacePreset) => ({
  ...row,
  customParams: JSON.parse(row.customParams || '{}'),
  tags: JSON.parse(row.tags || '[]'),
})

router.get('/', (req: Request, res: Response): void => {
  const {
    search = '',
    tags = '',
    sortBy = 'rating',
    filterType = '',
    limit = '20',
    offset = '0',
  } = req.query

  let query = 'SELECT * FROM marketplace_presets WHERE 1=1'
  const params: (string | number)[] = []

  if (search) {
    query += ' AND (name LIKE ? OR description LIKE ? OR author LIKE ?)'
    const searchTerm = `%${search}%`
    params.push(searchTerm, searchTerm, searchTerm)
  }

  if (filterType) {
    query += ' AND filterType = ?'
    params.push(filterType as string)
  }

  if (tags) {
    const tagList = (tags as string).split(',')
    for (const tag of tagList) {
      query += ' AND tags LIKE ?'
      params.push(`%${tag}%`)
    }
  }

  const sortColumn =
    sortBy === 'downloads'
      ? 'downloads'
      : sortBy === 'newest'
      ? 'createdAt'
      : sortBy === 'rating'
      ? 'rating'
      : 'rating'
  const sortOrder = sortBy === 'newest' ? 'DESC' : 'DESC'
  query += ` ORDER BY ${sortColumn} ${sortOrder} LIMIT ? OFFSET ?`
  params.push(parseInt(limit as string), parseInt(offset as string))

  try {
    const rows = db.prepare(query).all(...params) as MarketplacePreset[]
    const total = db
      .prepare(
        'SELECT COUNT(*) as count FROM marketplace_presets WHERE 1=1' +
          (search ? ' AND (name LIKE ? OR description LIKE ? OR author LIKE ?)' : '') +
          (filterType ? ' AND filterType = ?' : '')
      )
      .get(
        ...(search
          ? [`%${search}%`, `%${search}%`, `%${search}%`]
          : []),
        ...(filterType ? [filterType] : [])
      ) as { count: number }

    const presets = rows.map(parsePreset)
    res.json({
      success: true,
      data: presets,
      pagination: {
        total: total.count,
        limit: parseInt(limit as string),
        offset: parseInt(offset as string),
      },
    })
  } catch (error) {
    res.status(500).json({ success: false, error: 'Failed to fetch presets' })
  }
})

router.get('/:id', (req: Request, res: Response): void => {
  const { id } = req.params

  try {
    const row = db
      .prepare('SELECT * FROM marketplace_presets WHERE id = ?')
      .get(id) as MarketplacePreset | undefined

    if (!row) {
      res.status(404).json({ success: false, error: 'Preset not found' })
      return
    }

    db.prepare('UPDATE marketplace_presets SET downloads = downloads + 1 WHERE id = ?').run(id)

    const updatedRow = db
      .prepare('SELECT * FROM marketplace_presets WHERE id = ?')
      .get(id) as MarketplacePreset

    res.json({
      success: true,
      data: parsePreset(updatedRow),
    })
  } catch (error) {
    res.status(500).json({ success: false, error: 'Failed to fetch preset' })
  }
})

router.post('/', (req: Request, res: Response): void => {
  const id = uuidv4()
  const {
    name,
    description = '',
    author = 'Anonymous',
    filterType,
    intensity = 0.5,
    customParams = {},
    thumbnailData = null,
    tags = [],
  } = req.body

  if (!name || !filterType) {
    res.status(400).json({ success: false, error: 'Name and filterType are required' })
    return
  }

  try {
    db.prepare(
      `INSERT INTO marketplace_presets (
        id, name, description, author, filterType, intensity,
        customParams, thumbnailData, tags
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`
    ).run(
      id,
      name,
      description,
      author,
      filterType,
      intensity,
      JSON.stringify(customParams),
      thumbnailData,
      JSON.stringify(tags)
    )

    const row = db
      .prepare('SELECT * FROM marketplace_presets WHERE id = ?')
      .get(id) as MarketplacePreset

    res.status(201).json({
      success: true,
      data: parsePreset(row),
    })
  } catch (error) {
    res.status(500).json({ success: false, error: 'Failed to create preset' })
  }
})

router.post('/:id/rate', (req: Request, res: Response): void => {
  const { id } = req.params
  const { userId, rating } = req.body

  if (!userId || rating === undefined) {
    res.status(400).json({ success: false, error: 'userId and rating are required' })
    return
  }

  if (rating < 1 || rating > 5) {
    res.status(400).json({ success: false, error: 'Rating must be between 1 and 5' })
    return
  }

  const tx = db.transaction(() => {
    const ratingId = uuidv4()

    db.prepare(
      `INSERT OR REPLACE INTO marketplace_ratings (id, presetId, userId, rating)
       VALUES (?, ?, ?, ?)`
    ).run(ratingId, id, userId, rating)

    const result = db
      .prepare(
        `SELECT AVG(rating) as avgRating, COUNT(*) as count
         FROM marketplace_ratings WHERE presetId = ?`
      )
      .get(id) as { avgRating: number; count: number }

    db.prepare(
      'UPDATE marketplace_presets SET rating = ?, ratingCount = ? WHERE id = ?'
    ).run(result.avgRating || 0, result.count || 0, id)

    return result
  })

  try {
    const result = tx()
    res.json({
      success: true,
      data: {
        rating: result.avgRating || 0,
        ratingCount: result.count || 0,
      },
    })
  } catch (error) {
    res.status(500).json({ success: false, error: 'Failed to rate preset' })
  }
})

router.delete('/:id', (req: Request, res: Response): void => {
  const { id } = req.params

  try {
    const result = db.prepare('DELETE FROM marketplace_presets WHERE id = ?').run(id)

    if (result.changes === 0) {
      res.status(404).json({ success: false, error: 'Preset not found' })
      return
    }

    db.prepare('DELETE FROM marketplace_ratings WHERE presetId = ?').run(id)

    res.json({ success: true, message: 'Preset deleted' })
  } catch (error) {
    res.status(500).json({ success: false, error: 'Failed to delete preset' })
  }
})

router.get('/trending', (_req: Request, res: Response): void => {
  try {
    const rows = db
      .prepare(
        `SELECT * FROM marketplace_presets
         ORDER BY (rating * 0.6 + (downloads / 1000.0) * 0.4) DESC
         LIMIT 6`
      )
      .all() as MarketplacePreset[]

    res.json({
      success: true,
      data: rows.map(parsePreset),
    })
  } catch (error) {
    res.status(500).json({ success: false, error: 'Failed to fetch trending' })
  }
})

export default router
