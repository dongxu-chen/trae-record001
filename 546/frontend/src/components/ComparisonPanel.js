import React, { useState } from 'react';

function ComparisonPanel({ openApiSpec, endpoints }) {
  const [path, setPath] = useState('');
  const [method, setMethod] = useState('GET');
  const [statusCode, setStatusCode] = useState('200');
  const [env1Name, setEnv1Name] = useState('dev');
  const [env2Name, setEnv2Name] = useState('prod');
  const [env1ResponseBody, setEnv1ResponseBody] = useState('');
  const [env2ResponseBody, setEnv2ResponseBody] = useState('');
  const [comparisonResult, setComparisonResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleEndpointSelect = (endpoint) => {
    setPath(endpoint.path);
    setMethod(endpoint.method);
  };

  const handleCompare = async () => {
    if (!env1ResponseBody.trim() || !env2ResponseBody.trim()) {
      alert('请填写两个环境的响应体');
      return;
    }

    setLoading(true);
    setComparisonResult(null);

    try {
      const response = await fetch('/api/compare', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          openApiSpec,
          path,
          method,
          statusCode: parseInt(statusCode),
          env1Name,
          env2Name,
          env1ResponseBody,
          env2ResponseBody
        })
      });

      const data = await response.json();
      setComparisonResult(data);
    } catch (error) {
      alert('对比失败: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadJUnit = async () => {
    if (!comparisonResult) return;

    try {
      const response = await fetch('/api/compare/junit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          openApiSpec,
          path,
          method,
          statusCode: parseInt(statusCode),
          env1Name,
          env2Name,
          env1ResponseBody,
          env2ResponseBody
        })
      });

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `comparison-junit-report-${Date.now()}.xml`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      alert('下载失败: ' + error.message);
    }
  };

  const getDiffTypeClass = (type) => {
    const typeMap = {
      'FIELD_ADDED': 'added',
      'FIELD_REMOVED': 'removed',
      'VALUE_CHANGED': 'changed',
      'TYPE_CHANGED': 'type',
      'ARRAY_LENGTH_CHANGED': 'array',
      'STRUCTURE_MISMATCH': 'structure'
    };
    return typeMap[type] || 'structure';
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
    const labels = {
      'CRITICAL': '严重',
      'HIGH': '高',
      'MEDIUM': '中',
      'LOW': '低'
    };
    return labels[severity] || '中';
  };

  const getSeverityHighlightClass = (severity) => {
    const classes = {
      'CRITICAL': 'diff-critical',
      'HIGH': 'diff-high',
      'MEDIUM': 'diff-medium',
      'LOW': 'diff-low'
    };
    return classes[severity] || 'diff-medium';
  };

  const formatValue = (value) => {
    if (value === null || value === undefined) {
      return '<null>';
    }
    if (typeof value === 'object') {
      return JSON.stringify(value, null, 2);
    }
    return String(value);
  };

  return (
    <div>
      <h3 style={{ marginTop: 0 }}>多环境对比</h3>

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
            placeholder="/api/users"
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

      <div className="form-row">
        <div className="form-group">
          <label>环境1名称</label>
          <input
            type="text"
            value={env1Name}
            onChange={(e) => setEnv1Name(e.target.value)}
          />
        </div>
        <div className="form-group">
          <label>环境2名称</label>
          <input
            type="text"
            value={env2Name}
            onChange={(e) => setEnv2Name(e.target.value)}
          />
        </div>
      </div>

      <div className="comparison-container">
        <div className="form-group">
          <label>{env1Name} 环境响应体</label>
          <textarea
            style={{ height: '200px', fontFamily: 'Consolas, monospace', fontSize: '12px' }}
            placeholder='{"id": 1, ...}'
            value={env1ResponseBody}
            onChange={(e) => setEnv1ResponseBody(e.target.value)}
          />
        </div>
        <div className="form-group">
          <label>{env2Name} 环境响应体</label>
          <textarea
            style={{ height: '200px', fontFamily: 'Consolas, monospace', fontSize: '12px' }}
            placeholder='{"id": 1, ...}'
            value={env2ResponseBody}
            onChange={(e) => setEnv2ResponseBody(e.target.value)}
          />
        </div>
      </div>

      <div className="btn-group">
        <button 
          className="btn btn-primary"
          onClick={handleCompare}
          disabled={loading}
        >
          {loading ? '对比中...' : '开始对比'}
        </button>
        {comparisonResult && (
          <button 
            className="btn btn-secondary"
            onClick={handleDownloadJUnit}
          >
            下载JUnit报告
          </button>
        )}
      </div>

      {comparisonResult && (
        <div className="comparison-result">
          <h4>
            {comparisonResult.hasDifferences ? (
              <span style={{ color: '#dc2626' }}>
                发现 {comparisonResult.differences.length} 处差异
                {comparisonResult.differences && comparisonResult.differences.some(d => d.severity === 'CRITICAL') && (
                  <span className="severity-badge severity-badge-critical" style={{ marginLeft: '10px' }}>
                    包含严重问题
                  </span>
                )}
              </span>
            ) : (
              <span style={{ color: '#166534' }}>两个环境响应完全一致 ✓</span>
            )}
          </h4>

          {comparisonResult.differences && comparisonResult.differences.map((diff, idx) => (
            <div key={idx} className={`difference-item ${getSeverityHighlightClass(diff.severity)}`}>
              <div className="difference-field">
                {diff.field}
                <span className={`difference-type diff-type-${getDiffTypeClass(diff.type)}`}>
                  {diff.type}
                </span>
                <span className={`severity-badge ${getSeverityBadgeClass(diff.severity)}`}>
                  {getSeverityLabel(diff.severity)}
                </span>
              </div>
              <div style={{ fontSize: '12px', color: '#666', marginBottom: '8px' }}>
                {diff.description}
              </div>
              {diff.type !== 'STRUCTURE_MISMATCH' && (
                <div className="difference-values">
                  <div>
                    <div className="env-label">{env1Name}</div>
                    <div className="env-value">{formatValue(diff.env1Value)}</div>
                  </div>
                  <div>
                    <div className="env-label">{env2Name}</div>
                    <div className="env-value">{formatValue(diff.env2Value)}</div>
                  </div>
                </div>
              )}
            </div>
          ))}

          {comparisonResult.env1Validation && comparisonResult.env2Validation && (
            <div style={{ marginTop: '20px', borderTop: '1px solid #eee', paddingTop: '20px' }}>
              <h5>规范校验结果</h5>
              <div className="comparison-container">
                <div className={`validation-result ${comparisonResult.env1Validation.valid ? 'valid' : 'invalid'}`} style={{ margin: 0 }}>
                  <strong>{env1Name}: </strong>
                  {comparisonResult.env1Validation.valid ? '通过 ✓' : `失败 (${comparisonResult.env1Validation.errors.length} 个错误)`}
                </div>
                <div className={`validation-result ${comparisonResult.env2Validation.valid ? 'valid' : 'invalid'}`} style={{ margin: 0 }}>
                  <strong>{env2Name}: </strong>
                  {comparisonResult.env2Validation.valid ? '通过 ✓' : `失败 (${comparisonResult.env2Validation.errors.length} 个错误)`}
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default ComparisonPanel;
