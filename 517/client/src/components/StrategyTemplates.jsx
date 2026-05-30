import { useState } from 'react';

const StrategyTemplates = ({ templates, currentTemplate, onApplyTemplate }) => {
  const [showDetail, setShowDetail] = useState(null);

  const getMethodLabel = (method) => {
    const labels = {
      mask: '掩码',
      hash: '哈希',
      truncate: '截断',
      replace: '替换',
      shuffle: '打乱'
    };
    return labels[method] || method;
  };

  return (
    <div className="strategy-templates">
      <div className="templates-header">
        <h3>📋 脱敏策略模板</h3>
        <span className="templates-count">共 {templates.length} 个模板</span>
      </div>
      
      <div className="templates-grid">
        {templates.map(template => (
          <div 
            key={template.id} 
            className={`template-card ${currentTemplate === template.id ? 'active' : ''}`}
            style={{ '--template-color': template.color }}
          >
            <div className="template-icon" style={{ background: template.color + '20' }}>
              <span style={{ fontSize: '1.5rem' }}>{template.icon}</span>
            </div>
            <div className="template-info">
              <h4 className="template-name">{template.name}</h4>
              <p className="template-desc">{template.description}</p>
            </div>
            <div className="template-actions">
              <button 
                className="btn btn-small btn-outline"
                onClick={() => setShowDetail(showDetail === template.id ? null : template.id)}
              >
                {showDetail === template.id ? '收起' : '详情'}
              </button>
              <button 
                className="btn btn-small btn-primary"
                onClick={() => onApplyTemplate(template)}
              >
                应用
              </button>
            </div>
            
            {showDetail === template.id && (
              <div className="template-detail">
                <div className="detail-title">包含规则：</div>
                <div className="detail-rules">
                  {Object.entries(template.rules).map(([field, rule]) => (
                    <div key={field} className={`detail-rule-item ${rule.enabled ? 'enabled' : ''}`}>
                      <span className="rule-field">{rule.label}</span>
                      <span className="rule-status">
                        {rule.enabled ? (
                          <span className={`method-badge ${rule.method}`}>
                            {getMethodLabel(rule.method)}
                          </span>
                        ) : (
                          <span className="rule-disabled">未启用</span>
                        )}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default StrategyTemplates;
