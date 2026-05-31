import React from 'react';

function MergeDirection({ data }) {
  if (!data) return null;

  const hasFailed = data.status === 'fail' || data.status === 'warning';
  const sourceBranch = data.metadata?.source_branch;
  const targetBranch = data.metadata?.target_branch;

  const getSeverity = (item) => {
    if (item.status === 'pass') return 'passed';
    if (item.status === 'skip') return 'info';
    return item.severity;
  };

  return (
    <div className="check-section">
      <h2>
        <span className={`status-icon ${hasFailed ? 'failed' : 'passed'}`}></span>
        {data.display_name}
        {sourceBranch && targetBranch && (
          <span style={{ fontSize: '0.8em', color: '#888', marginLeft: '10px' }}>
            - {sourceBranch} → {targetBranch}
          </span>
        )}
      </h2>

      {data.summary && (
        <div style={{ marginBottom: '15px', color: '#888', fontSize: '0.9em' }}>
          共 {data.summary.total} 项检查: 
          <span style={{ color: '#4ade80', marginLeft: '10px' }}>{data.summary.passed} 通过</span>
          {data.summary.failed > 0 && (
            <span style={{ color: '#ef4444', marginLeft: '10px' }}>{data.summary.failed} 失败</span>
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
                  {item.suggestion}
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
    </div>
  );
}

export default MergeDirection;
