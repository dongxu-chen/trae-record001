import React from 'react';

function HotKeyPanel({ hotkeys }) {
  if (!hotkeys || hotkeys.length === 0) {
    return (
      <div className="card">
        <div className="card-header">
          <h2>热点Key分析</h2>
        </div>
        <div className="card-body">
          <div className="empty">暂无数据</div>
        </div>
      </div>
    );
  }

  const maxCount = Math.max(...hotkeys.map(k => k.Count), 1);

  return (
    <div className="card">
      <div className="card-header">
        <h2>热点Key分析 (Top 10)</h2>
      </div>
      <div className="card-body" style={{ padding: 0 }}>
        <div style={{ maxHeight: '350px', overflowY: 'auto' }}>
          {hotkeys.slice(0, 10).map((item, index) => (
            <div
              key={index}
              style={{
                padding: '12px 20px',
                borderBottom: '1px solid #f0f0f0',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <span style={{
                  fontFamily: 'Monaco, Consolas, monospace',
                  fontSize: '13px',
                  fontWeight: 500,
                  maxWidth: '70%',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                }} title={item.Key}>
                  {item.Key}
                </span>
                <span style={{ fontSize: '12px', color: '#8c8c8c' }}>
                  DB {item.DB} | {item.EventType}
                </span>
              </div>
              <div style={{
                width: '100%',
                height: '8px',
                background: '#f0f0f0',
                borderRadius: '4px',
                overflow: 'hidden',
              }}>
                <div style={{
                  width: `${(item.Count / maxCount) * 100}%`,
                  height: '100%',
                  background: item.EventType === 'expired' ? '#f5222d' :
                             item.EventType === 'del' ? '#faad14' : '#52c41a',
                  borderRadius: '4px',
                  transition: 'width 0.3s',
                }} />
              </div>
              <div style={{ fontSize: '12px', color: '#8c8c8c', marginTop: '4px' }}>
                {item.Count} 次
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default HotKeyPanel;
