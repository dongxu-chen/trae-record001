import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Legend,
  Tooltip,
} from 'recharts';
import type { CapacityResult } from '../types';

interface CostBreakdownChartProps {
  result: CapacityResult;
}

function CostBreakdownChart({ result }: CostBreakdownChartProps) {
  const data = [
    { name: '计算成本', value: result.breakdown.computeCost },
    { name: '存储成本', value: result.breakdown.storageCost },
    { name: '网络成本', value: result.breakdown.networkCost },
    { name: '人力成本', value: result.breakdown.laborCost },
  ];

  const COLORS = ['#667eea', '#764ba2', '#f093fb', '#f5576c'];

  return (
    <div style={{ height: '280px', display: 'flex', alignItems: 'center' }}>
      <div style={{ flex: 1 }}>
        <ResponsiveContainer width="100%" height={250}>
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              innerRadius={50}
              outerRadius={80}
              paddingAngle={5}
              dataKey="value"
            >
              {data.map((_, index) => (
                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip
              formatter={(value: number) => [`$${value.toFixed(2)}`, '成本']}
              contentStyle={{
                background: 'white',
                border: '1px solid #e2e8f0',
                borderRadius: '8px',
              }}
            />
            <Legend />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <div style={{ width: '180px', paddingLeft: '20px' }}>
        <div style={{ marginBottom: '12px' }}>
          <div className="result-label">月度总成本</div>
          <div className="result-value orange" style={{ fontSize: '20px' }}>
            ${result.monthlyCost.toFixed(2)}
          </div>
        </div>
        <div style={{ fontSize: '12px', color: '#718096' }}>
          <div>服务器数量: {result.recommendedServers} 台</div>
          <div>单台成本: ${(result.monthlyCost / result.recommendedServers).toFixed(2)}/月</div>
        </div>
      </div>
    </div>
  );
}

export default CostBreakdownChart;
