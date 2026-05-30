import React, { useState } from 'react';
import ReactECharts from 'echarts-for-react';
import { BarChart2, LineChart, PieChart } from 'lucide-react';
import { PivotResult, ChartType } from '@/types';
import { useChartData } from '@/hooks/useChartData';

interface ChartPanelProps {
  pivotResult: PivotResult;
}

export const ChartPanel: React.FC<ChartPanelProps> = ({ pivotResult }) => {
  const [chartType, setChartType] = useState<ChartType>('bar');
  const chartOption = useChartData(pivotResult, chartType);

  const chartTypes: { type: ChartType; icon: React.ReactNode; label: string }[] = [
    { type: 'bar', icon: <BarChart2 size={18} />, label: '柱状图' },
    { type: 'line', icon: <LineChart size={18} />, label: '折线图' },
    { type: 'pie', icon: <PieChart size={18} />, label: '饼图' },
  ];

  return (
    <div className="h-full flex flex-col bg-white rounded-xl shadow-card p-4">
      <div className="flex items-center justify-between mb-4 pb-3 border-b border-gray-100">
        <h3 className="text-lg font-semibold text-gray-800">数据可视化</h3>
        <div className="flex gap-1">
          {chartTypes.map(ct => (
            <button
              key={ct.type}
              onClick={() => setChartType(ct.type)}
              className={`
                flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium
                transition-all duration-200
                ${chartType === ct.type
                  ? 'bg-primary-500 text-white shadow-md'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }
              `}
              title={ct.label}
            >
              {ct.icon}
              <span className="hidden sm:inline">{ct.label}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 min-h-0">
        <ReactECharts
          option={chartOption}
          style={{ height: '100%', width: '100%' }}
          opts={{ renderer: 'canvas' }}
        />
      </div>
    </div>
  );
};
