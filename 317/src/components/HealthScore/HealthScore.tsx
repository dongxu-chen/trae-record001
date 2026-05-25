import React from 'react';
import { HealthScore as HealthScoreType } from '../../types';
import './HealthScore.css';

interface HealthScoreProps {
  healthScore: HealthScoreType | null;
}

const getScoreColor = (score: number): string => {
  if (score >= 90) return '#22c55e';
  if (score >= 70) return '#84cc16';
  if (score >= 50) return '#f59e0b';
  if (score >= 30) return '#f97316';
  return '#ef4444';
};

const getScoreStatus = (score: number): string => {
  if (score >= 90) return '优秀';
  if (score >= 70) return '良好';
  if (score >= 50) return '一般';
  if (score >= 30) return '较差';
  return '危险';
};

export const HealthScore: React.FC<HealthScoreProps> = ({ healthScore }) => {
  if (!healthScore) {
    return (
      <div className="health-score-container">
        <div className="health-score-loading">加载中...</div>
      </div>
    );
  }

  const color = getScoreColor(healthScore.overall);
  const status = getScoreStatus(healthScore.overall);
  const circumference = 2 * Math.PI * 45;
  const strokeDashoffset = circumference - (healthScore.overall / 100) * circumference;

  return (
    <div className="health-score-container">
      <h3 className="health-score-title">网络健康评分</h3>
      
      <div className="health-score-main">
        <svg className="score-circle" viewBox="0 0 100 100">
          <circle
            cx="50"
            cy="50"
            r="45"
            fill="none"
            stroke="#1e293b"
            strokeWidth="8"
          />
          <circle
            cx="50"
            cy="50"
            r="45"
            fill="none"
            stroke={color}
            strokeWidth="8"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            transform="rotate(-90 50 50)"
            style={{ transition: 'stroke-dashoffset 0.5s ease' }}
          />
        </svg>
        <div className="score-content">
          <span className="score-value" style={{ color }}>{healthScore.overall.toFixed(1)}</span>
          <span className="score-status" style={{ color }}>{status}</span>
        </div>
      </div>

      <div className="health-score-details">
        <div className="score-item">
          <div className="score-item-label">设备健康</div>
          <div className="score-item-bar">
            <div 
              className="score-item-fill" 
              style={{ 
                width: `${healthScore.deviceScore}%`,
                backgroundColor: getScoreColor(healthScore.deviceScore)
              }}
            />
          </div>
          <div className="score-item-value">{healthScore.deviceScore.toFixed(1)}%</div>
        </div>

        <div className="score-item">
          <div className="score-item-label">链路健康</div>
          <div className="score-item-bar">
            <div 
              className="score-item-fill" 
              style={{ 
                width: `${healthScore.linkScore}%`,
                backgroundColor: getScoreColor(healthScore.linkScore)
              }}
            />
          </div>
          <div className="score-item-value">{healthScore.linkScore.toFixed(1)}%</div>
        </div>

        <div className="score-item">
          <div className="score-item-label">连通性</div>
          <div className="score-item-bar">
            <div 
              className="score-item-fill" 
              style={{ 
                width: `${healthScore.availabilityScore}%`,
                backgroundColor: getScoreColor(healthScore.availabilityScore)
              }}
            />
          </div>
          <div className="score-item-value">{healthScore.availabilityScore.toFixed(1)}%</div>
        </div>
      </div>

      <div className="health-stats-grid">
        <div className="health-stat">
          <span className="stat-icon">📡</span>
          <div className="stat-info">
            <span className="stat-value">{healthScore.details.onlineDevices}/{healthScore.details.totalDevices}</span>
            <span className="stat-label">在线设备</span>
          </div>
        </div>
        <div className="health-stat">
          <span className="stat-icon">🔗</span>
          <div className="stat-info">
            <span className="stat-value">{healthScore.details.upLinks}/{healthScore.details.totalLinks}</span>
            <span className="stat-label">正常链路</span>
          </div>
        </div>
        <div className="health-stat">
          <span className="stat-icon">⏱️</span>
          <div className="stat-info">
            <span className="stat-value">{healthScore.details.avgLatency}ms</span>
            <span className="stat-label">平均延迟</span>
          </div>
        </div>
        <div className="health-stat">
          <span className="stat-icon">📉</span>
          <div className="stat-info">
            <span className="stat-value">{healthScore.details.avgPacketLoss}%</span>
            <span className="stat-label">平均丢包</span>
          </div>
        </div>
        <div className="health-stat">
          <span className="stat-icon">📊</span>
          <div className="stat-info">
            <span className="stat-value">{healthScore.details.avgUtilization}%</span>
            <span className="stat-label">平均利用率</span>
          </div>
        </div>
        <div className="health-stat">
          <span className="stat-icon">⚠️</span>
          <div className="stat-info">
            <span className="stat-value" style={{ color: healthScore.details.activeFaults > 0 ? '#ef4444' : 'inherit' }}>
              {healthScore.details.activeFaults}
            </span>
            <span className="stat-label">活跃故障</span>
          </div>
        </div>
      </div>
    </div>
  );
};
