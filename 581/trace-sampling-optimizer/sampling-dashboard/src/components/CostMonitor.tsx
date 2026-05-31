import React, { useState, useEffect } from 'react';
import {
  CostSummary,
  CpuCostSummary,
  fetchAllCostAssessments,
  ComprehensiveCostAssessment,
} from '../api/apiClient';

interface Props {
  costSummary: CostSummary | null;
  cpuCostSummary: CpuCostSummary | null;
}

const CostMonitor: React.FC<Props> = ({ costSummary, cpuCostSummary }) => {
  const [assessments, setAssessments] = useState<Record<string, ComprehensiveCostAssessment>>({});
  const [activeTab, setActiveTab] = useState<'budget' | 'cpu' | 'assessments'>('budget');

  useEffect(() => {
    const loadAssessments = async () => {
      try {
        const res = await fetchAllCostAssessments();
        setAssessments(res.data);
      } catch (e) {
        console.error('Failed to load assessments', e);
      }
    };
    loadAssessments();
    const interval = setInterval(loadAssessments, 10000);
    return () => clearInterval(interval);
  }, []);

  if (!costSummary || !cpuCostSummary) {
    return (
      <div style={{
        background: '#1e293b',
        borderRadius: '12px',
        padding: '20px',
        border: '1px solid #334155',
        height: '100%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        color: '#64748b',
      }}>
        加载成本数据中...
      </div>
    );
  }

  const utilization = costSummary.utilizationPercent;
  const gaugeAngle = (utilization / 100) * 180;
  const gaugeColor =
    utilization < 50 ? '#10b981' :
    utilization < 80 ? '#f59e0b' : '#ef4444';

  const breakdown = costSummary.serviceBreakdown || {};
  const sortedBreakdown = Object.entries(breakdown)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 6);
  const maxBreakdown = sortedBreakdown.length > 0 ? sortedBreakdown[0][1] : 1;

  const totalCost = Object.values(breakdown).reduce((a, b) => a + b, 0);
  const cpuTotal = cpuCostSummary.totalCpuCost;
  const storagePct = totalCost > 0 ? ((totalCost - cpuTotal) / totalCost) * 100 : 0;
  const cpuPct = totalCost > 0 ? (cpuTotal / totalCost) * 100 : 0;

  return (
    <div style={{
      background: '#1e293b',
      borderRadius: '12px',
      padding: '20px',
      border: '1px solid #334155',
    }}>
      <h3 style={{ margin: '0 0 12px', fontSize: '16px', fontWeight: 600, color: '#f1f5f9' }}>
        💰 成本监控
      </h3>

      {}
      <div style={{ display: 'flex', gap: '4px', marginBottom: '12px' }}>
        {(['budget', 'cpu', 'assessments'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            style={{
              flex: 1,
              padding: '6px 8px',
              borderRadius: '6px',
              border: 'none',
              background: activeTab === tab ? '#3b82f6' : '#0f172a',
              color: activeTab === tab ? '#fff' : '#94a3b8',
              fontSize: '12px',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            {tab === 'budget' ? '预算' : tab === 'cpu' ? 'CPU' : '评估'}
          </button>
        ))}
      </div>

      {activeTab === 'budget' && (
        <>
          {}
          <div style={{ textAlign: 'center', marginBottom: '16px' }}>
            <svg width="160" height="90" viewBox="0 0 160 90">
              {}
              <path d="M 20 80 A 60 60 0 0 1 140 80" fill="none" stroke="#334155" strokeWidth="12" strokeLinecap="round" />
              {}
              <path
                d="M 20 80 A 60 60 0 0 1 140 80"
                fill="none"
                stroke={gaugeColor}
                strokeWidth="12"
                strokeLinecap="round"
                strokeDasharray={`${(utilization / 100) * 188} 188`}
              />
              <text x="80" y="72" textAnchor="middle" fill={gaugeColor} fontSize="20" fontWeight="700">
                {utilization.toFixed(1)}%
              </text>
              <text x="80" y="88" textAnchor="middle" fill="#94a3b8" fontSize="10">预算使用率</text>
            </svg>
          </div>

          {}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', marginBottom: '12px' }}>
            <MetricItem label="日预算" value={`$${costSummary.dailyBudgetUsd.toFixed(2)}`} />
            <MetricItem label="已花费" value={`$${costSummary.currentSpendUsd.toFixed(2)}`} />
            <MetricItem label="剩余" value={`$${costSummary.remainingBudget.toFixed(2)}`} />
            <MetricItem
              label="告警"
              value={costSummary.alertTriggered ? '⚠️ 已触发' : '✅ 正常'}
              valueColor={costSummary.alertTriggered ? '#ef4444' : '#10b981'}
            />
          </div>

          {}
          <div style={{ borderTop: '1px solid #334155', paddingTop: '10px' }}>
            <h4 style={{ margin: '0 0 8px', fontSize: '12px', color: '#94a3b8' }}>
              成本构成
            </h4>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <svg width="60" height="60" viewBox="0 0 60 60">
                <circle cx="30" cy="30" r="25" fill="#1e40af" />
                <path
                  d={`M 30 30 L 30 5 A 25 25 0 ${cpuPct > 50 ? 1 : 0} 1 ${30 + 25 * Math.sin(cpuPct * Math.PI / 180)} ${30 - 25 * Math.cos(cpuPct * Math.PI / 180)} Z`}
                  fill="#06b6d4"
                />
                <circle cx="30" cy="30" r="15" fill="#1e293b" />
              </svg>
              <div style={{ fontSize: '11px', flex: 1 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                  <span style={{ color: '#cbd5e1' }}>存储+网络+计算</span>
                  <span style={{ color: '#94a3b8' }}>{storagePct.toFixed(1)}%</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                  <span style={{ color: '#06b6d4', fontWeight: 600 }}>CPU处理</span>
                  <span style={{ color: '#06b6d4' }}>{cpuPct.toFixed(1)}%</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: '#cbd5e1' }}>CPU日成本</span>
                  <span style={{ color: '#f1f5f9', fontWeight: 600 }}>${cpuTotal.toFixed(4)}</span>
                </div>
              </div>
            </div>
          </div>
        </>
      )}

      {activeTab === 'cpu' && (
        <div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', marginBottom: '12px' }}>
            <MetricItem label="每Span CPU成本" value={`$${cpuCostSummary.costPerSpanCpu.toFixed(6)}`} />
            <MetricItem label="CPU乘数" value={`${cpuCostSummary.cpuCostMultiplier.toFixed(1)}x`} />
            <MetricItem label="Core小时成本" value={`$${cpuCostSummary.cpuCoreCostPerHourUsd.toFixed(3)}`} />
            <MetricItem label="单Core处理量" value={`${cpuCostSummary.spansProcessedPerCoreSecond.toLocaleString()}/s`} />
          </div>

          <div style={{ background: '#0f172a', borderRadius: '8px', padding: '10px', marginBottom: '12px' }}>
            <div style={{ fontSize: '11px', color: '#64748b', marginBottom: '4px' }}>采样CPU开销</div>
            <div style={{ fontSize: '16px', fontWeight: 700, color: '#06b6d4' }}>
              {(cpuCostSummary.samplingCpuOverheadPercent * 100).toFixed(1)}%
            </div>
          </div>

          <div style={{ borderTop: '1px solid #334155', paddingTop: '10px' }}>
            <h4 style={{ margin: '0 0 8px', fontSize: '12px', color: '#94a3b8' }}>
              服务CPU成本分布
            </h4>
            {Object.entries(cpuCostSummary.cpuCostPerService || {})
              .sort((a, b) => b[1] - a[1])
              .slice(0, 5)
              .map(([svc, cost]) => (
                <div key={svc} style={{ marginBottom: '6px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px' }}>
                    <span style={{ color: '#cbd5e1' }}>{svc.replace('-service', '')}</span>
                    <span style={{ color: '#06b6d4' }}>${cost.toFixed(5)}</span>
                  </div>
                </div>
              ))}
          </div>
        </div>
      )}

      {activeTab === 'assessments' && (
        <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
          {Object.entries(assessments)
            .sort((a, b) => b[1].compositeScore - a[1].compositeScore)
            .map(([svc, assessment]) => (
              <div
                key={svc}
                style={{
                  background: '#0f172a',
                  borderRadius: '8px',
                  padding: '10px',
                  marginBottom: '8px',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '12px', fontWeight: 600, color: '#f1f5f9' }}>
                    {svc.replace('-service', '')}
                  </span>
                  <span
                    style={{
                      fontSize: '11px',
                      padding: '2px 6px',
                      borderRadius: '4px',
                      background: assessment.recommendation === 'INCREASE_SAMPLING' ? '#064e3b' :
                                assessment.recommendation === 'REDUCE_SAMPLING' ? '#450a0a' : '#1e3a5f',
                      color: assessment.recommendation === 'INCREASE_SAMPLING' ? '#6ee7b7' :
                             assessment.recommendation === 'REDUCE_SAMPLING' ? '#fca5a5' : '#93c5fd',
                      fontWeight: 600,
                    }}
                  >
                    {assessment.recommendation === 'INCREASE_SAMPLING' ? '↑ 提高采样' :
                     assessment.recommendation === 'REDUCE_SAMPLING' ? '↓ 降低采样' : '→ 保持'}
                  </span>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4px', marginTop: '6px', fontSize: '10px' }}>
                  <div>
                    <span style={{ color: '#64748b' }}>综合得分: </span>
                    <span style={{ color: '#fbbf24', fontWeight: 600 }}>
                      {(assessment.compositeScore * 100).toFixed(0)}
                    </span>
                  </div>
                  <div>
                    <span style={{ color: '#64748b' }}>风险: </span>
                    <span style={{ color: '#f87171', fontWeight: 600 }}>
                      {(assessment.aggregateRisk * 100).toFixed(0)}%
                    </span>
                  </div>
                  <div>
                    <span style={{ color: '#64748b' }}>成本效率: </span>
                    <span style={{ color: '#34d399', fontWeight: 600 }}>
                      {assessment.costEfficiency.toFixed(1)}
                    </span>
                  </div>
                  <div>
                    <span style={{ color: '#64748b' }}>建议率: </span>
                    <span style={{ color: '#60a5fa', fontWeight: 600 }}>
                      {(assessment.recommendedRate * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
              </div>
            ))}
        </div>
      )}
    </div>
  );
};

const MetricItem: React.FC<{
  label: string;
  value: string;
  valueColor?: string;
}> = ({ label, value, valueColor }) => (
  <div style={{
    background: '#0f172a',
    borderRadius: '8px',
    padding: '8px 10px',
  }}>
    <div style={{ fontSize: '11px', color: '#64748b' }}>{label}</div>
    <div style={{ fontSize: '14px', fontWeight: 600, color: valueColor || '#f1f5f9' }}>{value}</div>
  </div>
);

export default CostMonitor;
