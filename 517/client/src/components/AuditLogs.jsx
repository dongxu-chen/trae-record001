import { useState, useEffect } from 'react';

const AuditLogs = ({ logs, loading }) => {
  const [filter, setFilter] = useState('all');
  const [searchText, setSearchText] = useState('');

  const getActionLabel = (action) => {
    const labels = {
      mask: '单条脱敏',
      mask_batch: '批量脱敏',
      view: '数据查看',
      export: '数据导出'
    };
    return labels[action] || action;
  };

  const getActionIcon = (action) => {
    const icons = {
      mask: '🔒',
      mask_batch: '📊',
      view: '👁️',
      export: '📥'
    };
    return icons[action] || '📝';
  };

  const formatTime = (timestamp) => {
    const date = new Date(timestamp);
    return date.toLocaleString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  };

  const filteredLogs = logs
    .filter(log => filter === 'all' || log.action === filter)
    .filter(log => 
      !searchText || 
      log.userName?.toLowerCase().includes(searchText.toLowerCase()) ||
      log.sensitiveFields?.some(f => f.toLowerCase().includes(searchText.toLowerCase()))
    );

  const stats = {
    total: logs.length,
    mask: logs.filter(l => l.action === 'mask').length,
    mask_batch: logs.filter(l => l.action === 'mask_batch').length
  };

  return (
    <div className="audit-logs">
      <div className="audit-header">
        <h3>📜 脱敏审计日志</h3>
        <div className="audit-stats">
          <span className="stat-item">
            <span className="stat-value">{stats.total}</span>
            <span className="stat-label">总记录</span>
          </span>
          <span className="stat-item">
            <span className="stat-value">{stats.mask}</span>
            <span className="stat-label">单条脱敏</span>
          </span>
          <span className="stat-item">
            <span className="stat-value">{stats.mask_batch}</span>
            <span className="stat-label">批量处理</span>
          </span>
        </div>
      </div>

      <div className="audit-filters">
        <div className="filter-tabs">
          {['all', 'mask', 'mask_batch'].map(type => (
            <button
              key={type}
              className={`filter-tab ${filter === type ? 'active' : ''}`}
              onClick={() => setFilter(type)}
            >
              {type === 'all' ? '全部' : getActionLabel(type)}
            </button>
          ))}
        </div>
        <input
          type="text"
          className="search-input"
          placeholder="搜索用户或字段..."
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
        />
      </div>

      {loading ? (
        <div className="audit-loading">
          <div className="spinner small"></div>
          加载中...
        </div>
      ) : (
        <div className="audit-list">
          {filteredLogs.length === 0 ? (
            <div className="audit-empty">
              <span className="empty-icon">📭</span>
              <p>暂无审计记录</p>
            </div>
          ) : (
            filteredLogs.slice(0, 50).map(log => (
              <div key={log.id} className="audit-item">
                <div className="audit-icon">{getActionIcon(log.action)}</div>
                <div className="audit-content">
                  <div className="audit-top">
                    <span className="audit-user">{log.userName || '匿名用户'}</span>
                    <span className="audit-time">{formatTime(log.timestamp)}</span>
                  </div>
                  <div className="audit-middle">
                    <span className="audit-action">{getActionLabel(log.action)}</span>
                    <span className="audit-permission">权限: {log.permission || 'normal'}</span>
                  </div>
                  {log.sensitiveFields && log.sensitiveFields.length > 0 && (
                    <div className="audit-fields">
                      <span className="fields-label">敏感字段:</span>
                      {log.sensitiveFields.map(field => (
                        <span key={field} className="field-tag">{field}</span>
                      ))}
                    </div>
                  )}
                  {log.recordCount && (
                    <div className="audit-count">
                      处理记录数: <strong>{log.recordCount}</strong>
                    </div>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
};

export default AuditLogs;
