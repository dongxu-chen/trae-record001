import { useEffect, useState } from 'react'
import { AlertTriangle, AlertCircle, Info, CheckCircle2, ChevronLeft, ChevronRight, X, Send, FileJson, Loader2, Sparkles } from 'lucide-react'
import { useStore } from '@/store'
import { cn } from '@/lib/utils'
import type { Severity, AlertStatus, Alert, AnomalySample, AnomalySampleRecord } from '@/types'

function relativeTime(dateStr: string): string {
  const now = Date.now()
  const then = new Date(dateStr).getTime()
  const diff = Math.max(0, now - then)
  const seconds = Math.floor(diff / 1000)
  const minutes = Math.floor(seconds / 60)
  const hours = Math.floor(minutes / 60)
  const days = Math.floor(hours / 24)
  if (days > 0) return `${days}天前`
  if (hours > 0) return `${hours}小时前`
  if (minutes > 0) return `${minutes}分钟前`
  return '刚刚'
}

const severityConfig: Record<Severity, { label: string; color: string; bg: string; border: string; icon: typeof AlertCircle }> = {
  critical: { label: '严重', color: 'text-red-400', bg: 'bg-red-500/10', border: 'border-red-500', icon: AlertCircle },
  warning: { label: '警告', color: 'text-amber-400', bg: 'bg-amber-500/10', border: 'border-amber-500', icon: AlertTriangle },
  info: { label: '信息', color: 'text-cyan-400', bg: 'bg-cyan-500/10', border: 'border-cyan-500', icon: Info },
}

const statusConfig: Record<AlertStatus, { label: string; color: string; bg: string }> = {
  active: { label: '活跃', color: 'text-red-400', bg: 'bg-red-500/10' },
  acknowledged: { label: '已确认', color: 'text-amber-400', bg: 'bg-amber-500/10' },
  resolved: { label: '已解决', color: 'text-gray-400', bg: 'bg-gray-500/10' },
}

const severityOptions = [
  { key: '', label: '全部' },
  { key: 'critical', label: '严重' },
  { key: 'warning', label: '警告' },
  { key: 'info', label: '信息' },
]

const statusOptions = [
  { key: '', label: '全部' },
  { key: 'active', label: '活跃' },
  { key: 'acknowledged', label: '已确认' },
  { key: 'resolved', label: '已解决' },
]

function FilterChip({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'px-3 py-1 rounded-full text-sm border transition-all',
        active
          ? 'border-cyan-500 bg-cyan-500/10 text-cyan-400'
          : 'border-gray-700 bg-gray-800/50 text-gray-400 hover:border-gray-500'
      )}
    >
      {label}
    </button>
  )
}

function StatusDot({ status }: { status: AlertStatus }) {
  if (status === 'active') {
    return <span className="relative flex h-2.5 w-2.5"><span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75" /><span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-red-500" /></span>
  }
  if (status === 'acknowledged') {
    return <span className="inline-flex rounded-full h-2.5 w-2.5 bg-amber-400" />
  }
  return <CheckCircle2 className="h-3.5 w-3.5 text-gray-500" />
}

