import { useState, useMemo } from 'react'
import ExampleParser from '../utils/exampleParser'
import RuleEngine from '../utils/ruleEngine'

function ExampleInput({ onExampleRule }) {
  const [inputValue, setInputValue] = useState('')
  const [parsedResults, setParsedResults] = useState([])
  const [selectedIdx, setSelectedIdx] = useState(-1)

  const exampleParser = useMemo(() => new ExampleParser(), [])
  const ruleEngine = useMemo(() => new RuleEngine(), [])

  const handleInputChange = (value) => {
    setInputValue(value)

    if (!value.trim()) {
      setParsedResults([])
      setSelectedIdx(-1)
      return
    }

    const results = exampleParser.parseExample(value)
    setParsedResults(results)
    setSelectedIdx(results.length > 0 ? 0 : -1)
  }

  const handleSelectResult = (idx) => {
    setSelectedIdx(idx)
  }

  const handleApply = () => {
    if (selectedIdx < 0 || !parsedResults[selectedIdx]) return

    const result = parsedResults[selectedIdx]
    const rule = ruleEngine.getRuleById(result.ruleId)

    if (!rule) return

    let finalConfig = { ...result.config }

    if (result.config._customApply) {
      const customApply = result.config._customApply
      finalConfig._customApply = customApply
    }

    const enhancedRule = { ...rule }
    if (result.description) {
      enhancedRule.example = result.description
    }

    onExampleRule(enhancedRule, finalConfig)
  }

  const hints = exampleParser.getExampleHints()

  return (
    <div>
      <div style={{ fontSize: '13px', color: '#6b7280', marginBottom: '12px' }}>
        输入几个示例值，系统自动识别模式并生成填充规则
      </div>

      <div className="form-group">
        <label>输入示例（用逗号或空格分隔）</label>
        <textarea
          value={inputValue}
          onChange={(e) => handleInputChange(e.target.value)}
          placeholder="例如: 1, 2, 3, 4&#10;或: 技术部, 产品部, 市场部&#10;或: 2024-01-01, 2024-01-02, 2024-01-03&#10;或: SKU001, SKU002, SKU003"
          style={{
            width: '100%',
            minHeight: '80px',
            padding: '8px 12px',
            fontSize: '14px',
            fontFamily: 'monospace',
            border: '2px solid #e5e7eb',
            borderRadius: '8px',
            transition: 'border-color 0.2s'
          }}
        />
      </div>

      {parsedResults.length > 0 && (
        <div style={{ marginTop: '12px' }}>
          <div style={{ fontSize: '13px', fontWeight: '500', color: '#374151', marginBottom: '8px' }}>
            识别到 {parsedResults.length} 种模式：
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {parsedResults.map((result, idx) => (
              <div
                key={idx}
                onClick={() => handleSelectResult(idx)}
                style={{
                  padding: '10px 12px',
                  border: `2px solid ${idx === selectedIdx ? '#667eea' : '#e5e7eb'}`,
                  borderRadius: '8px',
                  cursor: 'pointer',
                  background: idx === selectedIdx ? '#ede9fe' : 'white',
                  transition: 'all 0.15s'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{
                      width: '20px',
                      height: '20px',
                      borderRadius: '50%',
                      background: idx === selectedIdx ? '#667eea' : '#d1d5db',
                      color: 'white',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: '11px',
                      fontWeight: 600
                    }}>
                      {idx + 1}
                    </span>
                    <span style={{ fontWeight: 600, fontSize: '14px', color: '#374151' }}>
                      {result.patternName}
                    </span>
                  </div>
                  <span style={{
                    fontSize: '12px',
                    fontWeight: 600,
                    color: result.confidence >= 0.7 ? '#059669' : '#d97706'
                  }}>
                    {Math.round(result.confidence * 100)}% 匹配
                  </span>
                </div>
                <div style={{
                  marginTop: '6px',
                  padding: '6px 10px',
                  background: idx === selectedIdx ? '#f5f3ff' : '#f8fafc',
                  borderRadius: '6px',
                  fontSize: '13px',
                  color: '#4b5563',
                  fontStyle: 'italic'
                }}>
                  {result.description}
                </div>
              </div>
            ))}
          </div>

          <button
            className="btn btn-success"
            style={{ width: '100%', marginTop: '16px', justifyContent: 'center' }}
            onClick={handleApply}
          >
            使用此规则
          </button>
        </div>
      )}

      {inputValue.trim() && parsedResults.length === 0 && (
        <div style={{
          marginTop: '12px',
          padding: '12px',
          background: '#fef3c7',
          borderRadius: '8px',
          fontSize: '13px',
          color: '#92400e'
        }}>
          未识别到模式，请尝试输入更多示例值
        </div>
      )}

      <div style={{ marginTop: '16px', padding: '12px', background: '#f0f9ff', borderRadius: '8px' }}>
        <div style={{ fontSize: '13px', fontWeight: '500', color: '#0369a1', marginBottom: '8px' }}>
          💬 支持的示例格式
        </div>
        {hints.map((hint, idx) => (
          <div key={idx} style={{ marginBottom: '6px' }}>
            <div style={{ fontSize: '12px', fontWeight: 600, color: '#0c4a6e' }}>
              {hint.name}
            </div>
            <div style={{ fontSize: '11px', color: '#6b7280', fontFamily: 'monospace' }}>
              {hint.examples.join(' | ')}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default ExampleInput
