import { Router } from 'express'
import db from '../database'

const router = Router()

router.get('/:projectId', (req, res) => {
  const annotations = db.prepare(`
    SELECT a.*, u.username
    FROM annotations a
    LEFT JOIN users u ON a.user_id = u.id
    WHERE a.project_id = ?
    ORDER BY a.created_at DESC
  `).all(req.params.projectId)

  res.json(annotations.map((a: any) => ({
    id: a.id.toString(),
    projectId: a.project_id.toString(),
    label: a.label,
    type: a.type,
    geometry: JSON.parse(a.geometry),
    pointIndices: [],
    userId: a.user_id?.toString(),
    userName: a.username,
    createdAt: a.created_at,
    updatedAt: a.updated_at,
  })))
})

router.post('/:projectId', (req, res) => {
  const { projectId } = req.params
  const { label, type, geometry, pointIndices } = req.body
  const userId = 1

  const result = db.prepare(`
    INSERT INTO annotations (project_id, user_id, label, type, geometry, point_count)
    VALUES (?, ?, ?, ?, ?, ?)
  `).run(
    projectId,
    userId,
    label,
    type,
    JSON.stringify(geometry),
    pointIndices?.length || 0
  )

  const annotation = db.prepare('SELECT * FROM annotations WHERE id = ?').get(result.lastInsertRowid)

  res.status(201).json({
    id: (annotation as any).id.toString(),
    projectId: (annotation as any).project_id.toString(),
    label: (annotation as any).label,
    type: (annotation as any).type,
    geometry: JSON.parse((annotation as any).geometry),
    pointIndices: [],
    userId: (annotation as any).user_id?.toString(),
    createdAt: (annotation as any).created_at,
    updatedAt: (annotation as any).updated_at,
  })
})

router.delete('/:projectId/:annotationId', (req, res) => {
  db.prepare('DELETE FROM annotations WHERE id = ? AND project_id = ?').run(
    req.params.annotationId,
    req.params.projectId
  )

  res.json({ success: true })
})

router.get('/:projectId/export', (req, res) => {
  const { projectId } = req.params
  const format = req.query.format as string || 'json'

  const annotations = db.prepare(`
    SELECT a.*, u.username
    FROM annotations a
    LEFT JOIN users u ON a.user_id = u.id
    WHERE a.project_id = ?
  `).all(projectId)

  const project = db.prepare('SELECT name FROM projects WHERE id = ?').get(projectId)

  if (format === 'json') {
    const exportData = {
      projectId,
      projectName: (project as any)?.name,
      exportedAt: new Date().toISOString(),
      annotations: annotations.map((a: any) => ({
        id: a.id.toString(),
        label: a.label,
        type: a.type,
        geometry: JSON.parse(a.geometry),
        userName: a.username,
        createdAt: a.created_at,
      })),
      statistics: {
        totalAnnotations: annotations.length,
        labelDistribution: annotations.reduce((acc: any, a: any) => {
          acc[a.label] = (acc[a.label] || 0) + 1
          return acc
        }, {}),
      },
    }

    res.setHeader('Content-Type', 'application/json')
    res.setHeader('Content-Disposition', `attachment; filename="annotations_${projectId}.json"`)
    res.json(exportData)
  } else {
    res.setHeader('Content-Type', 'application/json')
    res.setHeader('Content-Disposition', `attachment; filename="annotations_${projectId}.json"`)
    res.json({
      projectId,
      exportedAt: new Date().toISOString(),
      annotations: [],
      note: 'LAS export requires additional point cloud processing',
    })
  }
})

export default router
