import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import type { TrafficForecast } from '../types';

interface TrafficChartProps {
  forecast: TrafficForecast;
}

function TrafficChart({ forecast }: TrafficChartProps) {
  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return `${date.getMonth() + 1}/${date.getDate()}`;
  };

  const chartData = [
    ...forecast.historicalData.slice(-14).map((d) => ({
      date: formatDate(d.timestamp),
      requests: d.requestsPerSec,
      type: '历史',
    })),
    ...forecast.predictedData.map((d) => ({
      date: formatDate(d.timestamp),
      requests: d.requestsPerSec,
      type: '预测',
    })),
  ];

  return (
    <div className="chart-container">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis dataKey="date" stroke="#718096" fontSize={12} />
          <YAxis stroke="#718096" fontSize={12} />
          <Tooltip
            contentStyle={{
              background: 'white',
              border: '1px solid #e2e8f0',
              borderRadius: '8px',
              boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
            }}
          />
          <Legend />
          <Line
            type="monotone"
            dataKey="requests"
            stroke="#667eea"
            strokeWidth={2}
            dot={{ fill: '#667eea', r: 3 }}
            activeDot={{ r: 5 }}
            name="请求数/秒"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export default TrafficChart;
