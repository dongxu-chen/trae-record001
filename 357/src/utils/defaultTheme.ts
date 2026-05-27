import type { ChartTheme } from '@/types/theme';

export const defaultTheme: ChartTheme = {
  color: [
    '#5470c6',
    '#91cc75',
    '#fac858',
    '#ee6666',
    '#73c0de',
    '#3ba272',
    '#fc8452',
    '#9a60b4',
    '#ea7ccc',
  ],
  backgroundColor: '#ffffff',
  textStyle: {
    color: '#333333',
    fontFamily: 'system-ui, -apple-system, sans-serif',
    fontSize: 12,
  },
  title: {
    textStyle: {
      color: '#333333',
      fontSize: 18,
      fontWeight: 'bold',
    },
    subtextStyle: {
      color: '#666666',
      fontSize: 12,
    },
  },
  line: {
    itemStyle: {
      borderWidth: 2,
    },
    lineStyle: {
      width: 2,
    },
    symbolSize: 6,
    symbol: 'emptyCircle',
    smooth: false,
  },
  bar: {
    itemStyle: {
      borderWidth: 0,
    },
  },
  pie: {
    itemStyle: {
      borderWidth: 0,
    },
    label: {
      color: '#333333',
      fontSize: 12,
    },
  },
  scatter: {
    itemStyle: {
      borderWidth: 0,
    },
  },
  grid: {
    show: false,
    borderColor: '#e0e0e0',
    borderWidth: 1,
  },
  categoryAxis: {
    axisLine: {
      show: true,
      lineStyle: {
        color: '#666666',
        width: 1,
        type: 'solid',
      },
    },
    axisTick: {
      show: true,
      lineStyle: {
        color: '#666666',
        width: 1,
        type: 'solid',
      },
    },
    axisLabel: {
      show: true,
      color: '#666666',
      fontSize: 12,
    },
    splitLine: {
      show: false,
      lineStyle: {
        color: '#e0e0e0',
        type: 'dashed',
        width: 1,
      },
    },
  },
  valueAxis: {
    axisLine: {
      show: false,
      lineStyle: {
        color: '#666666',
        width: 1,
        type: 'solid',
      },
    },
    axisTick: {
      show: false,
      lineStyle: {
        color: '#666666',
        width: 1,
        type: 'solid',
      },
    },
    axisLabel: {
      show: true,
      color: '#666666',
      fontSize: 12,
    },
    splitLine: {
      show: true,
      lineStyle: {
        color: '#e0e0e0',
        type: 'solid',
        width: 1,
      },
    },
  },
  legend: {
    show: true,
    textStyle: {
      color: '#333333',
      fontSize: 12,
    },
  },
  tooltip: {
    backgroundColor: 'rgba(50, 50, 50, 0.9)',
    borderColor: '#333333',
    borderWidth: 0,
    textStyle: {
      color: '#ffffff',
      fontSize: 12,
    },
  },
};
