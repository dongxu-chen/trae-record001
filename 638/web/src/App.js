import React, { useState, useEffect, useMemo } from 'react';
import { useDashboard, useTuning, useTuningHistory, useLinkages, usePendingLinkages, useCostBenefitHistory } from './hooks/useApi';
import DeploymentCard from './components/DeploymentCard';
import MetricCard from './components/MetricCard';
import HPARecommendation from './components/HPARecommendation';
import PredictionChart from './components/PredictionChart';
import CostAnalysis from './components/CostAnalysis';
import AutoTuningStatus from './components/AutoTuningStatus';
import ScalingLinkage from './components/ScalingLinkage';
import CostBenefitAnalysis from './components/CostBenefitAnalysis';
import { Activity, Cpu, DollarSign, TrendingUp, Server, GitBranch, Sliders, TrendingUp as TrendUp } from 'lucide-react';

function parseResults(data) {
  if (!data) return [];
  return Object.values(data);
}

export default function App() {
  const { data, loading, error, refetch } = useDashboard();
  const { data: tuningData } = useTuning();
  const { data: tuningHistory } = useTuningHistory();
  const { data: linkagesData } = useLinkages();
  const { data: pendingLinkagesData } = usePendingLinkages();
  const { data: costBenefitHistory } = useCostBenefitHistory();
  const [selectedKey, setSelectedKey] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');

  const results = useMemo(() => parseResults(data), [data]);
  const selected = useMemo(() => {
    if (!selectedKey) return results[0] || null;
    return results.find(r => `${r.namespace}/${r.deployment}` === selectedKey);
  }, [results, selectedKey]);

  useEffect(() => {
    if (results.length > 0 && !selectedKey) {
      setSelectedKey(`${results[0].namespace}/${results[0].deployment}`);
    }
  }, [results, selectedKey]);

  const totalReplicas = results.reduce((s, r) => s + (r.currentReplicas || 0), 0);
  const totalRecommended = results.reduce((s, r) => s + (r.recommendedReplicas || 0), 0);
  const totalCost = results.reduce((s, r) => s + ((r.costAnalysis || {}).totalMonthlyCost || 0), 0);
  const totalSavings = results.reduce((s, r) => s + ((r.costAnalysis || {}).potentialSavings || 0), 0);
  const avgScore = results.length > 0
    ? results.reduce((s, r) => s + ((r.hpaRecommendation || {}).score || 0), 0) / results.length
    : 0;
  const totalPendingLinkages = results.reduce((s, r) => s + ((r.pendingLinkages || []).length), 0);
  const avgReward = tuningData ? tuningData.bestReward : 0;

  const tabs = [
    { id: 'overview', label: 'Overview', icon: Server },
    { id: 'autotuning', label: 'Auto Tuning', icon: Sliders },
    { id: 'linkage', label: 'Scaling Linkage', icon: GitBranch },
  ];

  return (
    <div style={{ minHeight: '100vh', background: '#0f172a' }}>
      <div style={{ borderBottom: '1px solid #1e293b', padding: '16px 32px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', maxWidth: 1600, margin: '0 auto' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{ width: 40, height: 40, background: 'linear-gradient(135deg, #3b82f6, #8b5cf6)', borderRadius: 10, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Server size={22} color="#fff" />
            </div>
            <div>
              <h1 style={{ fontSize: 20, marginBottom: 2 }}>K8s Autoscaler</h1>
              <div style={{ fontSize: 12, color: '#64748b' }}>Predictive HPA & Cost Optimization</div>
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <div style={{ display: 'flex', gap: 4, background: '#1e293b', padding: 4, borderRadius: 8 }}>
              {tabs.map(tab => {
                const Icon = tab.icon;
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 6,
                      padding: '8px 16px',
                      borderRadius: 6,
                      border: 'none',
                      background: activeTab === tab.id ? '#334155' : 'transparent',
                      color: activeTab === tab.id ? '#f1f5f9' : '#64748b',
                      cursor: 'pointer',
                      fontSize: 13,
                    }}
                  >
                    <Icon size={14} />
                    {tab.label}
                  </button>
                );
              })}
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '6px 12px', background: '#1e293b', borderRadius: 8 }}>
              <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#10b981' }} />
              <span style={{ fontSize: 12, color: '#94a3b8' }}>Connected</span>
            </div>
          </div>
        </div>
      </div>

      <div style={{ maxWidth: 1600, margin: '0 auto', padding: 24 }}>
        {activeTab === 'overview' && (
          <>
            <div className="grid-4" style={{ marginBottom: 24 }}>
              <div className="metric-card border-blue" style={{ border: 'none', borderLeft: '4px solid #3b82f6' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                  <span style={{ fontSize: 12, color: '#64748b' }}>Total Replicas</span>
                  <Cpu size={18} color="#3b82f6" />
                </div>
                <div style={{ fontSize: 28, fontWeight: 700, color: '#f1f5f9' }}>{totalReplicas}</div>
                <div style={{ fontSize: 12, color: '#64748b', marginTop: 4 }}>
                  <span style={{ color: totalRecommended > totalReplicas ? '#ef4444' : totalRecommended < totalReplicas ? '#10b981' : '#64748b' }}>
                    {totalRecommended > totalReplicas ? '↑' : totalRecommended < totalReplicas ? '↓' : '→'} Recommended: {totalRecommended}
                  </span>
                </div>
              </div>

              <div className="metric-card border-green" style={{ border: 'none', borderLeft: '4px solid #10b981' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                  <span style={{ fontSize: 12, color: '#64748b' }}>Avg Score</span>
                  <Activity size={18} color="#10b981" />
                </div>
                <div style={{ fontSize: 28, fontWeight: 700, color: '#f1f5f9' }}>{avgScore.toFixed(0)}</div>
                <div className="progress-bar" style={{ marginTop: 10 }}>
                  <div className="progress-bar-fill green" style={{ width: `${avgScore}%` }} />
                </div>
              </div>

              <div className="metric-card border-yellow" style={{ border: 'none', borderLeft: '4px solid #f59e0b' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                  <span style={{ fontSize: 12, color: '#64748b' }}>Monthly Cost</span>
                  <DollarSign size={18} color="#f59e0b" />
                </div>
                <div style={{ fontSize: 28, fontWeight: 700, color: '#f1f5f9' }}>${totalCost.toFixed(0)}</div>
                <div style={{ fontSize: 12, color: '#64748b', marginTop: 4 }}>
                  <span style={{ color: '#10b981' }}>Potential: ${totalSavings.toFixed(0)} savings</span>
                </div>
              </div>

              <div className="metric-card border-purple" style={{ border: 'none', borderLeft: '4px solid #8b5cf6' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                  <span style={{ fontSize: 12, color: '#64748b' }}>Deployments</span>
                  <TrendUp size={18} color="#8b5cf6" />
                </div>
                <div style={{ fontSize: 28, fontWeight: 700, color: '#f1f5f9' }}>{results.length}</div>
                <div style={{ fontSize: 12, color: '#64748b', marginTop: 4 }}>
                  <span style={{ color: totalPendingLinkages > 0 ? '#f59e0b' : '#10b981' }}>
                    {totalPendingLinkages > 0 ? `${totalPendingLinkages} pending linkages` : 'No pending actions'}
                  </span>
                </div>
              </div>
            </div>

            <div style={{ marginBottom: 24 }}>
              <h2 style={{ marginBottom: 16 }}>Deployments</h2>
              {loading && !results.length ? (
                <div className="card" style={{ textAlign: 'center', padding: 48 }}>
                  <div style={{ color: '#64748b' }}>Loading...</div>
                </div>
              ) : results.length === 0 ? (
                <div className="card" style={{ textAlign: 'center', padding: 48 }}>
                  <div style={{ color: '#64748b' }}>No deployments found. Add deployments via API to watch.</div>
                </div>
              ) : (
                <div className="grid-auto">
                  {results.map((r) => {
                    const key = `${r.namespace}/${r.deployment}`;
                    return (
                      <DeploymentCard
                        key={key}
                        result={r}
                        selected={selectedKey === key}
                        onClick={() => setSelectedKey(key)}
                      />
                    );
                  })}
                </div>
              )}
            </div>

            {selected && (
              <>
                <div style={{ marginBottom: 24 }}>
                  <h2 style={{ marginBottom: 16 }}>
                    Metrics — {selected.namespace}/{selected.deployment}
                  </h2>
                  <div className="grid-4">
                    {(selected.hpaRecommendation?.metrics || []).map((m, i) => (
                      <MetricCard key={i} metric={m} />
                    ))}
                  </div>
                </div>

                {selected.hpaRecommendation?.usedComposite && selected.hpaRecommendation?.fusionMetrics && (
                  <div style={{ marginBottom: 24 }}>
                    <h2 style={{ marginBottom: 16 }}>
                      🔗 Fusion Metrics (CPU+Memory+QPS) — Composite Load: {(selected.hpaRecommendation.compositeLoad || 0).toFixed(2)}
                    </h2>
                    <div className="grid-3">
                      {(selected.hpaRecommendation.fusionMetrics || []).map((m, i) => (
                        <MetricCard key={i} metric={m} showFusion={true} />
                      ))}
                    </div>
                  </div>
                )}

                <div className="grid-2" style={{ marginBottom: 24 }}>
                  <HPARecommendation recommendation={selected.hpaRecommendation} />
                  <CostAnalysis costAnalysis={selected.costAnalysis} />
                </div>

                {selected.costBenefit && selected.costBenefit.action && (
                  <div style={{ marginBottom: 24 }}>
                    <h2 style={{ marginBottom: 16 }}>💰 Cost-Benefit Analysis</h2>
                    <CostBenefitAnalysis costBenefit={selected.costBenefit} />
                  </div>
                )}

                {selected.pendingLinkages && selected.pendingLinkages.length > 0 && (
                  <div style={{ marginBottom: 24 }}>
                    <h2 style={{ marginBottom: 16 }}>🔗 Pending Scaling Linkages</h2>
                    <ScalingLinkage pendingLinkages={selected.pendingLinkages} compact={true} />
                  </div>
                )}

                <PredictionChart
                  scaleDecision={selected.scaleDecision}
                  prediction={selected.scaleDecision}
                />
              </>
            )}
          </>
        )}

        {activeTab === 'autotuning' && (
          <div>
            <h2 style={{ marginBottom: 16 }}>⚙️ Rolling Window Auto Tuning</h2>
            <AutoTuningStatus tuningResult={tuningData} tuningHistory={tuningHistory} />
          </div>
        )}

        {activeTab === 'linkage' && (
          <div>
            <h2 style={{ marginBottom: 16 }}>🔗 Scaling Linkage</h2>
            <ScalingLinkage linkages={linkagesData} pendingLinkages={pendingLinkagesData} />
          </div>
        )}
      </div>
    </div>
  );
}
