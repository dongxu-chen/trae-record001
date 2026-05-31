import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { mockData } from '../services/api';

const Dashboard = () => {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setTimeout(() => {
      setSummary({
        summary: mockData.summary,
        violationsByType: mockData.violationsByType,
        violationsBySeverity: mockData.violationsBySeverity,
        violationsByAccount: mockData.violationsByAccount,
      });
      setLoading(false);
    }, 500);
  }, []);

  if (loading) {
    return (
      <div className="card">
        <div style={{ textAlign: 'center', padding: '3rem' }}>加载中...</div>
      </div>
    );
  }

  return (
    <div>
      <h1 style={{ marginBottom: '1.5rem', fontSize: '1.75rem', fontWeight: '700' }}>仪表盘</h1>

      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-value stat-total">{summary.summary.totalResources}</div>
          <div className="stat-label">资源总数</div>
        </div>
        <div className="stat-card">
          <div className="stat-value stat-compliant">{summary.summary.compliant}</div>
          <div className="stat-label">合规资源</div>
        </div>
        <div className="stat-card">
          <div className="stat-value stat-noncompliant">{summary.summary.nonCompliant}</div>
          <div className="stat-label">不合规资源</div>
        </div>
        <div className="stat-card">
          <div className="stat-value stat-rate">{summary.summary.complianceRate.toFixed(1)}%</div>
          <div className="stat-label">合规率</div>
        </div>
      </div>

      <div className="charts-grid">
        <div className="chart-container">
          <div className="chart-title">违规按资源类型分布</div>
          <div style={{ height: '200px', display: 'flex', alignItems: 'flex-end', gap: '1rem', padding: '1rem 0' }}>
            {Object.entries(summary.violationsByType).map(([type, count]) => (
              <div key={type} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                <div
                  style={{
                    width: '100%',
                    backgroundColor: type === 'ECS' ? '#3b82f6' : type === 'RDS' ? '#10b981' : '#f59e0b',
                    height: `${(count / Math.max(...Object.values(summary.violationsByType))) * 150}px`,
                    borderRadius: '4px 4px 0 0',
                    marginBottom: '0.5rem',
                    minHeight: '4px',
                  }}
                />
                <span style={{ fontSize: '0.875rem', fontWeight: '500' }}>{type}</span>
                <span style={{ fontSize: '0.75rem', color: '#6b7280' }}>{count} 违规</span>
              </div>
            ))}
          </div>
        </div>

        <div className="chart-container">
          <div className="chart-title">违规按严重程度分布</div>
          <div style={{ padding: '0.5rem 0' }}>
            {Object.entries(summary.violationsBySeverity).map(([severity, count]) => (
              <div key={severity} style={{ marginBottom: '1rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
                  <span className={`badge badge-${severity}`} style={{ textTransform: 'capitalize' }}>
                    {severity === 'high' ? '高' : severity === 'medium' ? '中' : '低'}
                  </span>
                  <span style={{ fontWeight: '600' }}>{count} 项</span>
                </div>
                <div style={{ height: '8px', backgroundColor: '#e5e7eb', borderRadius: '4px', overflow: 'hidden' }}>
                  <div
                    style={{
                      width: `${(count / summary.summary.totalViolations) * 100}%`,
                      height: '100%',
                      backgroundColor: severity === 'high' ? '#ef4444' : severity === 'medium' ? '#f59e0b' : '#3b82f6',
                      borderRadius: '4px',
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="chart-container">
          <div className="chart-title">违规按账号分布</div>
          <div style={{ padding: '0.5rem 0' }}>
            {Object.entries(summary.violationsByAccount).map(([account, count], index) => (
              <div key={account} style={{ marginBottom: '1rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
                  <span style={{ fontWeight: '500' }}>{account}</span>
                  <span style={{ fontWeight: '600' }}>{count} 项</span>
                </div>
                <div style={{ height: '8px', backgroundColor: '#e5e7eb', borderRadius: '4px', overflow: 'hidden' }}>
                  <div
                    style={{
                      width: `${(count / summary.summary.totalViolations) * 100}%`,
                      height: '100%',
                      backgroundColor: ['#8b5cf6', '#06b6d4'][index % 2],
                      borderRadius: '4px',
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="card" style={{ marginTop: '1.5rem' }}>
        <div className="card-header">
          <span>快速操作</span>
        </div>
        <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
          <Link to="/resources" className="btn btn-primary" style={{ textDecoration: 'none' }}>
            查看所有资源
          </Link>
          <Link to="/compliance" className="btn btn-success" style={{ textDecoration: 'none' }}>
            执行合规检查
          </Link>
          <Link to="/rules" className="btn btn-secondary" style={{ textDecoration: 'none' }}>
            管理合规规则
          </Link>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
