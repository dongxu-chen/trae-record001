import React from 'react';
import { Box, ArrowUpCircle, ArrowDownCircle, MinusCircle, DollarSign, Zap } from 'lucide-react';

export default function DeploymentCard({ result, onClick, selected }) {
  if (!result) return null;

  const r = result;
  const direction = r.recommendedReplicas > r.currentReplicas ? 'up' :
    r.recommendedReplicas < r.currentReplicas ? 'down' : 'none';
  const hpa = r.hpaRecommendation || {};
  const cost = r.costAnalysis || {};

  const ArrowIcon = direction === 'up' ? ArrowUpCircle : direction === 'down' ? ArrowDownCircle : MinusCircle;
  const arrowColor = direction === 'up' ? '#ef4444' : direction === 'down' ? '#10b981' : '#64748b';

  return (
    <div
      className="card"
      onClick={onClick}
      style={{
        cursor: 'pointer',
        border: selected ? '2px solid #3b82f6' : '1px solid #334155',
        transition: 'all 0.2s',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 }}>
        <div>
          <div style={{ fontSize: 16, fontWeight: 600, color: '#f1f5f9', marginBottom: 2 }}>
            {r.deployment}
          </div>
          <div style={{ fontSize: 12, color: '#64748b' }}>{r.namespace}</div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 4, color: arrowColor }}>
            <ArrowIcon size={18} />
            <span style={{ fontSize: 13, fontWeight: 600 }}>
              {r.currentReplicas} → {r.recommendedReplicas}
            </span>
          </div>
        </div>
      </div>

      <div className="grid-4" style={{ marginBottom: 16 }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 20, fontWeight: 700, color: '#3b82f6' }}>{r.currentReplicas}</div>
          <div style={{ fontSize: 10, color: '#64748b', textTransform: 'uppercase' }}>Replicas</div>
        </div>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 20, fontWeight: 700, color: '#8b5cf6' }}>{hpa.score ? hpa.score.toFixed(0) : '-'}</div>
          <div style={{ fontSize: 10, color: '#64748b', textTransform: 'uppercase' }}>Score</div>
        </div>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 20, fontWeight: 700, color: '#10b981' }}>${(cost.totalMonthlyCost || 0).toFixed(0)}</div>
          <div style={{ fontSize: 10, color: '#64748b', textTransform: 'uppercase' }}>Mo Cost</div>
        </div>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 20, fontWeight: 700, color: '#f59e0b' }}>${(cost.potentialSavings || 0).toFixed(0)}</div>
          <div style={{ fontSize: 10, color: '#64748b', textTransform: 'uppercase' }}>Savings</div>
        </div>
      </div>

      {hpa.metrics && hpa.metrics.length > 0 && (
        <div style={{ display: 'flex', gap: 8 }}>
          {hpa.metrics.slice(0, 4).map((m, i) => {
            const pct = Math.min((m.currentUtilization / m.targetUtilization) * 100, 100);
            const color = pct > 85 ? '#ef4444' : pct > 65 ? '#f59e0b' : '#10b981';
            return (
              <div key={i} style={{ flex: 1 }}>
                <div style={{ fontSize: 10, color: '#64748b', marginBottom: 4 }}>{m.type}</div>
                <div className="progress-bar" style={{ height: 6 }}>
                  <div className="progress-bar-fill" style={{ width: `${pct}%`, background: color, height: 6 }} />
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
