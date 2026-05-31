import React from 'react';

function formatCPU(v) {
  return (v / 1000).toFixed(2) + ' cores';
}

function formatMemory(v) {
  return (v / (1024 * 1024 * 1024)).toFixed(2) + ' GiB';
}

function formatQPS(v) {
  return v.toFixed(1) + ' req/s';
}

function formatLatency(v) {
  return (v * 1000).toFixed(1) + ' ms';
}

function formatValue(type, v) {
  switch (type) {
    case 'CPU': return formatCPU(v);
    case 'Memory': return formatMemory(v);
    case 'QPS': return formatQPS(v);
    case 'Latency': return formatLatency(v);
    default: return v.toFixed(2);
  }
}

function getUtilPercent(current, target) {
  if (!target || target === 0) return 0;
  return Math.min((current / target) * 100, 150);
}

function getBarColor(percent) {
  if (percent > 90) return 'red';
  if (percent > 70) return 'yellow';
  return 'green';
}

function getBorderColor(type) {
  switch (type) {
    case 'CPU': return 'border-blue';
    case 'Memory': return 'border-green';
    case 'QPS': return 'border-yellow';
    case 'Latency': return 'border-red';
    default: return 'border-blue';
  }
}

export default function MetricCard({ metric, showFusion }) {
  const utilPercent = getUtilPercent(metric.currentUtilization, metric.targetUtilization);
  const barColor = getBarColor(utilPercent);

  const displayValue = showFusion && metric.weight
    ? `${(metric.currentUtilization * metric.weight).toFixed(2)} × ${metric.weight}`
    : formatValue(metric.type, metric.currentUtilization);

  return (
    <div className={`metric-card ${getBorderColor(metric.type)}`}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <span style={{ fontSize: 13, color: '#94a3b8', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          {metric.type} {showFusion ? '(Fusion)' : ''}
        </span>
        <span style={{ fontSize: 11, color: '#64748b' }}>
          Weight: {metric.weight}
        </span>
      </div>
      <div style={{ fontSize: 24, fontWeight: 700, color: '#f1f5f9', marginBottom: 4 }}>
        {displayValue}
      </div>
      <div style={{ fontSize: 12, color: '#64748b', marginBottom: 12 }}>
        {showFusion ? 'Weighted Ratio' : 'Target'}: {formatValue(metric.type, metric.targetUtilization)}
      </div>
      <div className="progress-bar">
        <div
          className={`progress-bar-fill ${barColor}`}
          style={{ width: `${Math.min(utilPercent, 100)}%` }}
        />
      </div>
      <div style={{ fontSize: 11, color: '#64748b', marginTop: 6, textAlign: 'right' }}>
        {utilPercent.toFixed(0)}% of target
      </div>
    </div>
  );
}
