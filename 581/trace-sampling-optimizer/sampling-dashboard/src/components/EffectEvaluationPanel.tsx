import React, { useState, useEffect } from 'react';
import {
  fetchAllEvaluations,
  SamplingEffectReport,
  OverallEvaluation,
} from '../api/apiClient';

interface Props {}

const EffectEvaluationPanel: React.FC<Props> = () => {
  const [overallEvaluation, setOverallEvaluation] = useState<OverallEvaluation | null>(null);
  const [serviceEvaluations, setServiceEvaluations] = useState<Record<string, SamplingEffectReport>>({});
  const [activeTab, setActiveTab] = useState<'overall' | 'service'>('overall');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadEvaluations = async () => {
      try {
        const res = await fetchAllEvaluations();
        const data = res.data;
        const overall = data._overall as OverallEvaluation;
        const services: Record<string, SamplingEffectReport> = {};
        for (const [key, value] of Object.entries(data)) {
          if (key !== '_overall') {
            services[key] = value as SamplingEffectReport;
          }
        }
        setOverallEvaluation(overall);
        setServiceEvaluations(services);
      } catch (e) {
        console.error('Failed to load evaluations', e);
      } finally {
        setLoading(false);
      }
    };
    loadEvaluations();
    const interval = setInterval(loadEvaluations, 10000);
    return () => clearInterval(interval);
  }, []);

  if (loading || !overallEvaluation) {
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
        加载评估数据中...
      </div>
    );
  }

  const problemTypeLabels: Record<string, string> = {
    ERROR_SPIKE: '错误突增',
    LATENCY_SPIKE: '延迟突增',
    BUSINESS_ANOMALY: '业务异常',
    DEPENDENCY_FAILURE: '依赖失败',
    RESOURCE_EXHAUSTION: '资源耗尽',
    UNCLASSIFIED: '未分类',
  };

  return (
    <div style={{
      background: '#1e293b',
      borderRadius: '12px',
      padding: '20px',
      border: '1px solid #334155',
    }}>
      <h3 style={{ margin: '0 0 12px', fontSize: '16px', fontWeight: 600, color: '#f1f5f9' }}>
        📊 采样效果评估
      </h3>

      <div style={{ display: 'flex', gap: '4px', marginBottom: '12px' }}>
        {(['overall', 'service'] as const).map((tab) => (
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
            {tab === 'overall' ? '总览' : '服务明细'}
          </button>
        ))}
      </div>

      {activeTab === 'overall' && (
        <div>
          {}
          <div style={{ textAlign: 'center', marginBottom: '16px', padding: '16px', background: '#0f172a', borderRadius: '8px' }}>
            <div style={{ fontSize: '11px', color: '#64748b', marginBottom: '4px' }}>整体问题发现率</div>
            <div style={{ fontSize: '32px', fontWeight: 800, color: overallEvaluation.overallDetectionRate >= 0.95 ? '#10b981' : overallEvaluation.overallDetectionRate >= 0.8 ? '#f59e0b' : '#ef4444' }}>
              {(overallEvaluation.overallDetectionRate * 100).toFixed(1)}%
            </div>
            <div style={{ fontSize: '11px', color: '#94a3b8', marginTop: '4px' }}>
              目标: 95%+
            </div>
          </div>

          {}
          <div style={{ marginBottom: '12px' }}>
            <h4 style={{ margin: '0 0 8px', fontSize: '12px', color: '#94a3b8' }}>按问题类型发现率</h4>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px' }}>
              {Object.entries(overallEvaluation.detectionRateByProblemType || {}).map(([type, rate]) => (
                <div key={type} style={{ background: '#0f172a', borderRadius: '6px', padding: '8px' }}>
                  <div style={{ fontSize: '10px', color: '#64748b' }}>
                    {problemTypeLabels[type] || type}
                  </div>
                  <div style={{ fontSize: '14px', fontWeight: 700, color: rate >= 0.9 ? '#10b981' : rate >= 0.7 ? '#f59e0b' : '#ef4444' }}>
                    {(rate * 100).toFixed(0)}%
                  </div>
                </div>
              ))}
            </div>
          </div>

          {}
          <div>
            <h4 style={{ margin: '0 0 8px', fontSize: '12px', color: '#94a3b8' }}>采样率 vs 发现率相关性</h4>
            <div style={{ background: '#0f172a', borderRadius: '6px', padding: '10px' }}>
              {Object.entries(overallEvaluation.samplingRateDetectionCorrelation || {}).slice(0, 5).map(([rate, detectionRate]) => (
                <div key={rate} style={{ marginBottom: '6px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', marginBottom: '2px' }}>
                    <span style={{ color: '#cbd5e1' }}>采样率 {(Number(rate) * 100).toFixed(0)}%</span>
                    <span style={{ color: '#10b981', fontWeight: 600 }}>{(detectionRate * 100).toFixed(0)}% 发现</span>
                  </div>
                  <div style={{ background: '#1e293b', borderRadius: '3px', height: '4px' }}>
                    <div style={{
                      width: `${detectionRate * 100}%`,
                      height: '100%',
                      background: 'linear-gradient(90deg, #3b82f6, #10b981)',
                      borderRadius: '3px',
                    }} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {activeTab === 'service' && (
        <div style={{ maxHeight: '350px', overflowY: 'auto' }}>
          {Object.entries(serviceEvaluations)
            .sort((a, b) => b[1].detectionRate - a[1].detectionRate)
            .map(([serviceName, report]) => (
              <div
                key={serviceName}
                style={{
                  background: '#0f172a',
                  borderRadius: '8px',
                  padding: '10px',
                  marginBottom: '8px',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                  <span style={{ fontSize: '12px', fontWeight: 600, color: '#f1f5f9' }}>
                    {serviceName.replace('-service', '')}
                  </span>
                  <span style={{
                    fontSize: '12px',
                    fontWeight: 700,
                    color: report.detectionRate >= 0.95 ? '#10b981' : report.detectionRate >= 0.8 ? '#f59e0b' : '#ef4444',
                  }}>
                    {(report.detectionRate * 100).toFixed(1)}%
                  </span>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4px', fontSize: '10px' }}>
                  <div>
                    <span style={{ color: '#64748b' }}>发现/总数: </span>
                    <span style={{ color: '#cbd5e1' }}>{report.problemsDetected}/{report.totalProblems}</span>
                  </div>
                  <div>
                    <span style={{ color: '#64748b' }}>变化: </span>
                    <span style={{ color: report.detectionRateChange >= 0 ? '#10b981' : '#ef4444', fontWeight: 600 }}>
                      {report.detectionRateChange >= 0 ? '+' : ''}{(report.detectionRateChange * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div>
                    <span style={{ color: '#64748b' }}>平均采样: </span>
                    <span style={{ color: '#60a5fa' }}>{(report.averageSamplingRate * 100).toFixed(1)}%</span>
                  </div>
                  <div>
                    <span style={{ color: '#64748b' }}>成本效率: </span>
                    <span style={{ color: '#fbbf24' }}>{report.costEfficiency.toFixed(2)}</span>
                  </div>
                </div>
              </div>
            ))}
          {Object.keys(serviceEvaluations).length === 0 && (
            <div style={{ textAlign: 'center', color: '#64748b', padding: '20px' }}>
              暂无服务评估数据
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default EffectEvaluationPanel;
