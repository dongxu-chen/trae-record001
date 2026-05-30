import { useCallback, useEffect, useMemo, useState } from 'react'
import { FileText, RefreshCw, Database, Play, Sparkles, CheckCircle2, XCircle } from 'lucide-react'
import { ReactFlow, Handle, Position, Background, type Node, type Edge, type NodeProps } from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { useStore } from '@/store'
import { cn } from '@/lib/utils'
import type { LineageNode, TableStatus, AffectedReport, SqlParseResult, SqlParseLog } from '@/types'

const statusDot: Record<TableStatus, string> = {
  healthy: 'bg-emerald-400',
  warning: 'bg-amber-400',
  critical: 'bg-red-400',
}

function TableNode({ data, selected }: NodeProps) {
  return (
    <div
      className={cn(
        'px-4 py-3 rounded-lg border min-w-[150px] transition-shadow bg-[#0d1424]',
        selected
          ? 'border-cyan-400 shadow-[0_0_15px_rgba(6,182,212,0.45)]'
          : 'border-gray-700 hover:border-gray-600',
      )}
    >
      <Handle type="target" position={Position.Left} style={{ background: '#06B6D4', width: 8, height: 8, border: 'none' }} />
      <div className="flex items-center gap-2">
        <span className={cn('w-2.5 h-2.5 rounded-full shrink-0', statusDot[data.status as TableStatus])} />
        <span className="font-mono text-sm text-white truncate">{data.label as string}</span>
      </div>
      {data.schema && <p className="text-[10px] text-gray-500 mt-1 ml-[18px]">{data.schema as string}</p>}
      <Handle type="source" position={Position.Right} style={{ background: '#06B6D4', width: 8, height: 8, border: 'none' }} />
    </div>
  )
}

function ReportNode({ data, selected }: NodeProps) {
  return (
    <div
      className={cn(
        'px-4 py-3 rounded-lg border min-w-[150px] transition-shadow bg-[#0d1424]',
        selected
          ? 'border-violet-400 shadow-[0_0_15px_rgba(139,92,246,0.45)]'
          : 'border-gray-700 hover:border-gray-600',
      )}
    >
      <Handle type="target" position={Position.Left} style={{ background: '#8B5CF6', width: 8, height: 8, border: 'none' }} />
      <div className="flex items-center gap-2">
        <FileText className="w-3.5 h-3.5 text-violet-400 shrink-0" />
        <span className="font-mono text-sm text-white truncate">{data.label as string}</span>
      </div>
      {data.description && <p className="text-[10px] text-gray-500 mt-1 ml-[22px]">{data.description as string}</p>}
      <Handle type="source" position={Position.Right} style={{ background: '#8B5CF6', width: 8, height: 8, border: 'none' }} />
    </div>
  )
}

const nodeTypes = { table: TableNode, report: ReportNode }

function computeLayout(nodes: LineageNode[], edges: LineageEdge[]): Node[] {
  const X_GAP = 300
  const Y_GAP = 110

  const inDeg: Record<string, number> = {}
  const adj: Record<string, string[]> = {}
  for (const n of nodes) {
    inDeg[n.id] = 0
    adj[n.id] = []
  }
  for (const e of edges) {
    if (inDeg[e.target] !== undefined) inDeg[e.target]++
    if (adj[e.source]) adj[e.source].push(e.target)
  }

  const layer: Record<string, number> = {}
  const queue: string[] = []
  for (const n of nodes) {
    if (inDeg[n.id] === 0) {
      queue.push(n.id)
      layer[n.id] = 0
    }
  }

  let idx = 0
  while (idx < queue.length) {
    const curr = queue[idx++]
    for (const next of adj[curr] || []) {
      layer[next] = Math.max(layer[next] ?? 0, (layer[curr] ?? 0) + 1)
      inDeg[next]--
      if (inDeg[next] === 0) queue.push(next)
    }
  }

  for (const n of nodes) {
    if (layer[n.id] === undefined) layer[n.id] = 0
  }

  const buckets: Record<number, string[]> = {}
  for (const n of nodes) {
    const l = layer[n.id]
    ;(buckets[l] ??= []).push(n.id)
  }

  const pos: Record<string, { x: number; y: number }> = {}
  for (const [l, ids] of Object.entries(buckets)) {
    const totalH = (ids.length - 1) * Y_GAP
    const startY = -totalH / 2
    ids.forEach((id, i) => {
      pos[id] = { x: Number(l) * X_GAP, y: startY + i * Y_GAP }
    })
  }

  return nodes.map(n => {
    const parts = n.name.split('.')
    return {
      id: n.id,
      type: n.type === 'report' ? 'report' : 'table',
      position: pos[n.id] ?? { x: 0, y: 0 },
      data: {
        label: parts.length > 1 ? parts.slice(1).join('.') : n.name,
        schema: parts.length > 1 ? parts[0] : undefined,
        description: n.description,
        status: n.status,
      },
    }
  })
}

