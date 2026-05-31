import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

function LatencyPanel({ latency }) {
  if (!latency) {
    return (
      <div className="card">
        <div className="card-header">
          <h2>处理延迟监控</h2>
        </div>
        <div className="card-body">
          <div className="empty">暂无数据</div>
        </div>
      </div>
    );
  }

  const chartData = [
    { name: 'P50', value: latency.P50Ms || 0 },
    { name: 'P95', value: latency.P95Ms || 0 },
    { name: 'P99', value: latency.P99Ms || 0 },
    { name: 'Avg', value: latency.AvgMs || 0 },
    { name: 'Max', value: latency.MaxMs || 0 },
  ];

  return (
    <div className="card">
      <div className="card-header">
        <h2>处理延迟监控 (ms)</h2>
      </div>
      <div className="card-body">
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px', marginBottom: '20px' }}>
          <div className="stat-card" style={{ padding: '12px', margin: 0 }}>
            <div className="label">平均延迟</div>
            <div className="value" style={{ fontSize: '18px' }}>
              {latency.AvgMs?.toFixed(2) || 0} ms
            </div>
          </div>
          <div className="stat-card" style={{ padding: '12px', margin: 0 }}>
            <div className="label">P99 延迟</div>
            <div className="value" style={{ fontSize: '18px' }}>
              {latency.P99Ms?.toFixed(2) || 0} ms
            </div>
          </div>
          <div className="stat-card" style={{ padding: '12px', margin: 0 }}>
            <div className="label">样本数</div>
            <div className="value" style={{ fontSize: '18px' }}>
              {latency.Count || 0}
            </div>
          </div>
        </div>
        <div className="chart-container" style={{ height: '200px' }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="value" fill="#1890ff" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}

export default LatencyPanel;
