import type { DataPoint } from '../types';

export interface SnapResult {
  index: number;
  point: DataPoint;
  distance: number;
}

export function findNearestDataPoint(
  clientX: number,
  clientY: number,
  dataPoints: DataPoint[],
  chartContainer: HTMLElement,
  chartType: 'timeSeries' | 'scatter' | 'bar'
): SnapResult | null {
  if (dataPoints.length === 0) return null;

  const rect = chartContainer.getBoundingClientRect();
  const canvasX = clientX - rect.left;
  const canvasY = clientY - rect.top;

  const padding = { left: 60, right: 40, top: 50, bottom: 50 };
  const chartWidth = rect.width - padding.left - padding.right;
  const chartHeight = rect.height - padding.top - padding.bottom;

  let minDistance = Infinity;
  let nearestIndex = -1;

  dataPoints.forEach((point, index) => {
    let pointX: number;
    let pointY: number;

    const yValues = dataPoints.map((p) => p.y);
    const minY = Math.min(...yValues);
    const maxY = Math.max(...yValues);
    const yRange = maxY - minY || 1;

    if (chartType === 'timeSeries' || chartType === 'bar') {
      pointX = padding.left + (index / (dataPoints.length - 1 || 1)) * chartWidth;
      pointY = padding.top + (1 - (point.y - minY) / yRange) * chartHeight;
    } else {
      const xValues = dataPoints.map((p) => Number(p.x));
      const minX = Math.min(...xValues);
      const maxX = Math.max(...xValues);
      const xRange = maxX - minX || 1;

      pointX = padding.left + ((Number(point.x) - minX) / xRange) * chartWidth;
      pointY = padding.top + (1 - (point.y - minY) / yRange) * chartHeight;
    }

    const distance = Math.sqrt(Math.pow(canvasX - pointX, 2) + Math.pow(canvasY - pointY, 2));

    if (distance < minDistance) {
      minDistance = distance;
      nearestIndex = index;
    }
  });

  if (nearestIndex >= 0) {
    return {
      index: nearestIndex,
      point: dataPoints[nearestIndex],
      distance: minDistance,
    };
  }

  return null;
}

export const SNAP_THRESHOLD = 50;
