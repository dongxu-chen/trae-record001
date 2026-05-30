import { useState, useEffect } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar,
  LineChart, Line,
} from 'recharts'
import { X, Loader2, Settings2, Save, RotateCcw } from 'lucide-react'
import { useStore } from '@/store'
import { api } from '@/utils/api'
import { cn } from '@/lib/utils'
import type { TableScoreDetail, ScoreWeightConfig } from '@/types'

const DIMENSION_LABELS: Record<string, string> = {
  completeness: '完整性',
  consistency: '一致性',
  timeliness: '及时性',
  accuracy: '准确性',
}

function scoreColor(score: number) {
  if (score > 90) return 'text-emerald-400'
  if (score >= 70) return 'text-amber-400'
  return 'text-red-400'
}

function scoreBarColor(score: number) {
  if (score > 90) return 'bg-emerald-400'
  if (score >= 70) return 'bg-amber-400'
  return 'bg-red-400'
}

function barFill(score: number) {
  if (score > 90) return '#34d399'
  if (score >= 70) return '#fbbf24'
  return '#f87171'
}

function statusDot(status: string) {
  if (status === 'healthy') return 'bg-emerald-400'
  if (status === 'warning') return 'bg-amber-400'
  return 'bg-red-400'
}

function MiniBar({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex items-center gap-2 text-xs">
      <span className="w-14 text-gray-400 shrink-0">{label}</span>
      <div className="flex-1 h-1.5 bg-gray-800 rounded-full overflow-hidden">
        <div className={cn('h-full rounded-full transition-all', scoreBarColor(value))} style={{ width: `${value}%` }} />
      </div>
      <span className={cn('w-8 text-right font-mono', scoreColor(value))}>{value}</span>
    </div>
  )
}

function WeightSlider({ label, value, onChange }: { label: string; value: number; onChange: (v: number) => void }) {
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between">
        <span className="text-xs text-gray-400">{label}</span>
        <span className="text-xs font-mono text-cyan-400">{(value * 100).toFixed(0)}%</span>
      </div>
      <input
        type="range"
        min={0}
        max={100}
        value={Math.round(value * 100)}
        onChange={e => onChange(parseInt(e.target.value) / 100)}
        className="w-full h-1.5 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-cyan-500"
      />
    </div>
  )
}

