import { useRef, useCallback, useEffect, useMemo } from 'react';
import { useGraphStore } from '../store/useGraphStore';
import {
  mathToScreen,
  calculateGridConfig,
  generateXTicks,
  generateYTicks,
  type GridConfig,
  type Tick
} from '../utils/coordinate';
import { evaluateFunction } from '../utils/expressionParser';
import { hexToRgba } from '../utils/colors';
import type { FunctionItem, ViewState, DrawConfig, IntegrationConfig } from '../types';
import { drawIntegrationArea } from './useIntegration';
import { drawAnimatedPath } from './useAnimation';

interface UseCanvasOptions {
  width: number;
  height: number;
  integrationPoints?: { x: number; y: number | null }[];
  integrationConfig?: IntegrationConfig;
  animatedPoints?: { x: number; y: number | null }[];
  animatedColor?: string;
  animatedEnabled?: boolean;
}

interface DrawFunctionOptions {
  ctx: CanvasRenderingContext2D;
  func: FunctionItem;
  viewState: ViewState;
  drawConfig: DrawConfig;
  width: number;
  height: number;
  isDerivative?: boolean;
}

export const useCanvas = ({
  width,
  height,
  integrationPoints = [],
  integrationConfig,
  animatedPoints = [],
  animatedColor = '#3b82f6',
  animatedEnabled = false
}: UseCanvasOptions) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const { functions, viewState, drawConfig } = useGraphStore();

  const mathToScreenLocal = useCallback((mx: number, my: number) => {
    return mathToScreen(mx, my, width, height, viewState);
  }, [width, height, viewState]);

  const gridConfig = useMemo<GridConfig>(() => {
    return calculateGridConfig(viewState);
  }, [viewState.xMin, viewState.xMax, viewState.yMin, viewState.yMax]);

  const xTicks = useMemo<Tick[]>(() => {
    return generateXTicks(viewState, width, gridConfig);
  }, [viewState, width, gridConfig]);

  const yTicks = useMemo<Tick[]>(() => {
    return generateYTicks(viewState, height, gridConfig);
  }, [viewState, height, gridConfig]);

  const drawGrid = useCallback(
    (ctx: CanvasRenderingContext2D) => {
      if (!viewState.gridVisible) return;

      xTicks.forEach((tick) => {
        ctx.beginPath();
        ctx.moveTo(tick.position, 0);
        ctx.lineTo(tick.position, height);

        if (tick.isMajor) {
          ctx.strokeStyle = drawConfig.gridColor;
          ctx.lineWidth = 1;
        } else {
          ctx.strokeStyle = hexToRgba(drawConfig.gridColor, 0.3);
          ctx.lineWidth = 0.5;
        }
        ctx.stroke();
      });

      yTicks.forEach((tick) => {
        ctx.beginPath();
        ctx.moveTo(0, tick.position);
        ctx.lineTo(width, tick.position);

        if (tick.isMajor) {
          ctx.strokeStyle = drawConfig.gridColor;
          ctx.lineWidth = 1;
        } else {
          ctx.strokeStyle = hexToRgba(drawConfig.gridColor, 0.3);
          ctx.lineWidth = 0.5;
        }
        ctx.stroke();
      });
    },
    [viewState.gridVisible, xTicks, yTicks, drawConfig.gridColor, width, height]
  );

  const drawAxes = useCallback(
    (ctx: CanvasRenderingContext2D) => {
      if (!viewState.axisVisible) return;

      ctx.strokeStyle = drawConfig.axisColor;
      ctx.fillStyle = drawConfig.axisColor;
      ctx.lineWidth = 2;
      ctx.font = '12px Inter, sans-serif';

      const { x: originX, y: originY } = mathToScreen(0, 0, width, height, viewState);

      const clampedOriginX = Math.max(0, Math.min(width, originX));
      const clampedOriginY = Math.max(0, Math.min(height, originY));

      ctx.beginPath();
      ctx.moveTo(0, clampedOriginY);
      ctx.lineTo(width, clampedOriginY);
      ctx.moveTo(clampedOriginX, 0);
      ctx.lineTo(clampedOriginX, height);
      ctx.stroke();

      ctx.beginPath();
      ctx.moveTo(width, clampedOriginY);
      ctx.lineTo(width - 10, clampedOriginY - 5);
      ctx.lineTo(width - 10, clampedOriginY + 5);
      ctx.closePath();
      ctx.fill();

      ctx.beginPath();
      ctx.moveTo(clampedOriginX, 0);
      ctx.lineTo(clampedOriginX - 5, 10);
      ctx.lineTo(clampedOriginX + 5, 10);
      ctx.closePath();
      ctx.fill();

      ctx.fillText('x', width - 15, clampedOriginY - 10);
      ctx.fillText('y', clampedOriginX + 10, 15);

      ctx.fillStyle = '#94a3b8';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'top';
      xTicks.forEach((tick) => {
        if (tick.isMajor && tick.label && Math.abs(tick.value) > 1e-10) {
          ctx.fillText(tick.label, tick.position, clampedOriginY + 6);
        }
      });

      ctx.textAlign = 'right';
      ctx.textBaseline = 'middle';
      yTicks.forEach((tick) => {
        if (tick.isMajor && tick.label && Math.abs(tick.value) > 1e-10) {
          ctx.fillText(tick.label, clampedOriginX - 6, tick.position);
        }
      });

      ctx.textAlign = 'right';
      ctx.textBaseline = 'top';
      ctx.fillText('O', clampedOriginX - 6, clampedOriginY + 6);
    },
    [viewState.axisVisible, drawConfig.axisColor, width, height, viewState, xTicks, yTicks]
  );

  const drawFunctionCurve = useCallback(
    ({ ctx, func, viewState, drawConfig, width, height, isDerivative = false }: DrawFunctionOptions) => {
      const compiled = isDerivative ? func.derivativeCompiled : func.compiledFunction;
      if (!compiled) return;

      const numPoints = Math.max(width * 3, 1500);
      const step = (viewState.xMax - viewState.xMin) / (numPoints - 1);

      ctx.strokeStyle = isDerivative ? hexToRgba(func.color, 0.6) : func.color;
      ctx.lineWidth = isDerivative ? drawConfig.lineWidth - 0.5 : drawConfig.lineWidth;
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';

      if (!isDerivative) {
        ctx.shadowColor = func.color;
        ctx.shadowBlur = 8;
      } else {
        ctx.shadowBlur = 0;
        ctx.setLineDash([8, 4]);
      }

      ctx.beginPath();
      let isFirstPoint = true;
      let lastY: number | null = null;

      for (let i = 0; i < numPoints; i++) {
        const x = viewState.xMin + i * step;
        const y = evaluateFunction(compiled, x);

        if (y === null || !isFinite(y) || Math.abs(y) > 1e12) {
          isFirstPoint = true;
          lastY = null;
          continue;
        }

        if (lastY !== null) {
          const diff = Math.abs(y - lastY);
          const range = viewState.yMax - viewState.yMin;
          if (diff > range * 0.3) {
            isFirstPoint = true;
          }
        }

        const { x: screenX, y: screenY } = mathToScreen(x, y, width, height, viewState);

        if (screenY < -2000 || screenY > height + 2000) {
          isFirstPoint = true;
          lastY = y;
          continue;
        }

        if (isFirstPoint) {
          ctx.moveTo(screenX, screenY);
          isFirstPoint = false;
        } else {
          ctx.lineTo(screenX, screenY);
        }

        lastY = y;
      }

      ctx.stroke();
      ctx.shadowBlur = 0;
      ctx.setLineDash([]);
    },
    []
  );

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas || width === 0 || height === 0) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.fillStyle = drawConfig.backgroundColor;
    ctx.fillRect(0, 0, width, height);

    drawGrid(ctx);
    drawAxes(ctx);

    if (integrationConfig?.enabled && integrationConfig.showArea && integrationPoints.length > 0) {
      drawIntegrationArea({
        ctx,
        points: integrationPoints,
        mathToScreen: mathToScreenLocal,
        lowerBound: integrationConfig.lowerBound,
        upperBound: integrationConfig.upperBound,
        viewState,
        fillColor: integrationConfig.fillColor,
        fillOpacity: integrationConfig.fillOpacity
      });
    }

    functions.forEach((func) => {
      if (!func.visible) return;
      drawFunctionCurve({
        ctx,
        func,
        viewState,
        drawConfig,
        width,
        height,
      });

      if (func.showDerivative && func.derivativeCompiled) {
        drawFunctionCurve({
          ctx,
          func,
          viewState,
          drawConfig,
          width,
          height,
          isDerivative: true,
        });
      }
    });

    if (animatedEnabled && animatedPoints.length > 0) {
      drawAnimatedPath({
        ctx,
        points: animatedPoints,
        mathToScreen: mathToScreenLocal,
        color: animatedColor,
        lineWidth: 3,
        showTrail: true,
        trailLength: 100
      });
    }
  }, [
    functions,
    viewState,
    drawConfig,
    width,
    height,
    drawGrid,
    drawAxes,
    drawFunctionCurve,
    integrationConfig,
    integrationPoints,
    animatedEnabled,
    animatedPoints,
    animatedColor,
    mathToScreenLocal
  ]);

  const exportToPNG = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return null;
    return canvas.toDataURL('image/png');
  }, []);

  useEffect(() => {
    draw();
  }, [draw]);

  return {
    canvasRef,
    draw,
    exportToPNG,
    gridConfig,
    xTicks,
    yTicks,
  };
};
