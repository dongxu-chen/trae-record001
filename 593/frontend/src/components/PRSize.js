import React, { useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

function PRSize({ data }) {
  const [showModules, setShowModules] = useState(true);

  if (!data) return null;

  const hasFailed = data.status === 'fail' || data.status === 'warning';
  const diff = data.metadata?.diff || {};
  const diffByModule = data.metadata?.diff_by_module || {};

  const getSeverity = (item) => {
    if (item.status === 'pass') return 'passed';
    if (item.status === 'skip') return 'info';
    return item.severity;
  };

  const moduleData = Object.entries(diffByModule).map(([module, stats]) => ({
    name: module,
    文件数: stats.num_files || 0,
    新增行: stats.additions || 0,
    删除行: stats.deletions || 0
  }));

  const itemsByModule = {};
  data.items.forEach(item => {
    const module = item.details?.module || 'other';
    if (!itemsByModule[module]) itemsByModule[module] = [];
    itemsByModule[module].push(item);
  });

  return (
    <div className="check-section">
      <h2>
        <span className={`status-icon ${hasFailed ? 'failed' : 'passed'}`}></span>
        {data.display_name}
        <span style={{ fontSize: '0.8em', color: '#888', marginLeft: '10px' }}>
          - {data.metadata?.source_branch} vs {data.metadata?.target_branch}
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
            {diff.num_files || 0}
          </div>
          <div style={{ color: '#888', fontSize: '0.9em' }}>变更文件</div>
        </div>
        <div style={{ flex: 1, minWidth: '150px', background: '#1a1a2e', padding: '15px', borderRadius: '8px', textAlign: 'center' }}>
          <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#4ade80' }}>
            +{diff.additions || 0}
          </div>
          <div style={{ color: '#888', fontSize: '0.9em' }}>新增行</div>
        </div>
        <div style={{ flex: 1, minWidth: '150px', background: '#1a1a2e', padding: '15px', borderRadius: '8px', textAlign: 'center' }}>
          <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#ef4444' }}>
            -{diff.deletions || 0}
          </div>
          <div style={{ color: '#888', fontSize: '0.9em' }}>删除行</div>
        </div>
        {Object.keys(diffByModule).length > 1 && (
          <div style={{ flex: 1, minWidth: '150px', background: '#1a1a2e', padding: '15px', borderRadius: '8px', textAlign: 'center' }}>
            <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#3b82f6' }}>
              {Object.keys(diffByModule).length}
            </div>
            <div style={{ color: '#888', fontSize: '0.9em' }}>涉及模块</div>
          </div>
        )}
      </div>

      {moduleData.length > 0 && (
        <div className="chart-container">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
            <h4 style={{ color: '#e94560', margin: 0 }}>按模块统计</h4>
            <button 
              onClick={() => setShowModules(!showModules)}
              style={{ background: 'none', border: '1px solid #e94560', color: '#e94560', padding: '5px 10px', borderRadius: '5px', cursor: 'pointer' }}
            >
              {showModules ? '隐藏模块详情' : '显示模块详情'}
            </button>
          </div>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={moduleData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#333" />
              <XAxis dataKey="name" stroke="#888" fontSize={12} />
              <YAxis stroke="#888" />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: '#1a1a2e',
                  border: '1px solid #333',
                  color: '#fff'
                }}
              />
              <Legend />
              <Bar dataKey="文件数" fill="#e94560" />
              <Bar dataKey="新增行" fill="#4ade80" />
              <Bar dataKey="删除行" fill="#ef4444" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {showModules && Object.keys(itemsByModule).map(moduleName => {
        const moduleItems = itemsByModule[moduleName];
        const hasModuleFail = moduleItems.some(i => i.status === 'fail' || i.status === 'warning');
        const isCoreModule = ['core', 'auth', 'config'].includes(moduleName);

        return (
          <div key={moduleName} style={{ marginTop: '20px' }}>
            <div style={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: '10px',
              padding: '10px',
              background: isCoreModule ? 'rgba(233, 69, 96, 0.1)' : 'transparent',
              borderRadius: '5px',
              marginBottom: '10px'
            }}>
              <span className={`status-icon ${hasModuleFail ? 'failed' : 'passed'}`}></span>
              <h4 style={{ margin: 0, color: isCoreModule ? '#e94560' : '#fff' }}>
                {moduleName === 'overall' ? '整体' : `模块: ${moduleName}`}
                {isCoreModule && <span style={{ fontSize: '0.7em', marginLeft: '8px', color: '#e94560' }}>🔒 核心模块</span>}
              </h4>
            </div>

            {moduleItems.map((item) => (
              <div 
                key={item.id} 
                className={`result-item ${getSeverity(item)}`}
                style={{ marginLeft: '20px' }}
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
                    {item.details?.thresholds && (
                      <div style={{ marginTop: '8px', color: '#888', fontSize: '0.85em' }}>
                        阈值配置: 警告 ({item.details.thresholds.warn.files}文件, {item.details.thresholds.warn.additions}+行), 
                        错误 ({item.details.thresholds.error.files}文件, {item.details.thresholds.error.additions}+行)
                      </div>
                    )}
                    {item.details?.files && (
                      <div className="details" style={{ marginTop: '10px' }}>
                        <details>
                          <summary style={{ cursor: 'pointer', color: '#888' }}>
                            查看变更文件 ({item.details.files.length})
                          </summary>
                          <pre style={{ 
                            background: '#0f3460', 
                            padding: '10px', 
                            borderRadius: '5px', 
                            fontSize: '0.85rem',
                            maxHeight: '150px',
                            overflow: 'auto'
                          }}>
                            {item.details.files.map(f => `• ${f}`).join('\n')}
                          </pre>
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
      })}
    </div>
  );
}

export default PRSize;