function AlertCard({ alert, onAcknowledge, onResolve, onViewSamples, samples }: { alert: Alert; onAcknowledge: (id: string) => void; onResolve: (id: string, resolution: string) => void; onViewSamples: (alertId: string) => void; samples?: AnomalySample[] }) {
  const [showResolve, setShowResolve] = useState(false)
  const [resolution, setResolution] = useState('')
  const sev = severityConfig[alert.severity]
  const stat = statusConfig[alert.status]
  const SevIcon = sev.icon
  const isCriticalActive = alert.severity === 'critical' && alert.status === 'active'
  const isResolved = alert.status === 'resolved'
  const hasSamples = samples && samples.length > 0

  const handleSubmitResolve = () => {
    if (resolution.trim()) {
      onResolve(alert.id, resolution.trim())
      setShowResolve(false)
      setResolution('')
    }
  }

  const handleCancelResolve = () => {
    setShowResolve(false)
    setResolution('')
  }

  return (
    <div
      className={cn(
        'relative flex rounded-lg border overflow-hidden transition-opacity',
        isResolved ? 'opacity-50' : 'opacity-100',
        isCriticalActive && 'animate-[pulse-glow_2s_ease-in-out_infinite]',
        alert.severity === 'critical' ? 'border-red-500/30' : alert.severity === 'warning' ? 'border-amber-500/30' : 'border-cyan-500/30'
      )}
      style={isCriticalActive ? { boxShadow: '0 0 15px rgba(239,68,68,0.15)' } : undefined}
    >
      <div className={cn('w-1.5 shrink-0', alert.severity === 'critical' ? 'bg-red-500' : alert.severity === 'warning' ? 'bg-amber-500' : 'bg-cyan-500')} />
      <div className="flex-1 p-4 bg-gray-900/60">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1.5">
              <span className={cn('inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium', sev.bg, sev.color)}>
                <SevIcon className="h-3 w-3" />{sev.label}
              </span>
              <span className={cn('inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-medium', stat.bg, stat.color)}>
                <StatusDot status={alert.status} />{stat.label}
              </span>
            </div>
            <div className="font-mono text-sm text-cyan-300 mb-1">{alert.table_name || alert.table_id}</div>
            <p className="text-sm text-gray-300 mb-2">{alert.message}</p>
            <div className="flex items-center gap-4 text-xs text-gray-500">
              <span>实际值: <span className="text-white font-medium">{alert.actual_value}</span></span>
              <span>阈值: <span className="text-white font-medium">{alert.threshold_value}</span></span>
              <span>{relativeTime(alert.triggered_at)}</span>
            </div>
          </div>
          <div className="shrink-0 flex flex-col items-end gap-2">
            <div className="flex items-center gap-2">
              <button
                onClick={() => onViewSamples(alert.id)}
                className="px-3 py-1 text-xs rounded border border-gray-600/50 text-gray-400 hover:bg-gray-600/10 hover:text-gray-300 transition-colors flex items-center gap-1"
              >
                <FileJson className="w-3 h-3" />
                查看样本
                {hasSamples && (
                  <span className="ml-1 px-1.5 py-0.5 text-[10px] rounded-full bg-emerald-500/20 text-emerald-400">
                    {samples![0].sample_count}
                  </span>
                )}
              </button>
              {alert.status === 'active' && (
                <button
                  onClick={() => onAcknowledge(alert.id)}
                  className="px-3 py-1 text-xs rounded border border-amber-500/50 text-amber-400 hover:bg-amber-500/10 transition-colors"
                >
                  确认
                </button>
              )}
              {alert.status === 'acknowledged' && !showResolve && (
                <button
                  onClick={() => setShowResolve(true)}
                  className="px-3 py-1 text-xs rounded border border-cyan-500/50 text-cyan-400 hover:bg-cyan-500/10 transition-colors"
                >
                  解决
                </button>
              )}
            </div>
          </div>
        </div>
        {showResolve && (
          <div className="mt-3 pt-3 border-t border-gray-700/50">
            <textarea
              value={resolution}
              onChange={(e) => setResolution(e.target.value)}
              placeholder="输入解决方案..."
              rows={2}
              className="w-full rounded bg-gray-800 border border-gray-700 text-sm text-gray-200 p-2 resize-none focus:outline-none focus:border-cyan-500/50 placeholder:text-gray-600"
            />
            <div className="flex justify-end gap-2 mt-2">
              <button onClick={handleCancelResolve} className="p-1 rounded text-gray-500 hover:text-gray-300 transition-colors"><X className="h-4 w-4" /></button>
              <button
                onClick={handleSubmitResolve}
                disabled={!resolution.trim()}
                className="p-1 rounded text-cyan-400 hover:text-cyan-300 disabled:text-gray-600 disabled:cursor-not-allowed transition-colors"
              >
                <Send className="h-4 w-4" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function SampleModal({ alert, samples, onClose, onGenerate, generating }: { alert: Alert | null; samples: AnomalySample[]; onClose: () => void; onGenerate: (alertId: string) => void; generating: boolean }) {
  if (!alert) return null

  const latestSample = samples[0]
  let sampleRecords: AnomalySampleRecord[] = []
  if (latestSample?.sample_data) {
    try {
      sampleRecords = JSON.parse(latestSample.sample_data)
    } catch {
      sampleRecords = []
    }
  }

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="rounded-xl border border-gray-700 bg-[#0d1424] w-full max-w-3xl max-h-[80vh] flex flex-col">
        <div className="flex items-center justify-between p-4 border-b border-gray-700/50">
          <div>
            <h2 className="text-lg font-semibold text-white flex items-center gap-2">
              <FileJson className="w-5 h-5 text-cyan-400" />
              异常样本数据
            </h2>
            <p className="text-sm text-gray-500 mt-0.5 font-mono">{alert.table_name || alert.table_id}</p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => onGenerate(alert.id)}
              disabled={generating}
              className="px-3 py-1.5 text-xs rounded-lg border border-cyan-500/50 bg-cyan-500/10 text-cyan-400 hover:bg-cyan-500/20 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-1.5"
            >
              {generating ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />}
              {generating ? '生成中...' : '生成样本'}
            </button>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-gray-700/50 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>
        <div className="flex-1 overflow-y-auto p-4">
          {sampleRecords.length > 0 ? (
            <div className="rounded-lg border border-gray-700/50 overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-[#0a0f1a]">
                    <th className="text-left text-gray-500 font-medium px-4 py-3 border-b border-gray-700/50">字段</th>
                    <th className="text-left text-gray-500 font-medium px-4 py-3 border-b border-gray-700/50">值</th>
                    <th className="text-left text-gray-500 font-medium px-4 py-3 border-b border-gray-700/50">异常原因</th>
                  </tr>
                </thead>
                <tbody>
                  {sampleRecords.map((record, idx) => (
                    <tr key={idx} className="border-b border-gray-700/30 hover:bg-[#0a0f1a]/50">
                      <td className="px-4 py-2.5 font-mono text-cyan-400">{record.field}</td>
                      <td className="px-4 py-2.5 text-gray-300 font-mono">
                        {record.value === null || record.value === undefined ? (
                          <span className="text-red-400">NULL</span>
                        ) : (
                          String(record.value)
                        )}
                      </td>
                      <td className="px-4 py-2.5 text-amber-400 text-xs">{record.reason}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-12 text-gray-500">
              <FileJson className="w-12 h-12 mb-3 opacity-30" />
              <p className="text-sm mb-4">暂无样本数据</p>
              <button
                onClick={() => onGenerate(alert.id)}
                disabled={generating}
                className="px-4 py-2 text-sm rounded-lg border border-cyan-500/50 bg-cyan-500/10 text-cyan-400 hover:bg-cyan-500/20 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
              >
                {generating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                {generating ? '生成中...' : '生成样本数据'}
              </button>
            </div>
          )}
          {latestSample && (
            <div className="mt-4 flex items-center justify-between text-xs text-gray-500">
              <span>样本数量: <span className="text-gray-300">{latestSample.sample_count}</span></span>
              <span>生成时间: <span className="text-gray-300">{new Date(latestSample.generated_at).toLocaleString()}</span></span>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default function Alerts() {
  const {
    alerts, alertsTotal, alertsLoading, alertsPage,
    alertsSeverity, alertsStatus, anomalySamples,
    fetchAlerts, setAlertsPage, setAlertsFilter,
    acknowledgeAlert, resolveAlert,
    fetchSamplesByAlert, generateSamples, generateSamplesForActiveAlerts,
  } = useStore()

  const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null)
  const [showSampleModal, setShowSampleModal] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [generatingBulk, setGeneratingBulk] = useState(false)
  const [loadingSamples, setLoadingSamples] = useState<string | null>(null)

  useEffect(() => { fetchAlerts() }, [])

  const totalPages = Math.ceil(alertsTotal / 10)

  const handleViewSamples = async (alertId: string) => {
    const alert = alerts.find(a => a.id === alertId)
    if (!alert) return

    setSelectedAlert(alert)
    setShowSampleModal(true)
    setLoadingSamples(alertId)
    try {
      await fetchSamplesByAlert(alertId)
    } finally {
      setLoadingSamples(null)
    }
  }

  const handleGenerateSample = async (alertId: string) => {
    setGenerating(true)
    try {
      await generateSamples({ alert_id: alertId })
      await fetchSamplesByAlert(alertId)
    } finally {
      setGenerating(false)
    }
  }

  const handleBulkGenerate = async () => {
    setGeneratingBulk(true)
    try {
      await generateSamplesForActiveAlerts()
      await fetchAlerts()
    } finally {
      setGeneratingBulk(false)
    }
  }

  const alertSamples = selectedAlert ? (anomalySamples[selectedAlert.id] || []) : []

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">告警中心</h1>
        <div className="flex items-center gap-3">
          <button
            onClick={handleBulkGenerate}
            disabled={generatingBulk}
            className="px-4 py-2 rounded-lg border border-emerald-500/50 bg-emerald-500/10 text-emerald-400 text-sm font-medium hover:bg-emerald-500/20 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
          >
            {generatingBulk ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
            {generatingBulk ? '生成中...' : '批量生成样本'}
          </button>
          <span className="text-sm text-gray-400">共 {alertsTotal} 条告警</span>
        </div>
      </div>

      <div className="flex flex-wrap gap-4 items-center">
        <div className="flex items-center gap-1.5">
          <span className="text-xs text-gray-500 mr-1">严重程度</span>
          {severityOptions.map(opt => (
            <FilterChip
              key={opt.key}
              label={opt.label}
              active={alertsSeverity === opt.key}
              onClick={() => setAlertsFilter(opt.key, alertsStatus)}
            />
          ))}
        </div>
        <div className="w-px h-5 bg-gray-700" />
        <div className="flex items-center gap-1.5">
          <span className="text-xs text-gray-500 mr-1">状态</span>
          {statusOptions.map(opt => (
            <FilterChip
              key={opt.key}
              label={opt.label}
              active={alertsStatus === opt.key}
              onClick={() => setAlertsFilter(alertsSeverity, opt.key)}
            />
          ))}
        </div>
      </div>

      {alertsLoading ? (
        <div className="flex items-center justify-center py-20 text-gray-500">加载中...</div>
      ) : alerts.length === 0 ? (
        <div className="flex items-center justify-center py-20 text-gray-500">暂无告警</div>
      ) : (
        <div className="space-y-3">
          {alerts.map(alert => (
            <AlertCard
              key={alert.id}
              alert={alert}
              onAcknowledge={acknowledgeAlert}
              onResolve={resolveAlert}
              onViewSamples={handleViewSamples}
              samples={anomalySamples[alert.id]}
            />
          ))}
        </div>
      )}

      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-4 pt-2">
          <button
            onClick={() => setAlertsPage(alertsPage - 1)}
            disabled={alertsPage <= 1}
            className="p-1.5 rounded border border-gray-700 text-gray-400 hover:border-cyan-500/50 hover:text-cyan-400 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
          <span className="text-sm text-gray-400">{alertsPage} / {totalPages}</span>
          <button
            onClick={() => setAlertsPage(alertsPage + 1)}
            disabled={alertsPage >= totalPages}
            className="p-1.5 rounded border border-gray-700 text-gray-400 hover:border-cyan-500/50 hover:text-cyan-400 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      )}

      <SampleModal
        alert={selectedAlert}
        samples={alertSamples}
        onClose={() => {
          setShowSampleModal(false)
          setSelectedAlert(null)
        }}
        onGenerate={handleGenerateSample}
        generating={generating}
      />

      {showSampleModal && loadingSamples === selectedAlert?.id && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-[60] pointer-events-none">
          <div className="flex items-center gap-2 text-gray-300 bg-[#0d1424] px-4 py-3 rounded-lg border border-gray-700">
            <Loader2 className="w-5 h-5 animate-spin text-cyan-400" />
            <span className="text-sm">加载样本数据中...</span>
          </div>
        </div>
      )}
    </div>
  )
}
