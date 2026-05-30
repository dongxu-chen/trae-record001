import React, { useState } from 'react';

function FixPanel({ openApiSpec, endpoints }) {
  const [path, setPath] = useState('');
  const [method, setMethod] = useState('GET');
  const [statusCode, setStatusCode] = useState('200');
  const [responseBody, setResponseBody] = useState('');
  const [autoFix, setAutoFix] = useState(false);
  const [fixResult, setFixResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [showFixed, setShowFixed] = useState(false);

  const handleEndpointSelect = (endpoint) => {
    setPath(endpoint.path);
    setMethod(endpoint.method);
  };

  const handleSuggest = async () => {
    if (!openApiSpec) {
      alert('请先输入并解析OpenAPI规范');
      return;
    }
    if (!path || !responseBody.trim()) {
      alert('请填写路径和响应体');
      return;
    }

    setLoading(true);
    setFixResult(null);
    setShowFixed(false);

    try {
      const response = await fetch('/api/fix/suggest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          openApiSpec,
          path,
          method,
          statusCode: parseInt(statusCode),
          responseBody,
          autoFix
        })
      });

      const data = await response.json();
      setFixResult(data);
    } catch (error) {
      alert('修复建议生成失败: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  const getFixTypeLabel = (type) => {
    const labels = {
      'ADD_MISSING_FIELD': '添加缺失字段',
      'FIX_TYPE_MISMATCH': '修复类型不匹配',
      'FIX_FORMAT': '修复格式错误',
      'FIX_VALUE_RANGE': '修复值范围',
      'REMOVE_EXTRA_FIELD': '移除多余字段',
      'FIX_STRUCTURE': '修复结构',
      'FIX_ENUM_VALUE': '修复枚举值'
    };
    return labels[type] || type;
  };

  const getSeverityBadgeClass = (severity) => {
    const classes = {
      'CRITICAL': 'severity-badge-critical',
      'HIGH': 'severity-badge-high',
      'MEDIUM': 'severity-badge-medium',
      'LOW': 'severity-badge-low'
    };
    return classes[severity] || 'severity-badge-medium';
  };

  const getSeverityLabel = (severity) => {
    const labels = { 'CRITICAL': '严重', 'HIGH': '高', 'MEDIUM': '中', 'LOW': '低' };
    return labels[severity] || '中';
  };

  return (
    <div>
      <h3 style={{ marginTop: 0 }}>自动修复建议</h3>

      {endpoints.length > 0 && (
        <div className="form-group">
          <label>选择端点 (可选)</label>
          <select
            onChange={(e) => {
              if (e.target.value) {
                const ep = JSON.parse(e.target.value);
                handleEndpointSelect(ep);
              }
            }}
            value=""
          >
            <option value="">-- 选择端点 --</option>
            {endpoints.map((ep, idx) => (
              <option key={idx} value={JSON.stringify(ep)}>
                {ep.method} {ep.path}
              </option>
            ))}
          </select>
        </div>
      )}

      <div className="form-row">
        <div className="form-group">
          <label>API路径</label>
          <input
            type="text"
            placeholder="/api/users/{id}"
            value={path}
            onChange={(e) => setPath(e.target.value)}
          />
        </div>
        <div className="form-group">
          <label>HTTP方法</label>
          <select value={method} onChange={(e) => setMethod(e.target.value)}>
            <option value="GET">GET</option>
            <option value="POST">POST</option>
            <option value="PUT">PUT</option>
            <option value="DELETE">DELETE</option>
            <option value="PATCH">PATCH</option>
          </select>
        </div>
        <div className="form-group">
          <label>状态码</label>
          <input
            type="number"
            value={statusCode}
            onChange={(e) => setStatusCode(e.target.value)}
          />
        </div>
      </div>

      <div className="form-group">
        <label>API响应体 (JSON)</label>
        <textarea
          style={{ height: '200px', fontFamily: 'Consolas, monospace', fontSize: '12px' }}
          placeholder='{"id": 1, "name": "test", ...}'
          value={responseBody}
          onChange={(e) => setResponseBody(e.target.value)}
        />
      </div>

      <div className="form-group">
        <label>
          <input
            type="checkbox"
            checked={autoFix}
            onChange={(e) => setAutoFix(e.target.checked)}
            style={{ marginRight: '8px' }}
          />
          自动修复 (生成修复后的响应体)
        </label>
      </div>

      <button
        className="btn btn-primary"
        onClick={handleSuggest}
        disabled={loading}
      >
        {loading ? '分析中...' : '生成修复建议'}
      </button>

      {fixResult && (
        <div style={{ marginTop: '20px' }}>
          {fixResult.valid ? (
            <div className="validation-result valid">
              <h4><span className="status-icon">✓</span> 响应校验通过，无需修复</h4>
            </div>
          ) : (
            <>
              <div className="validation-result invalid" style={{ marginBottom: '15px' }}>
                <h4>
                  <span className="status-icon">✗</span> 校验失败
                  {fixResult.errors && (
                    <span style={{ marginLeft: '10px', fontSize: '14px', fontWeight: 'normal' }}>
                      (共 {fixResult.errors.length} 个错误)
                    </span>
                  )}
                </h4>
              </div>

              {fixResult.suggestions && fixResult.suggestions.length > 0 && (
                <div>
                  <h5 style={{ marginBottom: '10px' }}>💡 修复建议</h5>
                  {fixResult.suggestions.map((suggestion, idx) => (
                    <div key={idx} className={`fix-suggestion-item severity-${(suggestion.severity || 'MEDIUM').toLowerCase()}`}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                        <span className="error-field">{suggestion.field || 'root'}</span>
                        <span className={`severity-badge ${getSeverityBadgeClass(suggestion.severity)}`}>
                          {getSeverityLabel(suggestion.severity)}
                        </span>
                        <span className="fix-type-badge">
                          {getFixTypeLabel(suggestion.fixType)}
                        </span>
                      </div>
                      <div style={{ color: '#555', fontSize: '13px', marginBottom: '8px' }}>
                        {suggestion.description}
                      </div>
                      {suggestion.suggestedFix && (
                        <div style={{ marginBottom: '8px' }}>
                          <span style={{ fontWeight: 600, fontSize: '12px', color: '#166534' }}>建议值: </span>
                          <code style={{ background: '#f0fdf4', padding: '2px 8px', borderRadius: '4px', fontSize: '12px' }}>
                            {suggestion.suggestedFix}
                          </code>
                        </div>
                      )}
                      {suggestion.codeSnippet && (
                        <div style={{ marginBottom: '8px' }}>
                          <div style={{ fontWeight: 600, fontSize: '12px', color: '#666', marginBottom: '4px' }}>代码示例:</div>
                          <pre style={{ background: '#1e1e1e', color: '#d4d4d4', padding: '8px', borderRadius: '4px', fontSize: '11px', margin: 0, overflow: 'auto' }}>
                            {suggestion.codeSnippet}
                          </pre>
                        </div>
                      )}
                      {suggestion.alternatives && suggestion.alternatives.length > 0 && (
                        <div style={{ fontSize: '12px', color: '#888' }}>
                          <span style={{ fontWeight: 600 }}>其他方案: </span>
                          {suggestion.alternatives.map((alt, i) => (
                            <span key={i}>
                              {i > 0 && ' | '}
                              {alt}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {fixResult.fixedResponse && (
                <div style={{ marginTop: '15px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                    <h5 style={{ margin: 0 }}>🔧 修复后的响应体</h5>
                    <button
                      className="btn btn-secondary"
                      onClick={() => setShowFixed(!showFixed)}
                      style={{ padding: '4px 12px', fontSize: '12px' }}
                    >
                      {showFixed ? '隐藏' : '查看'}
                    </button>
                  </div>
                  {showFixed && (
                    <div className="json-preview" style={{ maxHeight: '400px' }}>
                      {fixResult.fixedResponse}
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}

export default FixPanel;
