import { Router, type Request, type Response } from 'express'
import db from '../db.js'
import { v4 as uuidv4 } from 'uuid'

const router = Router()

function simpleMovingAverage(data: number[], window: number): number[] {
  const result: number[] = []
  for (let i = 0; i < data.length; i++) {
    const start = Math.max(0, i - window + 1)
    const slice = data.slice(start, i + 1)
    const avg = slice.reduce((a, b) => a + b, 0) / slice.length
    result.push(avg)
  }
  return result
}

function linearRegression(data: { x: number; y: number }[]): { slope: number; intercept: number } {
  const n = data.length
  const sumX = data.reduce((sum, d) => sum + d.x, 0)
  const sumY = data.reduce((sum, d) => sum + d.y, 0)
  const sumXY = data.reduce((sum, d) => sum + d.x * d.y, 0)
  const sumX2 = data.reduce((sum, d) => sum + d.x * d.x, 0)
  
  const slope = (n * sumXY - sumX * sumY) / (n * sumX2 - sumX * sumX)
  const intercept = (sumY - slope * sumX) / n
  
  return { slope, intercept }
}

router.get('/overview', (_req: Request, res: Response): void => {
  try {
    const latestForecast = db.prepare(`
      SELECT * FROM quality_forecast 
      ORDER BY generated_at DESC, horizon_days ASC
      LIMIT 1
    `).get() as any
    
    if (!latestForecast) {
      res.status(404).json({ error: 'No forecast data available' })
      return
    }
    
    const forecasts = db.prepare(`
      SELECT * FROM quality_forecast 
      ORDER BY horizon_days ASC
    `).all() as any[]
    
    res.json({
      latest: latestForecast,
      forecasts,
      summary: {
        next_7_days: forecasts.find(f => f.horizon_days === 7)?.predicted_alerts || 0,
        next_14_days: forecasts.find(f => f.horizon_days === 14)?.predicted_alerts || 0,
        next_30_days: forecasts.find(f => f.horizon_days === 30)?.predicted_alerts || 0,
        trend_direction: latestForecast.trend_direction,
        confidence: latestForecast.confidence
      }
    })
  } catch (error) {
    console.error('Failed to fetch forecast overview:', error)
    res.status(500).json({ error: 'Failed to fetch forecast overview' })
  }
})

