import { useEffect, useRef } from 'react';
import Decimal from 'decimal.js';
import { parse } from '../engine/parser';
import { evaluateToDecimal, EvaluateOptions, UserFunction } from '../engine/evaluator';

interface GraphCanvasProps {
  expression: string;
  xRange?: [number, number];
  yRange?: [number, number];
  width?: number;
  height?: number;
  userFunctions?: UserFunction[];
  angleMode?: 'deg' | 'rad';
  errorCallback?: (error: string | null) => void;
}

export default function GraphCanvas({
  expression,
  xRange = [-10, 10],
  yRange = [-10, 10],
  width = 600,
  height = 360,
  userFunctions = [],
  angleMode = 'rad',
  errorCallback,
}: GraphCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.clearRect(0, 0, width, height);

    const bg = ctx.createLinearGradient(0, 0, 0, height);
    bg.addColorStop(0, 'rgba(15, 22, 36, 0.95)');
    bg.addColorStop(1, 'rgba(8, 12, 24, 0.98)');
    ctx.fillStyle = bg;
    ctx.fillRect(0, 0, width, height);

    const padding = 40;
    const plotWidth = width - padding * 2;
    const plotHeight = height - padding * 2;

    const toCanvasX = (x: number) => padding + ((x - xRange[0]) / (xRange[1] - xRange[0])) * plotWidth;
    const toCanvasY = (y: number) => padding + (1 - (y - yRange[0]) / (yRange[1] - yRange[0])) * plotHeight;
    const toMathX = (cx: number) => xRange[0] + ((cx - padding) / plotWidth) * (xRange[1] - xRange[0]);

    ctx.strokeStyle = 'rgba(0, 229, 255, 0.15)';
    ctx.lineWidth = 0.5;

    const xStep = (xRange[1] - xRange[0]) / 10;
    for (let x = Math.ceil(xRange[0] / xStep) * xStep; x <= xRange[1]; x += xStep) {
      const cx = toCanvasX(x);
      ctx.beginPath();
      ctx.moveTo(cx, padding);
      ctx.lineTo(cx, height - padding);
      ctx.stroke();
    }

    const yStep = (yRange[1] - yRange[0]) / 8;
    for (let y = Math.ceil(yRange[0] / yStep) * yStep; y <= yRange[1]; y += yStep) {
      const cy = toCanvasY(y);
      ctx.beginPath();
      ctx.moveTo(padding, cy);
      ctx.lineTo(width - padding, cy);
      ctx.stroke();
    }

    ctx.strokeStyle = 'rgba(0, 229, 255, 0.5)';
    ctx.lineWidth = 1.5;

    if (yRange[0] <= 0 && yRange[1] >= 0) {
      const cy = toCanvasY(0);
      ctx.beginPath();
      ctx.moveTo(padding, cy);
      ctx.lineTo(width - padding, cy);
      ctx.stroke();
    }
    if (xRange[0] <= 0 && xRange[1] >= 0) {
      const cx = toCanvasX(0);
      ctx.beginPath();
      ctx.moveTo(cx, padding);
      ctx.lineTo(cx, height - padding);
      ctx.stroke();
    }

    ctx.fillStyle = 'rgba(255, 255, 255, 0.4)';
    ctx.font = '11px JetBrains Mono, monospace';
    ctx.textAlign = 'center';

    for (let x = Math.ceil(xRange[0] / xStep) * xStep; x <= xRange[1]; x += xStep) {
      if (Math.abs(x) < 0.001) continue;
      const cx = toCanvasX(x);
      ctx.fillText(x.toFixed(1), cx, height - padding + 16);
    }

    ctx.textAlign = 'right';
    for (let y = Math.ceil(yRange[0] / yStep) * yStep; y <= yRange[1]; y += yStep) {
      if (Math.abs(y) < 0.001) continue;
      const cy = toCanvasY(y) + 4;
      ctx.fillText(y.toFixed(1), padding - 8, cy);
    }

    if (!expression.trim()) {
      if (errorCallback) errorCallback(null);
      return;
    }

    const knownFunctions = new Set(userFunctions.map((f) => f.name));
    const knownIdents = new Set<string>(['x']);
    const { ast, error } = parse(expression, {
      knownFunctions,
      knownIdentifiers: knownIdents,
      allowFreeVariables: false,
    });

    if (error || !ast) {
      if (errorCallback) errorCallback(error?.message || '表达式无效');
      return;
    }
    if (errorCallback) errorCallback(null);

    const evalOptions: EvaluateOptions = {
      angleMode,
      userFunctions,
      variables: { x: '0' },
    };

    ctx.strokeStyle = '#00e5ff';
    ctx.lineWidth = 2;
    ctx.shadowColor = 'rgba(0, 229, 255, 0.6)';
    ctx.shadowBlur = 8;
    ctx.lineJoin = 'round';
    ctx.lineCap = 'round';

    const samples = plotWidth * 2;
    let firstPoint = true;
    let prevY: number | null = null;

    for (let i = 0; i <= samples; i++) {
      const cx = padding + (i / samples) * plotWidth;
      const mathX = toMathX(cx);
      try {
        const y = evaluateToDecimal(ast, { ...evalOptions, variables: { x: new Decimal(mathX) } });
        const yNum = y.toNumber();
        if (isFinite(yNum) && yNum >= yRange[0] - (yRange[1] - yRange[0]) && yNum <= yRange[1] + (yRange[1] - yRange[0])) {
          const cy = toCanvasY(Math.max(yRange[0], Math.min(yRange[1], yNum)));
          if (firstPoint) {
            ctx.beginPath();
            ctx.moveTo(cx, cy);
            firstPoint = false;
          } else {
            if (prevY !== null && Math.abs(yNum - prevY) > (yRange[1] - yRange[0]) * 0.8) {
              ctx.stroke();
              ctx.beginPath();
              ctx.moveTo(cx, cy);
            } else {
              ctx.lineTo(cx, cy);
            }
          }
          prevY = yNum;
        } else {
          if (!firstPoint) {
            ctx.stroke();
            firstPoint = true;
          }
          prevY = null;
        }
      } catch {
        if (!firstPoint) {
          ctx.stroke();
          firstPoint = true;
        }
        prevY = null;
      }
    }
    if (!firstPoint) ctx.stroke();

    ctx.shadowBlur = 0;
  }, [expression, xRange, yRange, width, height, userFunctions, angleMode, errorCallback]);

  return (
    <div ref={containerRef} className="graph-canvas-container">
      <canvas
        ref={canvasRef}
        width={width}
        height={height}
        style={{ width: '100%', height: 'auto', borderRadius: '14px' }}
      />
    </div>
  );
}
