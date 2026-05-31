import React, { useRef, useCallback, useMemo, memo } from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js';
import { Line } from 'react-chartjs-2';
import { FunctionConfig, Point, X_RANGE, Y_RANGE } from '../types';
import { generatePoints, computeDerivative, computeIntegral, formatPi, formatNumber } from '../utils/mathEngine';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

interface ChartCanvasProps {
  functions: FunctionConfig[];
  mousePosition: Point | null;
  markedPoints: Point[];
  onMouseMove: (point: Point | null) => void;
  onChartClick: (point: Point) => void;
  xRange?: [number, number];
  yRange?: [number, number];
}

interface CachedData {
  points: Point[];
  derivativePoints: Point[];
  integralPoints: Point[];
  configHash: string;
}

const getFunctionConfigHash = (func: FunctionConfig, xRange: [number, number]): string => {
  return `${func.id}-${func.type}-${func.frequency}-${func.phase}-${func.amplitude}-${func.expression}-${xRange[0]}-${xRange[1]}`;
};

const FunctionDataset = memo(function FunctionDataset({
  func,
  xRange,
  cacheRef,
}: {
  func: FunctionConfig;
  xRange: [number, number];
  cacheRef: React.MutableRefObject<Map<string, CachedData>>;
}) {
  const configHash = getFunctionConfigHash(func, xRange);

  const { points, derivativePoints, integralPoints } = useMemo(() => {
    let cached = cacheRef.current.get(func.id);

    if (cached && cached.configHash === configHash) {
      return cached;
    }

    const newPoints = generatePoints(func, xRange);
    const newDerivativePoints = computeDerivative(newPoints);
    const newIntegralPoints = computeIntegral(newPoints);

    const result: CachedData = {
      points: newPoints,
      derivativePoints: newDerivativePoints,
      integralPoints: newIntegralPoints,
      configHash,
    };

    cacheRef.current.set(func.id, result);
    return result;
  }, [func.id, configHash, xRange, cacheRef]);

  const datasets = useMemo(() => {
    const result: any[] = [];

    if (func.visible) {
      result.push({
        label: `${func.type.toUpperCase()}`,
        data: points.map((p) => (isFinite(p.y) ? p.y : null)),
        borderColor: func.color,
        backgroundColor: func.color + '20',
        borderWidth: 2,
        pointRadius: 0,
        tension: 0,
        fill: false,
        spanGaps: false,
      });

      if (func.showDerivative) {
        result.push({
          label: `${func.type.toUpperCase()} 导数`,
          data: derivativePoints.map((p) => (isFinite(p.y) ? p.y : null)),
          borderColor: func.color,
          borderDash: [5, 5],
          borderWidth: 1.5,
          pointRadius: 0,
          tension: 0,
          fill: false,
          spanGaps: false,
        });
      }

      if (func.showIntegral) {
        result.push({
          label: `${func.type.toUpperCase()} 积分`,
          data: integralPoints.map((p) => (isFinite(p.y) ? p.y : null)),
          borderColor: func.color,
          borderDash: [2, 2],
          borderWidth: 1.5,
          pointRadius: 0,
          tension: 0,
          fill: false,
          spanGaps: false,
        });
      }
    }

    return result;
  }, [func, points, derivativePoints, integralPoints]);

  return <>{datasets}</>;
});

