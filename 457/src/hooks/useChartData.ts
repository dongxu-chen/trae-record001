import { useMemo } from 'react';
import { PivotResult, ChartType } from '@/types';
import * as echarts from 'echarts';

export const useChartData = (pivotResult: PivotResult, chartType: ChartType) => {
  const chartOption = useMemo(() => {
    const { rowHeaders, colHeaders, data, rowTotals } = pivotResult;
    
    if (rowHeaders.length === 0 || colHeaders.length === 0) {
      return getEmptyOption();
    }

    const categories = rowHeaders.map(r => r.join(' - '));
    const series = colHeaders.map((colVals, colIdx) => ({
      name: colVals.join(' - '),
      type: chartType === 'pie' ? undefined : chartType,
      data: data.map(row => row[colIdx]?.value ?? 0),
      smooth: chartType === 'line',
      emphasis: {
        focus: 'series' as const,
      },
    }));

    if (chartType === 'pie') {
      return getPieOption(rowHeaders, rowTotals);
    }

    return {
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'shadow',
        },
      },
      legend: {
        data: series.map(s => s.name),
        type: 'scroll',
        bottom: 0,
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '15%',
        top: '10%',
        containLabel: true,
      },
      xAxis: {
        type: 'category',
        data: categories,
        axisLabel: {
          rotate: 30,
          interval: 0,
        },
      },
      yAxis: {
        type: 'value',
      },
      series: series.map(s => ({
        ...s,
        itemStyle: {
          borderRadius: chartType === 'bar' ? [4, 4, 0, 0] : 0,
        },
      })),
    };
  }, [pivotResult, chartType]);

  return chartOption;
};

const getEmptyOption = (): echarts.EChartsOption => ({
  title: {
    text: '请配置行、列和值字段',
    left: 'center',
    top: 'center',
    textStyle: {
      color: '#999',
      fontSize: 16,
    },
  },
});

const getPieOption = (
  rowHeaders: string[][],
  rowTotals: (any | null)[]
): echarts.EChartsOption => {
  const pieData = rowHeaders
    .map((r, i) => ({
      name: r.join(' - '),
      value: rowTotals[i]?.value ?? 0,
    }))
    .filter(d => d.value > 0);

  return {
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c} ({d}%)',
    },
    legend: {
      orient: 'vertical',
      left: 'left',
      type: 'scroll',
    },
    series: [
      {
        name: '数据分布',
        type: 'pie',
        radius: ['40%', '70%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 10,
          borderColor: '#fff',
          borderWidth: 2,
        },
        label: {
          show: false,
          position: 'center',
        },
        emphasis: {
          label: {
            show: true,
            fontSize: 18,
            fontWeight: 'bold',
          },
        },
        labelLine: {
          show: false,
        },
        data: pieData,
      },
    ],
  };
};
