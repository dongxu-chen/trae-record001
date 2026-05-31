import React, { useState, useEffect } from 'react';

const mockCostData = {
  reportDate: '2026-05-29',
  totalDailyCost: 1250.50,
  totalMonthlyCost: 37515.00,
  currency: 'CNY',
  byEnvironment: [
    { tagKey: 'Environment', tagValue: 'Production', resourceCount: 8, totalDailyCost: 875.35, totalMonthlyCost: 26260.50, percentage: 70.0 },
    { tagKey: 'Environment', tagValue: 'Development', resourceCount: 10, totalDailyCost: 325.15, totalMonthlyCost: 9754.50, percentage: 26.0 },
    { tagKey: 'Environment', tagValue: 'Testing', resourceCount: 2, totalDailyCost: 50.00, totalMonthlyCost: 1500.00, percentage: 4.0 },
  ],
  byDepartment: [
    { tagKey: 'Department', tagValue: 'Engineering', resourceCount: 12, totalDailyCost: 850.00, totalMonthlyCost: 25500.00, percentage: 68.0 },
    { tagKey: 'Department', tagValue: 'Finance', resourceCount: 3, totalDailyCost: 200.50, totalMonthlyCost: 6015.00, percentage: 16.0 },
    { tagKey: 'Department', tagValue: 'Sales', resourceCount: 2, totalDailyCost: 100.00, totalMonthlyCost: 3000.00, percentage: 8.0 },
    { tagKey: 'Department', tagValue: 'HR', resourceCount: 1, totalDailyCost: 50.00, totalMonthlyCost: 1500.00, percentage: 4.0 },
  ],
  byCostCenter: [
    { tagKey: 'CostCenter', tagValue: 'CC100', resourceCount: 8, totalDailyCost: 875.35, totalMonthlyCost: 26260.50, percentage: 70.0 },
    { tagKey: 'CostCenter', tagValue: 'CC200', resourceCount: 10, totalDailyCost: 325.15, totalMonthlyCost: 9754.50, percentage: 26.0 },
    { tagKey: 'CostCenter', tagValue: 'CC300', resourceCount: 2, totalDailyCost: 50.00, totalMonthlyCost: 1500.00, percentage: 4.0 },
  ],
  byProject: [
    { tagKey: 'Project', tagValue: 'API-Gateway', resourceCount: 5, totalDailyCost: 450.00, totalMonthlyCost: 13500.00, percentage: 36.0 },
    { tagKey: 'Project', tagValue: 'Web-Frontend', resourceCount: 4, totalDailyCost: 320.50, totalMonthlyCost: 9615.00, percentage: 25.6 },
    { tagKey: 'Project', tagValue: 'Data-Analytics', resourceCount: 6, totalDailyCost: 380.00, totalMonthlyCost: 11400.00, percentage: 30.4 },
  ],
  untagged: {
    tagKey: 'Untagged',
    tagValue: 'Resources without required tags',
    resourceCount: 1,
    totalDailyCost: 25.00,
    totalMonthlyCost: 750.00,
    percentage: 2.0,
  },
  trend: {
    labels: ['5/23', '5/24', '5/25', '5/26', '5/27', '5/28', '5/29'],
    data: [1180, 1210, 1240, 1200, 1230, 1260, 1250.50],
  },
  forecast: [37515, 38265, 39030],
};

