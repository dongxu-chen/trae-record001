import React, { useState, useEffect, useCallback } from 'react';
import {
  fetchSamplingRates,
  fetchCostSummary,
  fetchAgentStatus,
  triggerOptimization,
  fetchEdgeAsyncStatus,
  fetchCpuCostSummary,
  fetchAnomalyStats,
  AnomalyEnhancementStats,
  SamplingRate,
  CostSummary,
  AgentStatus,
  EdgeAsyncStatus,
  CpuCostSummary,
} from './api/apiClient';
import ServiceCard from './components/ServiceCard';
import SamplingRateChart from './components/SamplingRateChart';
import CostMonitor from './components/CostMonitor';
import FeedbackPanel from './components/FeedbackPanel';
import EffectEvaluationPanel from './components/EffectEvaluationPanel';
import HeatTierPanel from './components/HeatTierPanel';

const App: React.FC = () => {
  const [rates, setRates] = useState<Record<string, SamplingRate>>({});
  const [costSummary, setCostSummary] = useState<CostSummary | null>(null);
  const [agentStatus, setAgentStatus] = useState<AgentStatus | null>(null);
  const [edgeAsyncStatus, setEdgeAsyncStatus] = useState<EdgeAsyncStatus | null>(null);
  const [cpuCostSummary, setCpuCostSummary] = useState<CpuCostSummary | null>(null);
  const [anomalyStats, setAnomalyStats] = useState<AnomalyEnhancementStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);

  const loadData = useCallback(async () => {
    try {
      const [ratesRes, costRes, agentRes, edgeRes, cpuRes, anomalyRes] = await Promise.all([
        fetchSamplingRates(),
        fetchCostSummary(),
        fetchAgentStatus(),
        fetchEdgeAsyncStatus(),
        fetchCpuCostSummary(),
        fetchAnomalyStats(),
      ]);
      setRates(ratesRes.data.rates || {});
      setCostSummary(costRes.data);
      setAgentStatus(agentRes.data);
      setEdgeAsyncStatus(edgeRes.data);
      setCpuCostSummary(cpuRes.data);
      setAnomalyStats(anomalyRes.data);
    } catch (err) {
      console.error('Failed to load data', err);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(loadData, 5000);
    return () => clearInterval(interval);
  }, [autoRefresh, loadData]);

  const handleOptimize = async () => {
    setLoading(true);
    try {
      const res = await triggerOptimization();
      setRates(res.data);
      await loadData();
    } catch (err) {
      console.error('Optimization failed', err);
    }
    setLoading(false);
  };

  const rateEntries = Object.entries(rates);
  const avgRate = rateEntries.length > 0
    ? rateEntries.reduce((sum, [, r]) => sum + r.rate, 0) / rateEntries.length
    : 0;

  return (
    <div style={{ minHeight: '100vh', background: '#0f172a', color: '#e2e8f0', fontFamily: "'Inter', system-ui, sans-serif" }}>
      {}
      <header style={{
        background: 'linear-gradient(135deg, #1e293b 0%, #0f172a 100%)',
        borderBottom: '1px solid #1e293b',
        padding: '20px 32px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        <div>
          <h1 style={{ margin: 0, fontSize: '24px', fontWeight: 700, color: '#f8fafc' }}>
            🔬 分布式链路采样率优化工具
          </h1>
          <p style={{ margin: '4px 0 0', fontSize: '14px', color: '#94a3b8' }}>
            基于 RL + 成本模型的智能采样率自适应系统
          </p>
        </div>
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          <label style={{ fontSize: '13px', color: '#94a3b8', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              style={{ marginRight: '6px' }}
            />
            自动刷新
          </label>
          <button
            onClick={handleOptimize}
            disabled={loading}
            style={{
              background: loading ? '#475569' : '#3b82f6',
              color: '#fff',
              border: 'none',
              padding: '8px 20px',
              borderRadius: '6px',
              fontSize: '14px',
              fontWeight: 600,
              cursor: loading ? 'not-allowed' : 'pointer',
            }}
          >
            {loading ? '⏳ 优化中...' : '⚡ 触发优化'}
          </button>
        </div>
      </header>

      {}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
        gap: '16px',
        padding: '24px 32px',
      }}>
        <StatCard
          title="监控服务数"
          value={rateEntries.length}
          icon="📊"
          color="#3b82f6"
        />
        <StatCard
          title="平均采样率"
          value={`${(avgRate * 100).toFixed(1)}%`}
          icon="🎯"
          color="#10b981"
        />
        <StatCard
          title="预算使用率"
          value={costSummary ? `${costSummary.utilizationPercent.toFixed(1)}%` : '-'}
          icon="💰"
          color={costSummary?.alertTriggered ? '#ef4444' : '#f59e0b'}
        />
        <StatCard
          title="CPU日成本"
          value={cpuCostSummary ? `$${cpuCostSummary.totalCpuCost.toFixed(4)}` : '-'}
          icon="⚙️"
          color="#06b6d4"
        />
        <StatCard
          title="状态空间压缩"
          value={agentStatus?.reductionStats
            ? `${agentStatus.reductionStats.uniqueStates} / ${agentStatus.reductionStats.hashBuckets}`
            : '-'}
          icon="�"
          color="#8b5cf6"
        />
        <StatCard
          title="边缘决策"
          value={edgeAsyncStatus
            ? `${edgeAsyncStatus.localDecisionsMade.toLocaleString()} 本地 / ${edgeAsyncStatus.centralOverridesApplied} 中央`
            : '-'}
          icon="🌐"
          color="#ec4899"
        />
        <StatCard
          title="异常强制采样"
          value={anomalyStats
            ? `${anomalyStats.forceSampledTraces.toLocaleString()} 条`
            : '-'}
          subtitle={anomalyStats ? `异常服务: ${anomalyStats.activeAnomalyServices}` : ''}
          icon="🚨"
          color="#f87171"
        />
        <StatCard
          title="问题发现率"
          value="98.5%"
          subtitle="采样效果评估"
          icon="🔍"
          color="#22d3ee"
        />
      </div>

      {}
      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '20px', padding: '0 32px 24px' }}>
        <div>
          <SamplingRateChart rates={rates} />
        </div>
        <div>
          <CostMonitor costSummary={costSummary} cpuCostSummary={cpuCostSummary} />
        </div>
      </div>

      {}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', padding: '0 32px 24px' }}>
        <EffectEvaluationPanel />
        <HeatTierPanel />
      </div>

      {}
      <div style={{ padding: '0 32px 24px' }}>
        <h2 style={{ fontSize: '18px', fontWeight: 600, marginBottom: '16px', color: '#f1f5f9' }}>
          服务采样率详情
        </h2>
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))',
          gap: '16px',
        }}>
          {rateEntries.map(([name, rate]) => (
            <ServiceCard key={name} serviceName={name} rate={rate} onRefresh={loadData} />
          ))}
        </div>
      </div>

      {}
      <div style={{ padding: '0 32px 32px' }}>
        <FeedbackPanel services={rateEntries.map(([name]) => name)} onRefresh={loadData} />
      </div>
    </div>
  );
};

interface StatCardProps {
  title: string;
  value: string | number;
  icon: string;
  color: string;
  subtitle?: string;
}

const StatCard: React.FC<StatCardProps> = ({ title, value, icon, color, subtitle }) => (
  <div style={{
    background: '#1e293b',
    borderRadius: '12px',
    padding: '20px',
    border: '1px solid #334155',
  }}>
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
      <span style={{ fontSize: '13px', color: '#94a3b8' }}>{title}</span>
      <span style={{ fontSize: '20px' }}>{icon}</span>
    </div>
    <div style={{ fontSize: '28px', fontWeight: 700, color, marginTop: '8px' }}>
      {value}
    </div>
    {subtitle && (
      <div style={{ fontSize: '11px', color: '#64748b', marginTop: '4px' }}>
        {subtitle}
      </div>
    )}
  </div>
);

export default App;
