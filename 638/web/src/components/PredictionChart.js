import React, { useMemo } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Area, ComposedChart, Bar, Legend } from 'recharts';

function DirectionBadge({ direction }) {
  const cls = direction === 'up' ? 'up' : direction === 'down' ? 'down' : 'none';
  const arrow = direction === 'up' ? '↑' : direction === 'down' ? '↓' : '→';
  const label = direction === 'up' ? 'Scale Up' : direction === 'down' ? 'Scale Down' : 'No Change';
  return <span className={`status-badge ${cls}`}>{arrow} {label}</span>;
}

function generateChartData() {
  const now = Date.now();
  const data = [];
  for (let i = 60; i >= 0; i--) {
    const t = now - i * 60000;
    const cpuBase = 55 + 20 * Math.sin(2 * Math.PI * i / 120);
    const qpsBase = 80 + 30 * Math.sin(2 * Math.PI * i / 90 + 1);
    data.push({
      time: new Date(t).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
      cpu: Math.max(cpuBase + Math.random() * 8, 5),
      cpuPredicted: i <= 10 ? null : Math.max(cpuBase + 5 + Math.random() * 5, 10),
      qps: Math.max(qpsBase + Math.random() * 15, 10),
      qpsPredicted: i <= 10 ? null : Math.max(qpsBase + 10 + Math.random() * 10, 15),
      replicas: Math.round(3 + (cpuBase > 70 ? 2 : 0) + (qpsBase > 100 ? 1 : 0)),
    });
  }

  for (let i = 1; i <= 12; i++) {
    const t = now + i * 60000;
    const cpuPred = Math.max(60 + 25 * Math.sin(2 * Math.PI * (60 + i) / 120) + i * 0.5, 5);
    const qpsPred = Math.max(90 + 35 * Math.sin(2 * Math.PI * (60 + i) / 90 + 1) + i * 0.8, 10);
    data.push({
      time: new Date(t).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
      cpu: null,
      cpuPredicted: cpuPred,
      qps: null,
      qpsPredicted: qpsPred,
      replicas: Math.round(3 + (cpuPred > 70 ? 2 : 0) + (qpsPred > 100 ? 1 : 0)),
    });
  }
  return data;
}

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{ background: '#1e293b', border: '1px solid #475569', borderRadius: 8, padding: 12 }}>
      <div style={{ color: '#94a3b8', fontSize: 12, marginBottom: 6 }}>{label}</div>
      {payload.map((entry, i) => (
        <div key={i} style={{ color: entry.color, fontSize: 13 }}>
          {entry.name}: {entry.value?.toFixed(1)}
        </div>
      ))}
    </div>
  );
};

