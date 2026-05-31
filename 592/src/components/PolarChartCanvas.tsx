import React, { useRef, useMemo, memo } from 'react';
import {
  Chart as ChartJS,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
  Legend,
} from 'chart.js';
import { Line } from 'react-chartjs-2';
import { PolarCurveConfig, POLAR_CURVE_NAMES, POLAR_POINT_COUNT } from '../types';
import { generatePolarPoints, formatNumber } from '../utils/mathEngine';

ChartJS.register(
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
  Legend
);

interface PolarChartCanvasProps {
  curves: PolarCurveConfig[];
  selectedCurveId: string | null;
  onSelectCurve: (id: string) => void;
  animationTime?: number;
}

const PolarChartCanvas: React.FC<PolarChartCanvasProps> = ({
  curves,
  selectedCurveId,
  onSelectCurve,
  animationTime = 0,
}) => {
  const chartRef = useRef<ChartJS<'line'>>(null);

  const chartData = useMemo(() => {
    const datasets: any[] = [];

    curves.forEach((curve) => {
      if (!curve.visible) return;

      const animatedConfig = { ...curve };
      if (animationTime > 0) {
        animatedConfig.a = curve.a * (1 + 0.2 * Math.sin(animationTime));
        animatedConfig.b = curve.b * (1 + 0.15 * Math.cos(animationTime * 0.7));
      }

      const points = generatePolarPoints(animatedConfig, [0, 2 * Math.PI], POLAR_POINT_COUNT);

      datasets.push({
        label: POLAR_CURVE_NAMES[curve.type],
        data: points.map((p) => ({
          x: isFinite(p.x) ? p.x : null,
          y: isFinite(p.y) ? p.y : null,
        })),
        borderColor: curve.color,
        backgroundColor: curve.color + '30',
        borderWidth: 2.5,
        pointRadius: 0,
        tension: 0.1,
        fill: false,
        spanGaps: false,
      });
    });

    return { datasets };
  }, [curves, animationTime]);

  const options = useMemo(() => ({
    responsive: true,
    maintainAspectRatio: false,
    animation: {
      duration: 0,
    },
    interaction: {
      mode: 'nearest' as const,
      intersect: true,
    },
    scales: {
      x: {
        type: 'linear' as const,
        min: -3,
        max: 3,
        grid: {
          color: 'rgba(75, 85, 99, 0.3)',
        },
        ticks: {
          color: '#9CA3AF',
        },
      },
      y: {
        type: 'linear' as const,
        min: -3,
        max: 3,
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
            size: 12,
          },
          padding: 20,
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
            const x = context.parsed.x;
            const y = context.parsed.y;
            return `${label}: (${formatNumber(x, 3)}, ${formatNumber(y, 3)})`;
          },
        },
      },
    },
    onClick: (event: any, elements: any[]) => {
      if (elements.length > 0) {
        const datasetIndex = elements[0].datasetIndex;
        const visibleCurves = curves.filter((c) => c.visible);
        if (visibleCurves[datasetIndex]) {
          onSelectCurve(visibleCurves[datasetIndex].id);
        }
      }
    },
  }), [curves, onSelectCurve]);

  return (
    <div className="relative w-full h-full bg-gray-900/50 rounded-xl border border-gray-700 overflow-hidden">
      <Line ref={chartRef} data={chartData} options={options} />
    </div>
  );
};

export default memo(PolarChartCanvas);
