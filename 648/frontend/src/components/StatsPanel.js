import React from 'react';

function StatsPanel({ stats }) {
  if (!stats) return null;

  const statItems = [
    {
      label: '总事件数',
      value: stats.stats?.TotalEvents || 0,
      type: 'primary'
    },
    {
      label: '处理成功',
      value: stats.stats?.ProcessedEvents || 0,
      type: 'success'
    },
    {
      label: '处理失败',
      value: stats.stats?.FailedEvents || 0,
      type: 'error'
    },
    {
      label: '等待重试',
      value: stats.retry_pending || 0,
      type: 'warning'
    },
    {
      label: '过期事件',
      value: stats.stats?.ExpiredEvents || 0,
      type: ''
    },
    {
      label: '删除事件',
      value: stats.stats?.DeletedEvents || 0,
      type: ''
    },
    {
      label: '新增事件',
      value: stats.stats?.SetEvents || 0,
      type: ''
    }
  ];

  return (
    <div className="stats-grid">
      {statItems.map((item, index) => (
        <div key={index} className={`stat-card ${item.type}`}>
          <div className="label">{item.label}</div>
          <div className="value">{item.value}</div>
        </div>
      ))}
    </div>
  );
}

export default StatsPanel;
