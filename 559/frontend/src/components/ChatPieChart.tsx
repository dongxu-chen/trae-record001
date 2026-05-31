import React from 'react';
import ReactECharts from 'echarts-for-react';
import { ChatAnalysis } from '../types';

interface ChatPieChartProps {
  data: ChatAnalysis;
}

export const ChatPieChart: React.FC<ChatPieChartProps> = ({ data }) => {
  const chartData = [
    { value: data.question, name: '问题', color: '#ffd93d' },
    { value: data.praise, name: '好评', color: '#6bcb77' },
    { value: data.complaint, name: '投诉', color: '#ff6b6b' },
    { value: data.neutral, name: '中性', color: '#4d96ff' }
  ];

  const option = {
    title: {
      text: '评论情感分析',
      textStyle: {
        color: 'rgba(255, 255, 255, 0.8)',
        fontSize: 14
      },
      left: 'center'
    },
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(0, 0, 0, 0.8)',
      borderColor: 'rgba(255, 255, 255, 0.1)',
      textStyle: {
        color: '#fff'
      }
    },
    legend: {
      orient: 'vertical',
      right: '5%',
      top: 'center',
      textStyle: {
        color: 'rgba(255, 255, 255, 0.6)'
      }
    },
    series: [
      {
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['35%', '55%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 8,
          borderColor: 'rgba(15, 20, 25, 1)',
          borderWidth: 2
        },
        label: {
          show: false
        },
        emphasis: {
          label: {
            show: true,
            fontSize: 14,
            fontWeight: 'bold',
            color: '#fff'
          }
        },
        data: chartData.map(item => ({
          value: item.value,
          name: item.name,
          itemStyle: { color: item.color }
        }))
      }
    ]
  };

  return <ReactECharts option={option} style={{ height: '220px' }} />;
};
