import React, { useState } from 'react';

const mockAuditLogs = [
  {
    id: 'audit-20260529103000-abc123',
    timestamp: '2026-05-29T10:30:00+08:00',
    resourceId: 'ecs-prod-web-001',
    resourceName: 'ecs-prod-web-001',
    resourceType: 'ECS',
    accountId: 'account-prod-001',
    accountName: '生产账号',
    action: 'tag_modified',
    changes: [
      { key: 'Environment', oldValue: 'Development', newValue: 'Production' },
    ],
    operator: 'admin@example.com',
    operatorRole: 'role-admin',
    source: 'manual',
    description: '修改标签: Environment',
  },
  {
    id: 'audit-20260529094500-def456',
    timestamp: '2026-05-29T09:45:00+08:00',
    resourceId: 'ecs-dev-api-002',
    resourceName: 'ecs-dev-api-002',
    resourceType: 'ECS',
    accountId: 'account-dev-001',
    accountName: '开发账号',
    action: 'tag_added',
    changes: [
      { key: 'CostCenter', newValue: 'CC200' },
    ],
    operator: 'devops@example.com',
    operatorRole: 'role-dev-admin',
    source: 'template',
    description: '添加标签: CostCenter',
  },
  {
    id: 'audit-20260529082000-ghi789',
    timestamp: '2026-05-29T08:20:00+08:00',
    resourceId: 'rds-prod-db-001',
    resourceName: 'rds-prod-db-001',
    resourceType: 'RDS',
    accountId: 'account-prod-001',
    accountName: '生产账号',
    action: 'tags_applied',
    changes: [
      { key: 'Environment', newValue: 'Production' },
      { key: 'Department', newValue: 'Data' },
      { key: 'Backup', newValue: 'Enabled' },
    ],
    operator: 'system',
    operatorRole: 'system',
    source: 'auto_template',
    description: '批量应用标签模板',
  },
  {
    id: 'audit-20260528161500-jkl012',
    timestamp: '2026-05-28T16:15:00+08:00',
    resourceId: 'oss-dev-assets-001',
    resourceName: 'oss-dev-assets-001',
    resourceType: 'OSS',
    accountId: 'account-dev-001',
    accountName: '开发账号',
    action: 'tag_deleted',
    changes: [
      { key: 'Owner', oldValue: 'old-owner@example.com' },
    ],
    operator: 'admin@example.com',
    operatorRole: 'role-admin',
    source: 'manual',
    description: '删除标签: Owner',
  },
  {
    id: 'audit-20260528143000-mno345',
    timestamp: '2026-05-28T14:30:00+08:00',
    resourceId: 'ecs-prod-api-003',
    resourceName: 'ecs-prod-api-003',
    resourceType: 'ECS',
    accountId: 'account-prod-001',
    accountName: '生产账号',
    action: 'bulk_update',
    changes: [
      { key: 'Project', oldValue: 'OldProject', newValue: 'API-Gateway' },
      { key: 'Owner', oldValue: 'dev@example.com', newValue: 'api-team@example.com' },
    ],
    operator: 'team-lead@example.com',
    operatorRole: 'role-prod-operator',
    source: 'bulk',
    description: '批量更新标签: 2 个标签',
  },
];

const mockStats = {
  totalLogs: 156,
  byAction: {
    tag_added: 45,
    tag_modified: 68,
    tag_deleted: 23,
    tags_applied: 12,
    bulk_update: 8,
  },
  byOperator: {
    'admin@example.com': 45,
    'devops@example.com': 38,
    'team-lead@example.com': 25,
    system: 48,
  },
  byResourceType: {
    ECS: 89,
    RDS: 34,
    OSS: 33,
  },
  todayCount: 12,
  thisWeekCount: 89,
};

