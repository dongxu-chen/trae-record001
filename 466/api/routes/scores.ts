import { Router, type Request, type Response } from 'express'
import { v4 as uuidv4 } from 'uuid'
import db from '../db.js'

const router = Router()

const defaultWeights = { completeness_weight: 0.3, consistency_weight: 0.25, timeliness_weight: 0.2, accuracy_weight: 0.25 }

function getWeights(tableId: string) {
  const config = db.prepare('SELECT * FROM score_weight_config WHERE table_id = ?').get(tableId) as any
  if (config) {
    return {
      completeness_weight: config.completeness_weight,
      consistency_weight: config.consistency_weight,
      timeliness_weight: config.timeliness_weight,
      accuracy_weight: config.accuracy_weight,
    }
  }
  return { ...defaultWeights }
}

router.get('/', (_req: Request, res: Response): void => {
  try {
    const scores = db.prepare(`
      SELECT qs.*, mt.name as table_name, mt.status as table_status
      FROM quality_score qs
      JOIN monitored_table mt ON qs.table_id = mt.id
      WHERE qs.scored_at = (
        SELECT MAX(qs2.scored_at) FROM quality_score qs2 WHERE qs2.table_id = qs.table_id
      )
      ORDER BY qs.overall ASC
    `).all() as any[]
    const result = scores.map(s => {
      const w = getWeights(s.table_id)
      const overall = Math.round((s.completeness * w.completeness_weight + s.consistency * w.consistency_weight + s.timeliness * w.timeliness_weight + s.accuracy * w.accuracy_weight) * 10) / 10
      return {
        table_id: s.table_id,
        table_name: s.table_name,
        table_status: s.table_status,
        overall_score: overall,
        dimensions: [
          { dimension: 'completeness', score: Math.round(s.completeness * 10) / 10, weight: w.completeness_weight },
          { dimension: 'consistency', score: Math.round(s.consistency * 10) / 10, weight: w.consistency_weight },
          { dimension: 'timeliness', score: Math.round(s.timeliness * 10) / 10, weight: w.timeliness_weight },
          { dimension: 'accuracy', score: Math.round(s.accuracy * 10) / 10, weight: w.accuracy_weight },
        ],
      }
    })
    res.json(result)
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch scores' })
  }
})

router.get('/weights/:tableId', (req: Request, res: Response): void => {
  try {
    const { tableId } = req.params

    const table = db.prepare('SELECT id FROM monitored_table WHERE id = ?').get(tableId)
    if (!table) {
      res.status(404).json({ error: 'Table not found' })
      return
    }

    const config = db.prepare('SELECT * FROM score_weight_config WHERE table_id = ?').get(tableId) as any
    if (!config) {
      res.json({ table_id: tableId, ...defaultWeights, is_default: true })
      return
    }

    res.json({
      table_id: tableId,
      completeness_weight: config.completeness_weight,
      consistency_weight: config.consistency_weight,
      timeliness_weight: config.timeliness_weight,
      accuracy_weight: config.accuracy_weight,
      is_default: false,
    })
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch weight config' })
  }
})

router.put('/weights/:tableId', (req: Request, res: Response): void => {
  try {
    const { tableId } = req.params

    const table = db.prepare('SELECT id FROM monitored_table WHERE id = ?').get(tableId)
    if (!table) {
      res.status(404).json({ error: 'Table not found' })
      return
    }

    const { completeness_weight, consistency_weight, timeliness_weight, accuracy_weight } = req.body

    if (completeness_weight === undefined || consistency_weight === undefined || timeliness_weight === undefined || accuracy_weight === undefined) {
      res.status(400).json({ error: 'All weight fields are required: completeness_weight, consistency_weight, timeliness_weight, accuracy_weight' })
      return
    }

    if (completeness_weight <= 0 || consistency_weight <= 0 || timeliness_weight <= 0 || accuracy_weight <= 0) {
      res.status(400).json({ error: 'All weights must be positive numbers' })
      return
    }

    const sum = completeness_weight + consistency_weight + timeliness_weight + accuracy_weight
    const normalized = {
      completeness_weight: Math.round(completeness_weight / sum * 1000) / 1000,
      consistency_weight: Math.round(consistency_weight / sum * 1000) / 1000,
      timeliness_weight: Math.round(timeliness_weight / sum * 1000) / 1000,
      accuracy_weight: Math.round(accuracy_weight / sum * 1000) / 1000,
    }

    const now = new Date().toISOString().replace('T', ' ').slice(0, 19)
    const existing = db.prepare('SELECT id FROM score_weight_config WHERE table_id = ?').get(tableId) as { id: string } | undefined

    if (existing) {
      db.prepare(`
        UPDATE score_weight_config SET
          completeness_weight = ?, consistency_weight = ?, timeliness_weight = ?, accuracy_weight = ?, updated_at = ?
        WHERE id = ?
      `).run(normalized.completeness_weight, normalized.consistency_weight, normalized.timeliness_weight, normalized.accuracy_weight, now, existing.id)
    } else {
      db.prepare(`
        INSERT INTO score_weight_config (id, table_id, completeness_weight, consistency_weight, timeliness_weight, accuracy_weight, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
      `).run(uuidv4(), tableId, normalized.completeness_weight, normalized.consistency_weight, normalized.timeliness_weight, normalized.accuracy_weight, now)
    }

    res.json({ table_id: tableId, ...normalized, is_default: false })
  } catch (error) {
    res.status(500).json({ error: 'Failed to update weight config' })
  }
})

router.get('/:tableId', (req: Request, res: Response): void => {
  try {
    const { tableId } = req.params

    const table = db.prepare('SELECT * FROM monitored_table WHERE id = ?').get(tableId)
    if (!table) {
      res.status(404).json({ error: 'Table not found' })
      return
    }

    const latestScore = db.prepare(`
      SELECT * FROM quality_score
      WHERE table_id = ?
      ORDER BY scored_at DESC LIMIT 1
    `).get(tableId)

    const history = db.prepare(`
      SELECT * FROM quality_score
      WHERE table_id = ?
      ORDER BY scored_at ASC
    `).all(tableId)

    const w = getWeights(tableId)

    res.json({
      table_id: tableId,
      overall_score: latestScore ? Math.round(((latestScore as any).completeness * w.completeness_weight + (latestScore as any).consistency * w.consistency_weight + (latestScore as any).timeliness * w.timeliness_weight + (latestScore as any).accuracy * w.accuracy_weight) * 10) / 10 : 0,
      dimensions: latestScore ? [
        { dimension: 'completeness', score: Math.round((latestScore as any).completeness * 10) / 10, weight: w.completeness_weight },
        { dimension: 'consistency', score: Math.round((latestScore as any).consistency * 10) / 10, weight: w.consistency_weight },
        { dimension: 'timeliness', score: Math.round((latestScore as any).timeliness * 10) / 10, weight: w.timeliness_weight },
        { dimension: 'accuracy', score: Math.round((latestScore as any).accuracy * 10) / 10, weight: w.accuracy_weight },
      ] : [],
      history: (history as any[]).map(h => ({
        date: (h as any).scored_at.slice(0, 10),
        score: Math.round(((h as any).completeness * w.completeness_weight + (h as any).consistency * w.consistency_weight + (h as any).timeliness * w.timeliness_weight + (h as any).accuracy * w.accuracy_weight) * 10) / 10,
      })),
    })
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch score detail' })
  }
})

export default router
