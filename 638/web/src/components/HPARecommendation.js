import React from 'react';

function DirectionBadge({ direction }) {
  const cls = direction === 'up' ? 'up' : direction === 'down' ? 'down' : 'none';
  const arrow = direction === 'up' ? '↑' : direction === 'down' ? '↓' : '→';
  const label = direction === 'up' ? 'Scale Up' : direction === 'down' ? 'Scale Down' : 'No Change';
  return <span className={`status-badge ${cls}`}>{arrow} {label}</span>;
}

function ScoreRing({ score }) {
  const radius = 36;
  const circ = 2 * Math.PI * radius;
  const offset = circ - (score / 100) * circ;
  const color = score >= 80 ? '#10b981' : score >= 60 ? '#f59e0b' : '#ef4444';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
      <svg width="84" height="84" style={{ transform: 'rotate(-90deg)' }}>
        <circle cx="42" cy="42" r={radius} fill="none" stroke="#334155" strokeWidth="6" />
        <circle cx="42" cy="42" r={radius} fill="none" stroke={color} strokeWidth="6"
          strokeDasharray={circ} strokeDashoffset={offset} strokeLinecap="round" />
      </svg>
      <div style={{ marginTop: -58, fontSize: 18, fontWeight: 700, color }}>
        {score.toFixed(0)}
      </div>
      <div style={{ marginTop: 32, fontSize: 11, color: '#64748b' }}>SCORE</div>
    </div>
  );
}

export default function HPARecommendation({ recommendation }) {
  if (!recommendation) return null;
  const rec = recommendation;

  return (
    <div className="card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h2>HPA Strategy Recommendation</h2>
        <DirectionBadge direction={
          rec.targetReplicas > (rec.minReplicas || 0) ? 'up' :
          rec.targetReplicas < (rec.minReplicas || 0) ? 'down' : 'none'
        } />
      </div>

      <div style={{ display: 'flex', gap: 24, alignItems: 'flex-start' }}>
        <div style={{ flex: 1 }}>
          <div className="grid-3" style={{ marginBottom: 16 }}>
            <div>
              <div style={{ fontSize: 11, color: '#64748b', marginBottom: 4, textTransform: 'uppercase' }}>Min Replicas</div>
              <div style={{ fontSize: 20, fontWeight: 600 }}>{rec.minReplicas}</div>
            </div>
            <div>
              <div style={{ fontSize: 11, color: '#64748b', marginBottom: 4, textTransform: 'uppercase' }}>Target Replicas</div>
              <div style={{ fontSize: 20, fontWeight: 600, color: '#3b82f6' }}>{rec.targetReplicas}</div>
            </div>
            <div>
              <div style={{ fontSize: 11, color: '#64748b', marginBottom: 4, textTransform: 'uppercase' }}>Max Replicas</div>
              <div style={{ fontSize: 20, fontWeight: 600 }}>{rec.maxReplicas}</div>
            </div>
          </div>

          {rec.usedComposite !== undefined && (
            <div style={{ padding: '12px 16px', background: rec.usedComposite ? 'rgba(139, 92, 246, 0.1)' : '#0f172a', borderRadius: 8, marginBottom: 12, border: rec.usedComposite ? '1px solid #8b5cf6' : '1px solid #1e293b' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                <div style={{ fontSize: 11, color: '#64748b', textTransform: 'uppercase' }}>Composite Load Index</div>
                <span className={`status-badge ${rec.usedComposite ? 'up' : 'none'}`}>
                  {rec.usedComposite ? 'Active' : 'Inactive'}
                </span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <div style={{ fontSize: 24, fontWeight: 700, color: rec.usedComposite ? '#8b5cf6' : '#f1f5f9' }}>
                  {(rec.compositeLoad || 0).toFixed(2)}
                </div>
                <div style={{ flex: 1 }}>
                  <div className="progress-bar" style={{ height: 10 }}>
                    <div
                      className="progress-bar-fill"
                      style={{
                        width: `${Math.min((rec.compositeLoad || 0) * 100, 150)}%`,
                        background: (rec.compositeLoad || 0) > 0.75 ? 'linear-gradient(90deg, #ef4444, #f87171)' :
                          (rec.compositeLoad || 0) > 0.5 ? 'linear-gradient(90deg, #f59e0b, #fbbf24)' :
                          'linear-gradient(90deg, #10b981, #34d399)'
                      }}
                    />
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 4 }}>
                    <span style={{ fontSize: 10, color: '#64748b' }}>Target: 0.75</span>
                    <span style={{ fontSize: 10, color: '#64748b' }}>
                      {rec.usedComposite ? 'Using composite threshold' : 'Using individual metric thresholds'}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          )}

          <div style={{ padding: '12px 16px', background: '#0f172a', borderRadius: 8, marginBottom: 12 }}>
            <div style={{ fontSize: 11, color: '#64748b', marginBottom: 4, textTransform: 'uppercase' }}>Reason</div>
            <div style={{ fontSize: 13, color: '#cbd5e1' }}>{rec.reason}</div>
          </div>

          {rec.costImpact !== 0 && (
            <div style={{ padding: '12px 16px', background: '#0f172a', borderRadius: 8 }}>
              <div style={{ fontSize: 11, color: '#64748b', marginBottom: 4, textTransform: 'uppercase' }}>Cost Impact</div>
              <div style={{ fontSize: 13, color: rec.costImpact > 0 ? '#ef4444' : '#10b981' }}>
                {rec.costImpact > 0 ? '+' : ''}{rec.costImpact.toFixed(1)}%
              </div>
            </div>
          )}
        </div>

        <ScoreRing score={rec.score} />
      </div>
    </div>
  );
}