const AuditLogs = () => {
  const [logs] = useState(mockAuditLogs);
  const [filter, setFilter] = useState({
    resourceId: '',
    action: '',
    operator: '',
    startDate: '',
    endDate: '',
  });
  const [showDetail, setShowDetail] = useState(null);

  const actionLabels = {
    tag_added: { label: '添加标签', color: '#10b981', bg: '#dcfce7' },
    tag_modified: { label: '修改标签', color: '#3b82f6', bg: '#dbeafe' },
    tag_deleted: { label: '删除标签', color: '#ef4444', bg: '#fee2e2' },
    tags_applied: { label: '应用模板', color: '#8b5cf6', bg: '#ede9fe' },
    bulk_update: { label: '批量更新', color: '#f59e0b', bg: '#fef3c7' },
  };

  const formatTime = (timestamp) => {
    const date = new Date(timestamp);
    return date.toLocaleString('zh-CN');
  };

  const getActionStyle = (action) => {
    return actionLabels[action] || { label: action, color: '#6b7280', bg: '#f3f4f6' };
  };

  const filteredLogs = logs.filter(log => {
    if (filter.resourceId && !log.resourceId.includes(filter.resourceId)) return false;
    if (filter.action && log.action !== filter.action) return false;
    if (filter.operator && !log.operator.includes(filter.operator)) return false;
    return true;
  });

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>📋 标签变更审计</h1>
          <p className="page-subtitle">追踪所有标签修改操作，完整可追溯</p>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button className="btn btn-secondary">导出日志</button>
        </div>
      </div>

      <div className="stats-grid" style={{ gridTemplateColumns: 'repeat(4, 1fr)', marginBottom: '1.5rem' }}>
        <div className="stat-card">
          <div className="stat-value" style={{ color: '#3b82f6' }}>{mockStats.totalLogs}</div>
          <div className="stat-label">总日志数</div>
          <div className="stat-change">累计记录</div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{ color: '#10b981' }}>{mockStats.todayCount}</div>
          <div className="stat-label">今日操作</div>
          <div className="stat-change">今日新增</div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{ color: '#8b5cf6' }}>{mockStats.thisWeekCount}</div>
          <div className="stat-label">本周操作</div>
          <div className="stat-change">近7天</div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{ color: '#f59e0b' }}>5</div>
          <div className="stat-label">操作类型</div>
          <div className="stat-change">增删改查</div>
        </div>
      </div>

      <div className="card" style={{ marginBottom: '1.5rem' }}>
        <div className="card-header">🔍 筛选条件</div>
        <div style={{ padding: '1.5rem' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem' }}>
            <div className="form-group" style={{ marginBottom: 0 }}>
              <label>资源ID</label>
              <input
                type="text"
                placeholder="输入资源ID"
                value={filter.resourceId}
                onChange={(e) => setFilter({ ...filter, resourceId: e.target.value })}
              />
            </div>
            <div className="form-group" style={{ marginBottom: 0 }}>
              <label>操作类型</label>
              <select
                value={filter.action}
                onChange={(e) => setFilter({ ...filter, action: e.target.value })}
              >
                <option value="">全部</option>
                <option value="tag_added">添加标签</option>
                <option value="tag_modified">修改标签</option>
                <option value="tag_deleted">删除标签</option>
                <option value="tags_applied">应用模板</option>
                <option value="bulk_update">批量更新</option>
              </select>
            </div>
            <div className="form-group" style={{ marginBottom: 0 }}>
              <label>操作人</label>
              <input
                type="text"
                placeholder="输入操作人"
                value={filter.operator}
                onChange={(e) => setFilter({ ...filter, operator: e.target.value })}
              />
            </div>
            <div className="form-group" style={{ marginBottom: 0 }}>
              <label>操作日期</label>
              <input
                type="date"
                value={filter.startDate}
                onChange={(e) => setFilter({ ...filter, startDate: e.target.value })}
              />
            </div>
          </div>
          <div style={{ marginTop: '1rem', display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
            <button
              className="btn btn-secondary"
              onClick={() => setFilter({ resourceId: '', action: '', operator: '', startDate: '', endDate: '' })}
            >
              重置筛选
            </button>
            <button className="btn btn-primary">查询</button>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span>审计日志列表</span>
            <span style={{ fontSize: '0.875rem', color: '#6b7280' }}>共 {filteredLogs.length} 条记录</span>
          </div>
        </div>
        <div style={{ overflowX: 'auto' }}>
          <table className="table">
            <thead>
              <tr>
                <th>时间</th>
                <th>操作类型</th>
                <th>资源</th>
                <th>账号</th>
                <th>操作人</th>
                <th>变更内容</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {filteredLogs.map((log) => {
                const actionStyle = getActionStyle(log.action);
                return (
                  <tr key={log.id}>
                    <td style={{ fontSize: '0.8rem', whiteSpace: 'nowrap' }}>
                      {formatTime(log.timestamp)}
                    </td>
                    <td>
                      <span style={{
                        padding: '0.25rem 0.5rem',
                        borderRadius: '4px',
                        fontSize: '0.75rem',
                        fontWeight: '500',
                        color: actionStyle.color,
                        background: actionStyle.bg,
                      }}>
                        {actionStyle.label}
                      </span>
                    </td>
                    <td>
                      <div style={{ fontWeight: '500' }}>{log.resourceName}</div>
                      <div style={{ fontSize: '0.75rem', color: '#6b7280' }}>{log.resourceType}</div>
                    </td>
                    <td>{log.accountName}</td>
                    <td>
                      <div style={{ fontSize: '0.875rem' }}>{log.operator}</div>
                      <div style={{ fontSize: '0.7rem', color: '#6b7280' }}>{log.operatorRole}</div>
                    </td>
                    <td>
                      <div style={{ fontSize: '0.8rem', color: '#374151' }}>
                        {log.changes.length} 个标签变更
                      </div>
                    </td>
                    <td>
                      <button
                        className="btn btn-secondary"
                        style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}
                        onClick={() => setShowDetail(log)}
                      >
                        详情
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {showDetail && (
        <div className="modal-overlay" onClick={() => setShowDetail(null)}>
          <div className="modal" style={{ maxWidth: '600px' }} onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <span className="modal-title">📋 变更详情</span>
              <button className="modal-close" onClick={() => setShowDetail(null)}>×</button>
            </div>
            <div style={{ padding: '1.5rem' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
                <div>
                  <div style={{ fontSize: '0.75rem', color: '#6b7280', marginBottom: '0.25rem' }}>操作时间</div>
                  <div style={{ fontWeight: '500' }}>{formatTime(showDetail.timestamp)}</div>
                </div>
                <div>
                  <div style={{ fontSize: '0.75rem', color: '#6b7280', marginBottom: '0.25rem' }}>操作ID</div>
                  <div style={{ fontFamily: 'monospace', fontSize: '0.875rem' }}>{showDetail.id}</div>
                </div>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
                <div>
                  <div style={{ fontSize: '0.75rem', color: '#6b7280', marginBottom: '0.25rem' }}>资源名称</div>
                  <div style={{ fontWeight: '500' }}>{showDetail.resourceName}</div>
                </div>
                <div>
                  <div style={{ fontSize: '0.75rem', color: '#6b7280', marginBottom: '0.25rem' }}>资源类型</div>
                  <div style={{ fontWeight: '500' }}>{showDetail.resourceType}</div>
                </div>
                <div>
                  <div style={{ fontSize: '0.75rem', color: '#6b7280', marginBottom: '0.25rem' }}>操作账号</div>
                  <div style={{ fontWeight: '500' }}>{showDetail.accountName}</div>
                </div>
                <div>
                  <div style={{ fontSize: '0.75rem', color: '#6b7280', marginBottom: '0.25rem' }}>操作人</div>
                  <div style={{ fontWeight: '500' }}>{showDetail.operator}</div>
                </div>
              </div>
              <div style={{ marginBottom: '1rem' }}>
                <div style={{ fontSize: '0.75rem', color: '#6b7280', marginBottom: '0.25rem' }}>操作来源</div>
                <div style={{ fontWeight: '500' }}>{showDetail.source}</div>
              </div>

              <div style={{ borderTop: '1px solid #e5e7eb', paddingTop: '1rem' }}>
                <div style={{ fontSize: '0.875rem', fontWeight: '500', marginBottom: '0.75rem' }}>变更详情</div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                  {showDetail.changes.map((change, idx) => (
                    <div key={idx} style={{
                      padding: '1rem',
                      background: '#f9fafb',
                      borderRadius: '8px',
                      border: '1px solid #e5e7eb',
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
                        <span style={{ fontFamily: 'monospace', fontWeight: '600', color: '#1f2937' }}>{change.key}</span>
                      </div>
                      {change.oldValue && change.newValue && (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.875rem' }}>
                          <span style={{
                            padding: '0.25rem 0.5rem',
                            background: '#fee2e2',
                            color: '#991b1b',
                            borderRadius: '4px',
                            textDecoration: 'line-through',
                          }}>
                            {change.oldValue}
                          </span>
                          <span style={{ color: '#6b7280', margin: '0 0.25rem' }}>→</span>
                          <span style={{
                            padding: '0.25rem 0.5rem',
                            background: '#dcfce7',
                            color: '#166534',
                            borderRadius: '4px',
                            fontWeight: '500',
                          }}>
                            {change.newValue}
                          </span>
                        </div>
                      )}
                      {!change.oldValue && change.newValue && (
                        <div style={{ fontSize: '0.875rem' }}>
                          <span style={{ color: '#6b7280' }}>新值: </span>
                          <span style={{
                            padding: '0.25rem 0.5rem',
                            background: '#dcfce7',
                            color: '#166534',
                            borderRadius: '4px',
                            fontWeight: '500',
                          }}>
                            {change.newValue}
                          </span>
                        </div>
                      )}
                      {change.oldValue && !change.newValue && (
                        <div style={{ fontSize: '0.875rem' }}>
                          <span style={{ color: '#6b7280' }}>已删除: </span>
                          <span style={{
                            padding: '0.25rem 0.5rem',
                            background: '#fee2e2',
                            color: '#991b1b',
                            borderRadius: '4px',
                            textDecoration: 'line-through',
                          }}>
                            {change.oldValue}
                          </span>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              <div style={{ marginTop: '1.5rem', display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
                <button className="btn btn-secondary" onClick={() => setShowDetail(null)}>关闭</button>
                <button className="btn btn-primary">回滚到此版本</button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AuditLogs;