router.get('/timeseries', (req: Request, res: Response): void => {
  try {
    const { horizon = '30', include_history = 'true' } = req.query
    
    const horizonDays = parseInt(horizon as string)
    
    const historyDays = include_history === 'true' ? 30 : 0
    
    const alertHistory = db.prepare(`
      SELECT 
        DATE(triggered_at) as date,
        COUNT(*) as total,
        SUM(CASE WHEN severity = 'critical' THEN 1 ELSE 0 END) as critical,
        SUM(CASE WHEN severity = 'warning' THEN 1 ELSE 0 END) as warning
      FROM alert 
      WHERE triggered_at >= DATE('now', '-30 days')
      GROUP BY DATE(triggered_at)
      ORDER BY date ASC
    `).all() as { date: string; total: number; critical: number; warning: number }[]
    
    const historyValues = alertHistory.map(a => a.total)
    const smoothed = simpleMovingAverage(historyValues, 3)
    
    const dataPoints = alertHistory.map((a, i) => ({
      x: i,
      y: smoothed[i]
    }))
    
    const { slope, intercept } = linearRegression(dataPoints)
    
    const forecastPoints: {
      date: string
      predicted_alerts: number
      predicted_critical: number
      predicted_warning: number
      upper_bound: number
      lower_bound: number
      is_forecast: boolean
    }[] = []
    
    const today = new Date()
    
    for (let i = 0; i < historyDays; i++) {
      const date = new Date(today.getTime() - (historyDays - i) * 86400000)
      const dateStr = date.toISOString().slice(0, 10)
      const historyPoint = alertHistory.find(a => a.date === dateStr)
      
      if (historyPoint) {
        const stdDev = Math.sqrt(historyValues.reduce((sum, v) => sum + Math.pow(v - smoothed[alertHistory.indexOf(historyPoint)], 2), 0) / historyValues.length)
        forecastPoints.push({
          date: dateStr,
          predicted_alerts: historyPoint.total,
          predicted_critical: historyPoint.critical,
          predicted_warning: historyPoint.warning,
          upper_bound: Math.round(historyPoint.total + stdDev * 2),
          lower_bound: Math.max(0, Math.round(historyPoint.total - stdDev * 2)),
          is_forecast: false
        })
      }
    }
    
    const criticalRatio = historyValues.length > 0 
      ? alertHistory.reduce((sum, a) => sum + a.critical, 0) / alertHistory.reduce((sum, a) => sum + a.total, 0)
      : 0.35
    const warningRatio = 1 - criticalRatio
    
    for (let i = 1; i <= horizonDays; i++) {
      const forecastDate = new Date(today.getTime() + i * 86400000)
      const dateStr = forecastDate.toISOString().slice(0, 10)
      const xValue = historyDays + i
      
      const basePrediction = Math.max(0, slope * xValue + intercept)
      const randomness = (Math.random() - 0.5) * basePrediction * 0.3
      const predicted = Math.round(Math.max(0, basePrediction + randomness))
      
      const stdDev = Math.sqrt(historyValues.reduce((sum, v) => sum + Math.pow(v - smoothed[smoothed.length - 1], 2), 0) / historyValues.length)
      const marginOfError = stdDev * (1 + i / horizonDays * 0.5)
      
      forecastPoints.push({
        date: dateStr,
        predicted_alerts: predicted,
        predicted_critical: Math.round(predicted * criticalRatio),
        predicted_warning: Math.round(predicted * warningRatio),
        upper_bound: Math.round(predicted + marginOfError * 2),
        lower_bound: Math.max(0, Math.round(predicted - marginOfError * 2)),
        is_forecast: true
      })
    }
    
    const totalPredicted = forecastPoints
      .filter(f => f.is_forecast)
      .reduce((sum, f) => sum + f.predicted_alerts, 0)
    const totalCritical = forecastPoints
      .filter(f => f.is_forecast)
      .reduce((sum, f) => sum + f.predicted_critical, 0)
    const totalWarning = forecastPoints
      .filter(f => f.is_forecast)
      .reduce((sum, f) => sum + f.predicted_warning, 0)
    
    let trendDirection: 'increasing' | 'stable' | 'decreasing' = 'stable'
    if (Math.abs(slope) < 0.05) {
      trendDirection = 'stable'
    } else if (slope > 0) {
      trendDirection = 'increasing'
    } else {
      trendDirection = 'decreasing'
    }
    
    const confidence = Math.max(0.5, 1 - (horizonDays / 60))
    
    const history = forecastPoints.filter(f => !f.is_forecast).map(f => ({
      date: f.date,
      value: f.predicted_alerts,
      critical: f.predicted_critical,
      warning: f.predicted_warning
    }))
    
    const forecast = forecastPoints.filter(f => f.is_forecast).map(f => ({
      date: f.date,
      predicted_alerts: f.predicted_alerts,
      predicted_critical: f.predicted_critical,
      predicted_warning: f.predicted_warning,
      upper_bound: f.upper_bound,
      lower_bound: f.lower_bound
    }))
    
    res.json({
      horizon_days: horizonDays,
      trend_direction: trendDirection,
      confidence: Math.round(confidence * 100) / 100,
      total_predicted: totalPredicted,
      total_critical: totalCritical,
      total_warning: totalWarning,
      history,
      forecast,
      model: {
        type: 'linear_regression_with_smoothing',
        window_size: 3,
        slope: Math.round(slope * 1000) / 1000,
        intercept: Math.round(intercept * 100) / 100
      }
    })
  } catch (error) {
    console.error('Failed to generate forecast timeseries:', error)
    res.status(500).json({ error: 'Failed to generate forecast timeseries' })
  }
})

