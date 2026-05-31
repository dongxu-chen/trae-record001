import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { TrendingUp, TrendingDown, DollarSign, Clock, Target, CheckCircle, AlertTriangle, XCircle } from 'lucide-react';

const formatCurrency = (value) => `$${value.toFixed(2)}`;

const CostTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{ background: '#1e293b', border: '1px solid #475569', borderRadius: 8, padding: 12 }}>
      {payload.map((entry, i) => (
        <div key={i} style={{ color: entry.color, fontSize: 13 }}>
          {entry.name}: {formatCurrency(entry.value)}
        </div>
      ))}
    </div>
  );
};

const BenefitTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{ background: '#1e293b', border: '1px solid #475569', borderRadius: 8, padding: 12 }}>
      {payload.map((entry, i) => (
        <div key={i} style={{ color: entry.color, fontSize: 13 }}>
          {entry.name}: {formatCurrency(entry.value)}
        </div>
      ))}
    </div>
  );
};

export default function CostBenefitAnalysis({ costBenefit }) {
  if (!costBenefit) return null;

  const { action, cost, benefit, netBenefit, benefitCostRatio, recommendation, paybackHours, breakevenQPS, confidence } = costBenefit;

  const recConfig = {
    APPROVE: { color: '#00ff88', bg: 'rgba(0, 255, 136, 0.15)', border: 'rgba(0, 255, 136, 0.3)', Icon: CheckCircle },
    CAUTION: { color: '#ffd700', bg: 'rgba(255, 215, 0, 0.15)', border: 'rgba(255, 215, 0, 0.3)', Icon: AlertTriangle },
    REJECT: { color: '#ff6b6b', bg: 'rgba(255, 107, 107, 0.15)', border: 'rgba(255, 107, 107, 0.3)', Icon: XCircle },
  };

  const rec = recConfig[recommendation];
  const RecIcon = rec.Icon;

  const costData = [
    { name: 'Additional Compute', value: cost.additionalComputeCost, fill: '#3b82f6' },
    { name: 'Resource Waste', value: cost.resourceWasteCost, fill: '#ef4444' },
  ];

  const benefitData = [
    { name: 'Revenue Gain', value: benefit.revenueGain, fill: '#00ff88' },
    { name: 'Latency Penalty Avoided', value: benefit.latencyPenaltyAvoided, fill: '#8b5cf6' },
    { name: 'Downtime Avoided', value: benefit.downtimeAvoided, fill: '#f59e0b' },
    { name: 'SLA Error Penalty Avoided', value: benefit.sLAErrorPenaltyAvoided, fill: '#ec4899' },
  ];

  const bcRatioPercent = Math.min(benefitCostRatio * 50, 100);
  const bcRatioColor = benefitCostRatio >= 2 ? '#00ff88' : benefitCostRatio >= 1 ? '#ffd700' : '#ff6b6b';

  const confidencePercent = confidence * 100;
  const confidenceColor = confidence >= 0.8 ? '#00ff88' : confidence >= 0.5 ? '#ffd700' : '#ff6b6b';

  return (
    <div className="cost-benefit-panel" style={{ background: '#1a1a2e', borderRadius: 12, padding: 24, border: '1px solid #2a2a4e' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <div>
          <h2 style={{ color: '#ffffff', fontSize: 20, fontWeight: 600, marginBottom: 4 }}>
            Cost-Benefit Analysis
          </h2>
          <div style={{ fontSize: 12, color: '#64748b' }}>
            {action.service} ({action.namespace}) • {action.action === 'scale_up' ? 'Scale Up' : 'Scale Down'} • {action.oldReplicas} → {action.newReplicas} replicas
          </div>
        </div>
        <div
          className={`recommendation-badge ${recommendation.toLowerCase()}`}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 8,
            padding: '12px 20px',
            borderRadius: 9999,
            background: rec.bg,
            border: `1px solid ${rec.border}`,
            color: rec.color,
            fontSize: 14,
            fontWeight: 700,
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
          }}
        >
          <RecIcon size={18} />
          {recommendation}
        </div>
      </div>

      <div className="cost-benefit-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 16, marginBottom: 20 }}>
        <div className="breakdown-section" style={{ padding: 16, background: '#0f172a', borderRadius: 8, border: '1px solid #2a2a4e' }}>
          <div className="breakdown-title" style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 11, color: '#94a3b8', textTransform: 'uppercase', fontWeight: 600, marginBottom: 12 }}>
            <TrendingDown size={14} color="#ef4444" />
            Cost Breakdown
          </div>
          <div style={{ height: 120 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={costData} layout="vertical" margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" horizontal={false} />
                <XAxis type="number" stroke="#475569" fontSize={11} tickLine={false} axisLine={false} tickFormatter={(v) => formatCurrency(v)} />
                <YAxis type="category" dataKey="name" stroke="#475569" fontSize={11} tickLine={false} axisLine={false} width={110} />
                <Tooltip content={<CostTooltip />} />
                <Legend wrapperStyle={{ fontSize: 11, paddingTop: 10 }} />
                <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                  {costData.map((entry, i) => (
                    <rect key={i} fill={entry.fill} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div style={{ marginTop: 12, paddingTop: 12, borderTop: '1px solid #2a2a4e' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: 12, color: '#64748b' }}>Total Cost</span>
              <span style={{ fontSize: 16, fontWeight: 700, color: '#ef4444' }}>{formatCurrency(cost.totalCost)}/hr</span>
            </div>
          </div>
        </div>

        <div className="breakdown-section" style={{ padding: 16, background: '#0f172a', borderRadius: 8, border: '1px solid #2a2a4e' }}>
          <div className="breakdown-title" style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 11, color: '#94a3b8', textTransform: 'uppercase', fontWeight: 600, marginBottom: 12 }}>
            <TrendingUp size={14} color="#00ff88" />
            Benefit Breakdown
          </div>
          <div style={{ height: 120 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={benefitData} layout="vertical" margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" horizontal={false} />
                <XAxis type="number" stroke="#475569" fontSize={11} tickLine={false} axisLine={false} tickFormatter={(v) => formatCurrency(v)} />
                <YAxis type="category" dataKey="name" stroke="#475569" fontSize={11} tickLine={false} axisLine={false} width={140} />
                <Tooltip content={<BenefitTooltip />} />
                <Legend wrapperStyle={{ fontSize: 11, paddingTop: 10 }} />
                <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                  {benefitData.map((entry, i) => (
                    <rect key={i} fill={entry.fill} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div style={{ marginTop: 12, paddingTop: 12, borderTop: '1px solid #2a2a4e' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: 12, color: '#64748b' }}>Total Benefit</span>
              <span style={{ fontSize: 16, fontWeight: 700, color: '#00ff88' }}>{formatCurrency(benefit.totalBenefit)}/hr</span>
            </div>
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16, marginBottom: 20 }}>
        <div className="bc-ratio-display" style={{ padding: 16, background: '#0f172a', borderRadius: 8, border: '1px solid #2a2a4e' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 11, color: '#64748b', textTransform: 'uppercase', fontWeight: 600, marginBottom: 12 }}>
            <Target size={14} color={bcRatioColor} />
            Benefit / Cost Ratio
          </div>
          <div style={{ fontSize: 32, fontWeight: 700, color: bcRatioColor, marginBottom: 12 }}>
            {benefitCostRatio.toFixed(2)}x
          </div>
          <div style={{ width: '100%', height: 8, background: '#2a2a4e', borderRadius: 4, overflow: 'hidden' }}>
            <div style={{ width: `${bcRatioPercent}%`, height: '100%', background: `linear-gradient(90deg, #ff6b6b, #ffd700, #00ff88)`, borderRadius: 4, transition: 'width 0.3s ease' }} />
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 4, fontSize: 10, color: '#64748b' }}>
            <span>0x</span>
            <span>1x</span>
            <span>2x+</span>
          </div>
        </div>

        <div className="net-benefit-display" style={{ padding: 16, background: '#0f172a', borderRadius: 8, border: '1px solid #2a2a4e' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 11, color: '#64748b', textTransform: 'uppercase', fontWeight: 600, marginBottom: 12 }}>
            <DollarSign size={14} color={netBenefit >= 0 ? '#00ff88' : '#ff6b6b'} />
            Net Benefit
          </div>
          <div style={{ fontSize: 32, fontWeight: 700, color: netBenefit >= 0 ? '#00ff88' : '#ff6b6b' }}>
            {netBenefit >= 0 ? '+' : ''}{formatCurrency(netBenefit)}
            <span style={{ fontSize: 14, fontWeight: 500, color: '#64748b', marginLeft: 4 }}>/hr</span>
          </div>
          <div style={{ marginTop: 8, fontSize: 12, color: '#64748b' }}>
            {netBenefit >= 0 ? 'Positive return on scaling investment' : 'Scaling action results in net loss'}
          </div>
        </div>

        <div style={{ padding: 16, background: '#0f172a', borderRadius: 8, border: '1px solid #2a2a4e' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 11, color: '#64748b', textTransform: 'uppercase', fontWeight: 600, marginBottom: 12 }}>
            <Clock size={14} color="#8b5cf6" />
            Payback Period
          </div>
          <div style={{ fontSize: 24, fontWeight: 700, color: paybackHours > 0 && paybackHours !== Infinity ? '#f1f5f9' : '#64748b', marginBottom: 4 }}>
            {paybackHours > 0 && paybackHours !== Infinity ? `${paybackHours.toFixed(1)} hours` : 'N/A'}
          </div>
          <div style={{ fontSize: 12, color: '#64748b', marginBottom: 12 }}>
            {paybackHours > 0 && paybackHours !== Infinity ? 'Time to recover scaling costs' : 'No positive payback possible'}
          </div>
          <div style={{ paddingTop: 12, borderTop: '1px solid #2a2a4e' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: 11, color: '#64748b' }}>Breakeven QPS</span>
              <span style={{ fontSize: 16, fontWeight: 700, color: '#8b5cf6' }}>{breakevenQPS.toFixed(0)}</span>
            </div>
          </div>
        </div>
      </div>

      <div style={{ padding: 16, background: '#0f172a', borderRadius: 8, border: '1px solid #2a2a4e', marginBottom: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
          <span style={{ fontSize: 11, color: '#64748b', textTransform: 'uppercase', fontWeight: 600 }}>Confidence</span>
          <span style={{ fontSize: 14, fontWeight: 700, color: confidenceColor }}>{confidencePercent.toFixed(0)}%</span>
        </div>
        <div className="progress-bar" style={{ width: '100%', height: 8, background: '#2a2a4e', borderRadius: 4, overflow: 'hidden' }}>
          <div
            className="progress-bar-fill"
            style={{
              width: `${confidencePercent}%`,
              height: '100%',
              borderRadius: 4,
              background: `linear-gradient(90deg, ${confidenceColor}, ${confidence >= 0.8 ? '#34d399' : confidence >= 0.5 ? '#fbbf24' : '#f87171'})`,
              transition: 'width 0.3s ease',
            }}
          />
        </div>
      </div>

      <div className="summary-text" style={{ padding: 16, background: 'rgba(42, 42, 78, 0.5)', borderRadius: 8, border: '1px solid #2a2a4e', color: '#94a3b8', fontSize: 13, lineHeight: 1.6 }}>
        This scaling action costs <span style={{ color: '#ef4444', fontWeight: 600 }}>{formatCurrency(cost.totalCost)}/hour</span> but generates <span style={{ color: '#00ff88', fontWeight: 600 }}>{formatCurrency(benefit.totalBenefit)}/hour</span> in benefits, paying back in <span style={{ color: '#8b5cf6', fontWeight: 600 }}>{paybackHours > 0 && paybackHours !== Infinity ? `${paybackHours.toFixed(1)} hours` : 'N/A'}</span>.
      </div>
    </div>
  );
}
