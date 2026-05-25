import { Router } from 'express'
import db from '../database'

const router = Router()

router.get('/:projectId', (req, res) => {
  const { projectId } = req.params

  const annotations = db.prepare(`
    SELECT a.*, u.username
    FROM annotations a
    LEFT JOIN users u ON a.user_id = u.id
    WHERE a.project_id = ?
  `).all(projectId)

  const labelDistribution: Record<string, number> = {
    ground: 0,
    vehicle: 0,
    pedestrian: 0,
  }

  const userContributions: Record<string, { userId: string; username: string; count: number }> = {}

  annotations.forEach((a: any) => {
    labelDistribution[a.label] = (labelDistribution[a.label] || 0) + 1

    if (a.user_id) {
      const key = a.user_id.toString()
      if (!userContributions[key]) {
        userContributions[key] = {
          userId: key,
          username: a.username || 'Unknown',
          count: 0,
        }
      }
      userContributions[key].count++
    }
  })

  const totalPoints = annotations.reduce((sum: number, a: any) => sum + (a.point_count || 0), 0)

  res.json({
    totalAnnotations: annotations.length,
    totalPoints,
    labelDistribution,
    userContributions: Object.values(userContributions).sort((a, b) => b.count - a.count),
    progress: Math.min((annotations.length / 100) * 100, 100),
  })
})

export default router
