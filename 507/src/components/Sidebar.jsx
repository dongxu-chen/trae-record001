import { useState } from 'react'
import RuleConfigPanel from './RuleConfigPanel'
import BatchFillPanel from './BatchFillPanel'
import ExampleInput from './ExampleInput'
import AISuggestPanel from './AISuggestPanel'
import CrossTablePanel from './CrossTablePanel'
import AuditLogPanel from './AuditLogPanel'

function Sidebar({
  selectedColumn,
  columnName,
  columnAnalysis,
  recommendedRules,
  selectedRule,
  ruleConfig,
  showPreview,
  onRuleSelect,
  onConfigChange,
  onTogglePreview,
  onApplyFill,
  onBatchApply,
  onExampleRule,
  onRevert,
  data
}) {
  const [activeTab, setActiveTab] = useState('rules')

  const getTypeLabel = (type) => {
    const labels = {
      number: '数字', string: '文本', date: '日期', boolean: '布尔值', unknown: '未知',
      email: '邮箱', phone_cn: '手机号', url: 'URL', id_card_cn: '身份证号',
      postal_code_cn: '邮编', ip_address: 'IP地址', currency_cny: '人民币金额',
      percentage: '百分比', date_iso: '日期(ISO)', date_slash: '日期(斜杠)',
      date_cn: '日期(中文)', time_hms: '时间', sku_code: 'SKU编码',
      boolean_cn: '布尔值(中文)', boolean_en: '布尔值(英文)'
    }
    return labels[type] || type
  }

  const getConfidenceColor = (conf) => {
    if (conf >= 0.8) return '#059669'
    if (conf >= 0.5) return '#d97706'
    return '#9ca3af'
  }

  const tabs = [
    { key: 'rules', label: '规则' },
    { key: 'example', label: '示例' },
    { key: 'ai', label: '🤖' },
    { key: 'cross', label: '🔗' },
    { key: 'batch', label: '批量' },
    { key: 'audit', label: '📝' }
  ]

  return (
    <aside className="sidebar">
      <div className="panel">
        <div className="panel-header">📋 列信息 & 类型识别</div>
        {selectedColumn !== null && columnAnalysis ? (
          <>
            <div className="column-info">
              <div className="column-name">列 {String.fromCharCode(65 + selectedColumn)}: {columnName}</div>
              <div className="stats" style={{ marginTop: '8px' }}>
                <div>数据总行数: {columnAnalysis.stats?.totalCount || 0}</div>
                <div>已填充: {columnAnalysis.stats?.nonEmptyCount || 0}</div>
                <div>空值: {columnAnalysis.stats?.emptyCount || 0}</div>
                {columnAnalysis.stats?.uniqueCount !== undefined && (
                  <div>唯一值: {columnAnalysis.stats.uniqueCount}</div>
                )}
                {columnAnalysis.stats?.avg !== undefined && (
                  <div>平均值: {columnAnalysis.stats.avg.toFixed(2)}</div>
                )}
              </div>
            </div>

            {columnAnalysis.typeCandidates && columnAnalysis.typeCandidates.length > 0 && (
              <div style={{ marginTop: '12px' }}>
                <div style={{ fontSize: '13px', fontWeight: '500', color: '#374151', marginBottom: '8px' }}>
                  类型候选（按置信度排序）
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  {columnAnalysis.typeCandidates.map((candidate, idx) => (
                    <div
                      key={candidate.type}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        padding: '4px 8px',
                        background: idx === 0 ? '#ede9fe' : '#f8fafc',
                        borderRadius: '4px',
                        fontSize: '13px'
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        {idx === 0 && <span style={{ fontSize: '11px' }}>✓</span>}
                        <span style={{ fontWeight: idx === 0 ? 600 : 400, color: '#374151' }}>
                          {candidate.label}
                        </span>
                        {candidate.source && (
                          <span style={{ fontSize: '10px', color: '#9ca3af' }}>
                            ({candidate.source === 'data+keyword' ? '数据+关键词' : candidate.source === 'keyword' ? '关键词' : '数据'})
                          </span>
                        )}
                      </div>
                      <span style={{
                        fontSize: '12px',
                        fontWeight: 600,
                        color: getConfidenceColor(candidate.confidence)
                      }}>
                        {Math.round(candidate.confidence * 100)}%
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        ) : (
          <div className="empty-state">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ width: '48px', height: '48px', marginBottom: '12px', opacity: 0.5 }}>
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
              <polyline points="14 2 14 8 20 8"></polyline>
            </svg>
            <div>请点击表格中的列查看分析</div>
          </div>
        )}
      </div>

      <div className="panel" style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        <div className="panel-header" style={{ flexShrink: 0 }}>
          <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
            {tabs.map(tab => (
              <button
                key={tab.key}
                className={`btn ${activeTab === tab.key ? 'btn-primary' : 'btn-default'}`}
                style={{ padding: '4px 8px', fontSize: '12px', minWidth: tab.label.length <= 2 ? '44px' : 'auto' }}
                onClick={() => setActiveTab(tab.key)}
                title={tab.key === 'ai' ? 'AI建议' : tab.key === 'cross' ? '跨表关联' : tab.key === 'audit' ? '审计日志' : ''}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        <div style={{ flex: 1, overflowY: 'auto' }}>
          {activeTab === 'rules' && (
            <>
              {recommendedRules.length > 0 ? (
                <div className="rules-list">
                  {recommendedRules.map((rule, index) => (
                    <div
                      key={`${rule.id}-${index}`}
                      className={`rule-item ${selectedRule?.id === rule.id ? 'selected' : ''} ${rule.isRecommended ? 'recommended' : ''}`}
                      onClick={() => onRuleSelect(rule)}
                    >
                      <div className="rule-name">
                        {rule.name}
                        {rule.isRecommended && <span className="tag tag-success" style={{ marginLeft: '8px' }}>推荐</span>}
                      </div>
                      <div className="rule-desc">{rule.example || rule.description}</div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="empty-state">
                  <div>选择列后显示推荐规则</div>
                </div>
              )}

              {selectedRule && (
                <RuleConfigPanel rule={selectedRule} config={ruleConfig} onConfigChange={onConfigChange} />
              )}

              {selectedRule && (
                <div className="action-buttons">
                  <button className="btn btn-warning" onClick={onTogglePreview}>
                    {showPreview ? '关闭预览' : '开启预览'}
                  </button>
                  <button className="btn btn-success" onClick={onApplyFill}>
                    应用填充
                  </button>
                </div>
              )}
            </>
          )}

          {activeTab === 'example' && (
            <ExampleInput onExampleRule={onExampleRule} />
          )}

          {activeTab === 'ai' && (
            <AISuggestPanel
              columnName={columnName}
              dataType={columnAnalysis?.dataType}
              columnAnalysis={columnAnalysis}
              onApplySuggestion={onExampleRule}
            />
          )}

          {activeTab === 'cross' && (
            <CrossTablePanel
              data={data}
              onApplySuggestion={onExampleRule}
            />
          )}

          {activeTab === 'batch' && (
            <BatchFillPanel data={data} onBatchApply={onBatchApply} />
          )}

          {activeTab === 'audit' && (
            <AuditLogPanel onRevert={onRevert} />
          )}
        </div>
      </div>

      <div className="panel">
        <div style={{ fontSize: '13px', color: '#6b7280', lineHeight: '1.6' }}>
          <div><strong>规则</strong> 推荐规则 · <strong>示例</strong> 自然语言</div>
          <div><strong>🤖</strong> AI建议 · <strong>🔗</strong> 跨表关联</div>
          <div><strong>批量</strong> 多列填充 · <strong>📝</strong> 审计日志</div>
        </div>
      </div>
    </aside>
  )
}

export default Sidebar
