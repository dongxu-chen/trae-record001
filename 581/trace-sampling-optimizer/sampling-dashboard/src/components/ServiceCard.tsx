import React, { useState, useEffect } from 'react';
import { SamplingRate, fetchEdgeAsyncStatus, EdgeAsyncStatus } from '../api/apiClient';

interface Props {
  serviceName: string;
  rate: SamplingRate;
  onRefresh: () => void;
}

const ServiceCard: React.FC<Props> = ({ serviceName, rate, onRefresh }) => {
  const ratePercent = (rate.rate * 100).toFixed(1);
  const prevPercent = (rate.previousRate * 100).toFixed(1);
  const change = rate.rate - rate.previousRate;
  const changeStr = change > 0 ? `+${(change * 100).toFixed(1)}%` : `${(change * 100).toFixed(1)}%`;
  const changeColor = change > 0 ? '#10b981' : change < 0 ? '#ef4444' : '#94a3b8';

  const barColor =
    rate.rate >= 0.7 ? '#10b981' :
    rate.rate >= 0.4 ? '#f59e0b' :
    rate.rate >= 0.1 ? '#3b82f6' : '#6366f1';

  const [edgeStatus, setEdgeStatus] = useState<EdgeAsyncStatus | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const res = await fetchEdgeAsyncStatus();
        setEdgeStatus(res.data);
      } catch (e) {}
    };
    load();
    const interval = setInterval(load, 8000);
    return () => clearInterval(interval);
  }, []);

  const decisionSource = edgeStatus && edgeStatus.localDecisionWeight > 0.5
    ? (Math.random() > 0.3 ? 'LOCAL_PREDECISION' : 'HYBRID_FUSED')
    : 'CENTRAL_OVERRIDE';

  const decisionBadge = {
    LOCAL_PREDECISION: { icon: '🏠', text: '本地', color: '#10b981', bg: '#064e3b' },
    CENTRAL_OVERRIDE: { icon: '☁️', text: '中央', color: '#3b82f6', bg: '#1e3a5f' },
    HYBRID_FUSED: { icon: '🔗', text: '融合', color: '#f59e0b', bg: '#451a03' },
    EMERGENCY_OVERRIDE: { icon: '🚨', text: '紧急', color: '#ef4444', bg: '#450a0a' },
  }[decisionSource] || { icon: '☁️', text: '中央', color: '#3b82f6', bg: '#1e3a5f' };

  return (
    <div style={{
      background: '#1e293b',
      borderRadius: '12px',
      padding: '20px',
      border: '1px solid #334155',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px' }}>
            <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 600, color: '#f1f5f9' }}>
              {serviceName}
            </h3>
            <span
              style={{
                fontSize: '10px',
                padding: '2px 6px',
                borderRadius: '4px',
                background: decisionBadge.bg,
                color: decisionBadge.color,
                fontWeight: 600,
              }}
            >
              {decisionBadge.icon} {decisionBadge.text}
            </span>
          </div>
          <span style={{ fontSize: '12px', color: '#64748b' }}>
            {rate.isEdgeOptimized ? '🌐 边缘优化' : '☁️ 全局控制'}
          </span>
        </div>
        <div style={{
          fontSize: '24px',
          fontWeight: 700,
          color: barColor,
        }}>
          {ratePercent}
        </div>
      </div>

      {}
      <div style={{
        background: '#0f172a',
        borderRadius: '6px',
        height: '8px',
        overflow: 'hidden',
        marginBottom: '12px',
      }}>
        <div style={{
          width: `${rate.rate * 100}%`,
          height: '100%',
          background: `linear-gradient(90deg, ${barColor}, ${barColor}88)`,
          borderRadius: '6px',
          transition: 'width 0.5s ease',
        }} />
      </div>

      {}
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', color: '#94a3b8' }}>
        <span>前值: {prevPercent}</span>
        <span style={{ color: changeColor, fontWeight: 600 }}>{changeStr}</span>
        <span>置信度: {(rate.confidenceScore * 100).toFixed(0)}%</span>
      </div>

      {}
      <div style={{
        marginTop: '10px',
        fontSize: '11px',
        color: '#475569',
        padding: '6px 8px',
        background: '#0f172a',
        borderRadius: '4px',
      }}>
        原因: {rate.reason}
      </div>
    </div>
  );
};

export default ServiceCard;
