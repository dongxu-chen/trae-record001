import { Router, type Request, type Response } from 'express'
import db from '../db.js'
import { v4 as uuidv4 } from 'uuid'

const router = Router()

function generateSampleData(metricType: string, tableName: string, count: number = 10): any[] {
  const samples: any[] = []
  const fieldNames = ['user_id', 'order_id', 'product_id', 'amount', 'phone', 'email', 'create_time']
  
  for (let i = 0; i < count; i++) {
    const sample: any = {
      id: 10000 + Math.floor(Math.random() * 90000),
    }
    
    for (const field of fieldNames) {
      const hasNull = Math.random() < 0.3
      if (hasNull && (metricType === 'null_rate' || Math.random() < 0.5)) {
        sample[field] = null
      } else if (field === 'amount') {
        sample[field] = metricType === 'distribution_drift' 
          ? Math.round(Math.random() * 1000000) / 100 
          : Math.round(Math.random() * 10000) / 100
      } else if (field.includes('id')) {
        sample[field] = `ID${100000 + Math.floor(Math.random() * 900000)}`
      } else if (field === 'phone') {
        sample[field] = hasNull ? null : `13${Math.floor(Math.random() * 1000000000)}`
      } else if (field === 'email') {
        sample[field] = hasNull ? null : `user${Math.floor(Math.random() * 10000)}@example.com`
      } else if (field === 'create_time') {
        sample[field] = `2026-05-${String(1 + Math.floor(Math.random() * 27)).padStart(2, '0')} ${String(Math.floor(Math.random() * 24)).padStart(2, '0')}:${String(Math.floor(Math.random() * 60)).padStart(2, '0')}:00`
      } else {
        sample[field] = `value_${Math.floor(Math.random() * 1000)}`
      }
    }
    
    if (metricType === 'null_rate') {
      const reasonFields = fieldNames.filter(f => sample[f] === null)
      sample._reason = reasonFields.length > 0 
        ? `字段 [${reasonFields.join(', ')}] 存在空值` 
        : '空值异常'
    } else if (metricType === 'duplicate_rate') {
      sample._reason = `与其他记录存在重复的 ${fieldNames[Math.floor(Math.random() * fieldNames.length)]}`
    } else if (metricType === 'distribution_drift') {
      sample._reason = `数值分布偏离历史趋势，amount=${sample.amount}`
    } else if (metricType === 'row_count') {
      sample._reason = '数据行数异常波动'
    } else {
      sample._reason = '数据质量异常'
    }
    
    sample._table = tableName
    sample._index = i + 1
    
    samples.push(sample)
  }
  
  return samples
}

router.get('/alert/:alertId', (req: Request, res: Response): void => {
  try {
    const { alertId } = req.params
    
    const samples = db.prepare(`
      SELECT s.*, a.message as alert_message, a.severity, t.name as table_name
      FROM anomaly_sample s
      LEFT JOIN alert a ON s.alert_id = a.id
      LEFT JOIN monitored_table t ON s.table_id = t.id
      WHERE s.alert_id = ?
      ORDER BY s.generated_at DESC
    `).all(alertId) as any[]
    
    if (samples.length === 0) {
      res.status(404).json({ error: 'No samples found for this alert' })
      return
    }
    
    const result = samples.map(s => ({
      ...s,
      sample_data: typeof s.sample_data === 'string' ? JSON.parse(s.sample_data) : s.sample_data
    }))
    
    res.json(result)
  } catch (error) {
    console.error('Failed to fetch samples:', error)
    res.status(500).json({ error: 'Failed to fetch samples' })
  }
})

router.get('/table/:tableId', (req: Request, res: Response): void => {
  try {
    const { tableId } = req.params
    const { metric_type, limit = 5 } = req.query
    
    let query = `
      SELECT s.*, t.name as table_name
      FROM anomaly_sample s
      LEFT JOIN monitored_table t ON s.table_id = t.id
      WHERE s.table_id = ?
    `
    const params: any[] = [tableId]
    
    if (metric_type) {
      query += ' AND s.metric_type = ?'
      params.push(metric_type)
    }
    
    query += ' ORDER BY s.generated_at DESC LIMIT ?'
    params.push(Number(limit))
    
    const samples = db.prepare(query).all(...params) as any[]
    
    const result = samples.map(s => ({
      ...s,
      sample_data: typeof s.sample_data === 'string' ? JSON.parse(s.sample_data) : s.sample_data
    }))
    
    res.json(result)
  } catch (error) {
    console.error('Failed to fetch samples:', error)
    res.status(500).json({ error: 'Failed to fetch samples' })
  }
})