const impactColor: Record<string, string> = {
  high: 'text-red-400 bg-red-400/10 border-red-400/30',
  medium: 'text-amber-400 bg-amber-400/10 border-amber-400/30',
  low: 'text-cyan-400 bg-cyan-400/10 border-cyan-400/30',
}

const parseStatusIcon: Record<string, typeof CheckCircle2> = {
  success: CheckCircle2,
  failed: XCircle,
  pending: RefreshCw,
}

const parseStatusColor: Record<string, string> = {
  success: 'text-emerald-400',
  failed: 'text-red-400',
  pending: 'text-amber-400',
}

export default function ImpactAnalysis() {
  const {
    lineageNodes,
    lineageEdges,
    lineageLoading,
    selectedTableId,
    impactAnalysis,
    parseLogs,
    fetchLineage,
    selectTable,
    fetchParseLogs,
    parseSql,
    autoDiscoverLineage,
  } = useStore()

  const [sqlContent, setSqlContent] = useState('')
  const [targetTableId, setTargetTableId] = useState('')
  const [parseResult, setParseResult] = useState<SqlParseResult | null>(null)
  const [parsing, setParsing] = useState(false)
  const [discovering, setDiscovering] = useState(false)

  useEffect(() => {
    fetchLineage()
    fetchParseLogs()
  }, [fetchLineage, fetchParseLogs])

  const tableNodes = useMemo(
    () => lineageNodes.filter(n => n.type === 'table'),
    [lineageNodes],
  )

  const handleParseSql = async () => {
    if (!targetTableId || !sqlContent.trim()) return
    setParsing(true)
    try {
      const result = await parseSql({ target_table_id: targetTableId, sql_content: sqlContent })
      if (result) {
        setParseResult(result as SqlParseResult)
      }
      await fetchLineage()
    } finally {
      setParsing(false)
    }
  }

  const handleAutoDiscover = async () => {
    setDiscovering(true)
    try {
      await autoDiscoverLineage()
      await fetchLineage()
    } finally {
      setDiscovering(false)
    }
  }

  const rfNodes = useMemo(() => computeLayout(lineageNodes, lineageEdges), [lineageNodes, lineageEdges])

  const rfEdges = useMemo(
    (): Edge[] =>
      lineageEdges.map(e => {
        const sourceNode = lineageNodes.find(n => n.id === e.source)
        const targetNode = lineageNodes.find(n => n.id === e.target)
        const isReportEdge = sourceNode?.type === 'report' || targetNode?.type === 'report'
        return {
          id: `${e.source}-${e.target}`,
          source: e.source,
          target: e.target,
          animated: e.type === 'data_flow' || e.type === 'feed',
          style: { stroke: isReportEdge ? '#6D28D9' : '#334155', strokeWidth: 2 },
        }
      }),
    [lineageEdges, lineageNodes],
  )

  const onNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => selectTable(node.id),
    [selectTable],
  )

  const selectedNode = lineageNodes.find(n => n.id === selectedTableId)

  return (
    <div className="flex flex-col bg-[#0a0f1a]" style={{ height: 'calc(100vh - 112px)' }}>
      <div className="p-4 border-b border-gray-800 bg-[#0d1424]">
        <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <Database className="w-5 h-5 text-cyan-400" />
          SQL 血缘解析
        </h2>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div className="space-y-3">
            <textarea
              value={sqlContent}
              onChange={(e) => setSqlContent(e.target.value)}
              placeholder="在此输入 SQL 语句，例如：INSERT INTO target_table SELECT * FROM source_table"
              rows={4}
              className="w-full rounded-lg bg-[#0a0f1a] border border-gray-700 text-sm text-gray-200 p-3 resize-none focus:outline-none focus:border-cyan-500/50 placeholder:text-gray-600 font-mono"
            />
            <div className="flex items-center gap-3">
              <select
                value={targetTableId}
                onChange={(e) => setTargetTableId(e.target.value)}
                className="flex-1 bg-[#0a0f1a] border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-cyan-500"
              >
                <option value="">选择目标表</option>
                {tableNodes.map(node => (
                  <option key={node.id} value={node.id}>{node.name}</option>
                ))}
              </select>
              <button
                onClick={handleParseSql}
                disabled={parsing || !targetTableId || !sqlContent.trim()}
                className="px-4 py-2 rounded-lg border border-cyan-500/50 bg-cyan-500/10 text-cyan-400 text-sm font-medium hover:bg-cyan-500/20 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
              >
                <Play className="w-4 h-4" />
                {parsing ? '解析中...' : '解析 SQL'}
              </button>
              <button
                onClick={handleAutoDiscover}
                disabled={discovering}
                className="px-4 py-2 rounded-lg border border-violet-500/50 bg-violet-500/10 text-violet-400 text-sm font-medium hover:bg-violet-500/20 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
              >
                <Sparkles className="w-4 h-4" />
                {discovering ? '发现中...' : '自动发现血缘'}
              </button>
            </div>
          </div>
          <div className="space-y-3">
            <div className="rounded-lg border border-gray-700/50 bg-[#0a0f1a] p-3 min-h-[120px]">
              <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">解析结果</h3>
              {parseResult ? (
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <span className={cn('text-sm', parseStatusColor[parseResult.parse_status])}>
                      {parseResult.parse_status === 'success' ? '解析成功' : parseResult.parse_status === 'failed' ? '解析失败' : '解析中'}
                    </span>
                  </div>
                  {parseResult.source_tables && parseResult.source_tables.length > 0 && (
                    <div>
                      <span className="text-xs text-gray-500">源表：</span>
                      <div className="flex flex-wrap gap-1.5 mt-1">
                        {parseResult.source_tables.map((table, idx) => (
                          <span key={idx} className="text-xs px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 font-mono">
                            {table}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  {parseResult.new_edges && parseResult.new_edges.length > 0 && (
                    <div>
                      <span className="text-xs text-gray-500">新血缘边：</span>
                      <div className="flex flex-wrap gap-1.5 mt-1">
                        {parseResult.new_edges.map((edge, idx) => (
                          <span key={idx} className="text-xs px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 font-mono">
                            {edge.source_id} → {edge.target_id}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  {parseResult.error_message && (
                    <p className="text-xs text-red-400">{parseResult.error_message}</p>
                  )}
                </div>
              ) : (
                <p className="text-sm text-gray-600">暂无解析结果</p>
              )}
            </div>
            <div className="rounded-lg border border-gray-700/50 bg-[#0a0f1a] p-3 max-h-[120px] overflow-y-auto">
              <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">解析历史</h3>
              {parseLogs.length > 0 ? (
                <div className="space-y-1.5">
                  {parseLogs.slice(0, 5).map((log: SqlParseLog) => {
                    const StatusIcon = parseStatusIcon[log.parse_status]
                    const targetNode = lineageNodes.find(n => n.id === log.target_table_id)
                    return (
                      <div key={log.id} className="flex items-center gap-2 text-xs">
                        <StatusIcon className={cn('w-3.5 h-3.5 shrink-0', parseStatusColor[log.parse_status])} />
                        <span className="text-gray-400 font-mono truncate">{targetNode?.name || log.target_table_id}</span>
                        <span className="text-gray-600">→</span>
                        <span className="text-gray-400">{log.new_edges_count} 条新边</span>
                        <span className="text-gray-600 ml-auto">{new Date(log.parsed_at).toLocaleTimeString()}</span>
                      </div>
                    )
                  })}
                </div>
              ) : (
                <p className="text-sm text-gray-600">暂无解析历史</p>
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden">
        <div className="flex-1 relative flex flex-col">
          <div className="flex items-center justify-between p-3 border-b border-gray-800 bg-[#0d1424]">
            <h3 className="text-sm font-medium text-gray-400">血缘图谱</h3>
            <button
              onClick={() => { fetchLineage(); fetchParseLogs(); }}
              className="p-2 rounded-lg border border-gray-700 text-gray-400 hover:border-cyan-500/50 hover:text-cyan-400 transition-colors"
              title="刷新"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>
          <div className="flex-1 relative">
            {lineageLoading ? (
              <div className="flex items-center justify-center h-full text-gray-500 text-sm">加载中...</div>
            ) : (
              <ReactFlow
                nodes={rfNodes}
                edges={rfEdges}
                nodeTypes={nodeTypes}
                onNodeClick={onNodeClick}
                fitView
                proOptions={{ hideAttribution: true }}
                className="!bg-[#0a0f1a]"
              >
                <Background color="#1e293b" gap={24} />
              </ReactFlow>
            )}
          </div>
        </div>

      <div className="w-[40%] min-w-[320px] border-l border-gray-800 bg-[#0d1424] overflow-y-auto">
        {selectedTableId && selectedNode ? (
          <div className="p-5">
            <h2 className="text-lg font-semibold text-white mb-5">
              影响分析 — <span className="text-cyan-400 font-mono">{selectedNode.name}</span>
            </h2>

            <section className="mb-6">
              <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-3">下游影响</h3>
              {impactAnalysis?.affected_downstream.length ? (
                <div className="space-y-2">
                  {impactAnalysis.affected_downstream.map(t => (
                    <div key={t.table_id} className="rounded-lg border border-gray-700/50 bg-[#0a0f1a] p-3">
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-sm text-white">{t.table_name}</span>
                        <span
                          className={cn(
                            'text-[10px] font-semibold px-2 py-0.5 rounded border uppercase',
                            impactColor[t.impact_level] ?? impactColor.low,
                          )}
                        >
                          {t.impact_level}
                        </span>
                      </div>
                      {t.affected_metrics.length > 0 && (
                        <div className="flex gap-1.5 mt-2 flex-wrap">
                          {t.affected_metrics.map(m => (
                            <span key={m} className="text-[10px] px-1.5 py-0.5 rounded bg-gray-800 text-gray-400">
                              {m}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-gray-600">无下游影响</p>
              )}
            </section>

            <section className="mb-6">
              <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-3">受影响报表</h3>
              {impactAnalysis?.affected_reports?.length ? (
                <div className="space-y-2">
                  {impactAnalysis.affected_reports.map(r => (
                    <div key={r.report_id} className="rounded-lg border border-violet-500/20 bg-violet-500/5 p-3">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <FileText className="w-3.5 h-3.5 text-violet-400" />
                          <span className="font-mono text-sm text-white">{r.report_name}</span>
                        </div>
                        <span
                          className={cn(
                            'text-[10px] font-semibold px-2 py-0.5 rounded border uppercase',
                            impactColor[r.impact_level] ?? impactColor.low,
                          )}
                        >
                          {r.impact_level}
                        </span>
                      </div>
                      {r.affected_data_sources.length > 0 && (
                        <div className="flex gap-1.5 mt-2 flex-wrap">
                          {r.affected_data_sources.map(ds => (
                            <span key={ds} className="text-[10px] px-1.5 py-0.5 rounded bg-gray-800 text-gray-400">
                              {ds}
                            </span>
                          ))}
                        </div>
                      )}
                      <p className="text-xs text-amber-400/80 mt-2 leading-relaxed">{r.quality_risk}</p>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-gray-600">无受影响报表</p>
              )}
            </section>

            <section>
              <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-3">根因候选</h3>
              {impactAnalysis?.root_cause_candidates.length ? (
                <div className="space-y-2">
                  {impactAnalysis.root_cause_candidates.map(r => (
                    <div key={r.table_id} className="rounded-lg border border-gray-700/50 bg-[#0a0f1a] p-3">
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="font-mono text-sm text-white">{r.table_name}</span>
                        <span className="text-xs text-cyan-400 font-mono">{r.confidence}%</span>
                      </div>
                      <div className="w-full h-1.5 rounded-full bg-gray-800 mb-2">
                        <div
                          className="h-full rounded-full bg-gradient-to-r from-cyan-600 to-cyan-400 transition-all"
                          style={{ width: `${r.confidence}%` }}
                        />
                      </div>
                      <p className="text-xs text-gray-500 leading-relaxed">{r.reason}</p>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-gray-600">无根因候选</p>
              )}
            </section>
          </div>
        ) : (
          <div className="flex items-center justify-center h-full text-gray-600 text-sm">
            请选择一个节点查看影响分析
          </div>
        )}
      </div>
      </div>
    </div>
  )
}
