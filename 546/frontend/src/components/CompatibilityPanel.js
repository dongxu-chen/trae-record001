import React, { useState } from 'react';

function CompatibilityPanel({ openApiSpec, endpoints }) {
  const [path, setPath] = useState('');
  const [method, setMethod] = useState('GET');
  const [statusCode, setStatusCode] = useState('200');
  const [oldVersion, setOldVersion] = useState('v1');
  const [newVersion, setNewVersion] = useState('v2');
  const [oldSpec, setOldSpec] = useState('');
  const [newSpec, setNewSpec] = useState('');
  const [compatResult, setCompatResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleEndpointSelect = (endpoint) => {
    setPath(endpoint.path);
    setMethod(endpoint.method);
  };

  const handleUseCurrentAsOld = () => {
    setOldSpec(openApiSpec);
  };

  const handleUseCurrentAsNew = () => {
    setNewSpec(openApiSpec);
  };

  const handleCheck = async () => {
    if (!oldSpec.trim() || !newSpec.trim()) {
      alert('请输入两个版本的OpenAPI规范');
      return;
    }
    if (!path) {
      alert('请填写API路径');
      return;
    }

    setLoading(true);
    setCompatResult(null);

    try {
      const response = await fetch('/api/compatibility/check', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          oldOpenApiSpec: oldSpec,
          newOpenApiSpec: newSpec,
          oldVersion,
          newVersion,
          path,
          method,
          statusCode: parseInt(statusCode)
        })
      });

      const data = await response.json();
      setCompatResult(data);
    } catch (error) {
      alert('兼容性检查失败: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  const getCompatLevelClass = (level) => {
    const map = {
      'FULLY_COMPATIBLE': 'compat-fully',
      'BACKWARD_COMPATIBLE': 'compat-backward',
      'PARTIALLY_COMPATIBLE': 'compat-partial',
      'BREAKING_CHANGE': 'compat-breaking'
    };
    return map[level] || 'compat-partial';
  };

  const getCompatLevelLabel = (level) => {
    const labels = {
      'FULLY_COMPATIBLE': '完全兼容',
      'BACKWARD_COMPATIBLE': '向后兼容',
      'PARTIALLY_COMPATIBLE': '部分兼容',
      'BREAKING_CHANGE': '破坏性变更'
    };
    return labels[level] || '未知';
  };

  const getSeverityLabel = (severity) => {
    const labels = { 'BREAKING': '破坏性', 'WARNING': '警告', 'INFO': '信息' };
    return labels[severity] || '未知';
  };

  const getSeverityBadgeClass = (severity) => {
    const classes = {
      'BREAKING': 'severity-badge-critical',
      'WARNING': 'severity-badge-high',
      'INFO': 'severity-badge-low'
    };
    return classes[severity] || 'severity-badge-medium';
  };

  return (
    <div>
      <h3 style={{ marginTop: 0 }}>版本兼容性检测</h3>

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
          <label>旧版本名称</label>
          <input
            type="text"
            value={oldVersion}
            onChange={(e) => setOldVersion(e.target.value)}
          />
        </div>
        <div className="form-group">
          <label>新版本名称</label>
          <input
            type="text"
            value={newVersion}
            onChange={(e) => setNewVersion(e.target.value)}
          />
        </div>
      </div>

      <div className="compat-specs-container">
        <div className="form-group">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <label style={{ marginBottom: 0 }}>{oldVersion} OpenAPI规范</label>
            <button
              className="btn btn-secondary"
              onClick={handleUseCurrentAsOld}
              style={{ padding: '2px 8px', fontSize: '11px' }}
            >
              使用当前规范
            </button>
          </div>
          <textarea
            style={{ height: '200px', fontFamily: 'Consolas, monospace', fontSize: '12px', marginTop: '8px' }}
            placeholder="粘贴旧版本OpenAPI规范..."
            value={oldSpec}
            onChange={(e) => setOldSpec(e.target.value)}
          />
        </div>
        <div className="form-group">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <label style={{ marginBottom: 0 }}>{newVersion} OpenAPI规范</label>
            <button
              className="btn btn-secondary"
              onClick={handleUseCurrentAsNew}
              style={{ padding: '2px 8px', fontSize: '11px' }}
            >
              使用当前规范
            </button>
          </div>
          <textarea
            style={{ height: '200px', fontFamily: 'Consolas, monospace', fontSize: '12px', marginTop: '8px' }}
            placeholder="粘贴新版本OpenAPI规范..."
            value={newSpec}
            onChange={(e) => setNewSpec(e.target.value)}
          />
        </div>
      </div>

      <button
        className="btn btn-primary"
        onClick={handleCheck}
        disabled={loading}
      >
        {loading ? '检测中...' : '检测兼容性'}
      </button>

      {compatResult && (
        <div className="compatibility-result" style={{ marginTop: '20px' }}>
          <div className={`compat-level-banner ${getCompatLevelClass(compatResult.compatibilityLevel)}`}>
            <h4 style={{ margin: '0 0 5px' }}>
              {compatResult.compatible ? '✓' : '✗'} {getCompatLevelLabel(compatResult.compatibilityLevel)}
            </h4>
            <p style={{ margin: 0, fontSize: '13px' }}>
              {compatResult.oldVersion} → {compatResult.newVersion}：
              {compatResult.issues.length > 0
                ? `发现 ${compatResult.issues.length} 个变更`
                : '未发现变更'}
            </p>
          </div>

          {compatResult.issues && compatResult.issues.length > 0 && (
            <div style={{ marginTop: '15px' }}>
              <h5>变更详情</h5>
              <ul className="error-list">
                {compatResult.issues.map((issue, idx) => (
                  <li key={idx} className={`error-item ${issue.severity === 'BREAKING' ? 'severity-critical' : issue.severity === 'WARNING' ? 'severity-high' : 'severity-low'}`}>
                    <div>
                      <span className="error-field">{issue.field || 'root'}</span>
                      <span className={`severity-badge ${getSeverityBadgeClass(issue.severity)}`}>
                        {getSeverityLabel(issue.severity)}
                      </span>
                    </div>
                    <div style={{ marginTop: '4px', color: '#555' }}>{issue.description}</div>
                    {issue.oldDefinition && issue.newDefinition && (
                      <div style={{ marginTop: '6px', fontSize: '12px', display: 'flex', gap: '10px' }}>
                        <div style={{ flex: 1 }}>
                          <div style={{ fontWeight: 600, color: '#888', marginBottom: '2px' }}>旧版本</div>
                          <code style={{ background: '#f5f5f5', padding: '2px 6px', borderRadius: '3px' }}>
                            {issue.oldDefinition}
                          </code>
                        </div>
                        <div style={{ flex: 1 }}>
                          <div style={{ fontWeight: 600, color: '#888', marginBottom: '2px' }}>新版本</div>
                          <code style={{ background: '#f5f5f5', padding: '2px 6px', borderRadius: '3px' }}>
                            {issue.newDefinition}
                          </code>
                        </div>
                      </div>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {compatResult.suggestions && compatResult.suggestions.length > 0 && (
            <div style={{ marginTop: '15px', padding: '12px', background: '#fffbeb', borderRadius: '8px', border: '1px solid #fcd34d' }}>
              <h5 style={{ margin: '0 0 8px', color: '#92400e' }}>💡 修复建议</h5>
              <ul style={{ margin: 0, paddingLeft: '20px', fontSize: '13px' }}>
                {compatResult.suggestions.map((s, idx) => (
                  <li key={idx} style={{ marginBottom: '4px', color: '#78350f' }}>{s}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default CompatibilityPanel;
