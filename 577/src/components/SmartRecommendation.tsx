import { useEffect } from 'react'
import { Lightbulb, Target, CheckCircle, Sparkles } from 'lucide-react'
import { useAppStore, type AnalysisGoal, type SampleMethod } from '@/store/appStore'
import { generateRecommendation, getGoalLabel, getMethodLabel } from '@/utils/recommendationEngine'
import { cn } from '@/lib/utils'

const GOALS: Array<{ key: AnalysisGoal; label: string; icon: string; desc: string }> = [
  { key: 'descriptive', label: '描述统计', icon: '📊', desc: '概览数据分布' },
  { key: 'inferential', label: '推断统计', icon: '🔬', desc: '假设检验 / 置信区间' },
  { key: 'exploratory', label: '探索性分析', icon: '🔍', desc: '发现模式 / 异常' },
  { key: 'classification', label: '分类建模', icon: '🎯', desc: '构建分类模型' },
  { key: 'regression', label: '回归建模', icon: '📈', desc: '预测连续值' },
]

const METHOD_ICONS: Record<SampleMethod, string> = {
  random: '🎲',
  stratified: '📚',
  systematic: '📐',
}

export default function SmartRecommendation() {
  const fileMeta = useAppStore((s) => s.fileMeta)
  const analysisGoal = useAppStore((s) => s.analysisGoal)
  const allDataCache = useAppStore((s) => s.allDataCache)
  const recommendation = useAppStore((s) => s.recommendation)
  const setAnalysisGoal = useAppStore((s) => s.setAnalysisGoal)
  const setRecommendation = useAppStore((s) => s.setRecommendation)
  const setSampleConfig = useAppStore((s) => s.setSampleConfig)

  useEffect(() => {
    if (!fileMeta) return
    const rec = generateRecommendation({
      fileMeta,
      analysisGoal,
      data: allDataCache.length > 0 ? allDataCache : undefined,
    })
    setRecommendation(rec)
  }, [fileMeta, analysisGoal, allDataCache, setRecommendation])

  const applyRecommendation = () => {
    if (!recommendation) return
    setSampleConfig({ method: recommendation.recommendedMethod })
  }

  if (!fileMeta) return null

  return (
    <div className="rounded-xl border border-slate-700/50 bg-slate-800/50 p-5 backdrop-blur-sm">
      <div className="mb-3 flex items-center gap-2">
        <Lightbulb className="h-4 w-4 text-amber-400" />
        <span className="text-sm font-medium text-slate-200">智能抽样推荐</span>
      </div>

      <div className="mb-4">
        <p className="mb-2 text-xs font-medium text-slate-400">分析目标</p>
        <div className="grid grid-cols-5 gap-1.5">
          {GOALS.map(({ key, label, icon, desc }) => (
            <button
              key={key}
              onClick={() => setAnalysisGoal(key)}
              title={desc}
              className={cn(
                'flex flex-col items-center gap-0.5 rounded-lg border px-2 py-2 text-center transition-all',
                analysisGoal === key
                  ? 'border-amber-500/50 bg-amber-500/10 text-amber-400 shadow-lg shadow-amber-500/5'
                  : 'border-slate-600/30 bg-slate-900/30 text-slate-400 hover:border-slate-500/50 hover:text-slate-300',
              )}
            >
              <span className="text-lg">{icon}</span>
              <span className="text-[10px] font-medium">{label}</span>
            </button>
          ))}
        </div>
      </div>

      {recommendation && (
        <div className="space-y-3">
          <div className="rounded-lg bg-gradient-to-r from-amber-500/10 to-cyan-500/10 p-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-2xl">{METHOD_ICONS[recommendation.recommendedMethod]}</span>
                <div>
                  <p className="text-sm font-bold text-slate-200">
                    推荐：{getMethodLabel(recommendation.recommendedMethod)}
                  </p>
                  <p className="text-[10px] text-slate-500">
                    置信度 {(recommendation.confidence * 100).toFixed(0)}%
                    <span className="mx-1">·</span>
                    目标：{getGoalLabel(analysisGoal)}
                  </p>
                </div>
              </div>
              <button
                onClick={applyRecommendation}
                className="flex items-center gap-1 rounded-md bg-amber-500/20 px-2.5 py-1.5 text-[11px] font-semibold text-amber-400 transition hover:bg-amber-500/30"
              >
                <Sparkles className="h-3 w-3" />
                应用
              </button>
            </div>
          </div>

          <div className="space-y-1">
            {recommendation.reasons.map((reason, idx) => (
              <div key={idx} className="flex items-start gap-1.5">
                <CheckCircle className="mt-0.5 h-3 w-3 flex-shrink-0 text-emerald-400" />
                <span className="text-[11px] text-slate-400">{reason}</span>
              </div>
            ))}
          </div>

          {recommendation.alternatives.length > 0 && (
            <div>
              <p className="mb-1.5 text-[10px] font-medium uppercase tracking-wider text-slate-500">
                备选方案
              </p>
              <div className="space-y-1.5">
                {recommendation.alternatives.map((alt, idx) => (
                  <div
                    key={idx}
                    className="flex items-center gap-2 rounded-md bg-slate-900/40 px-2.5 py-1.5"
                  >
                    <span className="text-base">{METHOD_ICONS[alt.method]}</span>
                    <div>
                      <p className="text-[11px] font-semibold text-slate-300">
                        {getMethodLabel(alt.method)}
                      </p>
                      <p className="text-[10px] text-slate-500">{alt.reason}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
