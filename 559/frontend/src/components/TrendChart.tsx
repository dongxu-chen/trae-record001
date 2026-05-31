import React from 'react';
import ReactECharts from 'echarts-for-react';
import { TrendData } from '../types';

interface TrendChartProps {
  data: TrendData[];
  title: string;
  color: string;
  dataKey?: 'count' | 'score';
}

export const TrendChart: React.FC<TrendChartProps> = ({
  data,
  title,
  color,
  dataKey = 'count'
}) => {
  const option = {
    title: {
      text: title,
      textStyle: {
        color: 'rgba(255, 255, 255, 0.8)',
        fontSize: 14
      },
      left: 'center'
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: '20%',
      containLabel: true
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(0, 0, 0, 0.8)',
      borderColor: 'rgba(255, 255, 255, 0.1)',
      textStyle: {
        color: '#fff'
      }
    },
    xAxis: {
      type: 'category',
      data: data.map(item => {
        const time = new Date(item.timestamp);
        return time.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
      }),
      axisLine: {
        lineStyle: {
          color: 'rgba(255, 255, 255, 0.2)'
        }
      },
      axisLabel: {
        color: 'rgba(255, 255, 255, 0.5)',
        fontSize: 10
      }
    },
    yAxis: {
      type: 'value',
      axisLine: {
        show: false
      },
      splitLine: {
        lineStyle: {
          color: 'rgba(255, 255, 255, 0.05)'
        }
      },
      axisLabel: {
        color: 'rgba(255, 255, 255, 0.5)',
        fontSize: 10
      }
    },
    series: [
      {
        data: data.map(item => item[dataKey]),
        type: 'line',
        smooth: true,
        symbol: 'none',
        lineStyle: {
          color: color,
          width: 2
        },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: color + '40' },
              { offset: 1, color: color + '00' }
            ]
          }
        }
      }
    ]
  };

  return <ReactECharts option={option} style={{ height: '200px' }} />;
};
