import Database from 'better-sqlite3'
import { v4 as uuidv4 } from 'uuid'
import path from 'path'
import fs from 'fs'
import { fileURLToPath } from 'url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

const dataDir = path.join(__dirname, '..', 'data')
if (!fs.existsSync(dataDir)) {
  fs.mkdirSync(dataDir, { recursive: true })
}

const dbPath = path.join(dataDir, 'quality.db')
const db = new Database(dbPath)

db.pragma('journal_mode = WAL')
db.pragma('foreign_keys = ON')

db.exec(`
  CREATE TABLE IF NOT EXISTS monitored_table (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    schema_name TEXT NOT NULL,
    description TEXT,
    row_count INTEGER DEFAULT 0,
    null_rate REAL DEFAULT 0,
    duplicate_rate REAL DEFAULT 0,
    distribution_drift REAL DEFAULT 0,
    quality_score REAL DEFAULT 0,
    status TEXT DEFAULT 'healthy',
    updated_at TEXT DEFAULT (datetime('now'))
  );
  CREATE TABLE IF NOT EXISTS monitor_rule (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    table_id TEXT NOT NULL REFERENCES monitored_table(id),
    metric_type TEXT NOT NULL,
    condition TEXT NOT NULL,
    threshold REAL NOT NULL,
    schedule TEXT NOT NULL,
    severity TEXT DEFAULT 'warning',
    enabled INTEGER DEFAULT 1,
    field_importance TEXT DEFAULT 'medium',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
  );
  CREATE TABLE IF NOT EXISTS quality_metric (
    id TEXT PRIMARY KEY,
    table_id TEXT NOT NULL REFERENCES monitored_table(id),
    metric_type TEXT NOT NULL,
    value REAL NOT NULL,
    recorded_at TEXT DEFAULT (datetime('now'))
  );
  CREATE TABLE IF NOT EXISTS alert (
    id TEXT PRIMARY KEY,
    rule_id TEXT REFERENCES monitor_rule(id),
    table_id TEXT NOT NULL REFERENCES monitored_table(id),
    severity TEXT NOT NULL DEFAULT 'warning',
    status TEXT NOT NULL DEFAULT 'active',
    message TEXT NOT NULL,
    actual_value REAL,
    threshold_value REAL,
    triggered_at TEXT DEFAULT (datetime('now')),
    acknowledged_at TEXT,
    resolved_at TEXT,
    resolution TEXT
  );
  CREATE TABLE IF NOT EXISTS quality_score (
    id TEXT PRIMARY KEY,
    table_id TEXT NOT NULL REFERENCES monitored_table(id),
    completeness REAL DEFAULT 0,
    consistency REAL DEFAULT 0,
    timeliness REAL DEFAULT 0,
    accuracy REAL DEFAULT 0,
    overall REAL DEFAULT 0,
    scored_at TEXT DEFAULT (datetime('now'))
  );
  CREATE TABLE IF NOT EXISTS lineage_edge (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES monitored_table(id),
    target_id TEXT NOT NULL REFERENCES monitored_table(id),
    type TEXT DEFAULT 'data_flow'
  );
  CREATE TABLE IF NOT EXISTS field_importance (
    id TEXT PRIMARY KEY,
    table_id TEXT NOT NULL REFERENCES monitored_table(id),
    field_name TEXT NOT NULL,
    importance TEXT NOT NULL DEFAULT 'medium',
    updated_at TEXT DEFAULT (datetime('now'))
  );
  CREATE TABLE IF NOT EXISTS score_weight_config (
    id TEXT PRIMARY KEY,
    table_id TEXT NOT NULL REFERENCES monitored_table(id),
    completeness_weight REAL DEFAULT 0.3,
    consistency_weight REAL DEFAULT 0.25,
    timeliness_weight REAL DEFAULT 0.2,
    accuracy_weight REAL DEFAULT 0.25,
    updated_at TEXT DEFAULT (datetime('now'))
  );
  CREATE TABLE IF NOT EXISTS report_node (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    type TEXT NOT NULL DEFAULT 'report',
    status TEXT DEFAULT 'healthy',
    updated_at TEXT DEFAULT (datetime('now'))
  );
  CREATE TABLE IF NOT EXISTS report_lineage_edge (
    id TEXT PRIMARY KEY,
    source_table_id TEXT NOT NULL REFERENCES monitored_table(id),
    target_report_id TEXT NOT NULL REFERENCES report_node(id),
    impact_type TEXT DEFAULT 'feed'
  );
  CREATE TABLE IF NOT EXISTS sql_parse_log (
    id TEXT PRIMARY KEY,
    target_table_id TEXT REFERENCES monitored_table(id),
    sql_content TEXT NOT NULL,
    source_tables TEXT,
    parse_status TEXT DEFAULT 'pending',
    new_edges_count INTEGER DEFAULT 0,
    error_message TEXT,
    parsed_at TEXT DEFAULT (datetime('now'))
  );
  CREATE TABLE IF NOT EXISTS anomaly_sample (
    id TEXT PRIMARY KEY,
    alert_id TEXT REFERENCES alert(id),
    table_id TEXT NOT NULL REFERENCES monitored_table(id),
    metric_type TEXT NOT NULL,
    sample_data TEXT NOT NULL,
    sample_count INTEGER DEFAULT 0,
    generated_at TEXT DEFAULT (datetime('now'))
  );
  CREATE TABLE IF NOT EXISTS quality_forecast (
    id TEXT PRIMARY KEY,
    forecast_date TEXT NOT NULL,
    horizon_days INTEGER NOT NULL,
    predicted_alerts INTEGER DEFAULT 0,
    predicted_critical INTEGER DEFAULT 0,
    predicted_warning INTEGER DEFAULT 0,
    trend_direction TEXT DEFAULT 'stable',
    confidence REAL DEFAULT 0.8,
    model_version TEXT DEFAULT 'v1',
    generated_at TEXT DEFAULT (datetime('now'))
  );
`)