const ChartCanvas: React.FC<ChartCanvasProps> = ({
  functions,
  mousePosition,
  markedPoints,
  onMouseMove,
  onChartClick,
  xRange = X_RANGE,
  yRange = Y_RANGE,
}) => {
  const chartRef = useRef<ChartJS<'line'>>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const cacheRef = useRef<Map<string, CachedData>>(new Map());

  const labels = useMemo(() => {
    const result: string[] = [];
    const step = (xRange[1] - xRange[0]) / 100;
    for (let x = xRange[0]; x <= xRange[1]; x += step) {
      result.push(formatPi(x));
    }
    return result;
  }, [xRange]);

  const datasets = useMemo(() => {
    const result: any[] = [];
    functions.forEach((func) => {
      const configHash = getFunctionConfigHash(func, xRange);
      let cached = cacheRef.current.get(func.id);

      if (!cached || cached.configHash !== configHash) {
        const newPoints = generatePoints(func, xRange);
        cached = {
          points: newPoints,
          derivativePoints: computeDerivative(newPoints),
          integralPoints: computeIntegral(newPoints),
          configHash,
        };
        cacheRef.current.set(func.id, cached);
      }

      if (func.visible) {
        result.push({
          label: `${func.type.toUpperCase()}`,
          data: cached.points.map((p) => (isFinite(p.y) ? p.y : null)),
          borderColor: func.color,
          backgroundColor: func.color + '20',
          borderWidth: 2,
          pointRadius: 0,
          tension: 0,
          fill: false,
          spanGaps: false,
        });

        if (func.showDerivative) {
          result.push({
            label: `${func.type.toUpperCase()} 导数`,
            data: cached.derivativePoints.map((p) => (isFinite(p.y) ? p.y : null)),
            borderColor: func.color,
            borderDash: [5, 5],
            borderWidth: 1.5,
            pointRadius: 0,
            tension: 0,
            fill: false,
            spanGaps: false,
          });
        }

        if (func.showIntegral) {
          result.push({
            label: `${func.type.toUpperCase()} 积分`,
            data: cached.integralPoints.map((p) => (isFinite(p.y) ? p.y : null)),
            borderColor: func.color,
            borderDash: [2, 2],
            borderWidth: 1.5,
            pointRadius: 0,
            tension: 0,
            fill: false,
            spanGaps: false,
          });
        }
      }
    });

    return result;
  }, [functions, xRange]);

  const chartData = useMemo(() => ({ labels, datasets }), [labels, datasets]);

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
    onHover: (event: any, elements: any[]) => {
      if (chartRef.current) {
        const chart = chartRef.current;
        const canvas = chart.canvas;
        if (canvas) {
          const rect = canvas.getBoundingClientRect();
          const x = event.x - rect.left;
          const y = event.y - rect.top;
          const xScale = chart.scales.x;
          const yScale = chart.scales.y;
          if (xScale && yScale) {
            const xValue = xScale.getValueForPixel(x);
            const yValue = yScale.getValueForPixel(y);
            onMouseMove({ x: xValue, y: yValue });
          }
        }
      }
      if (elements.length === 0) {
        onMouseMove(null);
      }
    },
    onClick: (event: any) => {
      if (chartRef.current) {
        const chart = chartRef.current;
        const xScale = chart.scales.x;
        const yScale = chart.scales.y;
        if (xScale && yScale) {
          const x = xScale.getValueForPixel(event.x);
          const y = yScale.getValueForPixel(event.y);
          onChartClick({ x, y });
        }
      }
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
        displayColors: true,
        callbacks: {
          label: function(context: any) {
            const label = context.dataset.label || '';
            const value = context.parsed.y;
            return `${label}: ${formatNumber(value, 6)}`;
          },
          title: function(context: any) {
            const xValue = context[0].parsed.x;
            return `x = ${formatPi(xValue)}`;
          },
        },
      },
    },
    scales: {
      x: {
        type: 'linear' as const,
        min: xRange[0],
        max: xRange[1],
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
        min: yRange[0],
        max: yRange[1],
        grid: {
          color: 'rgba(75, 85, 99, 0.3)',
        },
        ticks: {
          color: '#9CA3AF',
          callback: function(value: number | string) {
            return formatNumber(Number(value), 2);
          },
        },
      },
    },
  }), [xRange, yRange, onMouseMove, onChartClick]);

  const renderCrosshair = useCallback(() => {
    if (!chartRef.current || !mousePosition) return null;

    const chart = chartRef.current;
    const xScale = chart.scales.x;
    const yScale = chart.scales.y;

    if (!xScale || !yScale) return null;

    const xPixel = xScale.getPixelForValue(mousePosition.x);
    const yPixel = yScale.getPixelForValue(mousePosition.y);

    return (
      <svg
        className="absolute inset-0 pointer-events-none"
        style={{ width: '100%', height: '100%' }}
      >
        <line
          x1={xPixel}
          y1={0}
          x2={xPixel}
          y2="100%"
          stroke="#165DFF"
          strokeWidth="1"
          strokeDasharray="4,4"
          opacity="0.6"
        />
        <line
          x1={0}
          y1={yPixel}
          x2="100%"
          y2={yPixel}
          stroke="#165DFF"
          strokeWidth="1"
          strokeDasharray="4,4"
          opacity="0.6"
        />
        <circle
          cx={xPixel}
          cy={yPixel}
          r="6"
          fill="#165DFF"
          stroke="white"
          strokeWidth="2"
        />
      </svg>
    );
  }, [mousePosition]);

  const renderMarkedPoints = useCallback(() => {
    if (!chartRef.current || markedPoints.length === 0) return null;

    const chart = chartRef.current;
    const xScale = chart.scales.x;
    const yScale = chart.scales.y;

    if (!xScale || !yScale) return null;

    return (
      <svg
        className="absolute inset-0 pointer-events-none"
        style={{ width: '100%', height: '100%' }}
      >
        {markedPoints.map((point, index) => {
          const xPixel = xScale.getPixelForValue(point.x);
          const yPixel = yScale.getPixelForValue(point.y);

          return (
            <g key={index}>
              <circle
                cx={xPixel}
                cy={yPixel}
                r="5"
                fill="#F53F3F"
                stroke="white"
                strokeWidth="2"
              />
              <text
                x={xPixel + 10}
                y={yPixel - 10}
                fill="#E5E7EB"
                fontSize="12"
                fontFamily="'JetBrains Mono'"
              >
                ({formatPi(point.x)}, {formatNumber(point.y, 4)})
              </text>
            </g>
          );
        })}
      </svg>
    );
  }, [markedPoints]);

  return (
    <div
      ref={containerRef}
      className="relative w-full h-full bg-gray-900/50 rounded-xl border border-gray-700 overflow-hidden"
    >
      <div className="relative w-full h-full">
        <Line ref={chartRef} data={chartData} options={options} redraw={false} />
        {renderCrosshair()}
        {renderMarkedPoints()}
      </div>
    </div>
  );
};

export default memo(ChartCanvas);
