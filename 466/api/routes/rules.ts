import { Router, type Request, type Response } from 'express'
import { v4 as uuidv4 } from 'uuid'
import db from '../db.js'

const router = Router()

const baseThresholds: Record<string, { warning: number; critical: number }> = {
  null_rate: { warning: 0.05, critical: 0.10 },
  duplicate_rate: { warning: 0.02, critical: 0.05 },
  distribution_drift: { warning: 0.15, critical: 0.25 },
  row_count: { warning: 0.5, critical: 0.5 },
}

const importanceMultipliers: Record<string, number> = {
  critical: 0.6,
  high: 0.8,
  medium: 1.0,
  low: 1.3,
}

router.get('/templates', (_req: Request, res: Response): void => {
  res.json([
    { id: 'tpl_null_rate', name: '空值率监控', metricType: 'null_rate', condition: '>', defaultThreshold: 0.05, severity: 'warning', description: '监控字段空值比例，当空值率超过阈值时触发告警' },
    { id: 'tpl_null_rate_critical', name: '空值率严重告警', metricType: 'null_rate', condition: '>', defaultThreshold: 0.10, severity: 'critical', description: '空值率严重超标时触发紧急告警' },
    { id: 'tpl_dup_rate', name: '重复率监控', metricType: 'duplicate_rate', condition: '>', defaultThreshold: 0.02, severity: 'warning', description: '监控数据重复比例，发现重复数据异常时告警' },
    { id: 'tpl_row_drop', name: '行数骤降告警', metricType: 'row_count', condition: '<', defaultThreshold: 0, severity: 'critical', description: '当数据行数低于阈值时触发，可能表示数据采集中断' },
    { id: 'tpl_drift_warn', name: '分布漂移预警', metricType: 'distribution_drift', condition: '>', defaultThreshold: 0.15, severity: 'warning', description: '监控数据分布变化，当漂移超过阈值时预警' },
    { id: 'tpl_drift_critical', name: '分布漂移严重告警', metricType: 'distribution_drift', condition: '>', defaultThreshold: 0.25, severity: 'critical', description: '数据分布发生严重偏移时触发紧急告警' },
  ])
})

router.get('/dynamic-threshold', (req: Request, res: Response): void => {
  try {
    const { tableId, metricType, fieldImportance } = req.query

    if (!metricType || !fieldImportance) {
      res.status(400).json({ error: 'Missing required query params: metricType, fieldImportance' })
      return
    }

    const base = baseThresholds[metricType as string]
    if (!base) {
      res.status(400).json({ error: `Unknown metricType: ${metricType}. Valid types: ${Object.keys(baseThresholds).join(', ')}` })
      return
    }

    const multiplier = importanceMultipliers[fieldImportance as string]
    if (!multiplier) {
      res.status(400).json({ error: `Unknown fieldImportance: ${fieldImportance}. Valid levels: ${Object.keys(importanceMultipliers).join(', ')}` })
      return
    }

    if (tableId) {
      const table = db.prepare('SELECT id FROM monitored_table WHERE id = ?').get(tableId as string)
      if (!table) {
        res.status(400).json({ error: 'Referenced table not found' })
        return
      }
    }

    const adjusted_warning = Math.round(base.warning * multiplier * 10000) / 10000
    const adjusted_critical = Math.round(base.critical * multiplier * 10000) / 10000

    res.json({
      base_threshold: base,
      importance_multiplier: multiplier,
      adjusted_threshold: { warning: adjusted_warning, critical: adjusted_critical },
      importance_level: fieldImportance,
    })
  } catch (error) {
    res.status(500).json({ error: 'Failed to compute dynamic threshold' })
  }
})

router.get('/field-importance/:tableId', (req: Request, res: Response): void => {
  try {
    const { tableId } = req.params

    const table = db.prepare('SELECT id FROM monitored_table WHERE id = ?').get(tableId)
    if (!table) {
      res.status(404).json({ error: 'Table not found' })
      return
    }

    const fields = db.prepare('SELECT * FROM field_importance WHERE table_id = ? ORDER BY field_name').all(tableId)
    res.json(fields)
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch field importance' })
  }
})

router.put('/field-importance/:tableId', (req: Request, res: Response): void => {
  try {
    const { tableId } = req.params

    const table = db.prepare('SELECT id FROM monitored_table WHERE id = ?').get(tableId)
    if (!table) {
      res.status(404).json({ error: 'Table not found' })
      return
    }

    const { fields } = req.body as { fields: { field_name: string; importance: string }[] }
    if (!Array.isArray(fields)) {
      res.status(400).json({ error: 'Request body must contain a "fields" array' })
      return
    }

    const validLevels = ['critical', 'high', 'medium', 'low']
    for (const f of fields) {
      if (!f.field_name || !f.importance || !validLevels.includes(f.importance)) {
        res.status(400).json({ error: `Invalid field config: field_name and importance (one of ${validLevels.join(', ')}) are required` })
        return
      }
    }

    const now = new Date().toISOString().replace('T', ' ').slice(0, 19)
    const upsert = db.transaction(() => {
      for (const f of fields) {
        const existing = db.prepare('SELECT id FROM field_importance WHERE table_id = ? AND field_name = ?').get(tableId, f.field_name) as { id: string } | undefined
        if (existing) {
          db.prepare('UPDATE field_importance SET importance = ?, updated_at = ? WHERE id = ?').run(f.importance, now, existing.id)
        } else {
          db.prepare('INSERT INTO field_importance (id, table_id, field_name, importance, updated_at) VALUES (?, ?, ?, ?, ?)').run(uuidv4(), tableId, f.field_name, f.importance, now)
        }
      }
    })

    upsert()

    const updated = db.prepare('SELECT * FROM field_importance WHERE table_id = ? ORDER BY field_name').all(tableId)
    res.json(updated)
  } catch (error) {
    res.status(500).json({ error: 'Failed to update field importance' })
  }
})

