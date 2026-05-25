import React, { useState } from 'react'
import { StyleAnalysis, TranslationStyle } from '../types'
import { analyzeStyle, getStyleLabel, getStyleColor, getStyleIcon, checkStyleConsistencyBatch } from '../services/styleCheckService'
import { LanguageCode } from '../types'

interface StyleAnalysisPanelProps {
  text: string
  lang: LanguageCode
  expectedStyle?: TranslationStyle
  onExpectedStyleChange?: (style: TranslationStyle) => void
  segments?: Array<{ id: string; text: string }>
}

const ScoreGauge: React.FC<{ score: number; label: string; color: string }> = ({ score, label, color }) => (
  <div className="flex flex-col items-center">
    <div className="relative w-20 h-20">
      <svg className="w-20 h-20 transform -rotate-90">
        <circle
          cx="40"
          cy="40"
          r="36"
          fill="none"
          stroke="#e5e7eb"
          strokeWidth="8"
        />
        <circle
          cx="40"
          cy="40"
          r="36"
          fill="none"
          stroke={color}
          strokeWidth="8"
          strokeDasharray={`${(score / 100) * 226.2} 226.2`}
          strokeLinecap="round"
          className="transition-all duration-500"
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
        <span className="text-xl font-bold" style={{ color }}>{score}</span>
      </div>
    </div>
    <span className="text-sm text-gray-600 mt-1">{label}</span>
  </div>
)

const StyleBadge: React.FC<{ style: TranslationStyle; confidence: number }> = ({ style, confidence }) => (
  <div className="flex items-center gap-2 px-4 py-2 rounded-xl bg-white shadow-sm border border-gray-200">
    <span className="text-2xl">{getStyleIcon(style)}</span>
    <div>
      <p className="font-semibold text-gray-800">{getStyleLabel(style)}</p>
      <p className="text-xs text-gray-500">置信度 {confidence}%</p>
    </div>
  </div>
)

const FeatureBar: React.FC<{ label: string; value: number; max: number; color: string }> = ({ label, value, max, color }) => (
  <div className="flex items-center gap-3">
    <span className="text-sm text-gray-600 w-20">{label}</span>
    <div className="flex-1 h-6 bg-gray-100 rounded-full overflow-hidden flex items-center px-2">
      <div
        className={`h-4 ${color} rounded-full transition-all duration-500`}
        style={{ width: `${(value / max) * 100}%` }}
      />
    </div>
    <span className="text-sm font-medium text-gray-700 w-8 text-right">{value}</span>
  </div>
)

const IssueItem: React.FC<{ issue: StyleAnalysis['issues'][0] }> = ({ issue }) => {
  const severityColors = {
    low: 'bg-yellow-50 border-yellow-200 text-yellow-800',
    medium: 'bg-orange-50 border-orange-200 text-orange-800',
    high: 'bg-red-50 border-red-200 text-red-800',
  }

  const typeLabels: Record<string, string> = {
    inconsistency: '一致性',
    formality_mismatch: '正式度',
    tone_mismatch: '语气',
    terminology_mismatch: '术语',
  }

  return (
    <div className={`p-3 rounded-lg border ${severityColors[issue.severity]} mb-2`}>
      <div className="flex items-start gap-2">
      <span className="text-lg">
        {issue.type === 'inconsistency' ? '⚠️' : 
         issue.type === 'formality_mismatch' ? '🎭' :
         issue.type === 'tone_mismatch' ? '🎨' : '📚'}
      </span>
      <div className="flex-1">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-xs px-2 py-0.5 rounded-full bg-white/50">
            {typeLabels[issue.type] || issue.type}
          </span>
          {issue.location && (
            <span className="text-xs opacity-70">位置: {issue.location}</span>
          )}
        </div>
        <p className="text-sm font-medium">{issue.message}</p>
        {issue.suggestion && (
          <p className="text-sm mt-1 opacity-80">💡 {issue.suggestion}</p>
        )}
      </div>
    </div>
    </div>
  )
}

