import ReactECharts from 'echarts-for-react';
import { useMemo } from 'react';
import { formatTime, formatNumber } from '@/utils/format';

interface LineChartProps {
  data: Array<{ time: number; value: number }>;
  title?: string;
  color?: string;
  height?: number;
  showArea?: boolean;
  smooth?: boolean;
}

const LineChart: React.FC<LineChartProps> = ({
  data,
  title,
  color = '#3B82F6',
  height = 300,
  showArea = true,
  smooth = true,
}) => {
  const option = useMemo(() => {
    const sortedData = [...data].sort((a, b) => a.time - b.time);

    return {
      backgroundColor: 'transparent',
      title: title
        ? {
            text: title,
            textStyle: {
              color: '#F1F5F9',
              fontSize: 14,
              fontWeight: 600,
            },
            left: 10,
            top: 10,
          }
        : undefined,
      tooltip: {
        trigger: 'axis',
        backgroundColor: 'rgba(15, 23, 42, 0.95)',
        borderColor: '#334155',
        borderWidth: 1,
        textStyle: {
          color: '#F1F5F9',
        },
        formatter: (params: any) => {
          const data = params[0];
          return `
            <div style="padding: 4px;">
              <div style="color: #94A3B8; margin-bottom: 4px;">
                ${formatTime(data.value[0])}
              </div>
              <div style="display: flex; align-items: center; gap: 8px;">
                <div style="width: 10px; height: 10px; background: ${color}; border-radius: 50%;"></div>
                <span style="font-weight: 500;">${formatNumber(data.value[1])}</span>
              </div>
            </div>
          `;
        },
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        top: title ? 50 : 20,
        containLabel: true,
      },
      xAxis: {
        type: 'time',
        axisLine: {
          lineStyle: {
            color: '#334155',
          },
        },
        axisLabel: {
          color: '#64748B',
          fontSize: 11,
          formatter: (value: number) => formatTime(value, 'MM-DD HH:mm'),
        },
        splitLine: {
          show: false,
        },
      },
      yAxis: {
        type: 'value',
        axisLine: {
          show: false,
        },
        axisLabel: {
          color: '#64748B',
          fontSize: 11,
        },
        splitLine: {
          lineStyle: {
            color: '#1E293B',
            type: 'dashed',
          },
        },
      },
      series: [
        {
          data: sortedData.map((d) => [d.time, d.value]),
          type: 'line',
          smooth,
          symbol: 'circle',
          symbolSize: 6,
          showSymbol: false,
          lineStyle: {
            color,
            width: 2,
          },
          itemStyle: {
            color,
          },
          areaStyle: showArea
            ? {
                color: {
                  type: 'linear',
                  x: 0,
                  y: 0,
                  x2: 0,
                  y2: 1,
                  colorStops: [
                    { offset: 0, color: `${color}40` },
                    { offset: 1, color: `${color}05` },
                  ],
                },
              }
            : undefined,
        },
      ],
    };
  }, [data, title, color, showArea, smooth]);

  return (
    <ReactECharts
      option={option}
      style={{ height, width: '100%' }}
      opts={{ renderer: 'canvas' }}
    />
  );
};

export default LineChart;
