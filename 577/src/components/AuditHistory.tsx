import { useState } from 'react'
import { History, FileText, Repeat, X, Eye, Clock } from 'lucide-react'
import { useAppStore, type AuditRecord } from '@/store/appStore'
import { getMethodLabel, getGoalLabel } from '@/utils/recommendationEngine'
import { cn } from '@/lib/utils'

export default function AuditHistory() {
  const auditHistory = useAppStore((s) => s.auditHistory)
  const activeAuditId = useAppStore((s) => s.activeAuditId)
  const fileMeta = useAppStore((s) => s.fileMeta)
  const applyAuditRecord = useAppStore((s) => s.applyAuditRecord)
  const setActiveAuditId = useAppStore((s) => s.setActiveAuditId)

  const [selectedRecord, setSelectedRecord] = useState<AuditRecord | null>(null)

  const relevantHistory = auditHistory.filter(h => fileMeta && h.fileId === fileMeta.fileId)

  const formatTime = (iso: string) => {
    const d = new Date(iso)
    return d.toLocaleString('zh-CN', { month: 'short', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' })
  }

  const handleReplay = (record: AuditRecord) => {
    applyAuditRecord(record)
    setSelectedRecord(null)
  }

  return (
    <div className="rounded-xl border border-slate-700/50 bg-slate-800/50 p-5 backdrop-blur-sm">
      <div className="mb-3 flex items-center gap-2">
        <History className="h-4 w-4 text-emerald-400" />
        <span className="text-sm font-medium text-slate-200">抽样审计</span>
        <span className="ml-auto rounded bg-slate-700/50 px-1.5 py-0.5 text-[10px] text-slate-400">
          {relevantHistory.length} 条记录
        </span>
      </div>

      {relevantHistory.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-6 text-center">
          <Clock className="mb-2 h-8 w-8 text-slate-600" />
          <p className="text-[11px] text-slate-500">暂无审计记录</p>
          <p className="text-[10px] text-slate-600">执行抽样后将自动记录</p>
        </div>
      ) : (
        <div className="max-h-64 space-y-1.5 overflow-y-auto pr-1">
          {relevantHistory.map((record) => (
            <button
              key={record.id}
              onClick={() => {
                setSelectedRecord(record === selectedRecord ? null : record)
                setActiveAuditId(record.id)
              }}
              className={cn(
                'w-full rounded-md border p-2.5 text-left transition-all',
                selectedRecord?.id === record.id || activeAuditId === record.id
                  ? 'border-emerald-500/50 bg-emerald-500/10'
                  : 'border-slate-700/30 bg-slate-900/30 hover:border-slate-600/50 hover:bg-slate-900/50',
              )}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="flex h-7 w-7 items-center justify-center rounded-md bg-slate-800">
                    <FileText className="h-3.5 w-3.5 text-slate-400" />
                  </div>
                  <div>
                    <p className="text-[11px] font-semibold text-slate-300">
                      {getMethodLabel(record.config.method)} · {(record.config.ratio * 100).toFixed(0)}%
                    </p>
                    <p className="text-[10px] text-slate-500">
                      {formatTime(record.timestamp)} · {record.stats.sampleSize} 条
                    </p>
                  </div>
                </div>
                {activeAuditId === record.id && (
                  <span className="rounded bg-emerald-500/20 px-1.5 py-0.5 text-[9px] font-semibold text-emerald-400">
                    当前
                  </span>
                )}
              </div>

              {selectedRecord?.id === record.id && (
                <div className="mt-2.5 border-t border-slate-700/50 pt-2.5">
                  <div className="mb-2 grid grid-cols-3 gap-2">
                    <MiniStat label="比例" value={`${(record.config.ratio * 100).toFixed(0)}%`} />
                    <MiniStat label="样本量" value={record.stats.sampleSize.toLocaleString()} />
                    <MiniStat label="KS值" value={record.comparison?.ksStatistic.toFixed(3) || '-'} />
                  </div>

                  {record.config.stratifyColumn && (
                    <p className="mb-2 text-[10px] text-slate-500">
                      分层字段: <span className="font-mono text-slate-300">{record.config.stratifyColumn}</span>
                    </p>
                  )}

                  {record.recommendation && (
                    <div className="mb-2 rounded bg-slate-900/60 p-2">
                      <p className="text-[10px] text-amber-400">
                        推荐方法: {getMethodLabel(record.recommendation.recommendedMethod)}
                        {' · '}
                        置信度 {(record.recommendation.confidence * 100).toFixed(0)}%
                      </p>
                    </div>
                  )}

                  <div className="flex gap-2">
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        handleReplay(record)
                      }}
                      className="flex flex-1 items-center justify-center gap-1 rounded-md bg-emerald-500/20 px-2 py-1.5 text-[10px] font-semibold text-emerald-400 transition hover:bg-emerald-500/30"
                    >
                      <Repeat className="h-3 w-3" />
                      复用参数
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        setSelectedRecord(null)
                      }}
                      className="flex items-center justify-center gap-1 rounded-md border border-slate-600/50 px-2 py-1.5 text-[10px] font-semibold text-slate-400 transition hover:bg-slate-700/50"
                    >
                      <X className="h-3 w-3" />
                      关闭
                    </button>
                  </div>
                </div>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

function MiniStat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-[9px] uppercase tracking-wider text-slate-500">{label}</p>
      <p className="font-mono text-[11px] font-bold text-slate-200">{value}</p>
    </div>
  )
}