const CostAllocation = () => {
  const [activeView, setActiveView] = useState('overview');
  const [selectedTag, setSelectedTag] = useState('Environment');
  const [loading, setLoading] = useState(false);

  const tagViews = [
    { key: 'Environment', label: '按环境', icon: '🌍' },
    { key: 'Department', label: '按部门', icon: '🏢' },
    { key: 'CostCenter', label: '按成本中心', icon: '💰' },
    { key: 'Project', label: '按项目', icon: '📋' },
  ];

  const getTagData = (tagKey) => {
    const key = 'by' + tagKey;
    return mockCostData[key] || [];
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('zh-CN', {
      style: 'currency',
      currency: 'CNY',
      minimumFractionDigits: 2,
    }).format(amount);
  };

  const getProgressColor = (percentage) => {
    if (percentage >= 50) return '#ef4444';
    if (percentage >= 20) return '#f59e0b';
    return '#3b82f6';
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>💰 标签成本分摊</h1>
          <p className="page-subtitle">按标签维度汇总和分析云资源费用</p>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button className="btn btn-secondary">导出报表</button>
          <button className="btn btn-primary">刷新数据</button>
        </div>
      </div>

      <div className="stats-grid" style={{ gridTemplateColumns: 'repeat(4, 1fr)', marginBottom: '1.5rem' }}>
        <div className="stat-card">
          <div className="stat-value" style={{ color: '#3b82f6' }}>{formatCurrency(mockCostData.totalDailyCost)}</div>
          <div className="stat-label">今日费用</div>
          <div className="stat-change" style={{ color: '#10b981' }}>↑ 3.2%</div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{ color: '#8b5cf6' }}>{formatCurrency(mockCostData.totalMonthlyCost)}</div>
          <div className="stat-label">本月费用</div>
          <div className="stat-change" style={{ color: '#10b981' }}>↑ 5.1%</div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{ color: '#10b981' }}>20</div>
          <div className="stat-label">资源总数</div>
          <div className="stat-change">已打标: 95%</div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{ color: mockCostData.untagged.percentage > 5 ? '#ef4444' : '#f59e0b' }}>
            {mockCostData.untagged.percentage}%
          </div>
          <div className="stat-label">未打标占比</div>
          <div className="stat-change">{mockCostData.untagged.resourceCount} 个资源</div>
        </div>
      </div>

      <div className="card" style={{ marginBottom: '1.5rem' }}>
        <div className="card-header">
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            {tagViews.map((view) => (
              <button
                key={view.key}
                className={`btn ${selectedTag === view.key ? 'btn-primary' : 'btn-secondary'}`}
                style={{ padding: '0.5rem 1rem', fontSize: '0.875rem' }}
                onClick={() => setSelectedTag(view.key)}
              >
                {view.icon} {view.label}
              </button>
            ))}
          </div>
        </div>
        <div style={{ padding: '1.5rem' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {getTagData(selectedTag).map((item, index) => (
              <div
                key={item.tagValue}
                style={{
                  padding: '1rem',
                  border: '1px solid #e5e7eb',
                  borderRadius: '8px',
                  background: '#fafafa',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                  <div>
                    <span style={{ fontWeight: '600', color: '#111827', fontSize: '1rem' }}>{item.tagValue}</span>
                    <span style={{ marginLeft: '0.75rem', fontSize: '0.875rem', color: '#6b7280' }}>
                      {item.resourceCount} 个资源
                    </span>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontWeight: '600', color: '#111827' }}>{formatCurrency(item.totalMonthlyCost)}</div>
                    <div style={{ fontSize: '0.75rem', color: '#6b7280' }}>/月</div>
                  </div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                  <div style={{ flex: 1, height: '10px', background: '#e5e7eb', borderRadius: '5px', overflow: 'hidden' }}>
                    <div
                      style={{
                        width: `${item.percentage}%`,
                        height: '100%',
                        background: getProgressColor(item.percentage),
                        transition: 'width 0.5s',
                      }}
                    />
                  </div>
                  <span style={{ fontWeight: '600', color: '#374151', minWidth: '50px', textAlign: 'right' }}>
                    {item.percentage}%
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '0.5rem', fontSize: '0.8rem', color: '#6b7280' }}>
                  <span>日均: {formatCurrency(item.totalDailyCost)}</span>
                  <span>占总费用</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
        <div className="card">
          <div className="card-header">📈 费用趋势 (近7天)</div>
          <div style={{ padding: '1.5rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', height: '150px', gap: '0.5rem' }}>
              {mockCostData.trend.data.map((value, i) => {
                const maxVal = Math.max(...mockCostData.trend.data);
                const height = (value / maxVal) * 100;
                return (
                  <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                    <div style={{ fontSize: '0.7rem', color: '#6b7280', marginBottom: '0.25rem' }}>
                      ¥{value.toFixed(0)}
                    </div>
                    <div
                      style={{
                        width: '100%',
                        height: `${height}%`,
                        background: 'linear-gradient(to top, #3b82f6, #60a5fa)',
                        borderRadius: '4px 4px 0 0',
                        minHeight: '4px',
                      }}
                    />
                    <div style={{ fontSize: '0.75rem', color: '#6b7280', marginTop: '0.5rem' }}>
                      {mockCostData.trend.labels[i]}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-header">🔮 费用预测 (未来3月)</div>
          <div style={{ padding: '1.5rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-around', alignItems: 'flex-end', height: '150px' }}>
              {mockCostData.forecast.map((value, i) => (
                <div key={i} style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: '0.75rem', fontWeight: '600', color: '#8b5cf6', marginBottom: '0.5rem' }}>
                    {formatCurrency(value)}
                  </div>
                  <div
                    style={{
                      width: '60px',
                      height: `${(value / mockCostData.forecast[2]) * 120}px`,
                      background: 'linear-gradient(to top, #8b5cf6, #a78bfa)',
                      borderRadius: '8px',
                      opacity: 0.6 + i * 0.15,
                    }}
                  />
                  <div style={{ fontSize: '0.8rem', color: '#6b7280', marginTop: '0.5rem' }}>
                    第{i + 1}月
                  </div>
                </div>
              ))}
            </div>
            <div style={{ textAlign: 'center', marginTop: '1rem', fontSize: '0.8rem', color: '#6b7280' }}>
              预计每月增长约 2%
            </div>
          </div>
        </div>
      </div>

      {mockCostData.untagged && mockCostData.untagged.resourceCount > 0 && (
        <div className="card" style={{ marginTop: '1.5rem', borderLeft: '4px solid #f59e0b' }}>
          <div className="card-header">⚠️ 未正确打标的资源</div>
          <div style={{ padding: '1.5rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <div style={{ fontWeight: '500', color: '#111827' }}>
                  发现 {mockCostData.untagged.resourceCount} 个资源缺少关键标签
                </div>
                <div style={{ fontSize: '0.875rem', color: '#6b7280', marginTop: '0.25rem' }}>
                  月度费用: {formatCurrency(mockCostData.untagged.totalMonthlyCost)} ({mockCostData.untagged.percentage}% 总费用)
                </div>
              </div>
              <button className="btn btn-primary">立即修复</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default CostAllocation;
