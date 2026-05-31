import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar } from 'recharts';
import { Activity, Sliders, TrendingUp, BarChart3 } from 'lucide-react';

const RewardTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{ background: '#1e293b', border: '1px solid #475569', borderRadius: 8, padding: 12 }}>
      <div style={{ color: '#94a3b8', fontSize: 12, marginBottom: 6 }}>{label}</div>
      {payload.map((entry, i) => (
        <div key={i} style={{ color: entry.color, fontSize: 13 }}>
          {entry.name}: {(entry.value * 100).toFixed(1)}%
        </div>
      ))}
    </div>
  );
};

const FusionTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{ background: '#1e293b', border: '1px solid #475569', borderRadius: 8, padding: 12 }}>
      <div style={{ color: '#94a3b8', fontSize: 12, marginBottom: 6 }}>{label}</div>
      {payload.map((entry, i) => (
        <div key={i} style={{ color: entry.color, fontSize: 13 }}>
          Weight: {(entry.value * 100).toFixed(1)}%
        </div>
      ))}
    </div>
  );
};

export default function AutoTuningStatus({ tuningResult, tuningHistory }) {
  if (!tuningResult) return null;

  const { params, bestReward, sampleCount, lastUpdate, explorationRate, rollingWindowSize } = tuningResult;
  const { scaleUpThreshold, scaleDownThreshold, compositeTarget, maxScaleUpRatio, scaleUpCooldownSec, scaleDownCooldownSec, fusionWeights } = params;

  const rewardPercent = bestReward * 100;
  const rewardColor = bestReward > 0.7 ? 'green' : bestReward > 0.4 ? 'yellow' : 'red';
  const isExploring = explorationRate > 0.5;

  const paramList = [
    { name: 'Scale Up Threshold', value: scaleUpThreshold.toFixed(2) },
    { name: 'Scale Down Threshold', value: scaleDownThreshold.toFixed(2) },
    { name: 'Composite Target', value: compositeTarget.toFixed(2) },
    { name: 'Max Scale Up Ratio', value: `${maxScaleUpRatio.toFixed(2)}x` },
    { name: 'Scale Up Cooldown', value: `${scaleUpCooldownSec}s` },
    { name: 'Scale Down Cooldown', value: `${scaleDownCooldownSec}s` },
  ];

  const rewardChartData = tuningHistory?.map((item, i) => ({
    time: new Date(item.timestamp).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
    reward: item.reward,
    avgCPU: item.avgCPU,
    avgQPS: item.avgQPS,
    avgLatency: item.avgLatency,
    slaViolations: item.slaViolations,
    costChangePercent: item.costChangePercent,
  })) || [];

  const fusionData = [
    { name: 'CPU', weight: fusionWeights.CPU, color: '#3b82f6' },
    { name: 'Memory', weight: fusionWeights.Memory, color: '#10b981' },
    { name: 'QPS', weight: fusionWeights.QPS, color: '#f59e0b' },
  ];

  return (
    <div className="auto-tuning-panel card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <Activity size={20} color="#00d4ff" />
          <h2>Auto-Tuning Status</h2>
        </div>
        <div style={{ fontSize: 11, color: '#64748b' }}>
          Window: {rollingWindowSize} samples
        </div>
      </div>

      <div className="reward-section" style={{ marginBottom: 20, padding: '16px', background: '#0f172a', borderRadius: 8, border: '1px solid #1e293b' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
          <TrendingUp size={16} color="#00ff88" />
          <span style={{ fontSize: 11, color: '#94a3b8', textTransform: 'uppercase', fontWeight: 600 }}>Best Reward</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <div style={{ fontSize: 32, fontWeight: 700, color: bestReward > 0.7 ? '#10b981' : bestReward > 0.4 ? '#f59e0b' : '#ef4444' }}>
            {rewardPercent.toFixed(1)}%
          </div>
          <div className="reward-bar progress-bar" style={{ flex: 1, height: 12 }}>
            <div
              className={`progress-bar-fill ${rewardColor}`}
              style={{ width: `${rewardPercent}%` }}
            />
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 16, marginBottom: 20 }}>
        <div style={{ padding: '16px', background: '#0f172a', borderRadius: 8, border: '1px solid #1e293b' }}>
          <div style={{ fontSize: 11, color: '#64748b', marginBottom: 4, textTransform: 'uppercase' }}>Sample Count</div>
          <div style={{ fontSize: 24, fontWeight: 700, color: '#f1f5f9' }}>{sampleCount}</div>
          <div style={{ fontSize: 10, color: '#64748b', marginTop: 4 }}>
            Last: {new Date(lastUpdate).toLocaleString('en-US')}
          </div>
        </div>
        <div style={{ padding: '16px', background: '#0f172a', borderRadius: 8, border: '1px solid #1e293b' }}>
          <div style={{ fontSize: 11, color: '#64748b', marginBottom: 4, textTransform: 'uppercase' }}>Exploration Rate</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{ fontSize: 24, fontWeight: 700, color: isExploring ? '#f59e0b' : '#10b981' }}>
              {(explorationRate * 100).toFixed(0)}%
            </div>
            <span className={`exploration-badge ${isExploring ? 'badge-explore' : 'badge-exploit'}`}>
              {isExploring ? 'Exploring' : 'Exploiting'}
            </span>
          </div>
        </div>
      </div>

      <div style={{ marginBottom: 20 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
          <Sliders size={16} color="#00d4ff" />
          <span style={{ fontSize: 11, color: '#94a3b8', textTransform: 'uppercase', fontWeight: 600 }}>Current Parameters</span>
        </div>
        <div className="tuning-params-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 12 }}>
          {paramList.map((param, i) => (
            <div key={i} className="param-card" style={{ padding: '12px 16px', background: '#0f172a', borderRadius: 8, border: '1px solid #1e293b' }}>
              <div className="param-name" style={{ fontSize: 11, color: '#64748b', marginBottom: 4, textTransform: 'uppercase' }}>
                {param.name}
              </div>
              <div className="param-value" style={{ fontSize: 18, fontWeight: 600, color: '#f1f5f9' }}>
                {param.value}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="fusion-chart-container" style={{ marginBottom: 20 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
          <BarChart3 size={16} color="#8b5cf6" />
          <span style={{ fontSize: 11, color: '#94a3b8', textTransform: 'uppercase', fontWeight: 600 }}>Fusion Weights</span>
        </div>
        <div style={{ height: 140, padding: '12px', background: '#0f172a', borderRadius: 8, border: '1px solid #1e293b' }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={fusionData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
              <XAxis dataKey="name" stroke="#475569" fontSize={11} tickLine={false} axisLine={false} />
              <YAxis stroke="#475569" fontSize={11} tickLine={false} axisLine={false} domain={[0, 1]} tickFormatter={(v) => (v * 100).toFixed(0) + '%'} />
              <Tooltip content={<FusionTooltip />} />
              <Bar dataKey="weight" radius={[4, 4, 0, 0]}>
                {fusionData.map((entry, i) => (
                  <rect key={i} fill={entry.color} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {rewardChartData.length > 0 && (
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
            <TrendingUp size={16} color="#00ff88" />
            <span style={{ fontSize: 11, color: '#94a3b8', textTransform: 'uppercase', fontWeight: 600 }}>Reward History</span>
          </div>
          <div style={{ height: 160, padding: '12px', background: '#0f172a', borderRadius: 8, border: '1px solid #1e293b' }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={rewardChartData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="time" stroke="#475569" fontSize={11} tickLine={false} />
                <YAxis stroke="#475569" fontSize={11} tickLine={false} domain={[0, 1]} tickFormatter={(v) => (v * 100).toFixed(0) + '%'} />
                <Tooltip content={<RewardTooltip />} />
                <Line type="monotone" dataKey="reward" stroke="#00d4ff" strokeWidth={2} dot={{ fill: '#00d4ff', r: 3 }} activeDot={{ r: 5, fill: '#00d4ff' }} name="Reward" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  );
}
