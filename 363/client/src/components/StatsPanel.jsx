import React, { useState, useEffect } from 'react';
import axios from 'axios';

const TYPE_LABELS = {
  compile: { label: '编译', icon: '⚙️', color: '#3b82f6' },
  test: { label: '测试', icon: '🧪', color: '#10b981' },
  build: { label: '构建', icon: '📦', color: '#f59e0b' },
  deploy: { label: '部署', icon: '🚀', color: '#ef4444' }
};

export default function StatsPanel({ isOpen, onClose }) {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);

  const loadStats = async () => {
    setLoading(true);
    try {
      const res = await axios.get('/api/stats');
      setStats(res.data);
    } catch (error) {
      console.error('加载统计失败:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      loadStats();
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const formatDuration = (seconds) => {
    if (seconds < 60) return `${seconds}s`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
    return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
  };

  return (
    <div className="stats-panel">
      <div className="stats-panel-header">
        <div className="stats-panel-title">📊 执行统计</div>
        <div>
          <button className="btn btn-secondary" onClick={loadStats} style={{ marginRight: '8px' }}>
            刷新
          </button>
          <button className="btn btn-secondary" onClick={onClose}>
            关闭
          </button>
        </div>
      </div>

      <div className="stats-panel-body">
        {loading ? (
          <div style={{ textAlign: 'center', padding: '40px', color: '#94a3b8' }}>
            加载中...
          </div>
        ) : stats ? (
          <>
            <div className="stats-overview">
              <div className="stat-card">
                <div className="stat-card-value">{stats.totalRuns}</div>
                <div className="stat-card-label">总执行次数</div>
              </div>
              <div className="stat-card" style={{ borderColor: '#10b981' }}>
                <div className="stat-card-value" style={{ color: '#10b981' }}>
                  {(stats.successRate * 100).toFixed(1)}%
                </div>
                <div className="stat-card-label">总体成功率</div>
              </div>
            </div>

            <div className="stats-section">
              <div className="stats-section-title">📈 各类型任务分析</div>
              <div className="stats-grid">
                {Object.entries(stats.byType || {}).map(([type, data]) => (
                  <div key={type} className="type-stat-card">
                    <div className="type-stat-header">
                      <span style={{ fontSize: '20px' }}>{TYPE_LABELS[type]?.icon || '📋'}</span>
                      <span style={{ fontWeight: '600' }}>{TYPE_LABELS[type]?.label || type}</span>
                    </div>
                    <div className="type-stat-row">
                      <span>执行次数</span>
                      <span style={{ fontWeight: '600' }}>{data.count}</span>
                    </div>
                    <div className="type-stat-row">
                      <span>成功次数</span>
                      <span style={{ fontWeight: '600', color: '#10b981' }}>{data.successCount}</span>
                    </div>
                    <div className="type-stat-row">
                      <span>成功率</span>
                      <span style={{ fontWeight: '600', color: data.count > 0 ? (data.successCount / data.count >= 0.9 ? '#10b981' : '#f59e0b') : '#94a3b8' }}>
                        {data.count > 0 ? ((data.successCount / data.count) * 100).toFixed(1) : 0}%
                      </span>
                    </div>
                    <div className="type-stat-row">
                      <span>平均耗时</span>
                      <span style={{ fontWeight: '600' }}>{formatDuration(data.avgDuration || 0)}</span>
                    </div>
                    <div className="type-stat-bar">
                      <div 
                        className="type-stat-bar-fill"
                        style={{
                          width: data.count > 0 ? `${(data.successCount / data.count) * 100}%` : '0%',
                          backgroundColor: TYPE_LABELS[type]?.color || '#6366f1'
                        }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="stats-section">
              <div className="stats-section-title">🕐 最近执行</div>
              <div className="recent-runs">
                {stats.recentRuns?.map((run, index) => (
                  <div key={index} className="recent-run-item">
                    <div style={{
                      width: '8px',
                      height: '8px',
                      borderRadius: '50%',
                      backgroundColor: run.status === 'success' ? '#10b981' : '#ef4444',
                      marginRight: '12px'
                    }} />
                    <div style={{ flex: 1 }}>
                      <div style={{ fontWeight: '500' }}>{run.name}</div>
                      <div style={{ fontSize: '12px', color: '#94a3b8' }}>
                        {new Date(run.startedAt).toLocaleString()} · {formatDuration(run.duration)}
                      </div>
                    </div>
                    <span style={{
                      padding: '2px 8px',
                      borderRadius: '4px',
                      fontSize: '12px',
                      backgroundColor: run.status === 'success' ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)',
                      color: run.status === 'success' ? '#10b981' : '#ef4444'
                    }}>
                      {run.status === 'success' ? '成功' : '失败'}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </>
        ) : null}
      </div>
    </div>
  );
}
