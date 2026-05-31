import React, { useRef, useMemo, memo } from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
  Legend,
} from 'chart.js';
import { Line } from 'react-chartjs-2';
import { FourierConfig, X_RANGE, POINT_COUNT } from '../types';
import { generateFourierPoints, generateFourierHarmonics, HARMONIC_COLORS, formatNumber, formatPi } from '../utils/mathEngine';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
  Legend
);

interface FourierDemoProps {
  config: FourierConfig;
  animationTime?: number;
}

const FourierDemo: React.FC<FourierDemoProps> = ({ config, animationTime = 0 }) => {
  const chartRef = useRef<ChartJS<'line'>>(null);

  const chartData = useMemo(() => {
    const labels: string[] = [];
    const step = (X_RANGE[1] - X_RANGE[0]) / 100;
    for (let x = X_RANGE[0]; x <= X_RANGE[1]; x += step) {
      labels.push(formatPi(x));
    }

    const datasets: any[] = [];

    const animatedConfig = { ...config };
    if (animationTime > 0) {
      animatedConfig.frequency = config.frequency * (1 + 0.1 * Math.sin(animationTime * 0.5));
    }

    if (config.showComponents) {
      const harmonics = generateFourierHarmonics(animatedConfig, X_RANGE, POINT_COUNT);
      harmonics.forEach((points, index) => {
        if (index < HARMONIC_COLORS.length) {
          const harmonicNumber = config.type === 'square' || config.type === 'triangle' ? 2 * index + 1 : index + 1;
          datasets.push({
            label: `第 ${harmonicNumber} 次谐波`,
            data: points.map((p) => (isFinite(p.y) ? p.y : null)),
            borderColor: HARMONIC_COLORS[index % HARMONIC_COLORS.length],
            backgroundColor: HARMONIC_COLORS[index % HARMONIC_COLORS.length] + '20',
            borderWidth: 1.5,
            borderDash: [3, 3],
            pointRadius: 0,
            tension: 0.1,
            fill: false,
            spanGaps: false,
            opacity: 0.6,
          });
        }
      });
    }

    if (config.showSum) {
      const sumPoints = generateFourierPoints(animatedConfig, X_RANGE, POINT_COUNT);
      datasets.push({
        label: `合成波形 (${config.harmonics} 次谐波)`,
        data: sumPoints.map((p) => (isFinite(p.y) ? p.y : null)),
        borderColor: '#FFFFFF',
        backgroundColor: '#FFFFFF30',
        borderWidth: 3,
        pointRadius: 0,
        tension: 0.1,
        fill: false,
        spanGaps: false,
      });
    }

    return { labels, datasets };
  }, [config, animationTime]);

  const options = useMemo(() => ({
    responsive: true,
    maintainAspectRatio: false,
    animation: {
      duration: 0,
    },
    interaction: {
      mode: 'index' as const,
      intersect: false,
    },
    scales: {
      x: {
        type: 'linear' as const,
        min: X_RANGE[0],
        max: X_RANGE[1],
        grid: {
          color: 'rgba(75, 85, 99, 0.3)',
        },
        ticks: {
          color: '#9CA3AF',
          callback: function(value: number | string) {
            return formatPi(Number(value));
          },
        },
      },
      y: {
        min: -2,
        max: 2,
        grid: {
          color: 'rgba(75, 85, 99, 0.3)',
        },
        ticks: {
          color: '#9CA3AF',
        },
      },
    },
    plugins: {
      legend: {
        display: true,
        position: 'top' as const,
        labels: {
          color: '#E5E7EB',
          font: {
            family: 'JetBrains Mono',
            size: 11,
          },
          padding: 15,
          filter: function(item: any, chart: any) {
            const datasets = chart.data.datasets;
            const visibleCount = datasets.filter((d: any) => !d.hidden).length;
            return visibleCount <= 12;
          },
        },
      },
      tooltip: {
        backgroundColor: 'rgba(14, 17, 22, 0.95)',
        titleColor: '#E5E7EB',
        bodyColor: '#9CA3AF',
        borderColor: '#374151',
        borderWidth: 1,
        padding: 12,
        callbacks: {
          label: function(context: any) {
            const label = context.dataset.label || '';
            const value = context.parsed.y;
            return `${label}: ${formatNumber(value, 4)}`;
          },
          title: function(context: any) {
            const xValue = context[0].parsed.x;
            return `x = ${formatPi(xValue)}`;
          },
        },
      },
    },
  }), []);

  return (
    <div className="relative w-full h-full bg-gray-900/50 rounded-xl border border-gray-700 overflow-hidden">
      <Line ref={chartRef} data={chartData} options={options} />
    </div>
  );
};

export default memo(FourierDemo);
