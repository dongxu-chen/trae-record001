import { useState } from 'react'
import { CheckCircle, AlertTriangle, XCircle, RefreshCw, Eye } from 'lucide-react'
import { useAnnotationStore } from '@/store/annotationStore'
import { useToolsStore } from '@/store/toolsStore'
import { QualityInspector, QualityIssue } from '@/utils/QualityInspector'
import { cn } from '@/utils/cn'

export default function QualityPanel() {
  const [sampleSize, setSampleSize] = useState(20)
  const { annotations } = useAnnotationStore()
  const {
    inspectionResult,
    setInspectionResult,
    isInspecting,
    setIsInspecting,
    qualityIssues,
    setQualityIssues,
  } = useToolsStore()

  const runInspection = async () => {
    if (annotations.length === 0) return

    setIsInspecting(true)
    
    await new Promise(resolve => setTimeout(resolve, 500))
    
    const inspector = new QualityInspector()
    inspector.setAnnotations(annotations)
    const result = inspector.inspectSample(sampleSize)
    
    setInspectionResult(result)
    setQualityIssues(result.inspection.issues)
    setIsInspecting(false)
  }

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'high': return 'text-red-400 bg-red-500/20'
      case 'medium': return 'text-yellow-400 bg-yellow-500/20'
      case 'low': return 'text-blue-400 bg-blue-500/20'
      default: return 'text-zinc-400 bg-zinc-500/20'
    }
  }

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'high': return <XCircle className="w-4 h-4" />
      case 'medium': return <AlertTriangle className="w-4 h-4" />
      case 'low': return <Eye className="w-4 h-4" />
      default: return <Eye className="w-4 h-4" />
    }
  }

  const getScoreColor = (score: number) => {
    if (score >= 90) return 'text-green-400'
    if (score >= 70) return 'text-yellow-400'
    return 'text-red-400'
  }

  return (
    <div className="glass-panel rounded-xl p-4 w-72">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-white">标注质检</h3>
        <button
          onClick={runInspection}
          disabled={isInspecting || annotations.length === 0}
          className="p-2 bg-zinc-700 hover:bg-zinc-600 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <RefreshCw className={cn("w-4 h-4 text-zinc-300", isInspecting && "animate-spin")} />
        </button>
      </div>

      {annotations.length === 0 && (
        <p className="text-sm text-zinc-500 text-center py-4">
          暂无标注数据
        </p>
      )}

      {annotations.length > 0 && !inspectionResult && !isInspecting && (
        <div className="space-y-4">
          <div>
            <label className="text-xs text-zinc-400 mb-1 block">抽检数量</label>
            <select
              value={sampleSize}
              onChange={(e) => setSampleSize(Number(e.target.value))}
              className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-white"
            >
              <option value={10}>10 个标注</option>
              <option value={20}>20 个标注</option>
              <option value={50}>50 个标注</option>
              <option value={100}>100 个标注</option>
            </select>
          </div>
          <button
            onClick={runInspection}
            className="w-full btn-primary"
          >
            开始抽检
          </button>
        </div>
      )}

      {isInspecting && (
        <div className="flex flex-col items-center py-8">
          <div className="w-12 h-12 border-4 border-zinc-700 border-t-primary-500 rounded-full animate-spin mb-3" />
          <p className="text-sm text-zinc-400">正在质检...</p>
        </div>
      )}

      {inspectionResult && !isInspecting && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-zinc-800/50 rounded-lg p-3 text-center">
              <div className="text-2xl font-bold text-white">
                {inspectionResult.sampleSize}
              </div>
              <div className="text-xs text-zinc-400">抽检数量</div>
            </div>
            <div className="bg-zinc-800/50 rounded-lg p-3 text-center">
              <div className={cn("text-2xl font-bold", getScoreColor(inspectionResult.inspection.qualityScore))}>
                {inspectionResult.inspection.qualityScore.toFixed(0)}
              </div>
              <div className="text-xs text-zinc-400">质量分</div>
            </div>
          </div>

          <div className="bg-zinc-800/50 rounded-lg p-3">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-zinc-300">通过率</span>
              <span className="text-sm font-medium text-green-400">
                {inspectionResult.inspection.passRate.toFixed(1)}%
              </span>
            </div>
            <div className="h-2 bg-zinc-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-green-500 transition-all"
                style={{ width: `${inspectionResult.inspection.passRate}%` }}
              />
            </div>
            <div className="flex justify-between text-xs text-zinc-500 mt-1">
              <span>通过 {inspectionResult.inspection.passed}</span>
              <span>检查 {inspectionResult.inspection.checked}</span>
            </div>
          </div>

          {qualityIssues.length > 0 && (
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-zinc-300">问题列表</span>
                <span className="text-xs text-zinc-500">
                  {qualityIssues.length} 个问题
                </span>
              </div>
              <div className="space-y-2 max-h-48 overflow-y-auto scrollbar-thin">
                {qualityIssues.slice(0, 10).map((issue: QualityIssue) => (
                  <div
                    key={issue.id}
                    className="bg-zinc-800/50 rounded-lg p-2"
                  >
                    <div className="flex items-start gap-2">
                      <span className={cn(
                        "p-1 rounded flex-shrink-0",
                        getSeverityColor(issue.severity)
                      )}>
                        {getSeverityIcon(issue.severity)}
                      </span>
                      <div className="flex-1 min-w-0">
                        <p className="text-xs text-white truncate">
                          {issue.message}
                        </p>
                        {issue.suggestedFix && (
                          <p className="text-[10px] text-zinc-500 mt-1">
                            建议: {issue.suggestedFix}
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {qualityIssues.length === 0 && (
            <div className="flex flex-col items-center py-4">
              <CheckCircle className="w-12 h-12 text-green-500 mb-2" />
              <p className="text-sm text-green-400">未发现问题</p>
            </div>
          )}

          <button
            onClick={runInspection}
            className="w-full btn-secondary text-sm"
          >
            重新抽检
          </button>
        </div>
      )}
    </div>
  )
}
