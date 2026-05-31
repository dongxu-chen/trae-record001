import ReactECharts from 'echarts-for-react';
import { useMemo } from 'react';
import { formatNumber } from '@/utils/format';

interface BarChartData {
  name: string;
  value: number;
  color?: string;
}

interface BarChartProps {
  data: BarChartData[];
  title?: string;
  xAxisName?: string;
  yAxisName?: string;
  height?: number;
  horizontal?: boolean;
  color?: string;
}

const BarChart: React.FC<BarChartProps> = ({
  data,
  title,
  xAxisName,
  yAxisName,
  height = 300,
  horizontal = false,
  color = '#3B82F6',
}) => {
  const option = useMemo(() => {
    const sortedData = [...data].sort((a, b) => b.value - a.value);
    const colors = sortedData.map((d) => d.color || color);

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
        axisPointer: {
          type: 'shadow',
          shadowStyle: {
            color: 'rgba(59, 130, 246, 0.1)',
          },
        },
        formatter: (params: any) => {
          const data = params[0];
          return `
            <div style="padding: 4px;">
              <div style="color: #94A3B8; margin-bottom: 4px;">${data.name}</div>
              <div style="font-weight: 500;">${formatNumber(data.value)}</div>
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
      xAxis: horizontal
        ? {
            type: 'value',
            name: xAxisName,
            nameTextStyle: {
              color: '#64748B',
            },
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
          }
        : {
            type: 'category',
            name: xAxisName,
            nameTextStyle: {
              color: '#64748B',
            },
            data: sortedData.map((d) => d.name),
            axisLine: {
              lineStyle: {
                color: '#334155',
              },
            },
            axisLabel: {
              color: '#64748B',
              fontSize: 11,
              rotate: data.length > 6 ? 30 : 0,
            },
            splitLine: {
              show: false,
            },
          },
      yAxis: horizontal
        ? {
            type: 'category',
            name: yAxisName,
            nameTextStyle: {
              color: '#64748B',
            },
            data: sortedData.map((d) => d.name),
            axisLine: {
              lineStyle: {
                color: '#334155',
              },
            },
            axisLabel: {
              color: '#64748B',
              fontSize: 11,
            },
            splitLine: {
              show: false,
            },
          }
        : {
            type: 'value',
            name: yAxisName,
            nameTextStyle: {
              color: '#64748B',
            },
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
          type: 'bar',
          data: sortedData.map((d, i) => ({
            value: d.value,
            itemStyle: {
              color: colors[i],
              borderRadius: horizontal ? [0, 6, 6, 0] : [6, 6, 0, 0],
            },
          })),
          barWidth: '60%',
          emphasis: {
            itemStyle: {
              shadowBlur: 10,
              shadowColor: 'rgba(0, 0, 0, 0.3)',
            },
          },
        },
      ],
    };
  }, [data, title, xAxisName, yAxisName, horizontal, color]);

  return (
    <ReactECharts
      option={option}
      style={{ height, width: '100%' }}
      opts={{ renderer: 'canvas' }}
    />
  );
};

export default BarChart;
