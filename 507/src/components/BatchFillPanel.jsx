import { useState, useMemo } from 'react'
import DataAnalyzer from '../utils/dataAnalyzer'
import RuleEngine from '../utils/ruleEngine'

function BatchFillPanel({ data, onBatchApply }) {
  const [selectedColumns, setSelectedColumns] = useState([])
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [autoRules, setAutoRules] = useState([])

  const dataAnalyzer = useMemo(() => new DataAnalyzer(), [])
  const ruleEngine = useMemo(() => new RuleEngine(), [])

  const headers = data[0] || []

  const analyzeAll = () => {
    setIsAnalyzing(true)
    const rules = []

    headers.forEach((header, colIndex) => {
      if (colIndex === 0) return
      
      const columnData = data.slice(1).map(row => row[colIndex])
      const analysis = dataAnalyzer.analyzeColumn(columnData, header)
      const recommended = ruleEngine.recommendRules(analysis)
      
      if (recommended.length > 0 && recommended[0].isRecommended) {
        rules.push({
          colIndex,
          columnName: header,
          rule: recommended[0],
          config: recommended[0].defaultConfig || {},
          enabled: true
        })
      }
    })

    setAutoRules(rules)
    setIsAnalyzing(false)
  }

  const toggleRule = (index) => {
    const newRules = [...autoRules]
    newRules[index].enabled = !newRules[index].enabled
    setAutoRules(newRules)
  }

  const handleApply = () => {
    const rulesToApply = autoRules
      .filter(r => r.enabled)
      .map(r => ({
        colIndex: r.colIndex,
        rule: r.rule,
        config: r.config
      }))
    
    onBatchApply(rulesToApply)
    setAutoRules([])
  }

  return (
    <div>
      <button
        className="btn btn-primary"
        style={{ width: '100%', marginBottom: '16px', justifyContent: 'center' }}
        onClick={analyzeAll}
        disabled={isAnalyzing}
      >
        {isAnalyzing ? '分析中...' : '🔍 智能分析所有列'}
      </button>

      {autoRules.length > 0 && (
        <>
          <div style={{ fontSize: '13px', color: '#6b7280', marginBottom: '12px' }}>
            检测到 {autoRules.length} 列可自动填充：
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {autoRules.map((item, index) => (
              <div
                key={index}
                style={{
                  padding: '10px 12px',
                  border: '1px solid #e5e7eb',
                  borderRadius: '6px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '10px',
                  background: item.enabled ? '#f0fdf4' : 'white'
                }}
              >
                <input
                  type="checkbox"
                  checked={item.enabled}
                  onChange={() => toggleRule(index)}
                />
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: '14px', fontWeight: '500', color: '#374151' }}>
                    {item.columnName}
                  </div>
                  <div style={{ fontSize: '12px', color: '#6b7280' }}>
                    {item.rule.name}
                  </div>
                </div>
                <span className="tag tag-success">自动</span>
              </div>
            ))}
          </div>
          <button
            className="btn btn-success"
            style={{ width: '100%', marginTop: '16px', justifyContent: 'center' }}
            onClick={handleApply}
          >
            批量应用填充
          </button>
        </>
      )}

      {autoRules.length === 0 && !isAnalyzing && (
        <div className="empty-state">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
            <line x1="3" y1="9" x2="21" y2="9"></line>
            <line x1="9" y1="21" x2="9" y2="9"></line>
          </svg>
          <div>点击上方按钮智能分析可填充列</div>
        </div>
      )}
    </div>
  )
}

export default BatchFillPanel
