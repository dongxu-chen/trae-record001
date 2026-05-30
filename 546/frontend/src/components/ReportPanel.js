import React, { useState } from 'react';

function ReportPanel({ openApiSpec, endpoints }) {
  const [path, setPath] = useState('');
  const [method, setMethod] = useState('GET');
  const [statusCode, setStatusCode] = useState('200');
  const [env1Name, setEnv1Name] = useState('dev');
  const [env2Name, setEnv2Name] = useState('prod');
  const [env1ResponseBody, setEnv1ResponseBody] = useState('');
  const [env2ResponseBody, setEnv2ResponseBody] = useState('');
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleGenerateReport = async () => {
    if (!env1ResponseBody.trim() || !env2ResponseBody.trim()) {
      alert('请填写两个环境的响应体');
      return;
    }

    setLoading(true);
    setReport(null);

    try {
      const response = await fetch('/api/compare/report', {
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
      setReport(data);
    } catch (error) {
      alert('生成报告失败: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  const exportReport = () => {
    if (!report) return;
    
    const reportStr = JSON.stringify(report, null, 2);
    const blob = new Blob([reportStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `comparison-report-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const copyReport = () => {
    if (!report) return;
    navigator.clipboard.writeText(JSON.stringify(report, null, 2))
      .then(() => alert('报告已复制到剪贴板'))
      .catch(err => alert('复制失败: ' + err));
  };

  const getTypeLabel = (type) => {
    const labels = {
      'FIELD_ADDED': '新增字段',
      'FIELD_REMOVED': '删除字段',
      'VALUE_CHANGED': '值变更',
      'TYPE_CHANGED': '类型变更',
      'ARRAY_LENGTH_CHANGED': '数组长度变更',
      'STRUCTURE_MISMATCH': '结构不匹配'
    };
    return labels[type] || type;
  };

  return (
    <div>
      <h3 style={{ marginTop: 0 }}>差异报告</h3>

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
            style={{ height: '150px', fontFamily: 'Consolas, monospace', fontSize: '12px' }}
            placeholder='{"id": 1, ...}'
            value={env1ResponseBody}
            onChange={(e) => setEnv1ResponseBody(e.target.value)}
          />
        </div>
        <div className="form-group">
          <label>{env2Name} 环境响应体</label>
          <textarea
            style={{ height: '150px', fontFamily: 'Consolas, monospace', fontSize: '12px' }}
            placeholder='{"id": 1, ...}'
            value={env2ResponseBody}
            onChange={(e) => setEnv2ResponseBody(e.target.value)}
          />
        </div>
      </div>

      <div className="btn-group">
        <button 
          className="btn btn-primary"
          onClick={handleGenerateReport}
          disabled={loading}
        >
          {loading ? '生成中...' : '生成报告'}
        </button>
        {report && (
          <>
            <button className="btn btn-secondary" onClick={exportReport}>
              导出JSON
            </button>
            <button className="btn btn-secondary" onClick={copyReport}>
              复制报告
            </button>
          </>
        )}
      </div>

      {report && (
        <div style={{ marginTop: '30px' }}>
          <h4>对比报告摘要</h4>
          
          <div className="report-summary">
            <div className="summary-card total">
              <div className="summary-value">{report.totalDifferences}</div>
              <div className="summary-label">总差异数</div>
            </div>
            <div className="summary-card added">
              <div className="summary-value">{report.differenceTypeSummary?.FIELD_ADDED || 0}</div>
              <div className="summary-label">新增字段</div>
            </div>
            <div className="summary-card removed">
              <div className="summary-value">{report.differenceTypeSummary?.FIELD_REMOVED || 0}</div>
              <div className="summary-label">删除字段</div>
            </div>
            <div className="summary-card changed">
              <div className="summary-value">{report.differenceTypeSummary?.VALUE_CHANGED || 0}</div>
              <div className="summary-label">值变更</div>
            </div>
          </div>

          <h5>差异详情</h5>
          {report.differences && report.differences.length > 0 ? (
            <table className="report-table">
              <thead>
                <tr>
                  <th>字段路径</th>
                  <th>差异类型</th>
                  <th>{env1Name} 值</th>
                  <th>{env2Name} 值</th>
                  <th>说明</th>
                </tr>
              </thead>
              <tbody>
                {report.differences.map((diff, idx) => (
                  <tr key={idx}>
                    <td style={{ fontFamily: 'Consolas, monospace', fontSize: '12px' }}>
                      {diff.field}
                    </td>
                    <td>
                      <span className={`difference-type diff-type-${diff.type === 'FIELD_ADDED' ? 'added' : diff.type === 'FIELD_REMOVED' ? 'removed' : diff.type === 'VALUE_CHANGED' ? 'changed' : 'type'}`}>
                        {getTypeLabel(diff.type)}
                      </span>
                    </td>
                    <td style={{ fontFamily: 'Consolas, monospace', fontSize: '11px', maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {diff.env1Value !== null && diff.env1Value !== undefined 
                        ? (typeof diff.env1Value === 'object' ? JSON.stringify(diff.env1Value) : String(diff.env1Value))
                        : '-'}
                    </td>
                    <td style={{ fontFamily: 'Consolas, monospace', fontSize: '11px', maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {diff.env2Value !== null && diff.env2Value !== undefined 
                        ? (typeof diff.env2Value === 'object' ? JSON.stringify(diff.env2Value) : String(diff.env2Value))
                        : '-'}
                    </td>
                    <td style={{ fontSize: '12px', color: '#666' }}>
                      {diff.description}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="no-data">
              两个环境响应完全一致，没有发现差异
            </div>
          )}

          <h5 style={{ marginTop: '30px' }}>完整报告 (JSON)</h5>
          <div className="json-preview">
            {JSON.stringify(report, null, 2)}
          </div>
        </div>
      )}
    </div>
  );
}

export default ReportPanel;
