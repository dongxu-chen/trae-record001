import React from 'react';
import { SamplingRate } from '../api/apiClient';

interface Props {
  rates: Record<string, SamplingRate>;
}

const SamplingRateChart: React.FC<Props> = ({ rates }) => {
  const entries = Object.entries(rates).sort((a, b) => b[1].rate - a[1].rate);

  const maxRate = 1.0;
  const chartHeight = 300;
  const barWidth = Math.min(60, Math.max(20, 600 / entries.length));
  const gap = 8;
  const svgWidth = entries.length * (barWidth + gap) + 80;
  const chartLeft = 50;
  const chartBottom = chartHeight - 40;
  const chartTop = 20;
  const chartAreaHeight = chartBottom - chartTop;

  const yTicks = [0, 0.25, 0.5, 0.75, 1.0];

  return (
    <div style={{
      background: '#1e293b',
      borderRadius: '12px',
      padding: '20px',
      border: '1px solid #334155',
    }}>
      <h3 style={{ margin: '0 0 16px', fontSize: '16px', fontWeight: 600, color: '#f1f5f9' }}>
        📈 各服务采样率分布
      </h3>
      <div style={{ overflowX: 'auto' }}>
        <svg width={svgWidth} height={chartHeight} viewBox={`0 0 ${svgWidth} ${chartHeight}`}>
          {}
          {yTicks.map((tick) => {
            const y = chartBottom - (tick / maxRate) * chartAreaHeight;
            return (
              <g key={tick}>
                <line
                  x1={chartLeft} y1={y} x2={svgWidth - 10} y2={y}
                  stroke="#334155" strokeWidth="1" strokeDasharray="4,4"
                />
                <text x={chartLeft - 8} y={y + 4} textAnchor="end"
                      fill="#94a3b8" fontSize="11">{`${(tick * 100).toFixed(0)}%`}</text>
              </g>
            );
          })}

          {}
          {entries.map(([name, rate], i) => {
            const x = chartLeft + i * (barWidth + gap) + gap;
            const barHeight = (rate.rate / maxRate) * chartAreaHeight;
            const y = chartBottom - barHeight;

            const prevBarHeight = (rate.previousRate / maxRate) * chartAreaHeight;
            const prevY = chartBottom - prevBarHeight;

            const color =
              rate.rate >= 0.7 ? '#10b981' :
              rate.rate >= 0.4 ? '#f59e0b' :
              rate.rate >= 0.1 ? '#3b82f6' : '#6366f1';

            const shortName = name.replace('-service', '').substring(0, 8);

            return (
              <g key={name}>
                {}
                <rect
                  x={x} y={prevY} width={barWidth} height={prevBarHeight}
                  fill={color} opacity="0.15" rx="3"
                />
                {}
                <rect
                  x={x} y={y} width={barWidth} height={barHeight}
                  fill={color} opacity="0.85" rx="3"
                >
                  <animate attributeName="height" from="0" to={barHeight} dur="0.5s" fill="freeze" />
                  <animate attributeName="y" from={chartBottom} to={y} dur="0.5s" fill="freeze" />
                </rect>
                {}
                <text x={x + barWidth / 2} y={y - 6} textAnchor="middle"
                      fill="#f8fafc" fontSize="10" fontWeight="600">
                  {(rate.rate * 100).toFixed(0)}%
                </text>
                {}
                <text x={x + barWidth / 2} y={chartBottom + 16} textAnchor="middle"
                      fill="#94a3b8" fontSize="10" transform={`rotate(-30, ${x + barWidth / 2}, ${chartBottom + 16})`}>
                  {shortName}
                </text>
              </g>
            );
          })}

          {}
          <line x1={chartLeft} y1={chartBottom} x2={svgWidth - 10} y2={chartBottom}
                stroke="#475569" strokeWidth="1" />
        </svg>
      </div>

      {}
      <div style={{ display: 'flex', gap: '16px', marginTop: '12px', justifyContent: 'center' }}>
        <Legend color="#10b981" label="高采样 (≥70%)" />
        <Legend color="#f59e0b" label="中采样 (40-70%)" />
        <Legend color="#3b82f6" label="低采样 (10-40%)" />
        <Legend color="#6366f1" label="极低 (<10%)" />
      </div>
    </div>
  );
};

const Legend: React.FC<{ color: string; label: string }> = ({ color, label }) => (
  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', color: '#94a3b8' }}>
    <div style={{ width: '12px', height: '12px', borderRadius: '2px', background: color }} />
    {label}
  </div>
);

export default SamplingRateChart;
