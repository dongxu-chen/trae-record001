import { Router, type Request, type Response } from 'express'
import { v4 as uuidv4 } from 'uuid'
import db from '../db/init.js'

const router = Router()

router.get('/', (_req: Request, res: Response): void => {
  const presets = db.prepare('SELECT * FROM presets ORDER BY createdAt DESC').all() as Array<{
    id: string
    name: string
    filterType: string
    intensity: number
    customParams: string
    createdAt: string
  }>
  const result = presets.map((p) => ({
    ...p,
    customParams: JSON.parse(p.customParams),
  }))
  res.json({ success: true, data: result })
})

router.post('/', (req: Request, res: Response): void => {
  const id = uuidv4()
  const { name, filterType, intensity = 0.5, customParams = {} } = req.body
  const customParamsStr = JSON.stringify(customParams)
  db.prepare(
    'INSERT INTO presets (id, name, filterType, intensity, customParams) VALUES (?, ?, ?, ?, ?)'
  ).run(id, name, filterType, intensity, customParamsStr)
  const preset = db.prepare('SELECT * FROM presets WHERE id = ?').get(id) as {
    id: string
    name: string
    filterType: string
    intensity: number
    customParams: string
    createdAt: string
  }
  res.status(201).json({
    success: true,
    data: { ...preset, customParams: JSON.parse(preset.customParams) },
  })
})

router.put('/:id', (req: Request, res: Response): void => {
  const { id } = req.params
  const existing = db.prepare('SELECT * FROM presets WHERE id = ?').get(id)
  if (!existing) {
    res.status(404).json({ success: false, error: 'Preset not found' })
    return
  }
  const { name, filterType, intensity, customParams } = req.body
  const updates: string[] = []
  const values: unknown[] = []
  if (name !== undefined) { updates.push('name = ?'); values.push(name) }
  if (filterType !== undefined) { updates.push('filterType = ?'); values.push(filterType) }
  if (intensity !== undefined) { updates.push('intensity = ?'); values.push(intensity) }
  if (customParams !== undefined) { updates.push('customParams = ?'); values.push(JSON.stringify(customParams)) }
  if (updates.length === 0) {
    res.status(400).json({ success: false, error: 'No fields to update' })
    return
  }
  values.push(id)
  db.prepare(`UPDATE presets SET ${updates.join(', ')} WHERE id = ?`).run(...values)
  const preset = db.prepare('SELECT * FROM presets WHERE id = ?').get(id) as {
    id: string
    name: string
    filterType: string
    intensity: number
    customParams: string
    createdAt: string
  }
  res.json({
    success: true,
    data: { ...preset, customParams: JSON.parse(preset.customParams) },
  })
})

router.delete('/:id', (req: Request, res: Response): void => {
  const { id } = req.params
  const result = db.prepare('DELETE FROM presets WHERE id = ?').run(id)
  if (result.changes === 0) {
    res.status(404).json({ success: false, error: 'Preset not found' })
    return
  }
  res.json({ success: true, message: 'Preset deleted' })
})

export default router
