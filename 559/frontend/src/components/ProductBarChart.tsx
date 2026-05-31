import React from 'react';
import ReactECharts from 'echarts-for-react';

interface ProductBarChartProps {
  clickData: Record<string, number>;
  orderData: Record<string, { count: number; amount: number }>;
}

export const ProductBarChart: React.FC<ProductBarChartProps> = ({
  clickData,
  orderData
}) => {
  const products = Object.keys(clickData).slice(0, 6);
  
  const option = {
    title: {
      text: '商品点击与订单对比',
      textStyle: {
        color: 'rgba(255, 255, 255, 0.8)',
        fontSize: 14
      },
      left: 'center'
    },
    legend: {
      data: ['点击量', '订单量'],
      textStyle: {
        color: 'rgba(255, 255, 255, 0.6)'
      },
      top: '10%'
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: '25%',
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
      data: products,
      axisLine: {
        lineStyle: {
          color: 'rgba(255, 255, 255, 0.2)'
        }
      },
      axisLabel: {
        color: 'rgba(255, 255, 255, 0.5)',
        fontSize: 10,
        rotate: 30
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
        name: '点击量',
        type: 'bar',
        data: products.map(p => clickData[p] || 0),
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#48dbfb' },
            { offset: 1, color: '#0abde3' }
          ]),
          borderRadius: [4, 4, 0, 0]
        }
      },
      {
        name: '订单量',
        type: 'bar',
        data: products.map(p => orderData[p]?.count || 0),
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#ff9ff3' },
            { offset: 1, color: '#f368e0' }
          ]),
          borderRadius: [4, 4, 0, 0]
        }
      }
    ]
  };

  return <ReactECharts option={option} style={{ height: '280px' }} />;
};
