import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api } from '@/utils/api'
import { cn } from '@/lib/utils'
import type { Rule, MetricType, Severity, ImportanceLevel, DynamicThreshold, FieldImportance } from '@/types'

type FormData = {
  name: string
  table_id: string
  metric_type: MetricType
  condition: string
  threshold: number
  schedule: string
  severity: Severity
  enabled: boolean
  field_importance: ImportanceLevel
}

const initialForm: FormData = {
  name: '',
  table_id: '',
  metric_type: 'row_count',
  condition: '>',
  threshold: 0,
  schedule: '0 * * * *',
  severity: 'warning',
  enabled: true,
  field_importance: 'medium',
}

const metricOptions: { value: MetricType; label: string }[] = [
  { value: 'row_count', label: 'row_count' },
  { value: 'null_rate', label: 'null_rate' },
  { value: 'duplicate_rate', label: 'duplicate_rate' },
  { value: 'distribution_drift', label: 'distribution_drift' },
]

const conditionOptions = ['>', '<', '>=', '<=', '==']
const severityOptions: { value: Severity; label: string }[] = [
  { value: 'critical', label: 'critical' },
  { value: 'warning', label: 'warning' },
  { value: 'info', label: 'info' },
]

const cronPresets = [
  { label: '每小时', value: '0 * * * *' },
  { label: '每6小时', value: '0 */6 * * *' },
  { label: '每天', value: '0 0 * * *' },
]

const importanceOptions: { value: ImportanceLevel; label: string; desc: string }[] = [
  { value: 'critical', label: '关键字段', desc: '阈值收紧至60%' },
  { value: 'high', label: '重要字段', desc: '阈值收紧至80%' },
  { value: 'medium', label: '普通字段', desc: '标准阈值' },
  { value: 'low', label: '低优先字段', desc: '阈值放宽至130%' },
]

