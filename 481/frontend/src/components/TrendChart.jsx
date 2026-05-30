import React from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';

const DIMENSION_COLORS = {
  overallScore: '#3b82f6',
  durationScore: '#a855f7',
  successRateScore: '#22c55e',
  frequencyScore: '#eab308',
  resourceScore: '#f97316',
};

const DIMENSION_LABELS = {
  overallScore: '综合评分',
  durationScore: '执行时长',
  successRateScore: '成功率',
  frequencyScore: '执行频率',
  resourceScore: '资源消耗',
};

export default function TrendChart({ trend }) {
  if (!trend || trend.length === 0) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 300, color: 'var(--text-muted)' }}>
        暂无趋势数据
      </div>
    );
  }

  const data = trend.map(p => ({
    ...p,
    time: p.timestamp ? p.timestamp.split(' ')[1]?.substring(0, 5) || p.timestamp : '',
  }));

  return (
    <div className="trend-container">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis dataKey="time" stroke="#64748b" tick={{ fontSize: 11 }} />
          <YAxis domain={[0, 100]} stroke="#64748b" tick={{ fontSize: 11 }} />
          <Tooltip
            contentStyle={{
              background: '#1e293b',
              border: '1px solid #334155',
              borderRadius: 8,
              color: '#f1f5f9',
              fontSize: 12,
            }}
          />
          <Legend wrapperStyle={{ fontSize: 12, color: '#94a3b8' }} />
          {Object.keys(DIMENSION_COLORS).map(key => (
            <Line
              key={key}
              type="monotone"
              dataKey={key}
              name={DIMENSION_LABELS[key]}
              stroke={DIMENSION_COLORS[key]}
              strokeWidth={key === 'overallScore' ? 2.5 : 1.5}
              dot={false}
              activeDot={{ r: 4 }}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