router.get('/', (_req: Request, res: Response): void => {
  try {
    const rules = db.prepare(`
      SELECT mr.*, mt.name as table_name
      FROM monitor_rule mr
      JOIN monitored_table mt ON mr.table_id = mt.id
      ORDER BY mr.created_at DESC
    `).all()
    res.json(rules)
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch rules' })
  }
})

router.get('/:id', (req: Request, res: Response): void => {
  try {
    const rule = db.prepare(`
      SELECT mr.*, mt.name as table_name
      FROM monitor_rule mr
      JOIN monitored_table mt ON mr.table_id = mt.id
      WHERE mr.id = ?
    `).get(req.params.id)

    if (!rule) {
      res.status(404).json({ error: 'Rule not found' })
      return
    }

    res.json(rule)
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch rule' })
  }
})

router.post('/', (req: Request, res: Response): void => {
  try {
    const { name, table_id, metric_type, condition, threshold, schedule, severity = 'warning', enabled = 1, field_importance = 'medium' } = req.body

    if (!name || !table_id || !metric_type || !condition || threshold === undefined || !schedule) {
      res.status(400).json({ error: 'Missing required fields: name, table_id, metric_type, condition, threshold, schedule' })
      return
    }

    const table = db.prepare('SELECT id FROM monitored_table WHERE id = ?').get(table_id)
    if (!table) {
      res.status(400).json({ error: 'Referenced table not found' })
      return
    }

    const id = uuidv4()
    const now = new Date().toISOString().replace('T', ' ').slice(0, 19)

    db.prepare(`
      INSERT INTO monitor_rule (id, name, table_id, metric_type, condition, threshold, schedule, severity, enabled, field_importance, created_at, updated_at)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `).run(id, name, table_id, metric_type, condition, threshold, schedule, severity, enabled ? 1 : 0, field_importance, now, now)

    const rule = db.prepare('SELECT * FROM monitor_rule WHERE id = ?').get(id)
    res.status(201).json(rule)
  } catch (error) {
    res.status(500).json({ error: 'Failed to create rule' })
  }
})

router.put('/:id', (req: Request, res: Response): void => {
  try {
    const existing = db.prepare('SELECT * FROM monitor_rule WHERE id = ?').get(req.params.id)
    if (!existing) {
      res.status(404).json({ error: 'Rule not found' })
      return
    }

    const { name, table_id, metric_type, condition, threshold, schedule, severity, enabled, field_importance } = req.body
    const now = new Date().toISOString().replace('T', ' ').slice(0, 19)

    db.prepare(`
      UPDATE monitor_rule SET
        name = COALESCE(?, name),
        table_id = COALESCE(?, table_id),
        metric_type = COALESCE(?, metric_type),
        condition = COALESCE(?, condition),
        threshold = COALESCE(?, threshold),
        schedule = COALESCE(?, schedule),
        severity = COALESCE(?, severity),
        enabled = COALESCE(?, enabled),
        field_importance = COALESCE(?, field_importance),
        updated_at = ?
      WHERE id = ?
    `).run(name || null, table_id || null, metric_type || null, condition || null, threshold ?? null, schedule || null, severity || null, enabled !== undefined ? (enabled ? 1 : 0) : null, field_importance || null, now, req.params.id)

    const rule = db.prepare('SELECT * FROM monitor_rule WHERE id = ?').get(req.params.id)
    res.json(rule)
  } catch (error) {
    res.status(500).json({ error: 'Failed to update rule' })
  }
})

router.delete('/:id', (req: Request, res: Response): void => {
  try {
    const existing = db.prepare('SELECT * FROM monitor_rule WHERE id = ?').get(req.params.id)
    if (!existing) {
      res.status(404).json({ error: 'Rule not found' })
      return
    }

    db.prepare('DELETE FROM monitor_rule WHERE id = ?').run(req.params.id)
    res.json({ success: true, message: 'Rule deleted' })
  } catch (error) {
    res.status(500).json({ error: 'Failed to delete rule' })
  }
})

router.patch('/:id/toggle', (req: Request, res: Response): void => {
  try {
    const existing = db.prepare('SELECT * FROM monitor_rule WHERE id = ?').get(req.params.id) as { id: string; enabled: number } | undefined
    if (!existing) {
      res.status(404).json({ error: 'Rule not found' })
      return
    }

    const newEnabled = existing.enabled ? 0 : 1
    const now = new Date().toISOString().replace('T', ' ').slice(0, 19)

    db.prepare('UPDATE monitor_rule SET enabled = ?, updated_at = ? WHERE id = ?').run(newEnabled, now, req.params.id)

    const rule = db.prepare('SELECT * FROM monitor_rule WHERE id = ?').get(req.params.id)
    res.json(rule)
  } catch (error) {
    res.status(500).json({ error: 'Failed to toggle rule' })
  }
})

export default router
