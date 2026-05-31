import { useState, useEffect, useMemo, useCallback } from 'react';
import type { IntegrationConfig, CompiledExpression } from '../types';
import {
  computeDefiniteIntegral,
  computeDefiniteIntegralAdaptive,
  generateIntegrationPoints
} from '../utils/binaryParser';

interface UseIntegrationProps {
  functions: { id: string; expression: string; compiledFunction: CompiledExpression }[];
  viewState: { xMin: number; xMax: number; yMin: number; yMax: number };
}

interface UseIntegrationReturn {
  integrationConfig: IntegrationConfig;
  setIntegrationConfig: React.Dispatch<React.SetStateAction<IntegrationConfig>>;
  integrationResult: number;
  integrationPoints: { x: number; y: number | null }[];
  selectedFunction: { id: string; expression: string } | null;
  setSelectedFunctionId: (id: string) => void;
  setLowerBound: (value: number) => void;
  setUpperBound: (value: number) => void;
  calculateIntegral: (useAdaptive?: boolean) => number;
  error?: string;
}

export function useIntegration({
  functions,
  viewState
}: UseIntegrationProps): UseIntegrationReturn {
  const [integrationConfig, setIntegrationConfig] = useState<IntegrationConfig>({
    enabled: false,
    functionId: '',
    lowerBound: 0,
    upperBound: 1,
    result: 0,
    showArea: true,
    fillColor: '#60a5fa',
    fillOpacity: 0.4
  });

  const [integrationResult, setIntegrationResult] = useState<number>(0);
  const [error, setError] = useState<string | undefined>();

  const selectedFunction = useMemo(() => {
    if (!integrationConfig.functionId) return null;
    return functions.find(f => f.id === integrationConfig.functionId) || null;
  }, [functions, integrationConfig.functionId]);

  const integrationPoints = useMemo(() => {
    if (!selectedFunction || !integrationConfig.enabled) return [];

    return generateIntegrationPoints(
      selectedFunction.compiledFunction,
      integrationConfig.lowerBound,
      integrationConfig.upperBound,
      300
    );
  }, [selectedFunction, integrationConfig.enabled, integrationConfig.lowerBound, integrationConfig.upperBound]);

  const calculateIntegral = useCallback((useAdaptive: boolean = true): number => {
    if (!selectedFunction) {
      setError('请先选择一个函数');
      return 0;
    }

    try {
      const { lowerBound, upperBound } = integrationConfig;
      let result: number;

      if (useAdaptive) {
        result = computeDefiniteIntegralAdaptive(
          selectedFunction.compiledFunction,
          lowerBound,
          upperBound,
          1e-8,
          25
        );
      } else {
        result = computeDefiniteIntegral(
          selectedFunction.compiledFunction,
          lowerBound,
          upperBound,
          100000
        );
      }

      setIntegrationResult(result);
      setError(undefined);
      setIntegrationConfig(prev => ({ ...prev, result }));
      return result;
    } catch (e) {
      setError((e as Error).message);
      return 0;
    }
  }, [selectedFunction, integrationConfig.lowerBound, integrationConfig.upperBound]);

  useEffect(() => {
    if (integrationConfig.enabled && selectedFunction) {
      calculateIntegral();
    }
  }, [integrationConfig.enabled, selectedFunction, integrationConfig.lowerBound, integrationConfig.upperBound, calculateIntegral]);

  const setSelectedFunctionId = useCallback((id: string) => {
    setIntegrationConfig(prev => ({ ...prev, functionId: id, enabled: true }));
  }, []);

  const setLowerBound = useCallback((value: number) => {
    setIntegrationConfig(prev => ({ ...prev, lowerBound: value }));
  }, []);

  const setUpperBound = useCallback((value: number) => {
    setIntegrationConfig(prev => ({ ...prev, upperBound: value }));
  }, []);

  return {
    integrationConfig,
    setIntegrationConfig,
    integrationResult,
    integrationPoints,
    selectedFunction,
    setSelectedFunctionId,
    setLowerBound,
    setUpperBound,
    calculateIntegral,
    error
  };
}

interface DrawIntegrationAreaProps {
  ctx: CanvasRenderingContext2D;
  points: { x: number; y: number | null }[];
  mathToScreen: (mx: number, my: number) => { x: number; y: number };
  lowerBound: number;
  upperBound: number;
  viewState: { xMin: number; xMax: number; yMin: number; yMax: number };
  fillColor: string;
  fillOpacity: number;
}