const tableCount = db.prepare('SELECT COUNT(*) as cnt FROM monitored_table').get() as { cnt: number }
if (tableCount.cnt === 0) {
  seedDatabase()
} else {
  runMigrations()
}

function runMigrations() {
  const now = new Date().toISOString().replace('T', ' ').slice(0, 19)

  const fieldImpCount = db.prepare('SELECT COUNT(*) as cnt FROM field_importance').get() as { cnt: number }
  const weightConfigCount = db.prepare('SELECT COUNT(*) as cnt FROM score_weight_config').get() as { cnt: number }
  const reportNodeCount = db.prepare('SELECT COUNT(*) as cnt FROM report_node').get() as { cnt: number }
  const sqlParseLogCount = db.prepare('SELECT COUNT(*) as cnt FROM sql_parse_log').get() as { cnt: number }
  const anomalySampleCount = db.prepare('SELECT COUNT(*) as cnt FROM anomaly_sample').get() as { cnt: number }
  const qualityForecastCount = db.prepare('SELECT COUNT(*) as cnt FROM quality_forecast').get() as { cnt: number }

  if (fieldImpCount.cnt > 0 && weightConfigCount.cnt > 0 && reportNodeCount.cnt > 0 && 
      sqlParseLogCount.cnt > 0 && anomalySampleCount.cnt > 0 && qualityForecastCount.cnt > 0) {
    return
  }

  const insertFieldImportance = db.prepare(`
    INSERT INTO field_importance (id, table_id, field_name, importance, updated_at)
    VALUES (?, ?, ?, ?, ?)
  `)

  const insertScoreWeightConfig = db.prepare(`
    INSERT INTO score_weight_config (id, table_id, completeness_weight, consistency_weight, timeliness_weight, accuracy_weight, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?)
  `)

  const insertReportNode = db.prepare(`
    INSERT INTO report_node (id, name, description, type, status, updated_at)
    VALUES (?, ?, ?, ?, ?, ?)
  `)

  const insertReportLineageEdge = db.prepare(`
    INSERT INTO report_lineage_edge (id, source_table_id, target_report_id, impact_type)
    VALUES (?, ?, ?, ?)
  `)

  const insertSqlParseLog = db.prepare(`
    INSERT INTO sql_parse_log (id, target_table_id, sql_content, source_tables, parse_status, new_edges_count, error_message, parsed_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
  `)

  const insertAnomalySample = db.prepare(`
    INSERT INTO anomaly_sample (id, alert_id, table_id, metric_type, sample_data, sample_count, generated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?)
  `)

  const insertQualityForecast = db.prepare(`
    INSERT INTO quality_forecast (id, forecast_date, horizon_days, predicted_alerts, predicted_critical, predicted_warning, trend_direction, confidence, model_version, generated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  `)

  const tables = db.prepare('SELECT id, name FROM monitored_table').all() as { id: string; name: string }[]
  const tableMap = new Map(tables.map(t => [t.name, t.id]))

  const migrate = db.transaction(() => {
    if (fieldImpCount.cnt === 0) {
      const fieldImportanceData: [string, string, string][] = [
        ['dim_user', 'user_id', 'critical'], ['dim_user', 'phone', 'high'], ['dim_user', 'email', 'high'], ['dim_user', 'register_time', 'medium'], ['dim_user', 'avatar_url', 'low'],
        ['dim_product', 'product_id', 'critical'], ['dim_product', 'price', 'critical'], ['dim_product', 'category_id', 'high'], ['dim_product', 'name', 'high'], ['dim_product', 'description', 'low'],
        ['dim_store', 'store_id', 'critical'], ['dim_store', 'region', 'high'], ['dim_store', 'address', 'medium'], ['dim_store', 'manager', 'low'], ['dim_store', 'opening_date', 'medium'],
        ['dim_category', 'category_id', 'critical'], ['dim_category', 'parent_id', 'high'], ['dim_category', 'level', 'medium'], ['dim_category', 'name', 'high'], ['dim_category', 'icon_url', 'low'],
        ['fact_orders', 'order_id', 'critical'], ['fact_orders', 'user_id', 'critical'], ['fact_orders', 'amount', 'critical'], ['fact_orders', 'status', 'high'], ['fact_orders', 'create_time', 'medium'],
        ['fact_payments', 'payment_id', 'critical'], ['fact_payments', 'order_id', 'critical'], ['fact_payments', 'channel', 'high'], ['fact_payments', 'amount', 'high'], ['fact_payments', 'pay_time', 'medium'],
        ['fact_returns', 'return_id', 'critical'], ['fact_returns', 'order_id', 'critical'], ['fact_returns', 'reason', 'medium'], ['fact_returns', 'amount', 'high'], ['fact_returns', 'create_time', 'medium'],
        ['ods_log', 'log_id', 'critical'], ['ods_log', 'user_id', 'high'], ['ods_log', 'event_type', 'high'], ['ods_log', 'event_time', 'critical'], ['ods_log', 'payload', 'low'],
        ['dws_user_daily', 'user_id', 'critical'], ['dws_user_daily', 'date', 'critical'], ['dws_user_daily', 'order_count', 'high'], ['dws_user_daily', 'total_amount', 'high'], ['dws_user_daily', 'active_duration', 'medium'],
        ['ads_sales_report', 'date', 'critical'], ['ads_sales_report', 'region', 'high'], ['ads_sales_report', 'total_sales', 'critical'], ['ads_sales_report', 'order_count', 'high'], ['ads_sales_report', 'return_rate', 'medium'],
      ]
      for (const [tableName, fieldName, importance] of fieldImportanceData) {
        const tid = tableMap.get(tableName)
        if (tid) {
          insertFieldImportance.run(uuidv4(), tid, fieldName, importance, now)
        }
      }
    }

    if (weightConfigCount.cnt === 0) {
      const criticalTableNames = ['ods_log', 'dws_user_daily', 'fact_returns']
      const warningTableNames = ['dim_store', 'fact_returns']
      for (const t of tables) {
        let cw = 0.3, csw = 0.25, tw = 0.2, aw = 0.25
        if (criticalTableNames.includes(t.name)) {
          aw = 0.35; tw = 0.15; cw = 0.3; csw = 0.2
        }
        if (warningTableNames.includes(t.name)) {
          cw = 0.35; csw = 0.2; tw = 0.2; aw = 0.25
        }
        const sum = cw + csw + tw + aw
        cw = Math.round(cw / sum * 1000) / 1000
        csw = Math.round(csw / sum * 1000) / 1000
        tw = Math.round(tw / sum * 1000) / 1000
        aw = Math.round(aw / sum * 1000) / 1000
        insertScoreWeightConfig.run(uuidv4(), t.id, cw, csw, tw, aw, now)
      }
    }

    if (reportNodeCount.cnt === 0) {
      const reportNodes = [
        { id: uuidv4(), name: 'rpt_daily_sales', description: '每日销售报表', status: 'warning' },
        { id: uuidv4(), name: 'rpt_user_activity', description: '用户活跃度报告', status: 'critical' },
        { id: uuidv4(), name: 'rpt_return_analysis', description: '退款分析报表', status: 'warning' },
        { id: uuidv4(), name: 'rpt_category_performance', description: '品类业绩报表', status: 'healthy' },
      ]
      const reportMap = new Map(reportNodes.map(r => [r.name, r.id]))
      for (const r of reportNodes) {
        insertReportNode.run(r.id, r.name, r.description, 'report', r.status, now)
      }

      const reportLineageData: [string, string, string][] = [
        ['ads_sales_report', 'rpt_daily_sales', 'feed'],
        ['fact_payments', 'rpt_daily_sales', 'feed'],
        ['dws_user_daily', 'rpt_user_activity', 'feed'],
        ['dim_user', 'rpt_user_activity', 'dimension'],
        ['fact_returns', 'rpt_return_analysis', 'feed'],
        ['dim_product', 'rpt_return_analysis', 'dimension'],
        ['dim_category', 'rpt_category_performance', 'feed'],
        ['ads_sales_report', 'rpt_category_performance', 'feed'],
        ['fact_orders', 'rpt_daily_sales', 'feed'],
        ['fact_returns', 'rpt_user_activity', 'feed'],
      ]
      for (const [tableName, reportName, impactType] of reportLineageData) {
        const sourceTableId = tableMap.get(tableName)
        const targetReportId = reportMap.get(reportName)
        if (sourceTableId && targetReportId) {
          insertReportLineageEdge.run(uuidv4(), sourceTableId, targetReportId, impactType)
        }
      }
    }

    if (sqlParseLogCount.cnt === 0) {
      const parseLogs = [
        { target: 'dws_user_daily', sql: 'INSERT OVERWRITE dws_user_daily SELECT user_id, date, COUNT(*) as order_count, SUM(amount) as total_amount FROM fact_orders WHERE dt = ? GROUP BY user_id, date', sources: 'fact_orders', status: 'success', edges: 1 },
        { target: 'ads_sales_report', sql: 'INSERT OVERWRITE ads_sales_report SELECT date, region, SUM(amount) as total_sales, COUNT(DISTINCT order_id) as order_count FROM fact_orders o JOIN dim_store s ON o.store_id = s.store_id GROUP BY date, region', sources: 'fact_orders,dim_store', status: 'success', edges: 2 },
        { target: 'fact_payments', sql: 'INSERT INTO fact_payments SELECT p.* FROM ods_payments p JOIN fact_orders o ON p.order_id = o.order_id', sources: 'ods_payments,fact_orders', status: 'success', edges: 1 },
      ]
      for (const log of parseLogs) {
        const targetId = tableMap.get(log.target)
        insertSqlParseLog.run(uuidv4(), targetId, log.sql, log.sources, log.status, log.edges, null, now)
      }
    }

    if (anomalySampleCount.cnt === 0) {
      const alerts = db.prepare('SELECT a.id, a.table_id, t.name as table_name FROM alert a JOIN monitored_table t ON a.table_id = t.id WHERE a.status = ?').all('active') as { id: string; table_id: string; table_name: string }[]
      for (const alert of alerts.slice(0, 5)) {
        const sampleData = JSON.stringify([
          { id: 1001, field: 'user_id', value: null, reason: '空值异常' },
          { id: 1002, field: 'user_id', value: null, reason: '空值异常' },
          { id: 1003, field: 'amount', value: 999999, reason: '数值异常' },
        ])
        insertAnomalySample.run(uuidv4(), alert.id, alert.table_id, 'null_rate', sampleData, 3, now)
      }
    }

    if (qualityForecastCount.cnt === 0) {
      const today = new Date()
      for (let horizon of [7, 14, 30]) {
        const baseAlerts = 8
        const trend = horizon <= 7 ? 'increasing' : horizon <= 14 ? 'stable' : 'decreasing'
        const predicted = horizon === 7 ? 12 : horizon === 14 ? 20 : 35
        const critical = Math.round(predicted * 0.35)
        const warning = predicted - critical
        const forecastDate = new Date(today.getTime() + horizon * 86400000).toISOString().slice(0, 10)
        insertQualityForecast.run(
          uuidv4(), forecastDate, horizon, predicted, critical, warning, trend,
          horizon === 7 ? 0.92 : horizon === 14 ? 0.85 : 0.75, 'v1', now
        )
      }
    }
  })

  try {
    migrate()
    console.log('Migrations completed successfully')
  } catch (e) {
    console.warn('Migration warning (may already be applied):', e)
  }
}

