import React, { useMemo, useState } from 'react';
import ReactECharts from 'echarts-for-react';
import type { ColumnStats, DatasetStats } from '../../types';

interface ComparisonChartProps {
  originalStats: DatasetStats;
  cleanedStats: DatasetStats;
  className?: string;
}

export const ComparisonChart: React.FC<ComparisonChartProps> = ({
  originalStats,
  cleanedStats,
  className = '',
}) => {
  const [selectedMetric, setSelectedMetric] = useState<'missing' | 'outliers' | 'unique'>('missing');

  const option = useMemo(() => {
    const numericCols = originalStats.columns.filter((c) => c.type === 'numeric');
    const labels = originalStats.columns.map((c) => c.name);

    let originalData: number[] = [];
    let cleanedData: number[] = [];
    let titleText = '';
    let yAxisLabel = '';

    switch (selectedMetric) {
      case 'missing':
        originalData = originalStats.columns.map((c) => c.missingPercent);
        cleanedData = cleanedStats.columns.map((c) => c.missingPercent);
        titleText = '缺失值占比对比';
        yAxisLabel = '占比 (%)';
        break;
      case 'outliers':
        originalData = numericCols.map((c) => c.outlierCount || 0);
        cleanedData = cleanedStats.columns
          .filter((c) => c.type === 'numeric')
          .map((c) => c.outlierCount || 0);
        titleText = '异常值数量对比';
        yAxisLabel = '数量';
        break;
      case 'unique':
        originalData = originalStats.columns.map((c) => c.uniqueCount || 0);
        cleanedData = cleanedStats.columns.map((c) => c.uniqueCount || 0);
        titleText = '唯一值数量对比';
        yAxisLabel = '数量';
        break;
    }

    const displayLabels = selectedMetric === 'outliers' ? numericCols.map((c) => c.name) : labels;

    return {
      backgroundColor: 'transparent',
      title: {
        text: titleText,
        textStyle: { color: '#94a3b8', fontSize: 13, fontWeight: 'normal' },
        left: 'center',
        top: 10,
      },
      legend: {
        data: ['清洗前', '清洗后'],
        top: 35,
        textStyle: { color: '#94a3b8' },
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        backgroundColor: '#1e293b',
        borderColor: '#475569',
        textStyle: { color: '#e2e8f0' },
        formatter: (params: any) => {
          let result = `<div style="font-weight: bold; margin-bottom: 4px;">${params[0].name}</div>`;
          params.forEach((p: any) => {
            const suffix = selectedMetric === 'missing' ? '%' : ' 个';
            result += `<div style="display: flex; align-items: center; gap: 8px;">
              <span style="display: inline-block; width: 10px; height: 10px; background: ${p.color}; border-radius: 2px;"></span>
              <span>${p.seriesName}: ${p.data}${suffix}</span>
            </div>`;
          });
          return result;
        },
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '10%',
        top: 80,
        containLabel: true,
      },
      xAxis: {
        type: 'category',
        data: displayLabels,
        axisLabel: {
          color: '#64748b',
          rotate: 30,
          fontSize: 11,
        },
        axisLine: { lineStyle: { color: '#475569' } },
      },
      yAxis: {
        type: 'value',
        name: yAxisLabel,
        nameTextStyle: { color: '#64748b', fontSize: 11 },
        axisLabel: {
          color: '#64748b',
          fontSize: 11,
          formatter: selectedMetric === 'missing' ? '{value}%' : '{value}',
        },
        axisLine: { lineStyle: { color: '#475569' } },
        splitLine: { lineStyle: { color: '#334155' } },
      },
      series: [
        {
          name: '清洗前',
          type: 'bar',
          data: originalData,
          itemStyle: {
            color: '#64748b',
            borderRadius: [4, 4, 0, 0],
          },
          emphasis: {
            itemStyle: {
              color: '#94a3b8',
            },
          },
        },
        {
          name: '清洗后',
          type: 'bar',
          data: cleanedData,
          itemStyle: {
            color: '#10b981',
            borderRadius: [4, 4, 0, 0],
          },
          emphasis: {
            itemStyle: {
              color: '#34d399',
            },
          },
        },
      ],
    };
  }, [originalStats, cleanedStats, selectedMetric]);

  return (
    <div className={className}>
      <div className="flex gap-2 mb-4">
        {[
          { key: 'missing', label: '缺失值' },
          { key: 'outliers', label: '异常值' },
          { key: 'unique', label: '唯一值' },
        ].map((metric) => (
          <button
            key={metric.key}
            onClick={() => setSelectedMetric(metric.key as any)}
            className={`px-3 py-1.5 text-sm rounded-lg transition-colors ${
              selectedMetric === metric.key
                ? 'bg-primary-500 text-white'
                : 'bg-bg-800 text-bg-300 hover:bg-bg-700'
            }`}
          >
            {metric.label}
          </button>
        ))}
      </div>
      <ReactECharts option={option} style={{ height: '100%', minHeight: 300 }} />
    </div>
  );
};
