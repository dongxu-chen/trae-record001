import React from 'react';
import { Card, Tag, Progress, Tooltip } from 'antd';
import {
  FireOutlined,
  RocketOutlined,
  LineChartOutlined,
  AlertOutlined,
  ClockCircleOutlined,
  StockOutlined
} from '@ant-design/icons';
import { HotPrediction } from '../types';

interface HotProductPredictionProps {
  predictions: HotPrediction[];
}

const levelConfig: Record<string, { label: string; color: string; icon: React.ReactNode; bg: string }> = {
  explosive: {
    label: '即将爆单',
    color: '#ff4d4f',
    icon: <RocketOutlined />,
    bg: 'rgba(255, 77, 79, 0.12)'
  },
  rising: {
    label: '上升趋势',
    color: '#faad14',
    icon: <LineChartOutlined />,
    bg: 'rgba(250, 173, 20, 0.12)'
  },
  potential: {
    label: '潜力商品',
    color: '#48dbfb',
    icon: <FireOutlined />,
    bg: 'rgba(72, 219, 251, 0.12)'
  },
  stable: {
    label: '稳定销售',
    color: '#8c8c8c',
    icon: <StockOutlined />,
    bg: 'rgba(140, 140, 140, 0.08)'
  }
};

const metricLabels: Record<string, { label: string; color: string }> = {
  click_velocity: { label: '点击增速', color: '#48dbfb' },
  order_velocity: { label: '订单增速', color: '#52c41a' },
  click_acceleration: { label: '点击加速度', color: '#feca57' },
  order_acceleration: { label: '订单加速度', color: '#ff9ff3' },
  sentiment_momentum: { label: '情感动量', color: '#ff6b6b' }
};

export const HotProductPrediction: React.FC<HotProductPredictionProps> = ({ predictions }) => {
  const hotItems = predictions.filter(p => p.prediction_level !== 'stable');
  const allItems = predictions;

  return (
    <Card
      title={
        <span>
          <RocketOutlined /> 爆款预测
          {hotItems.length > 0 && (
            <Tag color="red" style={{ marginLeft: '8px', fontSize: '10px' }}>
              {hotItems.length}个预爆
            </Tag>
          )}
        </span>
      }
      className="card-dark"
    >
      <div className="prediction-legend">
        {Object.entries(levelConfig).map(([key, cfg]) => (
          <span key={key} className="prediction-legend-item">
            <span className="legend-dot" style={{ background: cfg.color }}></span>
            <span style={{ color: cfg.color, fontSize: '10px' }}>{cfg.label}</span>
          </span>
        ))}
      </div>

      <div className="prediction-list">
        {allItems.map((pred) => {
          const cfg = levelConfig[pred.prediction_level] || levelConfig.stable;
          const isHot = pred.prediction_level !== 'stable';

          return (
            <div
              key={pred.id}
              className={`prediction-card ${isHot ? 'prediction-hot' : ''}`}
              style={{ borderLeft: `3px solid ${cfg.color}` }}
            >
              <div className="prediction-header-row">
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span style={{ fontWeight: 600, color: '#fff', fontSize: '13px' }}>{pred.name}</span>
                    <Tag
                      icon={cfg.icon}
                      color={pred.prediction_level === 'explosive' ? 'error' : pred.prediction_level === 'rising' ? 'warning' : 'processing'}
                      style={{ fontSize: '10px', padding: '0 4px', lineHeight: '16px', margin: 0 }}
                    >
                      {cfg.label}
                    </Tag>
                  </div>
                  <div style={{ fontSize: '11px', color: 'rgba(255,255,255,0.4)', marginTop: '2px' }}>
                    {pred.category} · ¥{pred.price} · 库存{pred.stock}
                  </div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div className="hot-score-value" style={{ color: cfg.color }}>
                    {pred.hot_score}
                  </div>
                  <div style={{ fontSize: '9px', color: 'rgba(255,255,255,0.4)' }}>爆款指数</div>
                </div>
              </div>

              <div className="prediction-score-bar">
                <Progress
                  percent={Math.min(Math.round(pred.hot_score), 100)}
                  size="small"
                  strokeColor={cfg.color}
                  trailColor="rgba(255,255,255,0.06)"
                  showInfo={false}
                />
              </div>

              <div className="prediction-metrics-grid">
                {Object.entries(pred.metrics).map(([key, value]) => {
                  const mc = metricLabels[key];
                  const normVal = Math.min(Math.abs(value) / 5 * 100, 100);
                  return (
                    <Tooltip key={key} title={`${mc.label}: ${value}`}>
                      <div className="prediction-metric-item">
                        <div style={{ fontSize: '9px', color: 'rgba(255,255,255,0.4)' }}>{mc.label}</div>
                        <div className="metric-bar-track">
                          <div
                            className="metric-bar-fill"
                            style={{
                              width: `${normVal}%`,
                              background: value >= 0 ? mc.color : '#ff4d4f'
                            }}
                          />
                        </div>
                      </div>
                    </Tooltip>
                  );
                })}
              </div>

              <div className="prediction-footer">
                {pred.estimated_peak_minutes && (
                  <span className="prediction-peak">
                    <ClockCircleOutlined /> 预计{pred.estimated_peak_minutes}分钟后达峰
                  </span>
                )}
                {pred.stock_burn_rate > 0 && (
                  <span className="prediction-burn">
                    消耗速率 {pred.stock_burn_rate}/分钟
                  </span>
                )}
              </div>

              <div className="prediction-recommendation" style={{ color: cfg.color, fontSize: '11px' }}>
                {pred.recommendation}
              </div>
            </div>
          );
        })}
      </div>
    </Card>
  );
};
