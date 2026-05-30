import { Router, type Request, type Response } from 'express'
import db from '../db.js'

const router = Router()

router.get('/', (req: Request, res: Response): void => {
  try {
    const { severity, status, page = '1', pageSize = '20' } = req.query
    const pageNum = Math.max(parseInt(page as string) || 1, 1)
    const pageSizeNum = Math.min(Math.max(parseInt(pageSize as string) || 20, 1), 100)
    const offset = (pageNum - 1) * pageSizeNum

    let whereClause = '1=1'
    const params: any[] = []

    if (severity) {
      whereClause += ' AND a.severity = ?'
      params.push(severity)
    }
    if (status) {
      whereClause += ' AND a.status = ?'
      params.push(status)
    }

    const total = db.prepare(`
      SELECT COUNT(*) as cnt FROM alert a WHERE ${whereClause}
    `).get(...params) as { cnt: number }

    const alerts = db.prepare(`
      SELECT a.*, mt.name as table_name, mr.name as rule_name
      FROM alert a
      JOIN monitored_table mt ON a.table_id = mt.id
      LEFT JOIN monitor_rule mr ON a.rule_id = mr.id
      WHERE ${whereClause}
      ORDER BY a.triggered_at DESC
      LIMIT ? OFFSET ?
    `).all(...params, pageSizeNum, offset)

    res.json({
      items: alerts,
      total: total.cnt,
    })
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch alerts' })
  }
})

router.get('/:id', (req: Request, res: Response): void => {
  try {
    const alert = db.prepare(`
      SELECT a.*, mt.name as table_name, mr.name as rule_name
      FROM alert a
      JOIN monitored_table mt ON a.table_id = mt.id
      LEFT JOIN monitor_rule mr ON a.rule_id = mr.id
      WHERE a.id = ?
    `).get(req.params.id)

    if (!alert) {
      res.status(404).json({ error: 'Alert not found' })
      return
    }

    res.json(alert)
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch alert' })
  }
})

router.patch('/:id/acknowledge', (req: Request, res: Response): void => {
  try {
    const existing = db.prepare('SELECT * FROM alert WHERE id = ?').get(req.params.id) as { id: string; status: string } | undefined
    if (!existing) {
      res.status(404).json({ error: 'Alert not found' })
      return
    }

    if (existing.status !== 'active') {
      res.status(400).json({ error: 'Only active alerts can be acknowledged' })
      return
    }

    const now = new Date().toISOString().replace('T', ' ').slice(0, 19)
    db.prepare("UPDATE alert SET status = 'acknowledged', acknowledged_at = ? WHERE id = ?").run(now, req.params.id)

    const alert = db.prepare(`
      SELECT a.*, mt.name as table_name, mr.name as rule_name
      FROM alert a
      JOIN monitored_table mt ON a.table_id = mt.id
      LEFT JOIN monitor_rule mr ON a.rule_id = mr.id
      WHERE a.id = ?
    `).get(req.params.id)

    res.json(alert)
  } catch (error) {
    res.status(500).json({ error: 'Failed to acknowledge alert' })
  }
})

router.patch('/:id/resolve', (req: Request, res: Response): void => {
  try {
    const existing = db.prepare('SELECT * FROM alert WHERE id = ?').get(req.params.id) as { id: string; status: string } | undefined
    if (!existing) {
      res.status(404).json({ error: 'Alert not found' })
      return
    }

    if (existing.status === 'resolved') {
      res.status(400).json({ error: 'Alert is already resolved' })
      return
    }

    const { resolution } = req.body
    const now = new Date().toISOString().replace('T', ' ').slice(0, 19)
    const acknowledgedAt = existing.status === 'active' ? now : undefined

    db.prepare(`
      UPDATE alert SET
        status = 'resolved',
        acknowledged_at = COALESCE(?, acknowledged_at),
        resolved_at = ?,
        resolution = ?
      WHERE id = ?
    `).run(acknowledgedAt || null, now, resolution || null, req.params.id)

    const alert = db.prepare(`
      SELECT a.*, mt.name as table_name, mr.name as rule_name
      FROM alert a
      JOIN monitored_table mt ON a.table_id = mt.id
      LEFT JOIN monitor_rule mr ON a.rule_id = mr.id
      WHERE a.id = ?
    `).get(req.params.id)

    res.json(alert)
  } catch (error) {
    res.status(500).json({ error: 'Failed to resolve alert' })
  }
})

export default router
