import React from 'react';
import ReactECharts from 'echarts-for-react';
import { TemplateComponent } from '../types';

interface ChartRendererProps {
  component: TemplateComponent;
  style?: React.CSSProperties;
}

const ChartRenderer: React.FC<ChartRendererProps> = ({ component, style }) => {
  const getChartOption = () => {
    const baseOption = {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'axis',
        backgroundColor: 'rgba(30, 41, 59)',
        borderColor: '#475569',
        textStyle: { color: '#E2E8F0' }
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        containLabel: true
      }
    };

    const mockData = {
      categories: ['1月', '2月', '3月', '4月', '5月', '6月'],
      values: [820, 932, 901, 934, 1290, 1330, 1320]
    };

    switch (component.chartType) {
      case 'line':
        return {
          ...baseOption,
          xAxis: {
            type: 'category',
            data: mockData.categories,
            axisLine: { lineStyle: { color: '#475569' } },
            axisLabel: { color: '#94A3B8' }
          },
          yAxis: {
            type: 'value',
            axisLine: { lineStyle: { color: '#475569' } },
            axisLabel: { color: '#94A3B8' },
            splitLine: { lineStyle: { color: '#334155' } }
          },
          series: [{
            data: mockData.values,
            type: 'line',
            smooth: true,
            areaStyle: {
              color: {
              type: 'linear',
              x: 0, y: 0, x2: 0, y2: 1,
              colorStops: [
                { offset: 0, color: 'rgba(59, 130, 246, 0.3)' },
                { offset: 1, color: 'rgba(59, 130, 246, 0.05)' }
              ]
            }
            },
            lineStyle: { color: '#3B82F6', width: 2 },
            itemStyle: { color: '#3B82F6' }
          }]
        };
      case 'bar':
        return {
          ...baseOption,
          xAxis: {
            type: 'category',
            data: mockData.categories,
            axisLine: { lineStyle: { color: '#475569' } },
            axisLabel: { color: '#94A3B8' }
          },
          yAxis: {
            type: 'value',
            axisLine: { lineStyle: { color: '#475569' } },
            axisLabel: { color: '#94A3B8' },
            splitLine: { lineStyle: { color: '#334155' } }
          },
          series: [{
            data: mockData.values,
            type: 'bar',
            barWidth: '50%',
            itemStyle: {
              color: {
                type: 'linear',
                x: 0, y: 0, x2: 0, y2: 1,
                colorStops: [
                  { offset: 0, color: '#10B981' },
                  { offset: 1, color: '#059669' }
                ]
              },
              borderRadius: [4, 4, 0, 0]
            }
          }]
        };
      case 'pie':
        return {
          ...baseOption,
          tooltip: {
            ...baseOption.tooltip,
            trigger: 'item'
          },
          series: [{
            type: 'pie',
            radius: ['40%', '70%'],
            avoidLabelOverlap: false,
            itemStyle: {
              borderRadius: 6,
              borderColor: '#1E293B',
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
            labelLine: {
              show: false
            },
            data: [
              { value: 1048, name: '搜索引擎', itemStyle: { color: '#3B82F6' } },
              { value: 735, name: '直接访问', itemStyle: { color: '#10B981' } },
              { value: 580, name: '邮件营销', itemStyle: { color: '#F59E0B' } },
              { value: 484, name: '联盟广告', itemStyle: { color: '#8B5CF6' } },
              { value: 300, name: '视频广告', itemStyle: { color: '#EF4444' } }
            ]
          }]
        };
      case 'area':
        return {
          ...baseOption,
          xAxis: {
            type: 'category',
            boundaryGap: false,
            data: mockData.categories,
            axisLine: { lineStyle: { color: '#475569' } },
            axisLabel: { color: '#94A3B8' }
          },
          yAxis: {
            type: 'value',
            axisLine: { lineStyle: { color: '#475569' } },
            axisLabel: { color: '#94A3B8' },
            splitLine: { lineStyle: { color: '#334155' } }
          },
          series: [{
            data: mockData.values,
            type: 'line',
            areaStyle: {
              color: {
              type: 'linear',
              x: 0, y: 0, x2: 0, y2: 1,
              colorStops: [
                { offset: 0, color: 'rgba(139, 92, 246, 0.4)' },
                { offset: 1, color: 'rgba(139, 92, 246, 0.05)' }
              ]
            }
            },
            lineStyle: { color: '#8B5CF6' }
          }]
        };
      case 'gauge':
        return {
          series: [{
            type: 'gauge',
            startAngle: 180,
            endAngle: 0,
            min: 0,
            max: 100,
            splitNumber: 10,
            itemStyle: {
              color: '#3B82F6'
            },
            progress: {
              show: true,
              roundCap: true,
              width: 18
            },
            pointer: {
              icon: 'path://M12.8,0.7l12,40.1H0.7L12.8,0.7z',
              length: '60%',
              width: 12,
              offsetCenter: [0, '5%'],
              itemStyle: {
                color: '#auto'
              }
            },
            axisLine: {
              roundCap: true,
              lineStyle: {
                width: 18,
                color: [[1, '#334155']]
              }
            },
            axisTick: {
              show: false
            },
            splitLine: {
              show: false
            },
            axisLabel: {
              show: false
            },
            title: {
              show: false
            },
            detail: {
              valueAnimation: true,
              fontSize: 24,
              offsetCenter: [0, '35%'],
              formatter: '{value}%',
              color: '#E2E8F0'
            },
            data: [{
              value: 75 }]
          }]
        };
      default:
        return baseOption;
    }
  };

  return (
    <div style={{ width: '100%', height: '100%', ...style }}>
      <ReactECharts
      option={getChartOption()}
      style={{ width: '100%', height: '100%' }}
      opts={{ renderer: 'canvas' }}
    />
    </div>
  );
};

export default ChartRenderer;
