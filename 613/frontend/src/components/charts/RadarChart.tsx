import ReactECharts from 'echarts-for-react';
import { useMemo } from 'react';

interface RadarData {
  name: string;
  value: number;
  max: number;
}

interface RadarChartProps {
  data: RadarData[];
  title?: string;
  color?: string;
  height?: number;
}

const RadarChart: React.FC<RadarChartProps> = ({
  data,
  title,
  color = '#3B82F6',
  height = 300,
}) => {
  const option = useMemo(() => {
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
            left: 'center',
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
      },
      radar: {
        indicator: data.map((d) => ({
          name: d.name,
          max: d.max,
        })),
        center: ['50%', '55%'],
        radius: '65%',
        splitNumber: 5,
        axisName: {
          color: '#94A3B8',
          fontSize: 11,
        },
        splitLine: {
          lineStyle: {
            color: '#334155',
          },
        },
        splitArea: {
          areaStyle: {
            color: ['rgba(30, 41, 59, 0.5)', 'rgba(30, 41, 59, 0.3)'],
          },
        },
        axisLine: {
          lineStyle: {
            color: '#334155',
          },
        },
      },
      series: [
        {
          type: 'radar',
          data: [
            {
              value: data.map((d) => d.value),
              name: '评分',
              symbol: 'circle',
              symbolSize: 6,
              lineStyle: {
                color,
                width: 2,
              },
              areaStyle: {
                color: {
                  type: 'radial',
                  x: 0.5,
                  y: 0.5,
                  r: 0.5,
                  colorStops: [
                    { offset: 0, color: `${color}80` },
                    { offset: 1, color: `${color}20` },
                  ],
                },
              },
              itemStyle: {
                color,
              },
            },
          ],
        },
      ],
    };
  }, [data, title, color]);

  return (
    <ReactECharts
      option={option}
      style={{ height, width: '100%' }}
      opts={{ renderer: 'canvas' }}
    />
  );
};

export default RadarChart;
