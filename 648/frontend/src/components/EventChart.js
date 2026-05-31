import React from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';

function EventChart({ stats }) {
  if (!stats || !stats.stats) return null;

  const data = [
    { name: '过期事件', value: stats.stats.ExpiredEvents || 0, color: '#f5222d' },
    { name: '删除事件', value: stats.stats.DeletedEvents || 0, color: '#faad14' },
    { name: '新增事件', value: stats.stats.SetEvents || 0, color: '#52c41a' }
  ].filter(item => item.value > 0);

  if (data.length === 0) {
    return (
      <div className="empty" style={{ padding: '80px 0' }}>
        暂无数据
      </div>
    );
  }

  return (
    <div className="chart-container">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius={60}
            outerRadius={100}
            paddingAngle={5}
            dataKey="value"
          >
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}

export default EventChart;
