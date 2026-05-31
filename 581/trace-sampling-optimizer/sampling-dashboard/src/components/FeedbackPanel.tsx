import React, { useState } from 'react';
import { submitFeedbackSignal, fetchFeedbackAnalysis, FeedbackAnalysis } from '../api/apiClient';

interface Props {
  services: string[];
  onRefresh: () => void;
}

const SIGNAL_TYPES = [
  'ERROR_RATE_INCREASED',
  'LATENCY_DEGRADED',
  'MISSING_CRITICAL_TRACE',
  'FALSE_POSITIVE_ANOMALY',
  'COST_OVERRUN',
  'OBSERVABILITY_GAP',
  'SAMPLING_EFFECTIVE',
];

const SIGNAL_LABELS: Record<string, string> = {
  ERROR_RATE_INCREASED: '🔴 错误率上升',
  LATENCY_DEGRADED: '🟡 延迟劣化',
  MISSING_CRITICAL_TRACE: '🟠 关键链路缺失',
  FALSE_POSITIVE_ANOMALY: '🔵 误报异常',
  COST_OVERRUN: '💰 成本超支',
  OBSERVABILITY_GAP: '👁️ 可观测性不足',
  SAMPLING_EFFECTIVE: '✅ 采样有效',
};

const FeedbackPanel: React.FC<Props> = ({ services, onRefresh }) => {
  const [selectedService, setSelectedService] = useState(services[0] || '');
  const [signalType, setSignalType] = useState(SIGNAL_TYPES[0]);
  const [severity, setSeverity] = useState(0.5);
  const [description, setDescription] = useState('');
  const [analysis, setAnalysis] = useState<FeedbackAnalysis | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState('');

  const handleSubmit = async () => {
    if (!selectedService) return;
    setSubmitting(true);
    setMessage('');
    try {
      await submitFeedbackSignal({
        serviceName: selectedService,
        signalType,
        severity,
        description,
      });
      setMessage('✅ 反馈信号已提交');
      onRefresh();
    } catch {
      setMessage('❌ 提交失败');
    }
    setSubmitting(false);
    setTimeout(() => setMessage(''), 3000);
  };

  const handleAnalyze = async () => {
    if (!selectedService) return;
    try {
      const res = await fetchFeedbackAnalysis(selectedService);
      setAnalysis(res.data);
    } catch {
      console.error('Failed to fetch analysis');
    }
  };

  return (
    <div style={{
      background: '#1e293b',
      borderRadius: '12px',
      padding: '20px',
      border: '1px solid #334155',
    }}>
      <h3 style={{ margin: '0 0 16px', fontSize: '16px', fontWeight: 600, color: '#f1f5f9' }}>
        🔄 反馈闭环控制
      </h3>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
        {}
        <div>
          <h4 style={{ margin: '0 0 12px', fontSize: '14px', color: '#cbd5e1' }}>提交反馈信号</h4>

          <div style={{ marginBottom: '12px' }}>
            <label style={{ fontSize: '12px', color: '#94a3b8', display: 'block', marginBottom: '4px' }}>
              服务名称
            </label>
            <select
              value={selectedService}
              onChange={(e) => setSelectedService(e.target.value)}
              style={{
                width: '100%',
                padding: '8px 10px',
                borderRadius: '6px',
                border: '1px solid #334155',
                background: '#0f172a',
                color: '#f1f5f9',
                fontSize: '13px',
              }}
            >
              {services.map((svc) => (
                <option key={svc} value={svc}>{svc}</option>
              ))}
            </select>
          </div>

          <div style={{ marginBottom: '12px' }}>
            <label style={{ fontSize: '12px', color: '#94a3b8', display: 'block', marginBottom: '4px' }}>
              信号类型
            </label>
            <select
              value={signalType}
              onChange={(e) => setSignalType(e.target.value)}
              style={{
                width: '100%',
                padding: '8px 10px',
                borderRadius: '6px',
                border: '1px solid #334155',
                background: '#0f172a',
                color: '#f1f5f9',
                fontSize: '13px',
              }}
            >
              {SIGNAL_TYPES.map((t) => (
                <option key={t} value={t}>{SIGNAL_LABELS[t]}</option>
              ))}
            </select>
          </div>

          <div style={{ marginBottom: '12px' }}>
            <label style={{ fontSize: '12px', color: '#94a3b8', display: 'block', marginBottom: '4px' }}>
              严重程度: {severity.toFixed(2)}
            </label>
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={severity}
              onChange={(e) => setSeverity(parseFloat(e.target.value))}
              style={{ width: '100%' }}
            />
          </div>

          <div style={{ marginBottom: '12px' }}>
            <label style={{ fontSize: '12px', color: '#94a3b8', display: 'block', marginBottom: '4px' }}>
              描述
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="描述反馈原因..."
              rows={3}
              style={{
                width: '100%',
                padding: '8px 10px',
                borderRadius: '6px',
                border: '1px solid #334155',
                background: '#0f172a',
                color: '#f1f5f9',
                fontSize: '13px',
                resize: 'vertical',
              }}
            />
          </div>

          <button
            onClick={handleSubmit}
            disabled={submitting}
            style={{
              width: '100%',
              padding: '10px',
              borderRadius: '6px',
              border: 'none',
              background: submitting ? '#475569' : '#3b82f6',
              color: '#fff',
              fontSize: '14px',
              fontWeight: 600,
              cursor: submitting ? 'not-allowed' : 'pointer',
            }}
          >
            {submitting ? '提交中...' : '📤 提交反馈'}
          </button>

          {message && (
            <div style={{
              marginTop: '8px',
              padding: '8px',
              borderRadius: '6px',
              background: message.includes('✅') ? '#064e3b' : '#450a0a',
              color: message.includes('✅') ? '#6ee7b7' : '#fca5a5',
              fontSize: '13px',
              textAlign: 'center',
            }}>
              {message}
            </div>
          )}
        </div>

        {}
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <h4 style={{ margin: 0, fontSize: '14px', color: '#cbd5e1' }}>反馈分析</h4>
            <button
              onClick={handleAnalyze}
              style={{
                padding: '6px 14px',
                borderRadius: '6px',
                border: '1px solid #334155',
                background: '#0f172a',
                color: '#94a3b8',
                fontSize: '12px',
                cursor: 'pointer',
              }}
            >
              📊 刷新分析
            </button>
          </div>

          {analysis ? (
            <div style={{ background: '#0f172a', borderRadius: '8px', padding: '16px' }}>
              <div style={{ fontSize: '13px', color: '#f1f5f9', marginBottom: '12px', fontWeight: 600 }}>
                {analysis.serviceName}
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                <MiniStat label="总信号数" value={analysis.totalSignals} />
                <MiniStat label="平均严重度" value={analysis.avgSeverity.toFixed(2)} />
                <MiniStat label="错误率信号" value={analysis.errorRateSignals} color="#ef4444" />
                <MiniStat label="延迟信号" value={analysis.latencySignals} color="#f59e0b" />
                <MiniStat label="链路缺失" value={analysis.missingTraceSignals} color="#f97316" />
                <MiniStat label="成本超支" value={analysis.costOverrunSignals} color="#ec4899" />
                <MiniStat label="采样有效" value={analysis.effectiveSignals} color="#10b981" />
              </div>
            </div>
          ) : (
            <div style={{
              background: '#0f172a',
              borderRadius: '8px',
              padding: '40px 16px',
              textAlign: 'center',
              color: '#475569',
              fontSize: '13px',
            }}>
              选择服务并点击刷新分析查看反馈数据
            </div>
          )}

          {}
          <div style={{
            marginTop: '16px',
            background: '#0f172a',
            borderRadius: '8px',
            padding: '16px',
          }}>
            <h4 style={{ margin: '0 0 10px', fontSize: '13px', color: '#cbd5e1' }}>闭环流程</h4>
            <div style={{ fontSize: '12px', color: '#94a3b8', lineHeight: '1.8' }}>
              <div>1️⃣ 提交反馈信号 → 信号入队</div>
              <div>2️⃣ 信号批处理 → 计算调整值</div>
              <div>3️⃣ RL Agent 学习 → 更新 Q 表</div>
              <div>4️⃣ 采样率调整 → 环境步进</div>
              <div>5️⃣ 效果评估 → 奖励反馈</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

const MiniStat: React.FC<{
  label: string;
  value: string | number;
  color?: string;
}> = ({ label, value, color }) => (
  <div style={{
    padding: '6px 8px',
    background: '#1e293b',
    borderRadius: '6px',
  }}>
    <div style={{ fontSize: '11px', color: '#64748b' }}>{label}</div>
    <div style={{ fontSize: '16px', fontWeight: 600, color: color || '#f1f5f9' }}>{value}</div>
  </div>
);

export default FeedbackPanel;
