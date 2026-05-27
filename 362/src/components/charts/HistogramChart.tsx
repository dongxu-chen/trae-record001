import React, { useMemo } from 'react';
import ReactECharts from 'echarts-for-react';
import type { ColumnStats } from '../../types';

interface HistogramChartProps {
  columns: ColumnStats[];
  selectedColumn?: string;
  className?: string;
}

export const HistogramChart: React.FC<HistogramChartProps> = ({
  columns,
  selectedColumn,
  className = '',
}) => {
  const option = useMemo(() => {
    const numericCols = columns.filter((c) => c.type === 'numeric');
    if (numericCols.length === 0) {
      return {
        backgroundColor: 'transparent',
        title: {
          text: '数值分布直方图',
          textStyle: { color: '#94a3b8', fontSize: 13, fontWeight: 'normal' },
          left: 'center',
          top: 10,
        },
        graphic: {
          type: 'text',
          left: 'center',
          top: 'middle',
          style: {
            text: '无数值列可显示',
            fill: '#64748b',
            fontSize: 14,
          },
        },
      };
    }

    const targetCol = selectedColumn
      ? numericCols.find((c) => c.name === selectedColumn) || numericCols[0]
      : numericCols[0];

    const histogram = targetCol.histogram || { bins: [], counts: [] };
    const binLabels = histogram.bins.map((bin, i) =>
      i < histogram.bins.length - 1
        ? `${bin.toFixed(1)} - ${histogram.bins[i + 1].toFixed(1)}`
        : `${bin.toFixed(1)}+`
    );

    return {
      backgroundColor: 'transparent',
      title: {
        text: `${targetCol.name} - 数值分布`,
        textStyle: { color: '#94a3b8', fontSize: 13, fontWeight: 'normal' },
        left: 'center',
        top: 10,
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        backgroundColor: '#1e293b',
        borderColor: '#475569',
        textStyle: { color: '#e2e8f0' },
        formatter: (params: any) => {
          const item = params[0];
          return `<div style="font-family: monospace;">
            <div style="font-weight: bold; margin-bottom: 4px;">${item.name}</div>
            <div>数量: ${item.data}</div>
          </div>`;
        },
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '10%',
        top: 50,
        containLabel: true,
      },
      xAxis: {
        type: 'category',
        data: binLabels,
        axisLabel: {
          color: '#64748b',
          rotate: 30,
          fontSize: 10,
          interval: 0,
        },
        axisLine: { lineStyle: { color: '#475569' } },
      },
      yAxis: {
        type: 'value',
        axisLabel: { color: '#64748b', fontSize: 11 },
        axisLine: { lineStyle: { color: '#475569' } },
        splitLine: { lineStyle: { color: '#334155' } },
      },
      series: [
        {
          type: 'bar',
          data: histogram.counts,
          itemStyle: {
            color: {
              type: 'linear',
              x: 0,
              y: 0,
              x2: 0,
              y2: 1,
              colorStops: [
                { offset: 0, color: '#3b82f6' },
                { offset: 1, color: '#1e40af' },
              ],
            },
            borderRadius: [4, 4, 0, 0],
          },
        },
      ],
    };
  }, [columns, selectedColumn]);

  return (
    <div className={className}>
      <ReactECharts option={option} style={{ height: '100%', minHeight: 250 }} />
    </div>
  );
};
