import { Router, type Request, type Response } from 'express'
import db from '../db.js'

const router = Router()

router.get('/lineage', (_req: Request, res: Response): void => {
  try {
    const tables = db.prepare('SELECT * FROM monitored_table').all() as any[]
    const edges = db.prepare('SELECT * FROM lineage_edge').all() as any[]
    const reportNodes = db.prepare('SELECT * FROM report_node').all() as any[]
    const reportEdges = db.prepare('SELECT * FROM report_lineage_edge').all() as any[]

    const nodes = [
      ...tables.map(t => ({
        id: t.id,
        name: t.name,
        schema: t.schema_name,
        status: t.status,
        qualityScore: t.quality_score,
        type: 'table' as const,
      })),
      ...reportNodes.map(r => ({
        id: r.id,
        name: r.name,
        schema: undefined,
        status: r.status,
        qualityScore: undefined,
        type: 'report' as const,
        description: r.description,
      })),
    ]

    const links = [
      ...edges.map(e => ({
        id: e.id,
        source: e.source_id,
        target: e.target_id,
        type: e.type,
      })),
      ...reportEdges.map(e => ({
        id: e.id,
        source: e.source_table_id,
        target: e.target_report_id,
        type: e.impact_type,
      })),
    ]

    res.json({ nodes, edges: links })
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch lineage' })
  }
})