export default function Scores() {
  const { scores, scoresLoading, fetchScores } = useStore()
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [detail, setDetail] = useState<TableScoreDetail | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [editingWeights, setEditingWeights] = useState(false)
  const [weights, setWeights] = useState<ScoreWeightConfig | null>(null)
  const [weightsSaving, setWeightsSaving] = useState(false)

  useEffect(() => { fetchScores() }, [fetchScores])

  useEffect(() => {
    if (!selectedId) { setDetail(null); setWeights(null); setEditingWeights(false); return }
    setDetailLoading(true)
    api.scores.get(selectedId)
      .then(setDetail)
      .catch(() => setDetail(null))
      .finally(() => setDetailLoading(false))
    api.scores.getWeights(selectedId)
      .then(setWeights)
      .catch(() => setWeights(null))
  }, [selectedId])

  const barData = scores.map(s => ({ name: s.table_name, score: s.overall_score, fill: barFill(s.overall_score) }))

  const selected = scores.find(s => s.table_id === selectedId)

  const handleSaveWeights = async () => {
    if (!selectedId || !weights) return
    setWeightsSaving(true)
    try {
      const total = weights.completeness_weight + weights.consistency_weight + weights.timeliness_weight + weights.accuracy_weight
      const normalized = {
        table_id: selectedId,
        completeness_weight: weights.completeness_weight / total,
        consistency_weight: weights.consistency_weight / total,
        timeliness_weight: weights.timeliness_weight / total,
        accuracy_weight: weights.accuracy_weight / total,
      }
      const result = await api.scores.updateWeights(selectedId, normalized)
      setWeights(result)
      setEditingWeights(false)
      fetchScores()
    } catch { /* ignore */ }
    finally { setWeightsSaving(false) }
  }

  return (
    <div className="min-h-screen bg-[#0a0f1a] text-white p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Quality Scores</h1>
        <p className="text-sm text-gray-400 mt-1">Data quality scores across all monitored tables</p>
      </div>

      <div className="rounded-xl border border-gray-800 bg-gray-900/50 p-5">
        <h2 className="text-sm font-semibold text-gray-300 mb-4">Overall Scores Overview</h2>
        {scoresLoading ? (
          <div className="flex items-center justify-center h-64"><Loader2 className="w-6 h-6 animate-spin text-cyan-400" /></div>
        ) : (
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={barData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
              <XAxis dataKey="name" tick={{ fill: '#9ca3af', fontSize: 11 }} axisLine={{ stroke: '#374151' }} />
              <YAxis domain={[0, 100]} tick={{ fill: '#9ca3af', fontSize: 11 }} axisLine={{ stroke: '#374151' }} />
              <Tooltip
                contentStyle={{ background: '#111827', border: '1px solid #374151', borderRadius: 8, color: '#e5e7eb' }}
                labelStyle={{ color: '#9ca3af' }}
              />
              <Bar dataKey="score" radius={[4, 4, 0, 0]}>
                {barData.map((entry, i) => (
                  <rect key={i} fill={entry.fill} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {scores.map(s => (
          <button
            key={s.table_id}
            onClick={() => setSelectedId(s.table_id)}
            className={cn(
              'rounded-xl border bg-gray-900/50 p-4 text-left transition-all duration-200 hover:scale-[1.02] hover:border-cyan-500/50',
              selectedId === s.table_id ? 'border-cyan-500/70 shadow-lg shadow-cyan-500/10' : 'border-gray-800'
            )}
          >
            <div className="flex items-center justify-between mb-3">
              <span className="font-mono text-sm text-cyan-300">{s.table_name}</span>
              <span className={cn('w-2 h-2 rounded-full', statusDot(s.overall_score > 90 ? 'healthy' : s.overall_score >= 70 ? 'warning' : 'critical'))} />
            </div>
            <p className={cn('text-4xl font-mono font-bold mb-4', scoreColor(s.overall_score))}>
              {s.overall_score}
            </p>
            <div className="space-y-2">
              {s.dimensions.map(d => (
                <MiniBar key={d.dimension} label={DIMENSION_LABELS[d.dimension] || d.dimension} value={d.score} />
              ))}
            </div>
          </button>
        ))}
      </div>

      {selectedId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" onClick={() => setSelectedId(null)}>
          <div
            className="bg-[#0a0f1a] border border-gray-700 rounded-2xl p-6 w-full max-w-3xl max-h-[85vh] overflow-y-auto shadow-2xl"
            onClick={e => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-5">
              <div>
                <h2 className="text-lg font-bold font-mono text-cyan-300">{selected?.table_name}</h2>
                <p className="text-xs text-gray-400 mt-0.5">Detailed quality analysis</p>
              </div>
              <button onClick={() => setSelectedId(null)} className="p-1.5 rounded-lg hover:bg-gray-800 transition-colors">
                <X className="w-5 h-5 text-gray-400" />
              </button>
            </div>

            {detailLoading ? (
              <div className="flex items-center justify-center h-64"><Loader2 className="w-6 h-6 animate-spin text-cyan-400" /></div>
            ) : detail ? (
              <div className="space-y-5">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                  <div className="rounded-xl border border-gray-800 bg-gray-900/50 p-4">
                    <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">Dimension Radar</h3>
                    <ResponsiveContainer width="100%" height={260}>
                      <RadarChart data={detail.dimensions.map(d => ({ dimension: DIMENSION_LABELS[d.dimension] || d.dimension, score: d.score }))}>
                        <PolarGrid stroke="#374151" />
                        <PolarAngleAxis dataKey="dimension" tick={{ fill: '#9ca3af', fontSize: 11 }} />
                        <PolarRadiusAxis domain={[0, 100]} tick={{ fill: '#6b7280', fontSize: 10 }} axisLine={false} />
                        <Radar dataKey="score" stroke="#06B6D4" fill="#06B6D4" fillOpacity={0.2} strokeWidth={2} />
                      </RadarChart>
                    </ResponsiveContainer>
                  </div>

                  <div className="rounded-xl border border-gray-800 bg-gray-900/50 p-4">
                    <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">Score History (30 Days)</h3>
                    <ResponsiveContainer width="100%" height={260}>
                      <LineChart data={detail.history}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                        <XAxis dataKey="date" tick={{ fill: '#6b7280', fontSize: 10 }} axisLine={{ stroke: '#374151' }} />
                        <YAxis domain={[0, 100]} tick={{ fill: '#6b7280', fontSize: 10 }} axisLine={{ stroke: '#374151' }} />
                        <Tooltip
                          contentStyle={{ background: '#111827', border: '1px solid #374151', borderRadius: 8, color: '#e5e7eb' }}
                          labelStyle={{ color: '#9ca3af' }}
                        />
                        <Line type="monotone" dataKey="score" stroke="#06B6D4" strokeWidth={2} dot={false} />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                <div className="col-span-1 md:col-span-2 rounded-xl border border-gray-800 bg-gray-900/50 p-4">
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">权重配置</h3>
                    <div className="flex items-center gap-2">
                      {editingWeights && (
                        <>
                          <button
                            onClick={() => {
                              setWeights({ table_id: selectedId, completeness_weight: 0.3, consistency_weight: 0.25, timeliness_weight: 0.2, accuracy_weight: 0.25 })
                            }}
                            className="p-1.5 rounded-md hover:bg-gray-800 text-gray-500 hover:text-gray-300 transition-colors"
                          >
                            <RotateCcw className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={handleSaveWeights}
                            disabled={weightsSaving}
                            className="flex items-center gap-1 px-3 py-1 text-xs rounded-md bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-white transition-colors"
                          >
                            <Save className="w-3 h-3" />
                            {weightsSaving ? '保存中...' : '保存'}
                          </button>
                        </>
                      )}
                      <button
                        onClick={() => setEditingWeights(!editingWeights)}
                        className={cn(
                          'p-1.5 rounded-md transition-colors',
                          editingWeights ? 'bg-cyan-500/20 text-cyan-400' : 'hover:bg-gray-800 text-gray-500 hover:text-gray-300'
                        )}
                      >
                        <Settings2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    {[
                      { key: 'completeness_weight' as const, label: '完整性' },
                      { key: 'consistency_weight' as const, label: '一致性' },
                      { key: 'timeliness_weight' as const, label: '及时性' },
                      { key: 'accuracy_weight' as const, label: '准确性' },
                    ].map(dim => (
                      editingWeights ? (
                        <WeightSlider
                          key={dim.key}
                          label={dim.label}
                          value={weights?.[dim.key] ?? 0.25}
                          onChange={v => setWeights(prev => prev ? { ...prev, [dim.key]: v } : null)}
                        />
                      ) : (
                        <div key={dim.key} className="space-y-1">
                          <div className="flex items-center justify-between">
                            <span className="text-xs text-gray-400">{dim.label}</span>
                            <span className="text-xs font-mono text-gray-500">{((weights?.[dim.key] ?? 0.25) * 100).toFixed(0)}%</span>
                          </div>
                          <div className="h-1.5 bg-gray-800 rounded-full overflow-hidden">
                            <div className="h-full rounded-full bg-cyan-500/60" style={{ width: `${(weights?.[dim.key] ?? 0.25) * 100}%` }} />
                          </div>
                        </div>
                      )
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              <div className="flex items-center justify-center h-40 text-gray-500 text-sm">Failed to load detail</div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
