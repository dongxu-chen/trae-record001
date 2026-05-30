import { Router, type Request, type Response } from 'express'
import db from '../db.js'

const router = Router()

router.get('/overview', (_req: Request, res: Response): void => {
  try {
    const tables = db.prepare('SELECT * FROM monitored_table').all() as any[]
    const activeAlerts = db.prepare("SELECT COUNT(*) as cnt FROM alert WHERE status = 'active'").get() as { cnt: number }
    const totalRules = db.prepare('SELECT COUNT(*) as cnt FROM monitor_rule').get() as { cnt: number }

    const overallScore = tables.length > 0
      ? Math.round(tables.reduce((sum, t) => sum + t.quality_score, 0) / tables.length * 10) / 10
      : 0

    const recentScores = db.prepare(`
      SELECT qs.scored_at, AVG(qs.overall) as avg_score
      FROM quality_score qs
      WHERE qs.scored_at >= datetime('now', '-30 days')
      GROUP BY DATE(qs.scored_at)
      ORDER BY qs.scored_at ASC
    `).all() as { scored_at: string; avg_score: number }[]

    const scoreTrend = recentScores.map(s => ({
      date: s.scored_at.slice(0, 10),
      score: Math.round(s.avg_score * 10) / 10,
    }))

    const statusBreakdown = {
      healthy: tables.filter(t => t.status === 'healthy').length,
      warning: tables.filter(t => t.status === 'warning').length,
      critical: tables.filter(t => t.status === 'critical').length,
    }

    res.json({
      overallScore,
      activeAlerts: activeAlerts.cnt,
      monitoredTables: tables.length,
      totalRules: totalRules.cnt,
      scoreTrend,
      statusBreakdown,
    })
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch dashboard overview' })
  }
})

router.get('/metrics-trend', (req: Request, res: Response): void => {
  try {
    const { tableId, metricType, days = '30' } = req.query
    const daysNum = Math.min(Math.max(parseInt(days as string) || 30, 1), 90)

    let query = `
      SELECT table_id, metric_type, value, recorded_at
      FROM quality_metric
      WHERE recorded_at >= datetime('now', '-${daysNum} days')
    `
    const params: any[] = []

    if (tableId) {
      query += ' AND table_id = ?'
      params.push(tableId)
    }
    if (metricType) {
      query += ' AND metric_type = ?'
      params.push(metricType)
    }

    query += ' ORDER BY recorded_at ASC'

    const metrics = db.prepare(query).all(...params) as any[]

    const tableInfo = db.prepare('SELECT id, name FROM monitored_table').all() as { id: string; name: string }[]
    const tableNameMap = new Map(tableInfo.map(t => [t.id, t.name]))

    const result = metrics.map(m => ({
      date: m.recorded_at.slice(0, 10),
      value: m.value,
      table_name: tableNameMap.get(m.table_id) || m.table_id,
    }))

    res.json(result)
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch metrics trend' })
  }
})

router.get('/anomaly-heatmap', (_req: Request, res: Response): void => {
  try {
    const tables = db.prepare('SELECT id, name FROM monitored_table').all() as { id: string; name: string }[]
    const metricTypes = ['null_rate', 'duplicate_rate', 'distribution_drift', 'row_count']

    const heatmap: { tableName: string; metricType: string; severity: number }[] = []

    for (const table of tables) {
      for (const mt of metricTypes) {
        const latest = db.prepare(`
          SELECT value FROM quality_metric
          WHERE table_id = ? AND metric_type = ?
          ORDER BY recorded_at DESC LIMIT 1
        `).get(table.id, mt) as { value: number } | undefined

        const threshold = db.prepare(`
          SELECT threshold, condition FROM monitor_rule
          WHERE table_id = ? AND metric_type = ? AND severity = 'warning'
          LIMIT 1
        `).get(table.id, mt) as { threshold: number; condition: string } | undefined

        let severity = 0
        if (latest && threshold) {
          if (threshold.condition === '>') {
            severity = latest.value > threshold.threshold ? Math.min(1, latest.value / threshold.threshold - 0.5) : 0
          } else {
            severity = latest.value < threshold.threshold ? Math.min(1, 1 - latest.value / threshold.threshold) : 0
          }
        }

        heatmap.push({
          table_name: table.name,
          metric: mt,
          severity: Math.round(severity * 100) / 100,
        })
      }
    }

    res.json(heatmap)
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch anomaly heatmap' })
  }
})

router.get('/recent-alerts', (req: Request, res: Response): void => {
  try {
    const limit = Math.min(Math.max(parseInt(req.query.limit as string) || 10, 1), 50)

    const alerts = db.prepare(`
      SELECT a.*, mt.name as table_name
      FROM alert a
      JOIN monitored_table mt ON a.table_id = mt.id
      ORDER BY a.triggered_at DESC
      LIMIT ?
    `).all(limit) as any[]

    res.json(alerts)
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch recent alerts' })
  }
})

export default router
