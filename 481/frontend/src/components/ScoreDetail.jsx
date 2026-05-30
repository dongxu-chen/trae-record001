import React from 'react';

const DIMENSION_LABELS = {
  duration: '执行时长',
  success_rate: '成功率',
  frequency: '执行频率',
  resource: '资源消耗',
};

function getScoreClass(score) {
  if (score >= 90) return 'healthy';
  if (score >= 80) return 'good';
  if (score >= 60) return 'warning';
  if (score >= 40) return 'poor';
  return 'critical';
}

export default function ScoreDetail({ score }) {
  if (!score) return null;

  return (
    <div className="card">
      <div className="card-title">
        🔍 评分详情 — {score.taskName}
      </div>
      <div className="dimension-bars">
        {score.dimensions?.map(dim => (
          <div key={dim.name} className="dimension-row">
            <div className="dimension-header">
              <span className="dimension-label">
                {DIMENSION_LABELS[dim.name] || dim.name}
                <span style={{ color: 'var(--text-muted)', fontSize: 11, marginLeft: 8 }}>
                  (权重 {Math.round(dim.weight * 100)}%)
                </span>
              </span>
              <span className={`dimension-score ${getScoreClass(dim.score)}`}>
                {dim.score}
              </span>
            </div>
            <div className="dimension-bar-bg">
              <div
                className={`dimension-bar-fill ${getScoreClass(dim.score)}`}
                style={{ width: `${dim.score}%` }}
              />
            </div>
          </div>
        ))}
      </div>
      <div style={{ marginTop: 20, padding: '14px 16px', background: 'var(--bg-primary)', borderRadius: 10, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ color: 'var(--text-secondary)', fontSize: 14 }}>综合健康度评分</span>
        <span style={{ fontSize: 28, fontWeight: 700, color: `var(--accent-${getScoreClass(score.overallScore) === 'healthy' ? 'green' : getScoreClass(score.overallScore) === 'good' ? 'blue' : getScoreClass(score.overallScore) === 'warning' ? 'yellow' : getScoreClass(score.overallScore) === 'poor' ? 'orange' : 'red'})` }}>
          {score.overallScore}
        </span>
      </div>
    </div>
  );
}
