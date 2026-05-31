import ReactECharts from 'echarts-for-react';
import { useMemo } from 'react';
import { formatNumber } from '@/utils/format';

interface PieChartData {
  name: string;
  value: number;
  color?: string;
}

interface PieChartProps {
  data: PieChartData[];
  title?: string;
  type?: 'pie' | 'donut';
  height?: number;
  showLegend?: boolean;
}

const PieChart: React.FC<PieChartProps> = ({
  data,
  title,
  type = 'donut',
  height = 300,
  showLegend = true,
}) => {
  const option = useMemo(() => {
    const colors = data.map((d) => d.color || '#3B82F6');

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
        trigger: 'item',
        backgroundColor: 'rgba(15, 23, 42, 0.95)',
        borderColor: '#334155',
        borderWidth: 1,
        textStyle: {
          color: '#F1F5F9',
        },
        formatter: (params: any) => {
          const percent = ((params.value / params.total) * 100).toFixed(1);
          return `
            <div style="padding: 4px;">
              <div style="margin-bottom: 4px;">${params.marker} ${params.name}</div>
              <div style="font-weight: 500;">${formatNumber(params.value)} (${percent}%)</div>
            </div>
          `;
        },
      },
      legend: showLegend
        ? {
            orient: 'vertical',
            right: 10,
            top: 'center',
            textStyle: {
              color: '#94A3B8',
              fontSize: 12,
            },
            itemWidth: 12,
            itemHeight: 12,
            itemGap: 12,
          }
        : undefined,
      color: colors,
      series: [
        {
          name: title,
          type: 'pie',
          radius: type === 'donut' ? ['50%', '75%'] : '70%',
          center: showLegend ? ['35%', '55%'] : ['50%', '55%'],
          avoidLabelOverlap: true,
          itemStyle: {
            borderRadius: 6,
            borderColor: '#1E293B',
            borderWidth: 2,
          },
          label: {
            show: false,
          },
          emphasis: {
            label: {
              show: true,
              fontSize: 14,
              fontWeight: 'bold',
              color: '#F1F5F9',
            },
            itemStyle: {
              shadowBlur: 10,
              shadowOffsetX: 0,
              shadowColor: 'rgba(0, 0, 0, 0.5)',
            },
          },
          data: data.map((d) => ({
            name: d.name,
            value: d.value,
          })),
        },
      ],
    };
  }, [data, title, type, showLegend]);

  return (
    <ReactECharts
      option={option}
      style={{ height, width: '100%' }}
      opts={{ renderer: 'canvas' }}
    />
  );
};

export default PieChart;
