import React, { useState } from 'react';

function MockPanel({ openApiSpec, endpoints }) {
  const [path, setPath] = useState('');
  const [method, setMethod] = useState('GET');
  const [statusCode, setStatusCode] = useState('200');
  const [mockResult, setMockResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleEndpointSelect = (endpoint) => {
    setPath(endpoint.path);
    setMethod(endpoint.method);
  };

  const handleGenerate = async () => {
    if (!openApiSpec) {
      alert('请先输入并解析OpenAPI规范');
      return;
    }
    if (!path) {
      alert('请填写API路径');
      return;
    }

    setLoading(true);
    setMockResult(null);

    try {
      const response = await fetch('/api/mock/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          openApiSpec,
          path,
          method,
          statusCode: parseInt(statusCode)
        })
      });

      const data = await response.json();
      setMockResult(data);
    } catch (error) {
      alert('Mock生成失败: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = () => {
    if (mockResult && mockResult.mockResponse) {
      navigator.clipboard.writeText(mockResult.mockResponse);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div>
      <h3 style={{ marginTop: 0 }}>Mock响应生成</h3>

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

      <button
        className="btn btn-primary"
        onClick={handleGenerate}
        disabled={loading}
      >
        {loading ? '生成中...' : '生成Mock响应'}
      </button>

      {mockResult && (
        <div className="mock-result" style={{ marginTop: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h4 style={{ margin: 0 }}>
              {mockResult.generated ? (
                <span style={{ color: '#166534' }}>✓ Mock数据已生成</span>
              ) : (
                <span style={{ color: '#dc2626' }}>✗ 生成失败</span>
              )}
            </h4>
            {mockResult.generated && (
              <button className="btn btn-secondary" onClick={handleCopy} style={{ padding: '4px 12px', fontSize: '12px' }}>
                {copied ? '已复制 ✓' : '复制JSON'}
              </button>
            )}
          </div>

          {mockResult.mockResponse && (
            <div className="json-preview" style={{ marginTop: '10px', maxHeight: '400px' }}>
              {mockResult.mockResponse}
            </div>
          )}

          {mockResult.generationNotes && mockResult.generationNotes.length > 0 && (
            <div style={{ marginTop: '10px' }}>
              <h5 style={{ margin: '0 0 5px', color: '#666' }}>生成说明</h5>
              <ul style={{ margin: 0, paddingLeft: '20px', fontSize: '12px', color: '#888' }}>
                {mockResult.generationNotes.map((note, idx) => (
                  <li key={idx}>{note}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default MockPanel;