router.post('/generate', (req: Request, res: Response): void => {
  try {
    const { alert_id, table_id, metric_type, sample_count = 10 } = req.body as {
      alert_id?: string
      table_id: string
      metric_type: string
      sample_count?: number
    }
    
    if (!table_id || !metric_type) {
      res.status(400).json({ error: 'table_id and metric_type are required' })
      return
    }
    
    const table = db.prepare('SELECT * FROM monitored_table WHERE id = ?').get(table_id) as any
    if (!table) {
      res.status(404).json({ error: 'Table not found' })
      return
    }
    
    let usedAlertId = alert_id
    if (!usedAlertId) {
      const activeAlert = db.prepare(
        "SELECT id FROM alert WHERE table_id = ? AND status = 'active' ORDER BY triggered_at DESC LIMIT 1"
      ).get(table_id) as { id: string } | undefined
      usedAlertId = activeAlert?.id
    }
    
    const sampleData = generateSampleData(metric_type, table.name, Math.min(sample_count, 50))
    const sampleId = uuidv4()
    const generatedAt = new Date().toISOString().replace('T', ' ').slice(0, 19)
    
    db.prepare(`
      INSERT INTO anomaly_sample (id, alert_id, table_id, metric_type, sample_data, sample_count, generated_at)
      VALUES (?, ?, ?, ?, ?, ?, ?)
    `).run(sampleId, usedAlertId || null, table_id, metric_type, JSON.stringify(sampleData), sampleData.length, generatedAt)
    
    res.json({
      id: sampleId,
      alert_id: usedAlertId,
      table_id,
      table_name: table.name,
      metric_type,
      sample_count: sampleData.length,
      sample_data: sampleData,
      generated_at: generatedAt,
      message: `成功生成 ${sampleData.length} 条异常样本`
    })
  } catch (error) {
    console.error('Failed to generate samples:', error)
    res.status(500).json({ error: 'Failed to generate samples' })
  }
})

router.post('/generate-for-active-alerts', (_req: Request, res: Response): void => {
  try {
    const activeAlerts = db.prepare(`
      SELECT a.id, a.table_id, r.metric_type, t.name as table_name
      FROM alert a
      JOIN monitored_table t ON a.table_id = t.id
      JOIN monitor_rule r ON a.rule_id = r.id
      WHERE a.status = 'active'
    `).all() as { id: string; table_id: string; metric_type: string; table_name: string }[]
    
    const results: { alert_id: string; table_name: string; metric_type: string; samples_generated: number }[] = []
    const generatedAt = new Date().toISOString().replace('T', ' ').slice(0, 19)
    
    for (const alert of activeAlerts) {
      const existing = db.prepare(
        'SELECT id FROM anomaly_sample WHERE alert_id = ?'
      ).get(alert.id)
      
      if (existing) continue
      
      const sampleData = generateSampleData(alert.metric_type, alert.table_name, 10)
      
      db.prepare(`
        INSERT INTO anomaly_sample (id, alert_id, table_id, metric_type, sample_data, sample_count, generated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
      `).run(uuidv4(), alert.id, alert.table_id, alert.metric_type, JSON.stringify(sampleData), sampleData.length, generatedAt)
      
      results.push({
        alert_id: alert.id,
        table_name: alert.table_name,
        metric_type: alert.metric_type,
        samples_generated: sampleData.length
      })
    }
    
    res.json({
      success: true,
      generated_count: results.length,
      total_samples: results.reduce((sum, r) => sum + r.samples_generated, 0),
      message: `为 ${results.length} 个活跃告警生成了异常样本`,
      results
    })
  } catch (error) {
    console.error('Failed to generate samples for alerts:', error)
    res.status(500).json({ error: 'Failed to generate samples' })
  }
})

router.delete('/:sampleId', (req: Request, res: Response): void => {
  try {
    const { sampleId } = req.params
    
    const result = db.prepare('DELETE FROM anomaly_sample WHERE id = ?').run(sampleId)
    
    if (result.changes === 0) {
      res.status(404).json({ error: 'Sample not found' })
      return
    }
    
    res.json({ message: 'Sample deleted successfully' })
  } catch (error) {
    console.error('Failed to delete sample:', error)
    res.status(500).json({ error: 'Failed to delete sample' })
  }
})

export default router