export default function RuleEditor() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const isEdit = Boolean(id)

  const [form, setForm] = useState<FormData>(initialForm)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [tables, setTables] = useState<{ id: string; name: string }[]>([])
  const [dynamicThreshold, setDynamicThreshold] = useState<DynamicThreshold | null>(null)
  const [fieldImportanceList, setFieldImportanceList] = useState<FieldImportance[]>([])

  useEffect(() => {
    api.scores.list().then(scores => {
      setTables(scores.map(s => ({ id: s.table_id, name: s.table_name })))
    })
  }, [])

  useEffect(() => {
    if (!form.table_id || !form.metric_type || !form.field_importance) {
      setDynamicThreshold(null)
      return
    }
    api.rules.dynamicThreshold({
      tableId: form.table_id,
      metricType: form.metric_type,
      fieldImportance: form.field_importance,
    }).then(setDynamicThreshold).catch(() => setDynamicThreshold(null))
  }, [form.table_id, form.metric_type, form.field_importance])

  useEffect(() => {
    if (!form.table_id) { setFieldImportanceList([]); return }
    api.rules.fieldImportance(form.table_id).then(setFieldImportanceList).catch(() => setFieldImportanceList([]))
  }, [form.table_id])

  useEffect(() => {
    if (!id) return
    setLoading(true)
    api.rules.get(id).then(rule => {
      setForm({
        name: rule.name,
        table_id: rule.table_id,
        metric_type: rule.metric_type,
        condition: rule.condition,
        threshold: rule.threshold,
        schedule: rule.schedule,
        severity: rule.severity,
        enabled: rule.enabled,
        field_importance: rule.field_importance || 'medium',
      })
    }).finally(() => setLoading(false))
  }, [id])

  const handleSubmit = async () => {
    setSaving(true)
    try {
      const payload = { ...form, field_importance: form.field_importance }
      if (isEdit && id) {
        await api.rules.update(id, payload)
      } else {
        await api.rules.create(payload)
      }
      navigate('/rules')
    } finally {
      setSaving(false)
    }
  }

  const updateField = <K extends keyof FormData>(key: K, value: FormData[K]) => {
    setForm(prev => ({ ...prev, [key]: value }))
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0a0f1a] flex items-center justify-center text-gray-500">
        加载中...
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-[#0a0f1a] text-gray-200 p-6">
      <h1 className="text-2xl font-bold text-white mb-6">
        {isEdit ? '编辑规则' : '新建规则'}
      </h1>

      <div className="max-w-2xl space-y-5">
        <div>
          <label className="block text-sm text-gray-400 mb-1">规则名称</label>
          <input
            type="text"
            value={form.name}
            onChange={e => updateField('name', e.target.value)}
            className="w-full bg-[#111827] border border-gray-700 rounded-lg px-3 py-2 text-gray-200 focus:outline-none focus:border-cyan-500 transition-colors"
          />
        </div>

        <div>
          <label className="block text-sm text-gray-400 mb-1">目标表</label>
          <select
            value={form.table_id}
            onChange={e => updateField('table_id', e.target.value)}
            className="w-full bg-[#111827] border border-gray-700 rounded-lg px-3 py-2 text-gray-200 focus:outline-none focus:border-cyan-500 transition-colors"
          >
            <option value="">选择表...</option>
            {tables.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
          </select>
        </div>

        <div className="grid grid-cols-3 gap-4">
          <div>
            <label className="block text-sm text-gray-400 mb-1">指标类型</label>
            <select
              value={form.metric_type}
              onChange={e => updateField('metric_type', e.target.value as MetricType)}
              className="w-full bg-[#111827] border border-gray-700 rounded-lg px-3 py-2 text-gray-200 focus:outline-none focus:border-cyan-500 transition-colors"
            >
              {metricOptions.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1">条件</label>
            <select
              value={form.condition}
              onChange={e => updateField('condition', e.target.value)}
              className="w-full bg-[#111827] border border-gray-700 rounded-lg px-3 py-2 text-gray-200 focus:outline-none focus:border-cyan-500 transition-colors"
            >
              {conditionOptions.map(c => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1">阈值</label>
            <input
              type="number"
              step="any"
              value={form.threshold}
              onChange={e => updateField('threshold', parseFloat(e.target.value) || 0)}
              className="w-full bg-[#111827] border border-gray-700 rounded-lg px-3 py-2 text-gray-200 focus:outline-none focus:border-cyan-500 transition-colors"
            />
          </div>
        </div>

        <div>
          <label className="block text-sm text-gray-400 mb-1">调度 (Cron)</label>
          <input
            type="text"
            value={form.schedule}
            onChange={e => updateField('schedule', e.target.value)}
            className="w-full bg-[#111827] border border-gray-700 rounded-lg px-3 py-2 text-gray-200 font-mono text-sm focus:outline-none focus:border-cyan-500 transition-colors"
          />
          <div className="flex gap-2 mt-2">
            {cronPresets.map(p => (
              <button
                key={p.value}
                onClick={() => updateField('schedule', p.value)}
                className={cn(
                  'px-3 py-1 text-xs rounded-md border transition-colors',
                  form.schedule === p.value
                    ? 'border-cyan-500/50 text-cyan-400 bg-cyan-500/10'
                    : 'border-gray-700 text-gray-400 hover:text-gray-200 hover:border-gray-600'
                )}
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="block text-sm text-gray-400 mb-2">字段重要性</label>
          <div className="grid grid-cols-4 gap-2">
            {importanceOptions.map(opt => (
              <button
                key={opt.value}
                type="button"
                onClick={() => updateField('field_importance', opt.value)}
                className={cn(
                  'p-3 rounded-lg border text-center transition-colors',
                  form.field_importance === opt.value
                    ? 'border-cyan-500/50 text-cyan-400 bg-cyan-500/10'
                    : 'border-gray-700 text-gray-400 hover:text-gray-200 hover:border-gray-600'
                )}
              >
                <p className="text-sm font-medium">{opt.label}</p>
                <p className="text-[10px] text-gray-500 mt-0.5">{opt.desc}</p>
              </button>
            ))}
          </div>
        </div>

        {dynamicThreshold && (
          <div className="rounded-lg border border-gray-700/50 bg-[#0a0f1a] p-3 space-y-1.5">
            <p className="text-xs text-gray-400">动态阈值预览</p>
            <div className="flex items-center gap-4 text-xs">
              <span className="text-gray-500">基础阈值: <span className="text-gray-300 font-mono">{dynamicThreshold.base_threshold}</span></span>
              <span className="text-gray-500">调整系数: <span className="text-cyan-400 font-mono">×{dynamicThreshold.importance_multiplier}</span></span>
              <span className="text-gray-500">调整后: <span className="text-white font-mono font-bold">{dynamicThreshold.adjusted_threshold}</span></span>
            </div>
          </div>
        )}

        {fieldImportanceList.length > 0 && (
          <div className="rounded-lg border border-gray-700/50 bg-[#0a0f1a] p-3">
            <p className="text-xs text-gray-400 mb-2">当前表字段重要性配置</p>
            <div className="flex flex-wrap gap-1.5">
              {fieldImportanceList.map(fi => (
                <span
                  key={fi.id}
                  className={cn(
                    'text-[10px] px-2 py-0.5 rounded-full border',
                    fi.importance === 'critical' ? 'text-red-400 bg-red-400/10 border-red-400/30' :
                    fi.importance === 'high' ? 'text-amber-400 bg-amber-400/10 border-amber-400/30' :
                    fi.importance === 'medium' ? 'text-cyan-400 bg-cyan-400/10 border-cyan-400/30' :
                    'text-gray-400 bg-gray-400/10 border-gray-400/30'
                  )}
                >
                  {fi.field_name} · {fi.importance}
                </span>
              ))}
            </div>
          </div>
        )}

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm text-gray-400 mb-1">级别</label>
            <select
              value={form.severity}
              onChange={e => updateField('severity', e.target.value as Severity)}
              className="w-full bg-[#111827] border border-gray-700 rounded-lg px-3 py-2 text-gray-200 focus:outline-none focus:border-cyan-500 transition-colors"
            >
              {severityOptions.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1">启用</label>
            <button
              type="button"
              onClick={() => updateField('enabled', !form.enabled)}
              className={cn(
                'flex items-center gap-2 px-3 py-2 rounded-lg border transition-colors',
                form.enabled
                  ? 'border-cyan-500/50 text-cyan-400 bg-cyan-500/10'
                  : 'border-gray-700 text-gray-500'
              )}
            >
              {form.enabled ? '已启用' : '已禁用'}
            </button>
          </div>
        </div>

        <div className="flex items-center gap-3 pt-4">
          <button
            onClick={handleSubmit}
            disabled={saving}
            className="px-6 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-white font-medium transition-colors"
          >
            {saving ? '保存中...' : '保存'}
          </button>
          <button
            onClick={() => navigate('/rules')}
            className="px-6 py-2 rounded-lg border border-gray-700 text-gray-400 hover:text-gray-200 hover:border-gray-600 transition-colors"
          >
            取消
          </button>
        </div>
      </div>
    </div>
  )
}
