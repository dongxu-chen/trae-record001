import React, { useMemo } from 'react';
import ReactECharts from 'echarts-for-react';
import type { ColumnStats } from '../../types';

interface MissingHeatmapChartProps {
  columns: ColumnStats[];
  title?: string;
  className?: string;
}

export const MissingHeatmapChart: React.FC<MissingHeatmapChartProps> = ({
  columns,
  title = '缺失值分布',
  className = '',
}) => {
  const option = useMemo(() => {
    const data = columns.map((col) => ({
      name: col.name,
      value: col.missingPercent,
      count: col.missingCount,
    }));

    return {
      backgroundColor: 'transparent',
      title: {
        text: title,
        textStyle: {
          color: '#94a3b8',
          fontSize: 13,
          fontWeight: 'normal',
        },
        left: 'center',
        top: 10,
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'shadow',
        },
        formatter: (params: any) => {
          const item = params[0];
          return `<div style="font-family: monospace;">
            <div style="font-weight: bold; margin-bottom: 4px;">${item.name}</div>
            <div>缺失值: ${item.data.count} 个</div>
            <div>占比: ${item.data.value.toFixed(2)}%</div>
          </div>`;
        },
        backgroundColor: '#1e293b',
        borderColor: '#475569',
        textStyle: {
          color: '#e2e8f0',
        },
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        top: 50,
        containLabel: true,
      },
      xAxis: {
        type: 'category',
        data: data.map((d) => d.name),
        axisLabel: {
          color: '#64748b',
          rotate: 45,
          fontSize: 11,
        },
        axisLine: {
          lineStyle: {
            color: '#475569',
          },
        },
      },
      yAxis: {
        type: 'value',
        max: 100,
        axisLabel: {
          color: '#64748b',
          fontSize: 11,
          formatter: '{value}%',
        },
        axisLine: {
          lineStyle: {
            color: '#475569',
          },
        },
        splitLine: {
          lineStyle: {
            color: '#334155',
          },
        },
      },
      series: [
        {
          type: 'bar',
          data: data,
          itemStyle: {
            color: (params: any) => {
              const value = params.data.value;
              if (value === 0) return '#10b981';
              if (value < 10) return '#f59e0b';
              if (value < 30) return '#f97316';
              return '#ef4444';
            },
            borderRadius: [4, 4, 0, 0],
          },
          emphasis: {
            itemStyle: {
              shadowBlur: 10,
              shadowColor: 'rgba(59, 130, 246, 0.5)',
            },
          },
        },
      ],
    };
  }, [columns, title]);

  return (
    <div className={className}>
      <ReactECharts option={option} style={{ height: '100%', minHeight: 200 }} />
    </div>
  );
};
