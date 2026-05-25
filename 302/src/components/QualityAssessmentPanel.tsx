import React from 'react'
import { QualityAssessment, QualityIssue } from '../types'
import { getQualityScoreColor, getQualityScoreBg, getQualityLabel } from '../services/qualityAssessment'

interface QualityAssessmentPanelProps {
  assessment: QualityAssessment | null
  isLoading?: boolean
  onReevaluate?: () => void
  onReview?: () => void
}

const ScoreBar: React.FC<{ score: number; label: string; showLabel?: boolean }> = ({ score, label, showLabel = true }) => (
  <div className="flex items-center gap-3">
    {showLabel && <span className="text-sm text-gray-600 w-16">{label}</span>}
    <div className="flex-1 h-3 bg-gray-200 rounded-full overflow-hidden">
      <div
        className={`h-full ${getQualityScoreBg(score)} transition-all duration-500`}
        style={{ width: `${score}%` }}
      />
    </div>
    <span className={`text-sm font-medium w-12 text-right ${getQualityScoreColor(score)}`}>
      {score}分
    </span>
  </div>
)

const IssueItem: React.FC<{ issue: QualityIssue }> = ({ issue }) => {
  const severityColors = {
    low: 'bg-yellow-100 text-yellow-800 border-yellow-300',
    medium: 'bg-orange-100 text-orange-800 border-orange-300',
    high: 'bg-red-100 text-red-800 border-red-300',
  }

  const severityLabels = {
    low: '轻微',
    medium: '中等',
    high: '严重',
  }

  const typeIcons: Record<string, string> = {
    fluency: '📖',
    fidelity: '🎯',
    terminology: '📚',
    grammar: '✏️',
    style: '🎨',
    other: '⚠️',
  }

  return (
    <div className={`p-3 rounded-lg border ${severityColors[issue.severity]} mb-2`}>
      <div className="flex items-start gap-2">
        <span className="text-lg">{typeIcons[issue.type] || '⚠️'}</span>
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs px-2 py-0.5 rounded-full bg-white/50">
              {severityLabels[issue.severity]}
            </span>
            <span className="text-xs opacity-70">
              {issue.type === 'fluency' ? '流畅度' :
               issue.type === 'fidelity' ? '忠实度' :
               issue.type === 'terminology' ? '术语' :
               issue.type === 'grammar' ? '语法' :
               issue.type === 'style' ? '风格' : '其他'}
            </span>
          </div>
          <p className="text-sm font-medium">{issue.message}</p>
          {issue.suggestion && (
            <p className="text-sm mt-1 opacity-80">💡 {issue.suggestion}</p>
          )}
          {issue.targetText && (
            <p className="text-xs mt-1 font-mono bg-white/30 px-2 py-1 rounded inline-block">
              问题文本: "{issue.targetText}"
            </p>
          )}
        </div>
      </div>
    </div>
  )
}

export const QualityAssessmentPanel: React.FC<QualityAssessmentPanelProps> = ({
  assessment,
  isLoading = false,
  onReevaluate,
  onReview,
}) => {
  if (isLoading) {
    return (
      <div className="bg-white rounded-xl shadow-lg p-6">
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
          <span className="ml-3 text-gray-600">正在评估翻译质量...</span>
        </div>
      </div>
    )
  }

  if (!assessment) {
    return (
      <div className="bg-white rounded-xl shadow-lg p-6">
        <div className="text-center py-8 text-gray-500">
          <span className="text-4xl block mb-3">📊</span>
          <p>翻译完成后将显示质量评估结果</p>
        </div>
      </div>
    )
  }

  const { score, issues, needsHumanReview, reviewReason, confidence } = assessment

  const highIssues = issues.filter(i => i.severity === 'high')
  const mediumIssues = issues.filter(i => i.severity === 'medium')
  const lowIssues = issues.filter(i => i.severity === 'low')

  return (
    <div className="bg-white rounded-xl shadow-lg overflow-hidden">
      <div className={`p-6 ${score.overall >= 80 ? 'bg-gradient-to-r from-green-50 to-emerald-50' : score.overall >= 60 ? 'bg-gradient-to-r from-yellow-50 to-orange-50' : 'bg-gradient-to-r from-red-50 to-rose-50'}`}>
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-gray-800 flex items-center gap-2">
              <span>📊</span> AI翻译质量评估
            </h3>
            <p className="text-sm text-gray-600 mt-1">
              置信度: {confidence}% · 评估时间: {new Date(assessment.timestamp).toLocaleString()}
            </p>
          </div>
          <div className="text-right">
            <div className={`text-4xl font-bold ${getQualityScoreColor(score.overall)}`}>
              {score.overall}
            </div>
            <div className={`text-sm ${getQualityScoreColor(score.overall)}`}>
              {getQualityLabel(score.overall)}
            </div>
          </div>
        </div>

        {needsHumanReview && (
          <div className="mt-4 p-4 bg-red-100 border border-red-300 rounded-lg">
            <div className="flex items-start gap-3">
              <span className="text-2xl">⚠️</span>
              <div>
                <p className="font-medium text-red-800">建议人工校对</p>
                <ul className="text-sm text-red-700 mt-1 list-disc list-inside">
                  {reviewReason.map((reason, idx) => (
                    <li key={idx}>{reason}</li>
                  ))}
                </ul>
                {onReview && (
                  <button
                    onClick={onReview}
                    className="mt-3 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors text-sm"
                  >
                    开始人工校对
                  </button>
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="p-6">
        <h4 className="text-sm font-medium text-gray-700 mb-4">多维度评分</h4>
        <div className="space-y-3">
          <ScoreBar score={score.overall} label="综合" />
          <ScoreBar score={score.fidelity} label="忠实度" />
          <ScoreBar score={score.fluency} label="流畅度" />
          <ScoreBar score={score.terminology} label="术语" />
          <ScoreBar score={score.grammar} label="语法" />
          <ScoreBar score={score.style} label="风格" />
        </div>
      </div>

      {issues.length > 0 && (
        <div className="px-6 pb-6">
          <div className="flex items-center justify-between mb-4">
            <h4 className="text-sm font-medium text-gray-700">
              发现问题 ({issues.length})
            </h4>
            <div className="flex gap-2 text-xs">
              {highIssues.length > 0 && (
                <span className="px-2 py-1 bg-red-100 text-red-700 rounded-full">
                  严重 {highIssues.length}
                </span>
              )}
              {mediumIssues.length > 0 && (
                <span className="px-2 py-1 bg-orange-100 text-orange-700 rounded-full">
                  中等 {mediumIssues.length}
                </span>
              )}
              {lowIssues.length > 0 && (
                <span className="px-2 py-1 bg-yellow-100 text-yellow-700 rounded-full">
                  轻微 {lowIssues.length}
                </span>
              )}
            </div>
          </div>

          <div className="max-h-80 overflow-y-auto">
            {highIssues.map(issue => (
              <IssueItem key={issue.id} issue={issue} />
            ))}
            {mediumIssues.map(issue => (
              <IssueItem key={issue.id} issue={issue} />
            ))}
            {lowIssues.map(issue => (
              <IssueItem key={issue.id} issue={issue} />
            ))}
          </div>
        </div>
      )}

      {onReevaluate && (
        <div className="px-6 pb-6">
          <button
            onClick={onReevaluate}
            className="w-full py-2 text-blue-600 border border-blue-300 rounded-lg hover:bg-blue-50 transition-colors text-sm"
          >
            🔄 重新评估
          </button>
        </div>
      )}
    </div>
  )
}