function seedDatabase() {
  const insertTable = db.prepare(`
    INSERT INTO monitored_table (id, name, schema_name, description, row_count, null_rate, duplicate_rate, distribution_drift, quality_score, status, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  `)

  const insertRule = db.prepare(`
    INSERT INTO monitor_rule (id, name, table_id, metric_type, condition, threshold, schedule, severity, enabled, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  `)

  const insertMetric = db.prepare(`
    INSERT INTO quality_metric (id, table_id, metric_type, value, recorded_at)
    VALUES (?, ?, ?, ?, ?)
  `)

  const insertAlert = db.prepare(`
    INSERT INTO alert (id, rule_id, table_id, severity, status, message, actual_value, threshold_value, triggered_at, acknowledged_at, resolved_at, resolution)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  `)

  const insertScore = db.prepare(`
    INSERT INTO quality_score (id, table_id, completeness, consistency, timeliness, accuracy, overall, scored_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
  `)

  const insertEdge = db.prepare(`
    INSERT INTO lineage_edge (id, source_id, target_id, type)
    VALUES (?, ?, ?, ?)
  `)

  const insertFieldImportance = db.prepare(`
    INSERT INTO field_importance (id, table_id, field_name, importance, updated_at)
    VALUES (?, ?, ?, ?, ?)
  `)

  const insertScoreWeightConfig = db.prepare(`
    INSERT INTO score_weight_config (id, table_id, completeness_weight, consistency_weight, timeliness_weight, accuracy_weight, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?)
  `)

  const insertReportNode = db.prepare(`
    INSERT INTO report_node (id, name, description, type, status, updated_at)
    VALUES (?, ?, ?, ?, ?, ?)
  `)

  const insertReportLineageEdge = db.prepare(`
    INSERT INTO report_lineage_edge (id, source_table_id, target_report_id, impact_type)
    VALUES (?, ?, ?, ?)
  `)

  const insertSqlParseLog = db.prepare(`
    INSERT INTO sql_parse_log (id, target_table_id, sql_content, source_tables, parse_status, new_edges_count, error_message, parsed_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
  `)

  const insertAnomalySample = db.prepare(`
    INSERT INTO anomaly_sample (id, alert_id, table_id, metric_type, sample_data, sample_count, generated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?)
  `)

  const insertQualityForecast = db.prepare(`
    INSERT INTO quality_forecast (id, forecast_date, horizon_days, predicted_alerts, predicted_critical, predicted_warning, trend_direction, confidence, model_version, generated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  `)

  const tables = [
    { id: uuidv4(), name: 'dim_user', schema_name: 'dw', description: '用户维度表，存储注册用户的基本信息、属性及标签数据', row_count: 2350000, null_rate: 0.012, duplicate_rate: 0.003, distribution_drift: 0.05, quality_score: 94.5, status: 'healthy' },
    { id: uuidv4(), name: 'dim_product', schema_name: 'dw', description: '商品维度表，存储SKU信息、品类归属及价格区间', row_count: 856000, null_rate: 0.035, duplicate_rate: 0.008, distribution_drift: 0.12, quality_score: 87.2, status: 'healthy' },
    { id: uuidv4(), name: 'dim_store', schema_name: 'dw', description: '门店维度表，存储线下门店信息及区域归属', row_count: 3240, null_rate: 0.085, duplicate_rate: 0.015, distribution_drift: 0.18, quality_score: 72.3, status: 'warning' },
    { id: uuidv4(), name: 'dim_category', schema_name: 'dw', description: '品类维度表，存储商品分类层级结构', row_count: 1560, null_rate: 0.02, duplicate_rate: 0.001, distribution_drift: 0.03, quality_score: 96.1, status: 'healthy' },
    { id: uuidv4(), name: 'fact_orders', schema_name: 'dw', description: '订单事实表，记录所有订单的交易明细及状态流转', row_count: 45800000, null_rate: 0.008, duplicate_rate: 0.002, distribution_drift: 0.06, quality_score: 95.8, status: 'healthy' },
    { id: uuidv4(), name: 'fact_payments', schema_name: 'dw', description: '支付事实表，记录订单支付流水及支付渠道信息', row_count: 42300000, null_rate: 0.015, duplicate_rate: 0.004, distribution_drift: 0.07, quality_score: 91.4, status: 'healthy' },
    { id: uuidv4(), name: 'fact_returns', schema_name: 'dw', description: '退货事实表，记录退货申请及退款处理流程', row_count: 3200000, null_rate: 0.045, duplicate_rate: 0.012, distribution_drift: 0.22, quality_score: 68.5, status: 'warning' },
    { id: uuidv4(), name: 'ods_log', schema_name: 'ods', description: '原始日志表，采集自前端埋点及服务端日志的原始数据', row_count: 156000000, null_rate: 0.15, duplicate_rate: 0.035, distribution_drift: 0.35, quality_score: 55.2, status: 'critical' },
    { id: uuidv4(), name: 'dws_user_daily', schema_name: 'dws', description: '用户日汇总表，按天汇总用户活跃、交易及行为指标', row_count: 8900000, null_rate: 0.025, duplicate_rate: 0.006, distribution_drift: 0.28, quality_score: 62.7, status: 'critical' },
    { id: uuidv4(), name: 'ads_sales_report', schema_name: 'ads', description: '销售报表，面向业务方的多维销售分析宽表', row_count: 450000, null_rate: 0.01, duplicate_rate: 0.002, distribution_drift: 0.04, quality_score: 93.8, status: 'healthy' },
  ]

  const ruleTemplates = [
    { metric_type: 'null_rate', condition: '>', severity: 'warning' },
    { metric_type: 'null_rate', condition: '>', severity: 'critical' },
    { metric_type: 'duplicate_rate', condition: '>', severity: 'warning' },
    { metric_type: 'row_count', condition: '<', severity: 'critical' },
    { metric_type: 'distribution_drift', condition: '>', severity: 'warning' },
    { metric_type: 'distribution_drift', condition: '>', severity: 'critical' },
  ]

  const now = new Date()

  const seed = db.transaction(() => {
    for (const t of tables) {
      const updatedAt = new Date(now.getTime() - Math.random() * 3600000).toISOString().replace('T', ' ').slice(0, 19)
      insertTable.run(t.id, t.name, t.schema_name, t.description, t.row_count, t.null_rate, t.duplicate_rate, t.distribution_drift, t.quality_score, t.status, updatedAt)

      const ruleConfigs = [
        { ...ruleTemplates[0], name: `${t.name} 空值率预警`, threshold: 0.05, schedule: '0 */6 * * *' },
        { ...ruleTemplates[1], name: `${t.name} 空值率严重告警`, threshold: 0.10, schedule: '0 */6 * * *' },
        { ...ruleTemplates[2], name: `${t.name} 重复率预警`, threshold: 0.02, schedule: '0 8 * * *' },
        { ...ruleTemplates[3], name: `${t.name} 行数骤降告警`, threshold: t.row_count * 0.5, schedule: '0 9 * * *' },
        { ...ruleTemplates[4], name: `${t.name} 分布漂移预警`, threshold: 0.15, schedule: '0 10 * * *' },
        { ...ruleTemplates[5], name: `${t.name} 分布漂移严重告警`, threshold: 0.25, schedule: '0 10 * * *' },
      ]

      const rulesForTable: { id: string; metric_type: string; threshold: number; severity: string }[] = []
      for (const rc of ruleConfigs) {
        const ruleId = uuidv4()
        const createdAt = new Date(now.getTime() - Math.random() * 30 * 86400000).toISOString().replace('T', ' ').slice(0, 19)
        insertRule.run(ruleId, rc.name, t.id, rc.metric_type, rc.condition, rc.threshold, rc.schedule, rc.severity, 1, createdAt, createdAt)
        rulesForTable.push({ id: ruleId, metric_type: rc.metric_type, threshold: rc.threshold, severity: rc.severity })
      }

      for (let day = 29; day >= 0; day--) {
        const date = new Date(now.getTime() - day * 86400000)
        const dateStr = date.toISOString().replace('T', ' ').slice(0, 10)

        const baseNull = t.null_rate
        const baseDup = t.duplicate_rate
        const baseDrift = t.distribution_drift
        const noise = () => (Math.random() - 0.5) * 0.02

        const nullVal = Math.max(0, Math.min(1, baseNull + noise() + (day < 5 && t.status !== 'healthy' ? 0.02 : 0)))
        const dupVal = Math.max(0, Math.min(1, baseDup + noise()))
        const driftVal = Math.max(0, Math.min(1, baseDrift + noise() + (day < 3 && t.status === 'critical' ? 0.05 : 0)))
        const rowCountVal = Math.max(0, t.row_count * (1 + (Math.random() - 0.5) * 0.05))

        insertMetric.run(uuidv4(), t.id, 'null_rate', nullVal, `${dateStr} 06:00:00`)
        insertMetric.run(uuidv4(), t.id, 'duplicate_rate', dupVal, `${dateStr} 08:00:00`)
        insertMetric.run(uuidv4(), t.id, 'distribution_drift', driftVal, `${dateStr} 10:00:00`)
        insertMetric.run(uuidv4(), t.id, 'row_count', rowCountVal, `${dateStr} 09:00:00`)
      }

      const completenessBase = 100 - t.null_rate * 500
      const consistencyBase = 100 - t.duplicate_rate * 800
      const timelinessBase = 100 - t.distribution_drift * 200
      const accuracyBase = t.quality_score

      for (let day = 29; day >= 0; day--) {
        const date = new Date(now.getTime() - day * 86400000)
        const dateStr = date.toISOString().replace('T', ' ').slice(0, 19)

        const cNoise = () => (Math.random() - 0.5) * 3
        const completeness = Math.max(0, Math.min(100, completenessBase + cNoise()))
        const consistency = Math.max(0, Math.min(100, consistencyBase + cNoise()))
        const timeliness = Math.max(0, Math.min(100, timelinessBase + cNoise()))
        const accuracy = Math.max(0, Math.min(100, accuracyBase + cNoise()))
        const overall = Math.round((completeness * 0.3 + consistency * 0.25 + timeliness * 0.2 + accuracy * 0.25) * 10) / 10

        insertScore.run(uuidv4(), t.id, Math.round(completeness * 10) / 10, Math.round(consistency * 10) / 10, Math.round(timeliness * 10) / 10, Math.round(accuracy * 10) / 10, overall, dateStr)
      }
    }

    const criticalTables = tables.filter(t => t.status === 'critical')
    const warningTables = tables.filter(t => t.status === 'warning')
    const healthyTables = tables.filter(t => t.status === 'healthy')

    for (const t of criticalTables) {
      const rules = db.prepare('SELECT id, metric_type, threshold, severity FROM monitor_rule WHERE table_id = ?').all(t.id) as { id: string; metric_type: string; threshold: number; severity: string }[]

      for (let i = 0; i < 4; i++) {
        const rule = rules[Math.floor(Math.random() * rules.length)]
        const triggeredAt = new Date(now.getTime() - Math.random() * 7 * 86400000)
        const triggeredStr = triggeredAt.toISOString().replace('T', ' ').slice(0, 19)
        const actualValue = rule.metric_type === 'null_rate' ? t.null_rate + Math.random() * 0.05
          : rule.metric_type === 'duplicate_rate' ? t.duplicate_rate + Math.random() * 0.02
          : rule.metric_type === 'distribution_drift' ? t.distribution_drift + Math.random() * 0.1
          : t.row_count * (0.3 + Math.random() * 0.3)

        let status: string, acknowledgedAt: string | null, resolvedAt: string | null, resolution: string | null
        if (i < 2) {
          status = 'active'
          acknowledgedAt = i === 0 ? new Date(triggeredAt.getTime() + 3600000).toISOString().replace('T', ' ').slice(0, 19) : null
          resolvedAt = null
          resolution = null
        } else if (i === 2) {
          status = 'acknowledged'
          acknowledgedAt = new Date(triggeredAt.getTime() + 1800000).toISOString().replace('T', ' ').slice(0, 19)
          resolvedAt = null
          resolution = null
        } else {
          status = 'resolved'
          acknowledgedAt = new Date(triggeredAt.getTime() + 1800000).toISOString().replace('T', ' ').slice(0, 19)
          resolvedAt = new Date(triggeredAt.getTime() + 86400000).toISOString().replace('T', ' ').slice(0, 19)
          resolution = '已定位根因并完成修复，数据已重新跑批补齐'
        }

        const msgTemplates: Record<string, string> = {
          null_rate: `${t.name} 空值率 ${Math.round(actualValue * 100)}% 超过阈值 ${Math.round(rule.threshold * 100)}%`,
          duplicate_rate: `${t.name} 重复率 ${Math.round(actualValue * 100)}% 超过阈值 ${Math.round(rule.threshold * 100)}%`,
          distribution_drift: `${t.name} 数据分布漂移 ${Math.round(actualValue * 100)}% 超过阈值 ${Math.round(rule.threshold * 100)}%`,
          row_count: `${t.name} 行数 ${Math.round(actualValue)} 低于阈值 ${Math.round(rule.threshold)}`,
        }

        insertAlert.run(uuidv4(), rule.id, t.id, rule.severity, status, msgTemplates[rule.metric_type] || `${t.name} 数据质量异常`, actualValue, rule.threshold, triggeredStr, acknowledgedAt, resolvedAt, resolution)
      }
    }

    for (const t of warningTables) {
      const rules = db.prepare('SELECT id, metric_type, threshold, severity FROM monitor_rule WHERE table_id = ?').all(t.id) as { id: string; metric_type: string; threshold: number; severity: string }[]

      for (let i = 0; i < 2; i++) {
        const rule = rules[Math.floor(Math.random() * rules.length)]
        const triggeredAt = new Date(now.getTime() - Math.random() * 14 * 86400000)
        const triggeredStr = triggeredAt.toISOString().replace('T', ' ').slice(0, 19)
        const actualValue = rule.metric_type === 'null_rate' ? t.null_rate + Math.random() * 0.03
          : rule.metric_type === 'duplicate_rate' ? t.duplicate_rate + Math.random() * 0.01
          : rule.metric_type === 'distribution_drift' ? t.distribution_drift + Math.random() * 0.05
          : t.row_count * (0.6 + Math.random() * 0.2)

        let status: string, acknowledgedAt: string | null, resolvedAt: string | null, resolution: string | null
        if (i === 0) {
          status = 'active'
          acknowledgedAt = null
          resolvedAt = null
          resolution = null
        } else {
          status = 'resolved'
          acknowledgedAt = new Date(triggeredAt.getTime() + 7200000).toISOString().replace('T', ' ').slice(0, 19)
          resolvedAt = new Date(triggeredAt.getTime() + 2 * 86400000).toISOString().replace('T', ' ').slice(0, 19)
          resolution = '数据源异常已修复，已触发重跑任务'
        }

        const msgTemplates: Record<string, string> = {
          null_rate: `${t.name} 空值率 ${Math.round(actualValue * 100)}% 超过阈值 ${Math.round(rule.threshold * 100)}%`,
          duplicate_rate: `${t.name} 重复率 ${Math.round(actualValue * 100)}% 超过阈值 ${Math.round(rule.threshold * 100)}%`,
          distribution_drift: `${t.name} 数据分布漂移 ${Math.round(actualValue * 100)}% 超过阈值 ${Math.round(rule.threshold * 100)}%`,
          row_count: `${t.name} 行数 ${Math.round(actualValue)} 低于阈值 ${Math.round(rule.threshold)}`,
        }

        insertAlert.run(uuidv4(), rule.id, t.id, rule.severity, status, msgTemplates[rule.metric_type] || `${t.name} 数据质量异常`, actualValue, rule.threshold, triggeredStr, acknowledgedAt, resolvedAt, resolution)
      }
    }

    for (const t of healthyTables) {
      const rules = db.prepare('SELECT id, metric_type, threshold, severity FROM monitor_rule WHERE table_id = ? AND severity = ?').all(t.id, 'warning') as { id: string; metric_type: string; threshold: number; severity: string }[]
      if (rules.length === 0) continue

      const rule = rules[Math.floor(Math.random() * rules.length)]
      const triggeredAt = new Date(now.getTime() - Math.random() * 30 * 86400000)
      const triggeredStr = triggeredAt.toISOString().replace('T', ' ').slice(0, 19)

      insertAlert.run(
        uuidv4(), rule.id, t.id, 'warning', 'resolved',
        `${t.name} 指标轻微波动，已自动恢复`,
        rule.threshold * 0.8, rule.threshold,
        triggeredStr,
        new Date(triggeredAt.getTime() + 3600000).toISOString().replace('T', ' ').slice(0, 19),
        new Date(triggeredAt.getTime() + 4 * 3600000).toISOString().replace('T', ' ').slice(0, 19),
        '指标自动恢复正常，判定为瞬时波动'
      )
    }

    const lineageEdges = [
      ['ods_log', 'dws_user_daily', 'data_flow'],
      ['dim_user', 'dws_user_daily', 'data_flow'],
      ['dim_user', 'fact_orders', 'dimension'],
      ['dim_product', 'fact_orders', 'dimension'],
      ['dim_store', 'fact_orders', 'dimension'],
      ['fact_orders', 'fact_payments', 'data_flow'],
      ['fact_orders', 'fact_returns', 'data_flow'],
      ['dim_category', 'dim_product', 'hierarchy'],
      ['dws_user_daily', 'ads_sales_report', 'data_flow'],
      ['fact_payments', 'ads_sales_report', 'data_flow'],
      ['fact_returns', 'ads_sales_report', 'data_flow'],
      ['dim_product', 'ads_sales_report', 'dimension'],
    ]

    const tableMap = new Map(tables.map(t => [t.name, t.id]))
    for (const [sourceName, targetName, type] of lineageEdges) {
      const sourceId = tableMap.get(sourceName)
      const targetId = tableMap.get(targetName)
      if (sourceId && targetId) {
        insertEdge.run(uuidv4(), sourceId, targetId, type)
      }
    }

    const fieldImportanceData: [string, string, string][] = [
      ['dim_user', 'user_id', 'critical'], ['dim_user', 'phone', 'high'], ['dim_user', 'email', 'high'], ['dim_user', 'register_time', 'medium'], ['dim_user', 'avatar_url', 'low'],
      ['dim_product', 'product_id', 'critical'], ['dim_product', 'price', 'critical'], ['dim_product', 'category_id', 'high'], ['dim_product', 'name', 'high'], ['dim_product', 'description', 'low'],
      ['dim_store', 'store_id', 'critical'], ['dim_store', 'region', 'high'], ['dim_store', 'address', 'medium'], ['dim_store', 'manager', 'low'], ['dim_store', 'opening_date', 'medium'],
      ['dim_category', 'category_id', 'critical'], ['dim_category', 'parent_id', 'high'], ['dim_category', 'level', 'medium'], ['dim_category', 'name', 'high'], ['dim_category', 'icon_url', 'low'],
      ['fact_orders', 'order_id', 'critical'], ['fact_orders', 'user_id', 'critical'], ['fact_orders', 'amount', 'critical'], ['fact_orders', 'status', 'high'], ['fact_orders', 'create_time', 'medium'],
      ['fact_payments', 'payment_id', 'critical'], ['fact_payments', 'order_id', 'critical'], ['fact_payments', 'channel', 'high'], ['fact_payments', 'amount', 'high'], ['fact_payments', 'pay_time', 'medium'],
      ['fact_returns', 'return_id', 'critical'], ['fact_returns', 'order_id', 'critical'], ['fact_returns', 'reason', 'medium'], ['fact_returns', 'amount', 'high'], ['fact_returns', 'create_time', 'medium'],
      ['ods_log', 'log_id', 'critical'], ['ods_log', 'user_id', 'high'], ['ods_log', 'event_type', 'high'], ['ods_log', 'event_time', 'critical'], ['ods_log', 'payload', 'low'],
      ['dws_user_daily', 'user_id', 'critical'], ['dws_user_daily', 'date', 'critical'], ['dws_user_daily', 'order_count', 'high'], ['dws_user_daily', 'total_amount', 'high'], ['dws_user_daily', 'active_duration', 'medium'],
      ['ads_sales_report', 'date', 'critical'], ['ads_sales_report', 'region', 'high'], ['ads_sales_report', 'total_sales', 'critical'], ['ads_sales_report', 'order_count', 'high'], ['ads_sales_report', 'return_rate', 'medium'],
    ]
    for (const [tableName, fieldName, importance] of fieldImportanceData) {
      const tid = tableMap.get(tableName)
      if (tid) {
        insertFieldImportance.run(uuidv4(), tid, fieldName, importance, now.toISOString().replace('T', ' ').slice(0, 19))
      }
    }

    const criticalTableNames = ['ods_log', 'dws_user_daily', 'fact_returns']
    const warningTableNames = ['dim_store', 'fact_returns']
    for (const t of tables) {
      let cw = 0.3, csw = 0.25, tw = 0.2, aw = 0.25
      if (criticalTableNames.includes(t.name)) {
        aw = 0.35; tw = 0.15; cw = 0.3; csw = 0.2
      }
      if (warningTableNames.includes(t.name)) {
        cw = 0.35; csw = 0.2; tw = 0.2; aw = 0.25
      }
      const sum = cw + csw + tw + aw
      cw = Math.round(cw / sum * 1000) / 1000
      csw = Math.round(csw / sum * 1000) / 1000
      tw = Math.round(tw / sum * 1000) / 1000
      aw = Math.round(aw / sum * 1000) / 1000
      insertScoreWeightConfig.run(uuidv4(), t.id, cw, csw, tw, aw, now.toISOString().replace('T', ' ').slice(0, 19))
    }

    const reportNodes = [
      { id: uuidv4(), name: 'rpt_daily_sales', description: '每日销售报表', status: 'warning' },
      { id: uuidv4(), name: 'rpt_user_activity', description: '用户活跃度报告', status: 'critical' },
      { id: uuidv4(), name: 'rpt_return_analysis', description: '退款分析报表', status: 'warning' },
      { id: uuidv4(), name: 'rpt_category_performance', description: '品类业绩报表', status: 'healthy' },
    ]
    const reportMap = new Map(reportNodes.map(r => [r.name, r.id]))
    for (const r of reportNodes) {
      insertReportNode.run(r.id, r.name, r.description, 'report', r.status, now.toISOString().replace('T', ' ').slice(0, 19))
    }

    const reportLineageData: [string, string, string][] = [
      ['ads_sales_report', 'rpt_daily_sales', 'feed'],
      ['fact_payments', 'rpt_daily_sales', 'feed'],
      ['dws_user_daily', 'rpt_user_activity', 'feed'],
      ['dim_user', 'rpt_user_activity', 'dimension'],
      ['fact_returns', 'rpt_return_analysis', 'feed'],
      ['dim_product', 'rpt_return_analysis', 'dimension'],
      ['dim_category', 'rpt_category_performance', 'feed'],
      ['ads_sales_report', 'rpt_category_performance', 'feed'],
      ['fact_orders', 'rpt_daily_sales', 'feed'],
      ['fact_returns', 'rpt_user_activity', 'feed'],
    ]
    for (const [tableName, reportName, impactType] of reportLineageData) {
      const sourceTableId = tableMap.get(tableName)
      const targetReportId = reportMap.get(reportName)
      if (sourceTableId && targetReportId) {
        insertReportLineageEdge.run(uuidv4(), sourceTableId, targetReportId, impactType)
      }
    }

    const parseLogs = [
      { target: 'dws_user_daily', sql: 'INSERT OVERWRITE dws_user_daily SELECT user_id, date, COUNT(*) as order_count, SUM(amount) as total_amount FROM fact_orders WHERE dt = ? GROUP BY user_id, date', sources: 'fact_orders', status: 'success', edges: 1 },
      { target: 'ads_sales_report', sql: 'INSERT OVERWRITE ads_sales_report SELECT date, region, SUM(amount) as total_sales, COUNT(DISTINCT order_id) as order_count FROM fact_orders o JOIN dim_store s ON o.store_id = s.store_id GROUP BY date, region', sources: 'fact_orders,dim_store', status: 'success', edges: 2 },
      { target: 'fact_payments', sql: 'INSERT INTO fact_payments SELECT p.* FROM ods_payments p JOIN fact_orders o ON p.order_id = o.order_id', sources: 'ods_payments,fact_orders', status: 'success', edges: 1 },
    ]
    for (const log of parseLogs) {
      const targetId = tableMap.get(log.target)
      insertSqlParseLog.run(uuidv4(), targetId, log.sql, log.sources, log.status, log.edges, null, now.toISOString().replace('T', ' ').slice(0, 19))
    }

    const alerts = db.prepare('SELECT id, table_id FROM alert WHERE status = ?').all('active') as { id: string; table_id: string }[]
    for (const alert of alerts.slice(0, 5)) {
      const sampleData = JSON.stringify([
        { id: 1001, field: 'user_id', value: null, reason: '空值异常' },
        { id: 1002, field: 'user_id', value: null, reason: '空值异常' },
        { id: 1003, field: 'amount', value: 999999, reason: '数值异常' },
      ])
      insertAnomalySample.run(uuidv4(), alert.id, alert.table_id, 'null_rate', sampleData, 3, now.toISOString().replace('T', ' ').slice(0, 19))
    }

    const today = new Date()
    for (let horizon of [7, 14, 30]) {
      const trend = horizon <= 7 ? 'increasing' : horizon <= 14 ? 'stable' : 'decreasing'
      const predicted = horizon === 7 ? 12 : horizon === 14 ? 20 : 35
      const critical = Math.round(predicted * 0.35)
      const warning = predicted - critical
      const forecastDate = new Date(today.getTime() + horizon * 86400000).toISOString().slice(0, 10)
      insertQualityForecast.run(
        uuidv4(), forecastDate, horizon, predicted, critical, warning, trend,
        horizon === 7 ? 0.92 : horizon === 14 ? 0.85 : 0.75, 'v1', now.toISOString().replace('T', ' ').slice(0, 19)
      )
    }
  })

  seed()
  console.log('Database seeded successfully')
}

export default db
