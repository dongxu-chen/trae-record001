import React from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip } from 'recharts';

const COLORS = ['#3b82f6', '#8b5cf6', '#10b981', '#f59e0b', '#ef4444'];

function formatUSD(v) {
  if (v >= 1000) return '$' + (v / 1000).toFixed(1) + 'K';
  return '$' + v.toFixed(2);
}

export default function CostAnalysis({ costAnalysis }) {
  if (!costAnalysis) return null;
  const ca = costAnalysis;

  const pieData = (ca.resourceCosts || []).map((rc, i) => ({
    name: rc.resourceType,
    value: rc.totalCost,
    color: COLORS[i % COLORS.length],
  }));

  const wasteData = (ca.resourceCosts || []).map((rc, i) => ({
    name: rc.resourceType,
    used: rc.usedQuantity * rc.unitCost,
    waste: rc.wasteCost,
    color: COLORS[i % COLORS.length],
  }));

  const savingsPercent = ca.savingsPercent || 0;
  const barColor = savingsPercent > 30 ? '#10b981' : savingsPercent > 10 ? '#f59e0b' : '#64748b';

  const CustomTooltip = ({ active, payload }) => {
    if (!active || !payload?.length) return null;
    return (
      <div style={{ background: '#1e293b', border: '1px solid #475569', borderRadius: 8, padding: 12 }}>
        {payload.map((entry, i) => (
          <div key={i} style={{ color: entry.color, fontSize: 13 }}>
            {entry.name}: {formatUSD(entry.value)}
          </div>
        ))}
      </div>
    );
  };

  return (
    <div className="card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h2>Cost Optimization</h2>
        <span className={`status-badge ${savingsPercent > 20 ? 'up' : 'none'}`}>
          {savingsPercent.toFixed(1)}% savings
        </span>
      </div>

      <div style={{ display: 'flex', gap: 24, marginBottom: 20 }}>
        <div style={{ width: 180, height: 180 }}>
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie data={pieData} cx="50%" cy="50%" innerRadius={50} outerRadius={75}
                paddingAngle={4} dataKey="value" stroke="none">
                {pieData.map((entry, i) => (
                  <Cell key={i} fill={entry.color} />
                ))}
              </Pie>
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div style={{ flex: 1 }}>
          <div className="grid-2" style={{ marginBottom: 16 }}>
            <div style={{ padding: '12px 16px', background: '#0f172a', borderRadius: 8 }}>
              <div style={{ fontSize: 11, color: '#64748b', marginBottom: 4, textTransform: 'uppercase' }}>Monthly Cost</div>
              <div style={{ fontSize: 22, fontWeight: 700 }}>{formatUSD(ca.totalMonthlyCost)}</div>
            </div>
            <div style={{ padding: '12px 16px', background: '#0f172a', borderRadius: 8 }}>
              <div style={{ fontSize: 11, color: '#64748b', marginBottom: 4, textTransform: 'uppercase' }}>Potential Savings</div>
              <div style={{ fontSize: 22, fontWeight: 700, color: '#10b981' }}>{formatUSD(ca.potentialSavings)}</div>
            </div>
          </div>

          <div style={{ height: 100 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={wasteData} margin={{ top: 0, right: 0, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="name" stroke="#475569" fontSize={11} tickLine={false} />
                <YAxis stroke="#475569" fontSize={11} tickLine={false} />
                <Tooltip content={<CustomTooltip />} />
                <Bar dataKey="used" stackId="a" fill="#3b82f6" name="Used" />
                <Bar dataKey="waste" stackId="a" fill="#ef4444" name="Waste" opacity={0.7} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div style={{ display: 'flex', gap: 16, marginBottom: 16 }}>
        <div style={{ flex: 1, padding: '12px 16px', background: '#0f172a', borderRadius: 8 }}>
          <div style={{ fontSize: 11, color: '#64748b', marginBottom: 4, textTransform: 'uppercase' }}>Current Replicas</div>
          <div style={{ fontSize: 18, fontWeight: 600 }}>{ca.currentReplicas}</div>
        </div>
        <div style={{ flex: 1, padding: '12px 16px', background: '#0f172a', borderRadius: 8 }}>
          <div style={{ fontSize: 11, color: '#64748b', marginBottom: 4, textTransform: 'uppercase' }}>Recommended</div>
          <div style={{ fontSize: 18, fontWeight: 600, color: '#3b82f6' }}>{ca.recommendedReplicas}</div>
        </div>
        <div style={{ flex: 1, padding: '12px 16px', background: '#0f172a', borderRadius: 8 }}>
          <div style={{ fontSize: 11, color: '#64748b', marginBottom: 4, textTransform: 'uppercase' }}>Savings %</div>
          <div style={{ fontSize: 18, fontWeight: 600, color: barColor }}>{savingsPercent.toFixed(1)}%</div>
        </div>
        <div style={{ flex: 1, padding: '12px 16px', background: '#0f172a', borderRadius: 8 }}>
          <div style={{ fontSize: 11, color: '#64748b', marginBottom: 4, textTransform: 'uppercase' }}>SLA Score</div>
          <div style={{ fontSize: 18, fontWeight: 600, color: ca.slaScore >= 90 ? '#10b981' : ca.slaScore >= 70 ? '#f59e0b' : '#ef4444' }}>
            {(ca.slaScore || 0).toFixed(0)}
          </div>
        </div>
      </div>

      {ca.slaConstraints && ca.slaConstraints.length > 0 && (
        <div style={{ marginBottom: 16, padding: '16px', background: '#0f172a', borderRadius: 8 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <div style={{ fontSize: 11, color: '#64748b', textTransform: 'uppercase' }}>SLA Constraints</div>
            <span className={`status-badge ${(ca.slaViolations || []).length > 0 ? 'down' : 'up'}`}>
              {(ca.slaViolations || []).length > 0 ? `${ca.slaViolations.length} Violations` : 'All Met'}
            </span>
          </div>
          <div className="grid-2">
            {ca.slaConstraints.map((sla, i) => {
              const isViolated = (ca.slaViolations || []).some(v => v.constraint?.name === sla.name);
              return (
                <div key={i} style={{
                  padding: '10px 14px',
                  background: isViolated ? 'rgba(239, 68, 68, 0.1)' : 'rgba(16, 185, 129, 0.05)',
                  borderRadius: 6,
                  border: isViolated ? '1px solid rgba(239, 68, 68, 0.3)' : '1px solid #1e293b'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                    <span style={{ fontSize: 13, fontWeight: 600, color: '#f1f5f9' }}>{sla.name}</span>
                    <span style={{ fontSize: 11, color: isViolated ? '#ef4444' : '#10b981' }}>
                      {isViolated ? 'VIOLATED' : 'OK'}
                    </span>
                  </div>
                  <div style={{ fontSize: 11, color: '#64748b' }}>
                    {sla.type} {sla.operator} {sla.value} (Priority: {sla.priority})
                  </div>
                  {isViolated && (ca.slaViolations || []).filter(v => v.constraint?.name === sla.name).map((v, j) => (
                    <div key={j} style={{ fontSize: 11, color: '#ef4444', marginTop: 4 }}>
                      Current: {v.currentValue.toFixed(2)}, Violation: {v.violationAmount.toFixed(2)} ({v.severity})
                    </div>
                  ))}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {ca.recommendations && ca.recommendations.length > 0 && (
        <div style={{ padding: '12px 16px', background: '#0f172a', borderRadius: 8 }}>
          <div style={{ fontSize: 11, color: '#64748b', marginBottom: 8, textTransform: 'uppercase' }}>Recommendations</div>
          {ca.recommendations.map((rec, i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 0', borderBottom: i < ca.recommendations.length - 1 ? '1px solid #1e293b' : 'none' }}>
              <span style={{ color: '#f59e0b', fontSize: 12 }}>●</span>
              <span style={{ fontSize: 13, color: '#cbd5e1' }}>{rec}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