router.post('/generate', (req: Request, res: Response): void => {
  try {
    const { horizon_days = 30 } = req.body as { horizon_days?: number }
    
    const alertHistory = db.prepare(`
      SELECT 
        DATE(triggered_at) as date,
        COUNT(*) as total,
        SUM(CASE WHEN severity = 'critical' THEN 1 ELSE 0 END) as critical,
        SUM(CASE WHEN severity = 'warning' THEN 1 ELSE 0 END) as warning
      FROM alert 
      WHERE triggered_at >= DATE('now', '-30 days')
      GROUP BY DATE(triggered_at)
      ORDER BY date ASC
    `).all() as { date: string; total: number; critical: number; warning: number }[]
    
    if (alertHistory.length === 0) {
      res.status(400).json({ error: 'Insufficient historical data for forecasting' })
      return
    }
    
    const totalAlerts = alertHistory.reduce((sum, a) => sum + a.total, 0)
    const criticalRatio = totalAlerts > 0 
      ? alertHistory.reduce((sum, a) => sum + a.critical, 0) / totalAlerts
      : 0.35
    const warningRatio = 1 - criticalRatio
    
    const avgDaily = totalAlerts / alertHistory.length
    const recentAvg = alertHistory.slice(-7).reduce((sum, a) => sum + a.total, 0) / Math.min(7, alertHistory.length)
    
    let trendDirection: 'increasing' | 'stable' | 'decreasing' = 'stable'
    if (recentAvg > avgDaily * 1.2) {
      trendDirection = 'increasing'
    } else if (recentAvg < avgDaily * 0.8) {
      trendDirection = 'decreasing'
    }
    
    const trendMultiplier = trendDirection === 'increasing' ? 1.2 : trendDirection === 'decreasing' ? 0.8 : 1.0
    
    const today = new Date()
    const generatedAt = today.toISOString().replace('T', ' ').slice(0, 19)
    
    const horizons = [7, 14, 30]
    const results: { horizon_days: number; predicted: number; critical: number; warning: number }[] = []
    
    for (const h of horizons) {
      const basePrediction = Math.round(avgDaily * h * trendMultiplier)
      const critical = Math.round(basePrediction * criticalRatio)
      const warning = basePrediction - critical
      const confidence = Math.max(0.5, 1 - (h / 60))
      
      const existing = db.prepare(
        'SELECT id FROM quality_forecast WHERE horizon_days = ? ORDER BY generated_at DESC LIMIT 1'
      ).get(h) as { id: string } | undefined
      
      if (!existing) {
        const forecastDate = new Date(today.getTime() + h * 86400000).toISOString().slice(0, 10)
        db.prepare(`
          INSERT INTO quality_forecast (
            id, forecast_date, horizon_days, predicted_alerts, 
            predicted_critical, predicted_warning, trend_direction, 
            confidence, model_version, generated_at
          ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        `).run(
          uuidv4(), forecastDate, h, basePrediction, critical, warning,
          trendDirection, Math.round(confidence * 100) / 100, 'v1', generatedAt
        )
      }
      
      results.push({ horizon_days: h, predicted: basePrediction, critical, warning })
    }
    
    const sevenDayResult = results.find(r => r.horizon_days === 7)
    
    res.json({
      success: true,
      horizon_days: horizon_days,
      predicted_alerts: sevenDayResult?.predicted || 0,
      predicted_critical: sevenDayResult?.critical || 0,
      predicted_warning: sevenDayResult?.warning || 0,
      trend_direction: trendDirection,
      message: `成功生成 ${horizons.length} 个预测时段的数据`,
      results
    })
  } catch (error) {
    console.error('Failed to generate forecast:', error)
    res.status(500).json({ error: 'Failed to generate forecast' })
  }
})

router.get('/alerts-by-table', (req: Request, res: Response): void => {
  try {
    const { horizon = '7' } = req.query
    const horizonDays = parseInt(horizon as string)
    
    const tableAlertCounts = db.prepare(`
      SELECT 
        t.id as table_id,
        t.name as table_name,
        t.status,
        COUNT(a.id) as alert_count
      FROM monitored_table t
      LEFT JOIN alert a ON t.id = a.table_id AND a.status = 'active'
      GROUP BY t.id
      ORDER BY alert_count DESC
    `).all() as { table_id: string; table_name: string; status: string; alert_count: number }[]
    
    const totalActiveAlerts = tableAlertCounts.reduce((sum, t) => sum + t.alert_count, 0)
    
    const results = tableAlertCounts.map(t => {
      const riskFactor = t.status === 'critical' ? 1.5 : t.status === 'warning' ? 1.2 : 1.0
      const baseRatio = totalActiveAlerts > 0 ? t.alert_count / totalActiveAlerts : 1 / tableAlertCounts.length
      const predicted = Math.round(baseRatio * horizonDays * 2 * riskFactor)
      
      return {
        table_id: t.table_id,
        table_name: t.table_name,
        current_status: t.status,
        current_active_alerts: t.alert_count,
        predicted_alerts: predicted,
        risk_level: t.status === 'critical' ? 'high' : t.status === 'warning' ? 'medium' : 'low'
      }
    })
    
    res.json(results)
  } catch (error) {
    console.error('Failed to fetch forecast by table:', error)
    res.status(500).json({ error: 'Failed to fetch forecast by table' })
  }
})

export default router
