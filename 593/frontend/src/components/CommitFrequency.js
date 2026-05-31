import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

function CommitFrequency({ data }) {
  if (!data) return null;

  const hasFailed = data.status === 'fail' || data.status === 'warning';

  const getSeverity = (item) => {
    if (item.status === 'pass') return 'passed';
    if (item.status === 'skip') return 'info';
    return item.severity;
  };

  const chartData = Object.entries(data.metadata?.commits_by_day || {}).map(([date, count]) => ({
    date: date.slice(5),
    提交数: count
  }));

  const authorData = Object.entries(data.metadata?.commits_by_author || {}).map(([author, count]) => ({
    author: author.length > 8 ? author.slice(0, 8) + '...' : author,
    提交数: count
  }));

  return (
    <div className="check-section">
      <h2>
        <span className={`status-icon ${hasFailed ? 'failed' : 'passed'}`}></span>
        {data.display_name}
        <span style={{ fontSize: '0.8em', color: '#888', marginLeft: '10px' }}>
          - {data.metadata?.branch} ({data.metadata?.days}天)
        </span>
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

      <div style={{ display: 'flex', gap: '20px', marginBottom: '20px', flexWrap: 'wrap' }}>
        <div style={{ flex: 1, minWidth: '150px', background: '#1a1a2e', padding: '15px', borderRadius: '8px', textAlign: 'center' }}>
          <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#e94560' }}>
            {data.metadata?.total_commits || 0}
          </div>
          <div style={{ color: '#888', fontSize: '0.9em' }}>总提交数</div>
        </div>
        <div style={{ flex: 1, minWidth: '150px', background: '#1a1a2e', padding: '15px', borderRadius: '8px', textAlign: 'center' }}>
          <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#3b82f6' }}>
            {data.metadata?.avg_per_day?.toFixed?.(1) || 0}
          </div>
          <div style={{ color: '#888', fontSize: '0.9em' }}>日均提交</div>
        </div>
        <div style={{ flex: 1, minWidth: '150px', background: '#1a1a2e', padding: '15px', borderRadius: '8px', textAlign: 'center' }}>
          <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#4ade80' }}>
            {Object.keys(data.metadata?.commits_by_author || {}).length}
          </div>
          <div style={{ color: '#888', fontSize: '0.9em' }}>贡献者数量</div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '20px' }}>
        {chartData.length > 0 && (
          <div className="chart-container">
            <h4 style={{ color: '#e94560', marginBottom: '15px' }}>每日提交趋势</h4>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                <XAxis dataKey="date" stroke="#888" />
                <YAxis stroke="#888" />
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: '#1a1a2e',
                    border: '1px solid #333',
                    color: '#fff'
                  }}
                />
                <Legend />
                <Bar dataKey="提交数" fill="#e94560" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        {authorData.length > 1 && (
          <div className="chart-container">
            <h4 style={{ color: '#e94560', marginBottom: '15px' }}>作者贡献分布</h4>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={authorData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                <XAxis type="number" stroke="#888" />
                <YAxis dataKey="author" type="category" stroke="#888" width={80} />
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: '#1a1a2e',
                    border: '1px solid #333',
                    color: '#fff'
                  }}
                />
                <Legend />
                <Bar dataKey="提交数" fill="#3b82f6" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {data.items.map((item) => (
        <div 
          key={item.id} 
          className={`result-item ${getSeverity(item)}`}
          style={{ marginTop: '15px' }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div style={{ flex: 1 }}>
              <div className="message" style={{ fontWeight: '600', marginBottom: '5px' }}>
                {item.status === 'pass' ? '✓' : item.status === 'warning' ? '⚠' : '✗'} {item.name}
              </div>
              <div className="message" style={{ color: '#ccc', fontSize: '0.95em' }}>
                {item.message}
              </div>
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
              {item.details?.commit_hashes && (
                <div className="details" style={{ marginTop: '10px' }}>
                  <details>
                    <summary style={{ cursor: 'pointer', color: '#888' }}>
                      查看相关提交 ({item.details.commit_hashes.length})
                    </summary>
                    <div style={{ 
                      background: '#0f3460', 
                      padding: '10px', 
                      borderRadius: '5px',
                      fontFamily: 'monospace',
                      fontSize: '0.85rem'
                    }}>
                      {item.details.commit_hashes.map(h => <div key={h}>• {h}</div>)}
                    </div>
                  </details>
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

export default CommitFrequency;