export const StyleAnalysisPanel: React.FC<StyleAnalysisPanelProps> = ({
  text,
  lang,
  expectedStyle,
  onExpectedStyleChange,
  segments,
}) => {
  const [analysis, setAnalysis] = useState<StyleAnalysis | null>(null)
  const [batchResults, setBatchResults] = useState<Array<{ id: string; analysis: StyleAnalysis; overallConsistency: number }> | null>(null)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [showBatch, setShowBatch] = useState(false)

  const handleAnalyze = async () => {
    if (!text.trim()) return

    setIsAnalyzing(true)
    try {
      const result = analyzeStyle(text, lang, expectedStyle)
      setAnalysis(result)

      if (segments && segments.length > 1) {
        const batchResult = checkStyleConsistencyBatch(segments, lang, expectedStyle)
        setBatchResults(batchResult)
      }
    } finally {
      setIsAnalyzing(false)
    }
  }

  const styleOptions: Array<{ value: TranslationStyle; label: string; icon: string }> = [
    { value: 'formal', label: '正式', icon: '🎩' },
    { value: 'friendly', label: '亲切', icon: '😊' },
    { value: 'neutral', label: '中性', icon: '⚖️' },
    { value: 'technical', label: '技术', icon: '💻' },
    { value: 'casual', label: '随意', icon: '🎈' },
  ]

  if (!text.trim()) {
    return (
      <div className="bg-white rounded-xl shadow-lg p-6">
        <div className="text-center py-8 text-gray-500">
          <span className="text-4xl block mb-3">🎨</span>
          <p>输入文本后可进行风格分析</p>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-xl shadow-lg overflow-hidden">
      <div className="p-6 bg-gradient-to-r from-pink-50 to-rose-50 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-800 flex items-center gap-2">
            <span>🎨</span> 翻译风格检查
          </h3>
          <button
            onClick={handleAnalyze}
            disabled={isAnalyzing || !text.trim()}
            className="px-4 py-2 bg-pink-600 text-white rounded-lg hover:bg-pink-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors text-sm flex items-center gap-2"
          >
            {isAnalyzing ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />
                分析中...
              </>
            ) : (
              <>
                <span>🔍</span> 开始分析
              </>
            )}
          </button>
        </div>

        {onExpectedStyleChange && (
          <div className="mt-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
            预期风格
            </label>
            <div className="flex flex-wrap gap-2">
              {styleOptions.map((option) => (
                <button
                  key={option.value}
                  onClick={() => onExpectedStyleChange(option.value)}
                  className={`px-3 py-1.5 rounded-lg text-sm transition-colors flex items-center gap-1 ${
                    expectedStyle === option.value
                      ? 'bg-pink-600 text-white'
                      : 'bg-white text-gray-700 border border-gray-300 hover:border-pink-300'
                  }`}
                >
                  <span>{option.icon}</span>
                  <span>{option.label}</span>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {analysis && (
        <>
          <div className="p-6 border-b border-gray-200">
            <div className="flex items-center justify-center gap-4 mb-6">
              <StyleBadge style={analysis.detectedStyle} confidence={analysis.confidence} />
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-sm font-medium text-gray-700">风格一致性</span>
                  <span className={`text-lg font-bold ${analysis.consistencyScore >= 80 ? 'text-green-600' : analysis.consistencyScore >= 60 ? 'text-yellow-600' : 'text-red-600'}`}>
                    {analysis.consistencyScore}%
                  </span>
                </div>
                <div className="h-3 bg-gray-200 rounded-full overflow-hidden">
                  <div
                    className={`h-full ${analysis.consistencyScore >= 80 ? 'bg-green-500' : analysis.consistencyScore >= 60 ? 'bg-yellow-500' : 'bg-red-500'}`}
                    style={{ width: `${analysis.consistencyScore}%` }}
                  />
                </div>
              </div>
            </div>
          </div>

          <div className="p-6 border-b border-gray-200 bg-gray-50">
            <h4 className="text-sm font-medium text-gray-700 mb-4">风格维度评分</h4>
            <div className="flex justify-around">
              <ScoreGauge score={analysis.formalityScore} label="正式度" color="#3B82F6" />
              <ScoreGauge score={analysis.friendlinessScore} label="亲切度" color="#10B981" />
              <ScoreGauge score={analysis.technicalityScore} label="技术性" color="#8B5CF6" />
            </div>
          </div>

          <div className="p-6 border-b border-gray-200">
            <h4 className="text-sm font-medium text-gray-700 mb-4">语言特征分析</h4>
            <div className="space-y-3">
              <FeatureBar label="人称代词" value={analysis.styleFeatures.pronouns} max={20} color="bg-blue-400" />
              <FeatureBar label="情态动词" value={analysis.styleFeatures.modalVerbs} max={15} color="bg-green-400" />
              <FeatureBar label="缩写形式" value={analysis.styleFeatures.contractions} max={10} color="bg-yellow-400" />
              <FeatureBar label="敬语使用" value={analysis.styleFeatures.honorifics} max={10} color="bg-purple-400" />
              <FeatureBar label="平均句长" value={analysis.styleFeatures.sentenceLength} max={80} color="bg-pink-400" />
              <FeatureBar label="词汇丰富度" value={analysis.styleFeatures.vocabularyComplexity} max={100} color="bg-indigo-400" />
            </div>
          </div>

          {analysis.issues.length > 0 && (
            <div className="p-6 border-b border-gray-200">
              <h4 className="text-sm font-medium text-gray-700 mb-3">
                发现问题 ({analysis.issues.length})
              </h4>
              <div className="max-h-60 overflow-y-auto">
                {analysis.issues.map(issue => (
                  <IssueItem key={issue.id} issue={issue} />
                ))}
              </div>
            </div>
          )}

          {analysis.suggestions.length > 0 && (
            <div className="p-6">
              <h4 className="text-sm font-medium text-gray-700 mb-3">
                💡 改进建议
              </h4>
              <ul className="space-y-2">
                {analysis.suggestions.map((suggestion, idx) => (
                  <li key={idx} className="text-sm text-gray-600 flex items-start gap-2">
                    <span className="text-pink-500 mt-0.5">•</span>
                    <span>{suggestion}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {batchResults && batchResults.length > 1 && (
            <div className="p-6 bg-gray-50 border-t border-gray-200">
              <button
                onClick={() => setShowBatch(!showBatch)}
                className="w-full flex items-center justify-between text-sm text-gray-700"
              >
                <span className="flex items-center gap-2">
                  <span>📊</span>
                  分段风格一致性分析 (整体一致性: {batchResults[0]?.overallConsistency || 0}%)
                </span>
                <span>{showBatch ? '▲' : '▼'}</span>
              </button>

              {showBatch && (
                <div className="mt-4 space-y-3">
                  {batchResults.map((result, idx) => (
                    <div key={result.id} className="p-3 bg-white rounded-lg border border-gray-200">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-medium text-gray-700">段落 {idx + 1}</span>
                        <div className="flex items-center gap-2">
                          <span className="text-lg">{getStyleIcon(result.analysis.detectedStyle)}</span>
                          <span className="text-sm text-gray-600">
                            {getStyleLabel(result.analysis.detectedStyle)}
                          </span>
                          <span className={`text-sm font-medium ${
                            result.analysis.consistencyScore >= 80 ? 'text-green-600' :
                            result.analysis.consistencyScore >= 60 ? 'text-yellow-600' : 'text-red-600'
                          }`}>
                            {result.analysis.consistencyScore}%
                          </span>
                        </div>
                      </div>
                      <p className="text-xs text-gray-500 line-clamp-2">
                        {result.analysis.issues.length > 0 
                          ? `${result.analysis.issues.length} 个问题需要关注`
                          : '风格一致'
                        }
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </>
      )}

      {!analysis && !isAnalyzing && (
        <div className="p-12 text-center text-gray-500">
          <span className="text-4xl block mb-3">✨</span>
          <p>点击"开始分析"按钮检测译文风格</p>
        </div>
      )}
    </div>
  )
}
