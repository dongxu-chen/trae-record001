import React from 'react';
import ReactECharts from 'echarts-for-react';
import { RealtimeMetrics } from '../types';

interface LatencyChartProps {
  data: RealtimeMetrics[];
}

const LatencyChart: React.FC<LatencyChartProps> = ({ data }) => {
  const times = data.map((m) => new Date(m.timestamp).toLocaleTimeString());

  const option = {
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(255, 255, 255, 0.95)',
      borderColor: '#e5e7eb',
      borderWidth: 1,
      textStyle: {
        color: '#374151',
      },
    },
    legend: {
      data: ['P50', 'P95', 'P99'],
      top: 0,
      right: 0,
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: '15%',
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: times,
      axisLine: {
        lineStyle: {
          color: '#e5e7eb',
        },
      },
      axisLabel: {
        color: '#6b7280',
        fontSize: 11,
      },
      splitLine: {
        show: true,
        lineStyle: {
          color: '#f3f4f6',
          type: 'dashed',
        },
      },
    },
    yAxis: {
      type: 'value',
      name: '延迟 (μs)',
      nameTextStyle: {
        color: '#6b7280',
        fontSize: 12,
      },
      axisLine: {
        show: false,
      },
      axisTick: {
        show: false,
      },
      axisLabel: {
        color: '#6b7280',
        fontSize: 11,
      },
      splitLine: {
        lineStyle: {
          color: '#f3f4f6',
          type: 'dashed',
        },
      },
    },
    series: [
      {
        name: 'P50',
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 4,
        data: data.map((m) => m.p50Latency),
        lineStyle: {
          width: 2,
          color: '#10b981',
        },
        itemStyle: {
          color: '#10b981',
        },
      },
      {
        name: 'P95',
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 4,
        data: data.map((m) => m.p95Latency),
        lineStyle: {
          width: 2,
          color: '#f59e0b',
        },
        itemStyle: {
          color: '#f59e0b',
        },
      },
      {
        name: 'P99',
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 4,
        data: data.map((m) => m.p99Latency),
        lineStyle: {
          width: 2,
          color: '#ef4444',
        },
        itemStyle: {
          color: '#ef4444',
        },
      },
    ],
  };

  return (
    <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
      <h3 className="text-lg font-semibold text-gray-800 mb-4">延迟分位统计</h3>
      <ReactECharts option={option} style={{ height: '300px' }} />
    </div>
  );
};

export default LatencyChart;
