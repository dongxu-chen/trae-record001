import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Plus, Trash2, ToggleLeft, ToggleRight, Filter } from 'lucide-react'
import { useStore } from '@/store'
import { cn } from '@/lib/utils'
import type { MetricType, Severity } from '@/types'

const metricBadge: Record<MetricType, string> = {
  row_count: 'bg-blue-500/20 text-blue-400 border border-blue-500/30',
  null_rate: 'bg-amber-500/20 text-amber-400 border border-amber-500/30',
  duplicate_rate: 'bg-purple-500/20 text-purple-400 border border-purple-500/30',
  distribution_drift: 'bg-pink-500/20 text-pink-400 border border-pink-500/30',
}

const severityBadge: Record<Severity, string> = {
  critical: 'bg-red-500/20 text-red-400 border border-red-500/30',
  warning: 'bg-amber-500/20 text-amber-400 border border-amber-500/30',
  info: 'bg-blue-500/20 text-blue-400 border border-blue-500/30',
}

export default function Rules() {
  const { rules, rulesLoading, fetchRules, toggleRule, deleteRule } = useStore()
  const [filterTable, setFilterTable] = useState('')
  const [filterMetric, setFilterMetric] = useState('')
  const [filterSeverity, setFilterSeverity] = useState('')
  const [filterEnabled, setFilterEnabled] = useState('')
  const [showFilters, setShowFilters] = useState(false)

  useEffect(() => { fetchRules() }, [fetchRules])

  const filtered = rules.filter(r => {
    if (filterTable && !r.table_name.includes(filterTable)) return false
    if (filterMetric && r.metric_type !== filterMetric) return false
    if (filterSeverity && r.severity !== filterSeverity) return false
    if (filterEnabled !== '' && r.enabled !== (filterEnabled === 'true')) return false
    return true
  })

  const uniqueTables = [...new Set(rules.map(r => r.table_name))]

  return (
    <div className="min-h-screen bg-[#0a0f1a] text-gray-200 p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-white">监控规则</h1>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowFilters(f => !f)}
            className={cn(
              'flex items-center gap-2 px-3 py-2 rounded-lg border transition-colors',
              showFilters ? 'border-cyan-500/50 text-cyan-400' : 'border-gray-700 text-gray-400 hover:text-gray-200'
            )}
          >
            <Filter size={16} /> 筛选
          </button>
          <Link
            to="/rules/new"
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white font-medium transition-colors"
          >
            <Plus size={16} /> 新建规则
          </Link>
        </div>
      </div>

      {showFilters && (
        <div className="mb-4 grid grid-cols-2 md:grid-cols-4 gap-3 p-4 rounded-xl bg-[#111827] border border-gray-800">
          <select
            value={filterTable}
            onChange={e => setFilterTable(e.target.value)}
            className="bg-[#0a0f1a] border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-cyan-500"
          >
            <option value="">全部表</option>
            {uniqueTables.map(t => <option key={t} value={t}>{t}</option>)}
          </select>
          <select
            value={filterMetric}
            onChange={e => setFilterMetric(e.target.value)}
            className="bg-[#0a0f1a] border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-cyan-500"
          >
            <option value="">全部指标</option>
            <option value="row_count">row_count</option>
            <option value="null_rate">null_rate</option>
            <option value="duplicate_rate">duplicate_rate</option>
            <option value="distribution_drift">distribution_drift</option>
          </select>
          <select
            value={filterSeverity}
            onChange={e => setFilterSeverity(e.target.value)}
            className="bg-[#0a0f1a] border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-cyan-500"
          >
            <option value="">全部级别</option>
            <option value="critical">critical</option>
            <option value="warning">warning</option>
            <option value="info">info</option>
          </select>
          <select
            value={filterEnabled}
            onChange={e => setFilterEnabled(e.target.value)}
            className="bg-[#0a0f1a] border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-cyan-500"
          >
            <option value="">全部状态</option>
            <option value="true">已启用</option>
            <option value="false">已禁用</option>
          </select>
        </div>
      )}

      {rulesLoading ? (
        <div className="flex items-center justify-center h-64 text-gray-500">加载中...</div>
      ) : filtered.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-64 text-gray-500">
          <p className="text-lg mb-2">暂无规则</p>
          <p className="text-sm">点击"新建规则"创建第一条监控规则</p>
        </div>
      ) : (
        <div className="rounded-xl border border-gray-800 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-[#111827] text-gray-400 text-left">
                <th className="px-4 py-3 font-medium">名称</th>
                <th className="px-4 py-3 font-medium">目标表</th>
                <th className="px-4 py-3 font-medium">指标类型</th>
                <th className="px-4 py-3 font-medium">阈值</th>
                <th className="px-4 py-3 font-medium">调度</th>
                <th className="px-4 py-3 font-medium">级别</th>
                <th className="px-4 py-3 font-medium">状态</th>
                <th className="px-4 py-3 font-medium">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800/60">
              {filtered.map(rule => (
                <tr key={rule.id} className="hover:bg-[#111827]/60 transition-colors">
                  <td className="px-4 py-3 font-mono text-cyan-400">{rule.name}</td>
                  <td className="px-4 py-3 text-gray-300">{rule.table_name}</td>
                  <td className="px-4 py-3">
                    <span className={cn('px-2 py-0.5 rounded-md text-xs font-medium', metricBadge[rule.metric_type])}>
                      {rule.metric_type}
                    </span>
                  </td>
                  <td className="px-4 py-3 font-mono text-gray-300">{rule.condition} {rule.threshold}</td>
                  <td className="px-4 py-3 font-mono text-xs text-gray-400">{rule.schedule}</td>
                  <td className="px-4 py-3">
                    <span className={cn('px-2 py-0.5 rounded-md text-xs font-medium', severityBadge[rule.severity])}>
                      {rule.severity}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => toggleRule(rule.id, !rule.enabled)}
                      className={cn('transition-colors', rule.enabled ? 'text-cyan-400' : 'text-gray-600')}
                    >
                      {rule.enabled ? <ToggleRight size={22} /> : <ToggleLeft size={22} />}
                    </button>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <Link
                        to={`/rules/${rule.id}`}
                        className="px-2 py-1 text-xs rounded border border-cyan-500/30 text-cyan-400 hover:bg-cyan-500/10 transition-colors"
                      >
                        编辑
                      </Link>
                      <button
                        onClick={() => deleteRule(rule.id)}
                        className="px-2 py-1 text-xs rounded border border-red-500/30 text-red-400 hover:bg-red-500/10 transition-colors"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