export default function PredictionChart({ scaleDecision, prediction }) {
  const chartData = useMemo(() => generateChartData(), []);

  const decision = scaleDecision || {};
  const pred = prediction || {};
  const patterns = pred.detectedPatterns || [];
  const hasPatterns = patterns.length > 0;

  function formatPeriod(durationNs) {
    const hours = durationNs / (1e9 * 60 * 60);
    if (hours >= 24 * 7) return `${(hours / (24 * 7)).toFixed(1)} 周`;
    if (hours >= 24) return `${(hours / 24).toFixed(1)} 天`;
    if (hours >= 1) return `${hours.toFixed(1)} 小时`;
    const minutes = durationNs / (1e9 * 60);
    if (minutes >= 1) return `${minutes.toFixed(1)} 分钟`;
    const seconds = durationNs / 1e9;
    return `${seconds.toFixed(1)} 秒`;
  }

  return (
    <div className="card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h2>Predictive Scaling Analysis</h2>
        {decision.scaleDirection && <DirectionBadge direction={decision.scaleDirection} />}
      </div>

      {hasPatterns && (
        <div style={{ marginBottom: 20, padding: '16px', background: 'rgba(139, 92, 246, 0.1)', borderRadius: 8, border: '1px solid rgba(139, 92, 246, 0.3)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <div style={{ fontSize: 11, color: '#94a3b8', textTransform: 'uppercase', fontWeight: 600 }}>
              🔄 Detected Periodic Patterns
            </div>
            <span className="status-badge up">{patterns.length} 模式</span>
          </div>
          <div className="grid-auto" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))' }}>
            {patterns.map((p, i) => (
              <div key={i} style={{
                padding: '10px 14px',
                background: '#0f172a',
                borderRadius: 6,
                border: '1px solid #1e293b'
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <span style={{ fontSize: 12, fontWeight: 600, color: '#f1f5f9' }}>
                    {formatPeriod(p.period)}
                  </span>
                  <span style={{ fontSize: 10, color: p.strength > 0.8 ? '#10b981' : '#f59e0b' }}>
                    Strength: {(p.strength * 100).toFixed(0)}%
                  </span>
                </div>
                <div style={{ fontSize: 10, color: '#64748b' }}>
                  Amplitude: {p.amplitude.toFixed(1)} | Phase: {p.phase.toFixed(2)}
                </div>
                <div className="progress-bar" style={{ height: 4, marginTop: 6 }}>
                  <div
                    className="progress-bar-fill"
                    style={{
                      width: `${p.strength * 100}%`,
                      background: p.strength > 0.8 ? 'linear-gradient(90deg, #10b981, #34d399)' :
                                  'linear-gradient(90deg, #f59e0b, #fbbf24)'
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div style={{ height: 280, marginBottom: 24 }}>
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={chartData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
            <defs>
              <linearGradient id="cpuGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="qpsGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#f59e0b" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
            <XAxis dataKey="time" stroke="#475569" fontSize={11} tickLine={false} />
            <YAxis stroke="#475569" fontSize={11} tickLine={false} />
            <Tooltip content={<CustomTooltip />} />
            <Legend wrapperStyle={{ fontSize: 12, color: '#94a3b8' }} />
            <Area type="monotone" dataKey="cpu" stroke="#3b82f6" fill="url(#cpuGrad)" strokeWidth={2} name="CPU Usage" />
            <Line type="monotone" dataKey="cpuPredicted" stroke="#3b82f6" strokeDasharray="6 3" strokeWidth={2} dot={false} name="CPU Predicted" />
            <Area type="monotone" dataKey="qps" stroke="#f59e0b" fill="url(#qpsGrad)" strokeWidth={2} name="QPS" />
            <Line type="monotone" dataKey="qpsPredicted" stroke="#f59e0b" strokeDasharray="6 3" strokeWidth={2} dot={false} name="QPS Predicted" />
            <Bar dataKey="replicas" fill="#8b5cf6" opacity={0.3} name="Replicas" yAxisId={0} barSize={4} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      <div className="grid-4">
        <div style={{ padding: '12px 16px', background: '#0f172a', borderRadius: 8 }}>
          <div style={{ fontSize: 11, color: '#64748b', marginBottom: 4, textTransform: 'uppercase' }}>Current Replicas</div>
          <div style={{ fontSize: 22, fontWeight: 700 }}>{decision.currentReplicas || '-'}</div>
        </div>
        <div style={{ padding: '12px 16px', background: '#0f172a', borderRadius: 8 }}>
          <div style={{ fontSize: 11, color: '#64748b', marginBottom: 4, textTransform: 'uppercase' }}>Desired Replicas</div>
          <div style={{ fontSize: 22, fontWeight: 700, color: '#3b82f6' }}>{decision.desiredReplicas || '-'}</div>
        </div>
        <div style={{ padding: '12px 16px', background: '#0f172a', borderRadius: 8 }}>
          <div style={{ fontSize: 11, color: '#64748b', marginBottom: 4, textTransform: 'uppercase' }}>Confidence</div>
          <div style={{ fontSize: 22, fontWeight: 700, color: decision.confidence > 0.7 ? '#10b981' : '#f59e0b' }}>
            {decision.confidence ? (decision.confidence * 100).toFixed(0) + '%' : '-'}
          </div>
        </div>
        <div style={{ padding: '12px 16px', background: '#0f172a', borderRadius: 8 }}>
          <div style={{ fontSize: 11, color: '#64748b', marginBottom: 4, textTransform: 'uppercase' }}>Predicted CPU</div>
          <div style={{ fontSize: 22, fontWeight: 700, color: '#8b5cf6' }}>
            {decision.predictedCPU ? (decision.predictedCPU / 1000).toFixed(2) + 'c' : '-'}
          </div>
        </div>
      </div>

      {decision.reason && (
        <div style={{ marginTop: 12, padding: '12px 16px', background: '#0f172a', borderRadius: 8 }}>
          <div style={{ fontSize: 11, color: '#64748b', marginBottom: 4, textTransform: 'uppercase' }}>Prediction Reason</div>
          <div style={{ fontSize: 13, color: '#cbd5e1' }}>{decision.reason}</div>
        </div>
      )}
    </div>
  );
}
