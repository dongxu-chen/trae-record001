import { Router, type Request, type Response } from 'express'
import { v4 as uuidv4 } from 'uuid'
import db from '../db/init.js'

const router = Router()

router.get('/custom', (_req: Request, res: Response): void => {
  const filters = db.prepare('SELECT * FROM custom_filters ORDER BY createdAt DESC').all() as Array<{
    id: string
    name: string
    filename: string
    fragmentShader: string
    uniforms: string
    createdAt: string
  }>
  const result = filters.map((f) => ({
    ...f,
    uniforms: JSON.parse(f.uniforms),
  }))
  res.json({ success: true, data: result })
})

router.post('/custom', (req: Request, res: Response): void => {
  const id = uuidv4()
  const { name, fragmentShader, uniforms = [] } = req.body
  const filename = `${id}.glsl`
  const uniformsStr = JSON.stringify(uniforms)
  db.prepare(
    'INSERT INTO custom_filters (id, name, filename, fragmentShader, uniforms) VALUES (?, ?, ?, ?, ?)'
  ).run(id, name, filename, fragmentShader, uniformsStr)
  const filter = db.prepare('SELECT * FROM custom_filters WHERE id = ?').get(id) as {
    id: string
    name: string
    filename: string
    fragmentShader: string
    uniforms: string
    createdAt: string
  }
  res.status(201).json({
    success: true,
    data: { ...filter, uniforms: JSON.parse(filter.uniforms) },
  })
})

router.delete('/custom/:id', (req: Request, res: Response): void => {
  const { id } = req.params
  const result = db.prepare('DELETE FROM custom_filters WHERE id = ?').run(id)
  if (result.changes === 0) {
    res.status(404).json({ success: false, error: 'Custom filter not found' })
    return
  }
  res.json({ success: true, message: 'Custom filter deleted' })
})

router.post('/custom/validate', (req: Request, res: Response): void => {
  const { fragmentShader } = req.body
  if (!fragmentShader || typeof fragmentShader !== 'string') {
    res.status(400).json({ valid: false, error: 'fragmentShader is required and must be a string' })
    return
  }
  const hasMain = fragmentShader.includes('void main')
  const hasFragColor = fragmentShader.includes('fragColor')
  if (!hasMain || !hasFragColor) {
    const errors: string[] = []
    if (!hasMain) errors.push("Missing 'void main' function")
    if (!hasFragColor) errors.push("Missing 'fragColor' output")
    res.json({ valid: false, error: errors.join('. ') })
    return
  }
  res.json({ valid: true, error: '' })
})

export default router