export function drawIntegrationArea({
  ctx,
  points,
  mathToScreen,
  lowerBound,
  upperBound,
  viewState,
  fillColor,
  fillOpacity
}: DrawIntegrationAreaProps): void {
  if (points.length === 0) return;

  const yZero = viewState.yMin <= 0 && viewState.yMax >= 0 ? 0 : Math.sign(viewState.yMin) === Math.sign(viewState.yMax)
    ? (Math.abs(viewState.yMin) < Math.abs(viewState.yMax) ? viewState.yMin : viewState.yMax)
    : 0;

  const lowerScreen = mathToScreen(lowerBound, yZero);
  const upperScreen = mathToScreen(upperBound, yZero);

  ctx.save();

  ctx.beginPath();
  ctx.moveTo(lowerScreen.x, lowerScreen.y);

  let firstPoint = true;
  let lastValidPoint: { x: number; y: number } | null = null;

  for (const point of points) {
    if (point.y === null || !Number.isFinite(point.y)) {
      if (lastValidPoint) {
        const screenY0 = mathToScreen(point.x, yZero).y;
        ctx.lineTo(lastValidPoint.x, screenY0);
        lastValidPoint = null;
      }
      firstPoint = true;
      continue;
    }

    const screen = mathToScreen(point.x, point.y);
    const screenY0 = mathToScreen(point.x, yZero).y;

    if (firstPoint) {
      ctx.lineTo(screen.x, screenY0);
      firstPoint = false;
    }

    ctx.lineTo(screen.x, screen.y);
    lastValidPoint = screen;
  }

  if (lastValidPoint) {
    ctx.lineTo(lastValidPoint.x, upperScreen.y);
  }

  ctx.lineTo(upperScreen.x, upperScreen.y);
  ctx.closePath();

  const gradient = ctx.createLinearGradient(0, upperScreen.y, 0, lowerScreen.y);
  gradient.addColorStop(0, hexToRgba(fillColor, fillOpacity * 0.5));
  gradient.addColorStop(1, hexToRgba(fillColor, fillOpacity));
  ctx.fillStyle = gradient;
  ctx.fill();

  ctx.strokeStyle = fillColor;
  ctx.lineWidth = 2;
  ctx.stroke();

  ctx.setLineDash([5, 5]);
  ctx.strokeStyle = hexToRgba(fillColor, 0.8);
  ctx.lineWidth = 1;

  ctx.beginPath();
  ctx.moveTo(lowerScreen.x, lowerScreen.y);
  ctx.lineTo(lowerScreen.x, mathToScreen(lowerBound, points[0]?.y ?? 0).y);
  ctx.stroke();

  ctx.beginPath();
  ctx.moveTo(upperScreen.x, upperScreen.y);
  const lastY = points[points.length - 1]?.y ?? 0;
  ctx.lineTo(upperScreen.x, mathToScreen(upperBound, lastY).y);
  ctx.stroke();

  ctx.setLineDash([]);

  ctx.fillStyle = fillColor;
  ctx.font = 'bold 14px sans-serif';
  ctx.textAlign = 'center';

  const midX = (lowerBound + upperBound) / 2;
  const labelY = yZero;
  const labelScreen = mathToScreen(midX, labelY);

  ctx.fillStyle = hexToRgba(fillColor, 0.2);
  const text = `∫ = ${formatNumber(integrate(points, lowerBound, upperBound))}`;
  const textWidth = ctx.measureText(text).width;
  ctx.fillRect(labelScreen.x - textWidth / 2 - 8, labelScreen.y - 20, textWidth + 16, 24);

  ctx.fillStyle = fillColor;
  ctx.fillText(text, labelScreen.x, labelScreen.y - 4);

  ctx.restore();
}

function integrate(points: { x: number; y: number | null }[], lower: number, upper: number): number {
  let sum = 0;
  for (let i = 0; i < points.length - 1; i++) {
    const p1 = points[i];
    const p2 = points[i + 1];
    if (p1.y !== null && p2.y !== null && Number.isFinite(p1.y) && Number.isFinite(p2.y)) {
      sum += (p1.y + p2.y) / 2 * (p2.x - p1.x);
    }
  }
  return sum;
}

function formatNumber(num: number): string {
  if (Math.abs(num) < 0.001 && num !== 0) {
    return num.toExponential(4);
  }
  if (Math.abs(num) >= 10000) {
    return num.toExponential(4);
  }
  return num.toFixed(6).replace(/\.?0+$/, '');
}

function hexToRgba(hex: string, alpha: number): string {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}
