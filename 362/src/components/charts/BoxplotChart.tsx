import React, { useMemo } from 'react';
import ReactECharts from 'echarts-for-react';
import type { ColumnStats } from '../../types';

interface BoxplotChartProps {
  columns: ColumnStats[];
  title?: string;
  className?: string;
}

export const BoxplotChart: React.FC<BoxplotChartProps> = ({
  columns,
  title = '异常值检测 (箱线图)',
  className = '',
}) => {
  const option = useMemo(() => {
    const numericCols = columns.filter((c) => c.type === 'numeric');
    if (numericCols.length === 0) {
      return {
        backgroundColor: 'transparent',
        title: {
          text: title,
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

    const boxData = numericCols.map((col) => [
      col.min !== undefined ? col.min : 0,
      col.q1 !== undefined ? col.q1 : 0,
      col.median !== undefined ? col.median : 0,
      col.q3 !== undefined ? col.q3 : 0,
      col.max !== undefined ? col.max : 0,
    ]);

    const outlierData: [string, number][] = [];
    numericCols.forEach((col, colIndex) => {
      if (col.outliers && col.outliers.length > 0) {
        col.outliers.forEach((value) => {
          outlierData.push([colIndex, value]);
        });
      }
    });

    return {
      backgroundColor: 'transparent',
      title: {
        text: title,
        textStyle: { color: '#94a3b8', fontSize: 13, fontWeight: 'normal' },
        left: 'center',
        top: 10,
      },
      tooltip: {
        trigger: 'item',
        backgroundColor: '#1e293b',
        borderColor: '#475569',
        textStyle: { color: '#e2e8f0' },
        formatter: (params: any) => {
          if (params.seriesType === 'boxplot') {
            const data = params.data;
            return `<div style="font-family: monospace;">
              <div style="font-weight: bold; margin-bottom: 4px;">${params.name}</div>
              <div>最小值: ${data[0]}</div>
              <div>Q1: ${data[1]}</div>
              <div>中位数: ${data[2]}</div>
              <div>Q3: ${data[3]}</div>
              <div>最大值: ${data[4]}</div>
            </div>`;
          } else {
            return `<div style="font-family: monospace;">
              <div style="color: #ef4444; font-weight: bold;">异常值</div>
              <div>${params.data[1]}</div>
            </div>`;
          }
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
        data: numericCols.map((c) => c.name),
        axisLabel: {
          color: '#64748b',
          rotate: 30,
          fontSize: 11,
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
          name: '箱线图',
          type: 'boxplot',
          data: boxData,
          itemStyle: {
            color: '#3b82f6',
            borderColor: '#60a5fa',
          },
          emphasis: {
            itemStyle: {
              color: '#2563eb',
            },
          },
        },
        {
          name: '异常值',
          type: 'scatter',
          data: outlierData,
          itemStyle: {
            color: '#ef4444',
          },
          symbolSize: 8,
        },
      ],
    };
  }, [columns, title]);

  return (
    <div className={className}>
      <ReactECharts option={option} style={{ height: '100%', minHeight: 300 }} />
    </div>
  );
};
