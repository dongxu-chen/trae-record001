import React, { useState } from 'react';

function ValidationPanel({ openApiSpec, endpoints }) {
  const [path, setPath] = useState('');
  const [method, setMethod] = useState('GET');
  const [statusCode, setStatusCode] = useState('200');
  const [responseBody, setResponseBody] = useState('');
  const [validationResult, setValidationResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [useStreaming, setUseStreaming] = useState(true);

  const handleEndpointSelect = (endpoint) => {
    setPath(endpoint.path);
    setMethod(endpoint.method);
  };

  const handleValidate = async () => {
    if (!openApiSpec) {
      alert('请先输入并解析OpenAPI规范');
      return;
    }
    if (!path || !responseBody.trim()) {
      alert('请填写路径和响应体');
      return;
    }

    setLoading(true);
    setValidationResult(null);

    try {
      const endpoint = useStreaming ? '/api/validate/streaming' : '/api/validate';
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          openApiSpec,
          path,
          method,
          statusCode: parseInt(statusCode),
          responseBody
        })
      });

      const data = await response.json();
      setValidationResult(data);
    } catch (error) {
      alert('校验失败: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadJUnit = async () => {
    if (!validationResult) return;

    try {
      const response = await fetch('/api/validate/junit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          openApiSpec,
          path,
          method,
          statusCode: parseInt(statusCode),
          responseBody
        })
      });

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `validation-junit-report-${Date.now()}.xml`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      alert('下载失败: ' + error.message);
    }
  };

  const getErrorTypeClass = (type) => {
    const typeMap = {
      'REQUIRED_FIELD_MISSING': 'required',
      'TYPE_MISMATCH': 'type',
      'FORMAT_INVALID': 'format',
      'STRUCTURE_INVALID': 'structure',
      'UNKNOWN_FIELD': 'structure',
      'SCHEMA_ERROR': 'default'
    };
    return typeMap[type] || 'default';
  };

  const getSeverityClass = (severity) => {
    const severityMap = {
      'CRITICAL': 'severity-critical',
      'HIGH': 'severity-high',
      'MEDIUM': 'severity-medium',
      'LOW': 'severity-low'
    };
    return severityMap[severity] || 'severity-medium';
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

  const getSeverityBadgeClass = (severity) => {
    const classes = {
      'CRITICAL': 'severity-badge-critical',
      'HIGH': 'severity-badge-high',
      'MEDIUM': 'severity-badge-medium',
      'LOW': 'severity-badge-low'
    };
    return classes[severity] || 'severity-badge-medium';
  };

  return (
    <div>
      <h3 style={{ marginTop: 0 }}>响应校验</h3>

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
        <label>
          <input
            type="checkbox"
            checked={useStreaming}
            onChange={(e) => setUseStreaming(e.target.checked)}
            style={{ marginRight: '8px' }}
          />
          启用流式校验 (降低内存占用)
        </label>
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

      <div className="btn-group">
        <button 
          className="btn btn-primary"
          onClick={handleValidate}
          disabled={loading}
        >
          {loading ? '校验中...' : '开始校验'}
        </button>
        {validationResult && (
          <button 
            className="btn btn-secondary"
            onClick={handleDownloadJUnit}
          >
            下载JUnit报告
          </button>
        )}
      </div>

      {validationResult && (
        <div className={`validation-result ${validationResult.valid ? 'valid' : 'invalid'}`}>
          <h4>
            <span className="status-icon">{validationResult.valid ? '✓' : '✗'}</span>
            校验结果: {validationResult.valid ? '通过' : '失败'}
            {!validationResult.valid && validationResult.errors && (
              <span style={{ marginLeft: '10px', fontSize: '14px', fontWeight: 'normal' }}>
                (共 {validationResult.errors.length} 个错误)
              </span>
            )}
          </h4>
          
          {!validationResult.valid && validationResult.errors && (
            <ul className="error-list">
              {validationResult.errors.map((err, idx) => (
                <li key={idx} className={`error-item ${getSeverityClass(err.severity)}`}>
                  <div>
                    <span className="error-field">{err.field || 'root'}</span>
                    <span className={`error-type error-type-${getErrorTypeClass(err.type)}`}>
                      {err.type}
                    </span>
                    <span className={`severity-badge ${getSeverityBadgeClass(err.severity)}`}>
                      {getSeverityLabel(err.severity)}
                    </span>
                  </div>
                  <div style={{ marginTop: '4px', color: '#555' }}>
                    {err.message}
                  </div>
                </li>
              ))}
            </ul>
          )}

          {validationResult.valid && (
            <p style={{ margin: 0, color: '#166534' }}>
              响应结构完全符合OpenAPI规范定义
            </p>
          )}
        </div>
      )}
    </div>
  );
}

export default ValidationPanel;
