import React from 'react';

function ConflictDetection({ data }) {
  if (!data) return null;

  const hasFailed = data.status === 'fail' || data.status === 'warning';
  const hasConflicts = data.metadata?.has_conflicts;
  const conflictCount = data.metadata?.conflict_count || 0;
  const conflictFiles = data.metadata?.conflict_files || [];

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
        <span style={{ fontSize: '0.8em', color: '#888', marginLeft: '10px' }}>
          - {data.metadata?.source_branch} → {data.metadata?.target_branch}
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

      {hasConflicts !== undefined && (
        <div style={{ 
          padding: '20px', 
          borderRadius: '8px', 
          marginBottom: '20px',
          background: hasConflicts ? 'rgba(239, 68, 68, 0.1)' : 'rgba(74, 222, 128, 0.1)',
          border: `1px solid ${hasConflicts ? '#ef4444' : '#4ade80'}`
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
            <div style={{ fontSize: '3rem' }}>
              {hasConflicts ? '⚠️' : '✅'}
            </div>
            <div>
              <div style={{ fontSize: '1.3rem', fontWeight: 'bold', color: hasConflicts ? '#ef4444' : '#4ade80' }}>
                {hasConflicts ? '检测到合并冲突' : '无合并冲突'}
              </div>
              <div style={{ color: '#ccc', marginTop: '5px' }}>
                {hasConflicts 
                  ? `检测到 ${conflictCount} 个文件存在冲突，需要手动解决` 
                  : '两个分支可以干净地合并'}
              </div>
            </div>
          </div>
        </div>
      )}

      {data.metadata?.static_detection && (
        <div style={{ 
          background: '#1a1a2e', 
          padding: '15px', 
          borderRadius: '8px', 
          marginBottom: '20px',
          fontSize: '0.9em'
        }}>
          <h4 style={{ color: '#e94560', marginTop: 0, marginBottom: '10px' }}>检测详情</h4>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '10px' }}>
            <div>
              <span style={{ color: '#888' }}>源分支变更文件: </span>
              <span style={{ color: '#fff' }}>{data.metadata.static_detection.source_files_changed}</span>
            </div>
            <div>
              <span style={{ color: '#888' }}>目标分支变更文件: </span>
              <span style={{ color: '#fff' }}>{data.metadata.static_detection.target_files_changed}</span>
            </div>
            <div>
              <span style={{ color: '#888' }}>共同变更文件: </span>
              <span style={{ color: hasConflicts ? '#ef4444' : '#fff' }}>{data.metadata.static_detection.common_files_changed}</span>
            </div>
            <div>
              <span style={{ color: '#888' }}>可干净合并: </span>
              <span style={{ color: data.metadata.merge_attempt?.can_merge_cleanly ? '#4ade80' : '#ef4444' }}>
                {data.metadata.merge_attempt?.can_merge_cleanly ? '是' : '否'}
              </span>
            </div>
          </div>
        </div>
      )}

      {conflictFiles.length > 0 && (
        <div style={{ marginBottom: '20px' }}>
          <h4 style={{ color: '#ef4444', marginBottom: '10px' }}>
            📋 冲突文件列表 ({conflictFiles.length})
          </h4>
          <div style={{ 
            background: '#1a1a2e', 
            padding: '15px', 
            borderRadius: '8px',
            maxHeight: '300px',
            overflow: 'auto'
          }}>
            {conflictFiles.map((file, idx) => (
              <div key={idx} style={{ 
                padding: '8px 12px', 
                borderBottom: '1px solid #333',
                display: 'flex',
                alignItems: 'center',
                gap: '10px'
              }}>
                <span style={{ color: '#ef4444' }}>✗</span>
                <code style={{ 
                  fontFamily: 'monospace', 
                  background: '#0f3460', 
                  padding: '3px 8px', 
                  borderRadius: '3px',
                  fontSize: '0.9em',
                  flex: 1
                }}>
                  {file}
                </code>
              </div>
            ))}
          </div>
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
              {item.suggestion && (
                <div style={{ 
                  background: 'rgba(59, 130, 246, 0.1)', 
                  padding: '15px', 
                  borderRadius: '5px', 
                  marginTop: '10px',
                  borderLeft: '3px solid #3b82f6',
                  whiteSpace: 'pre-wrap',
                  fontFamily: 'monospace',
                  fontSize: '0.9em'
                }}>
                  <div style={{ color: '#3b82f6', fontWeight: '600', marginBottom: '8px', fontFamily: 'sans-serif' }}>
                    💡 解决建议
                  </div>
                  {item.suggestion}
                </div>
              )}
              {Object.keys(item.details).length > 0 && item.details.conflict_files && (
                <div className="details" style={{ marginTop: '10px' }}>
                  <pre style={{ 
                    background: '#0f3460', 
                    padding: '10px', 
                    borderRadius: '5px', 
                    fontSize: '0.85rem',
                    maxHeight: '200px',
                    overflow: 'auto'
                  }}>
                    {JSON.stringify({
                      conflict_files: item.details.conflict_files,
                      common_files_changed: item.details.common_files_changed
                    }, null, 2)}
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

      {hasConflicts && (
        <div style={{ 
          marginTop: '20px', 
          padding: '15px', 
          background: 'rgba(245, 158, 11, 0.1)', 
          borderRadius: '8px',
          border: '1px solid #f59e0b'
        }}>
          <h4 style={{ color: '#f59e0b', marginTop: 0, marginBottom: '10px' }}>
            🛠️ 快速解决命令
          </h4>
          <div style={{ fontFamily: 'monospace', fontSize: '0.9em', lineHeight: '1.8' }}>
            <div style={{ marginBottom: '8px' }}>
              <span style={{ color: '#888' }}># 切换到目标分支:</span><br />
              <code style={{ background: '#1a1a2e', padding: '3px 6px', borderRadius: '3px' }}>
                git checkout {data.metadata?.target_branch}
              </code>
            </div>
            <div style={{ marginBottom: '8px' }}>
              <span style={{ color: '#888' }}># 合并源分支:</span><br />
              <code style={{ background: '#1a1a2e', padding: '3px 6px', borderRadius: '3px' }}>
                git merge {data.metadata?.source_branch}
              </code>
            </div>
            <div style={{ marginBottom: '8px' }}>
              <span style={{ color: '#888' }}># 查看冲突文件:</span><br />
              <code style={{ background: '#1a1a2e', padding: '3px 6px', borderRadius: '3px' }}>
                git status --porcelain | grep "^UU"
              </code>
            </div>
            <div>
              <span style={{ color: '#888' }}># 中止合并:</span><br />
              <code style={{ background: '#1a1a2e', padding: '3px 6px', borderRadius: '3px' }}>
                git merge --abort
              </code>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default ConflictDetection;
