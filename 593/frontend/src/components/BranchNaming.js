import React, { useState } from 'react';
import axios from 'axios';

function BranchNaming({ data }) {
  const [fixing, setFixing] = useState(false);
  const [fixResult, setFixResult] = useState(null);

  if (!data) return null;

  const hasFailed = data.status === 'fail' || data.status === 'warning';
  const branchName = data.metadata?.branch_name;

  const getSeverity = (item) => {
    if (item.status === 'pass') return 'passed';
    if (item.status === 'skip') return 'info';
    return item.severity;
  };

  const handleFix = async () => {
    setFixing(true);
    try {
      const response = await axios.post('/api/fix/branch-name', {
        branch: branchName,
        dry_run: true
      });
      setFixResult(response.data);
    } catch (error) {
      console.error('Error fixing branch name:', error);
    } finally {
      setFixing(false);
    }
  };

  return (
    <div className="check-section">
      <h2>
        <span className={`status-icon ${hasFailed ? 'failed' : 'passed'}`}></span>
        {data.display_name}
        {branchName && <span style={{ fontSize: '0.8em', color: '#888', marginLeft: '10px' }}>- {branchName}</span>}
      </h2>

      {data.summary && (
        <div style={{ marginBottom: '15px', color: '#888', fontSize: '0.9em' }}>
          共 {data.summary.total} 项检查: 
          <span style={{ color: '#4ade80', marginLeft: '10px' }}>{data.summary.passed} 通过</span>
          {data.summary.failed > 0 && (
            <span style={{ color: '#ef4444', marginLeft: '10px' }}>{data.summary.failed} 失败</span>
          )}
          {data.summary.warnings > 0 && (
            <span style={{ color: '#f59e0b', marginLeft: '10px' }}>{data.summary.warnings} 警告</span>
          )}
        </div>
      )}

      {data.items.map((item) => (
        <div 
          key={item.id} 
          className={`result-item ${getSeverity(item)}`}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div style={{ flex: 1 }}>
              <div className="message" style={{ fontWeight: '600', marginBottom: '5px' }}>
                {item.status === 'pass' ? '✓' : item.status === 'warning' ? '⚠' : '✗'} {item.name}
              </div>
              <div className="message" style={{ color: '#ccc', fontSize: '0.95em' }}>
                {item.message}
              </div>
              {item.description && (
                <div style={{ color: '#888', fontSize: '0.85em', marginTop: '5px' }}>
                  {item.description}
                </div>
              )}
              {item.suggestion && (
                <div style={{ 
                  background: 'rgba(59, 130, 246, 0.1)', 
                  padding: '10px', 
                  borderRadius: '5px', 
                  marginTop: '10px',
                  borderLeft: '3px solid #3b82f6'
                }}>
                  <span style={{ color: '#3b82f6', fontWeight: '600' }}>💡 建议: </span>
                  <span style={{ whiteSpace: 'pre-wrap', fontFamily: 'monospace', fontSize: '0.9em' }}>
                    {item.suggestion}
                  </span>
                </div>
              )}
              {Object.keys(item.details).length > 0 && (
                <div className="details" style={{ marginTop: '10px' }}>
                  <pre style={{ 
                    background: '#0f3460', 
                    padding: '10px', 
                    borderRadius: '5px', 
                    fontSize: '0.85rem',
                    maxHeight: '200px',
                    overflow: 'auto'
                  }}>
                    {JSON.stringify(item.details, null, 2)}
                  </pre>
                </div>
              )}
              {item.documentation_url && (
                <div style={{ marginTop: '8px', fontSize: '0.85em' }}>
                  <a href={item.documentation_url} target="_blank" rel="noopener noreferrer" 
                     style={{ color: '#e94560' }}>
                    📖 查看文档
                  </a>
                </div>
              )}
            </div>
            <div style={{ 
              display: 'flex', 
              flexDirection: 'column', 
              alignItems: 'flex-end',
              gap: '5px'
            }}>
              <span className={`status-badge ${item.status === 'pass' ? 'passed' : 'failed'}`} 
                    style={{ fontSize: '0.75em' }}>
                {item.status.toUpperCase()}
              </span>
              <span style={{ fontSize: '0.75em', color: '#888', textTransform: 'uppercase' }}>
                {item.severity}
              </span>
            </div>
          </div>
        </div>
      ))}

      {hasFailed && data.metadata?.suggested_name && (
        <div className="fix-section">
          <button className="fix-btn" onClick={handleFix} disabled={fixing}>
            {fixing ? '修复中...' : '🔧 自动修复 (预览)'}
          </button>
          {fixResult && (
            <div style={{ marginTop: '10px', padding: '10px', background: 'rgba(74, 222, 128, 0.1)', borderRadius: '5px' }}>
              <div style={{ color: '#4ade80', fontWeight: '600' }}>{fixResult.message}</div>
              {fixResult.suggested_name && (
                <div style={{ marginTop: '5px' }}>
                  建议命名: <code style={{ background: '#1a1a2e', padding: '2px 6px', borderRadius: '3px' }}>
                    {fixResult.suggested_name}
                  </code>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default BranchNaming;
