import { useState, useMemo } from 'react'
import LearningEngine from '../utils/learningEngine'
import RuleEngine from '../utils/ruleEngine'

function AISuggestPanel({ columnName, dataType, columnAnalysis, onApplySuggestion }) {
  const [expandedIdx, setExpandedIdx] = useState(-1)

  const learningEngine = useMemo(() => new LearningEngine(), [])
  const ruleEngine = useMemo(() => new RuleEngine(), [])
  const suggestions = useMemo(() => {
    if (!columnName) return []
    return learningEngine.getAISuggestions(columnName, dataType, columnAnalysis)
  }, [columnName, dataType, columnAnalysis, learningEngine])

  const summary = useMemo(() => {
    return learningEngine.getHistorySummary()
  }, [learningEngine])

  const handleApply = (suggestion) => {
    const rule = ruleEngine.getRuleById(suggestion.ruleId)
    if (!rule) return

    onApplySuggestion({
      ...rule,
      example: suggestion.reason
    }, suggestion.config)
  }

  const getSourceIcon = (source) => {
    switch (source) {
      case 'history_column': return '📂'
      case 'history_type': return '📊'
      case 'pattern_match': return '🔍'
      case 'ai_inference': return '🤖'
      default: return '💡'
    }
  }

  const getSourceColor = (source) => {
    switch (source) {
      case 'history_column': return '#7c3aed'
      case 'history_type': return '#2563eb'
      case 'pattern_match': return '#059669'
      case 'ai_inference': return '#d97706'
      default: return '#6b7280'
    }
  }

  return (
    <div>
      {summary.totalOperations > 0 && (
        <div style={{
          padding: '10px 12px',
          background: 'linear-gradient(135deg, #f0f9ff 0%, #ede9fe 100%)',
          borderRadius: '8px',
          marginBottom: '12px',
          fontSize: '12px',
          color: '#4b5563'
        }}>
          <div style={{ fontWeight: 600, marginBottom: '4px', color: '#1e40af' }}>
            🧠 学习模型状态
          </div>
          <div>已学习 {summary.totalOperations} 次操作 · {summary.learnedColumnPatterns} 个列模式 · {summary.learnedTypePatterns} 种类型模式</div>
        </div>
      )}

      {!columnName ? (
        <div className="empty-state">
          <div style={{ fontSize: '28px', marginBottom: '8px' }}>🤖</div>
          <div>选择列后获取AI建议</div>
        </div>
      ) : suggestions.length === 0 ? (
        <div style={{
          padding: '16px',
          textAlign: 'center',
          color: '#9ca3af',
          fontSize: '13px'
        }}>
          <div style={{ fontSize: '28px', marginBottom: '8px' }}>🤖</div>
          <div>暂无学习数据</div>
          <div style={{ marginTop: '4px', fontSize: '12px' }}>
            执行更多填充操作后，AI将学习您的模式并提供建议
          </div>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {suggestions.map((suggestion, idx) => (
            <div
              key={idx}
              style={{
                border: `1px solid ${idx === expandedIdx ? getSourceColor(suggestion.source) : '#e5e7eb'}`,
                borderRadius: '8px',
                overflow: 'hidden',
                transition: 'all 0.15s'
              }}
            >
              <div
                style={{
                  padding: '10px 12px',
                  cursor: 'pointer',
                  background: idx === expandedIdx ? '#faf5ff' : 'white'
                }}
                onClick={() => setExpandedIdx(idx === expandedIdx ? -1 : idx)}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span>{getSourceIcon(suggestion.source)}</span>
                    <span style={{ fontWeight: 500, fontSize: '14px', color: '#374151' }}>
                      {suggestion.ruleName}
                    </span>
                    <span style={{
                      fontSize: '11px',
                      padding: '1px 6px',
                      borderRadius: '4px',
                      background: getSourceColor(suggestion.source) + '20',
                      color: getSourceColor(suggestion.source),
                      fontWeight: 500
                    }}>
                      {suggestion.sourceLabel}
                    </span>
                  </div>
                  <span style={{
                    fontSize: '12px',
                    fontWeight: 600,
                    color: suggestion.confidence >= 0.7 ? '#059669' : '#d97706'
                  }}>
                    {Math.round(suggestion.confidence * 100)}%
                  </span>
                </div>
                <div style={{
                  marginTop: '4px',
                  fontSize: '12px',
                  color: '#6b7280',
                  fontStyle: 'italic'
                }}>
                  {suggestion.reason}
                </div>
              </div>

              {idx === expandedIdx && (
                <div style={{
                  padding: '10px 12px',
                  borderTop: '1px solid #e5e7eb',
                  background: '#faf5ff'
                }}>
                  <div style={{ fontSize: '12px', color: '#6b7280', marginBottom: '8px' }}>
                    配置预览: {JSON.stringify(suggestion.config, null, 2).slice(0, 100)}
                  </div>
                  <button
                    className="btn btn-success"
                    style={{ width: '100%', justifyContent: 'center', padding: '6px 12px', fontSize: '13px' }}
                    onClick={(e) => {
                      e.stopPropagation()
                      handleApply(suggestion)
                    }}
                  >
                    使用此建议
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default AISuggestPanel