router.get('/analyze/:tableId', (req: Request, res: Response): void => {
  try {
    const { tableId } = req.params

    const table = db.prepare('SELECT * FROM monitored_table WHERE id = ?').get(tableId) as any
    if (!table) {
      res.status(404).json({ error: 'Table not found' })
      return
    }

    const visited = new Set<string>()
    const downstream: { table_id: string; table_name: string; impact_level: string; affected_metrics: string[] }[] = []
    const queue: string[] = [tableId]

    while (queue.length > 0) {
      const currentId = queue.shift()!
      if (visited.has(currentId)) continue
      visited.add(currentId)

      const outEdges = db.prepare('SELECT * FROM lineage_edge WHERE source_id = ?').all(currentId) as any[]
      for (const edge of outEdges) {
        if (!visited.has(edge.target_id)) {
          const targetTable = db.prepare('SELECT * FROM monitored_table WHERE id = ?').get(edge.target_id) as any
          if (targetTable) {
            const activeRules = db.prepare(
              "SELECT metric_type FROM monitor_rule WHERE table_id = ? AND enabled = 1"
            ).all(edge.target_id) as { metric_type: string }[]
            const alertMetrics = db.prepare(
              "SELECT DISTINCT r.metric_type FROM alert a JOIN monitor_rule r ON a.rule_id = r.id WHERE a.table_id = ? AND a.status = 'active'"
            ).all(edge.target_id) as { metric_type: string }[]
            const affectedMetrics = [...new Set([...activeRules.map(r => r.metric_type), ...alertMetrics.map(a => a.metric_type)])]
            const impactLevel = targetTable.status === 'critical' ? 'high' : targetTable.status === 'warning' ? 'medium' : 'low'

            downstream.push({
              table_id: targetTable.id,
              table_name: targetTable.name,
              impact_level: impactLevel,
              affected_metrics: affectedMetrics,
            })
            queue.push(edge.target_id)
          }
        }
      }
    }

    const upstreamVisited = new Set<string>()
    const rootCauses: { table_id: string; table_name: string; confidence: number; reason: string }[] = []
    const upstreamQueue: string[] = [tableId]

    while (upstreamQueue.length > 0) {
      const currentId = upstreamQueue.shift()!
      if (upstreamVisited.has(currentId)) continue
      upstreamVisited.add(currentId)

      const inEdges = db.prepare('SELECT * FROM lineage_edge WHERE target_id = ?').all(currentId) as any[]
      for (const edge of inEdges) {
        if (!upstreamVisited.has(edge.source_id)) {
          const sourceTable = db.prepare('SELECT * FROM monitored_table WHERE id = ?').get(edge.source_id) as any
          if (sourceTable) {
            if (sourceTable.status === 'critical' || sourceTable.status === 'warning') {
              const activeAlerts = db.prepare(
                "SELECT COUNT(*) as cnt FROM alert WHERE table_id = ? AND status = 'active'"
              ).get(edge.source_id) as { cnt: number }
              const confidence = sourceTable.status === 'critical'
                ? Math.min(95, 70 + activeAlerts.cnt * 5)
                : Math.min(80, 40 + activeAlerts.cnt * 10)

              rootCauses.push({
                table_id: sourceTable.id,
                table_name: sourceTable.name,
                confidence,
                reason: sourceTable.status === 'critical'
                  ? '上游表状态异常，可能为根因'
                  : '上游表存在告警，疑似关联影响',
              })
            }
            upstreamQueue.push(edge.source_id)
          }
        }
      }
    }

    const allDownstreamIds = new Set(downstream.map(d => d.table_id))
    allDownstreamIds.add(tableId)

    const affectedReports: { report_id: string; report_name: string; impact_level: string; affected_data_sources: string[]; quality_risk: string }[] = []
    const reportVisited = new Set<string>()

    const directReportEdges = db.prepare('SELECT * FROM report_lineage_edge WHERE source_table_id = ?').all(tableId) as any[]
    for (const re of directReportEdges) {
      if (reportVisited.has(re.target_report_id)) continue
      reportVisited.add(re.target_report_id)

      const report = db.prepare('SELECT * FROM report_node WHERE id = ?').get(re.target_report_id) as any
      if (!report) continue

      const allSourceEdges = db.prepare('SELECT * FROM report_lineage_edge WHERE target_report_id = ?').all(re.target_report_id) as any[]
      const affectedSources: string[] = []
      for (const se of allSourceEdges) {
        const srcTable = db.prepare('SELECT name FROM monitored_table WHERE id = ?').get(se.source_table_id) as { name: string } | undefined
        if (srcTable) {
          affectedSources.push(srcTable.name)
        }
      }

      const impactedSourceCount = allSourceEdges.filter(se => allDownstreamIds.has(se.source_table_id)).length
      const impactLevel = table.status === 'critical' ? 'critical' : table.status === 'warning' ? 'high' : 'medium'

      const activeAlertCount = db.prepare(
        "SELECT COUNT(*) as cnt FROM alert WHERE table_id = ? AND status = 'active'"
      ).get(tableId) as { cnt: number }

      let qualityRisk: string
      if (table.status === 'critical') {
        qualityRisk = activeAlertCount.cnt > 2
          ? '数据质量严重异常，报表数据可能严重失真，建议暂停使用'
          : '数据源存在严重质量问题，报表数据可靠性存疑'
      } else if (table.status === 'warning') {
        qualityRisk = activeAlertCount.cnt > 0
          ? '数据源存在告警，报表数据可能出现偏差'
          : '数据源质量波动，建议关注报表数据准确性'
      } else {
        qualityRisk = '数据源质量正常，报表数据风险较低'
      }

      affectedReports.push({
        report_id: report.id,
        report_name: report.description || report.name,
        impact_level: impactLevel,
        affected_data_sources: affectedSources,
        quality_risk: qualityRisk,
      })
    }

    for (const dsTable of downstream) {
      const dsReportEdges = db.prepare('SELECT * FROM report_lineage_edge WHERE source_table_id = ?').all(dsTable.table_id) as any[]
      for (const re of dsReportEdges) {
        if (reportVisited.has(re.target_report_id)) continue
        reportVisited.add(re.target_report_id)

        const report = db.prepare('SELECT * FROM report_node WHERE id = ?').get(re.target_report_id) as any
        if (!report) continue

        const allSourceEdges = db.prepare('SELECT * FROM report_lineage_edge WHERE target_report_id = ?').all(re.target_report_id) as any[]
        const affectedSources: string[] = []
        for (const se of allSourceEdges) {
          const srcTable = db.prepare('SELECT name FROM monitored_table WHERE id = ?').get(se.source_table_id) as { name: string } | undefined
          if (srcTable) {
            affectedSources.push(srcTable.name)
          }
        }

        const dsTableData = db.prepare('SELECT status FROM monitored_table WHERE id = ?').get(dsTable.table_id) as { status: string } | undefined
        const impactLevel = dsTableData?.status === 'critical' ? 'high' : dsTableData?.status === 'warning' ? 'medium' : 'low'

        const indirectActiveAlerts = db.prepare(
          "SELECT COUNT(*) as cnt FROM alert WHERE table_id = ? AND status = 'active'"
        ).get(dsTable.table_id) as { cnt: number }

        let qualityRisk: string
        if (dsTableData?.status === 'critical') {
          qualityRisk = indirectActiveAlerts.cnt > 2
            ? '上游数据质量严重异常，间接影响报表数据可靠性'
            : '上游数据源存在严重质量问题，报表数据可能间接受影响'
        } else if (dsTableData?.status === 'warning') {
          qualityRisk = '上游数据源存在告警，报表数据可能间接受影响'
        } else {
          qualityRisk = '上游数据源质量波动，间接影响风险较低'
        }

        affectedReports.push({
          report_id: report.id,
          report_name: report.description || report.name,
          impact_level: impactLevel,
          affected_data_sources: affectedSources,
          quality_risk: qualityRisk,
        })
      }
    }

    res.json({
      source_table: table.name,
      affected_downstream: downstream,
      affected_reports: affectedReports,
      root_cause_candidates: rootCauses,
    })
  } catch (error) {
    console.error('Impact analysis failed:', error)
    res.status(500).json({ error: 'Failed to analyze impact' })
  }
})

export default router
