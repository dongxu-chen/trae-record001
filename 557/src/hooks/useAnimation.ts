import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import type { AnimationConfig, CompiledExpression } from '../types';
import { compileExpressionWithParameter, validateParameterizedExpression, substituteParameter } from '../utils/binaryParser';

interface UseAnimationProps {
  expression: string;
  viewState: { xMin: number; xMax: number };
  numPoints?: number;
}

interface UseAnimationReturn {
  animationConfig: AnimationConfig;
  setAnimationConfig: React.Dispatch<React.SetStateAction<AnimationConfig>>;
  currentPoints: { x: number; y: number | null }[];
  currentExpression: string;
  isPlaying: boolean;
  play: () => void;
  pause: () => void;
  reset: () => void;
  stepForward: () => void;
  stepBackward: () => void;
  setParameterValue: (value: number) => void;
  validation: { valid: boolean; error?: string };
  compiledFunction: CompiledExpression | null;
}

export function useAnimation({
  expression,
  viewState,
  numPoints = 500
}: UseAnimationProps): UseAnimationReturn {
  const [animationConfig, setAnimationConfig] = useState<AnimationConfig>({
    enabled: false,
    parameterName: 'a',
    parameterStart: 0,
    parameterEnd: 10,
    parameterSpeed: 1,
    currentValue: 0,
    isPlaying: false,
    loop: true,
    duration: 5
  });

  const animationFrameRef = useRef<number | null>(null);
  const startTimeRef = useRef<number>(0);
  const lastUpdateRef = useRef<number>(0);

  const validation = useMemo(() => {
    return validateParameterizedExpression(expression, animationConfig.parameterName);
  }, [expression, animationConfig.parameterName]);

  const compiledFunction = useMemo(() => {
    if (!validation.valid) return null;
    const result = compileExpressionWithParameter(
      expression,
      animationConfig.parameterName,
      animationConfig.currentValue
    );
    return result.success && result.compiled ? result.compiled : null;
  }, [expression, animationConfig.parameterName, animationConfig.currentValue, validation.valid]);

  const currentExpression = useMemo(() => {
    return substituteParameter(expression, animationConfig.parameterName, animationConfig.currentValue);
  }, [expression, animationConfig.parameterName, animationConfig.currentValue]);

  const currentPoints = useMemo(() => {
    if (!compiledFunction) return [];

    const points: { x: number; y: number | null }[] = [];
    const step = (viewState.xMax - viewState.xMin) / (numPoints - 1);

    for (let i = 0; i < numPoints; i++) {
      const x = viewState.xMin + i * step;
      const y = compiledFunction.evaluate(x);
      points.push({ x, y });
    }

    return points;
  }, [compiledFunction, viewState.xMin, viewState.xMax, numPoints]);

  const updateParameterFromTime = useCallback((elapsed: number) => {
    const { parameterStart, parameterEnd, duration, loop } = animationConfig;
    const range = parameterEnd - parameterStart;
    const t = (elapsed % duration) / duration;

    let value: number;
    if (loop) {
      const pingPongT = t < 0.5 ? t * 2 : 2 - t * 2;
      value = parameterStart + range * pingPongT;
    } else {
      value = parameterStart + range * Math.min(1, t);
    }

    setAnimationConfig(prev => ({ ...prev, currentValue: value }));
  }, [animationConfig]);

  const animate = useCallback((time: number) => {
    if (!animationConfig.isPlaying) return;

    if (!startTimeRef.current) {
      startTimeRef.current = time;
      lastUpdateRef.current = time;
    }

    const elapsed = (time - startTimeRef.current) / 1000;

    if (time - lastUpdateRef.current >= 16) {
      updateParameterFromTime(elapsed);
      lastUpdateRef.current = time;
    }

    if (!animationConfig.loop && elapsed >= animationConfig.duration) {
      setAnimationConfig(prev => ({ ...prev, isPlaying: false }));
      return;
    }

    animationFrameRef.current = requestAnimationFrame(animate);
  }, [animationConfig.isPlaying, animationConfig.loop, animationConfig.duration, updateParameterFromTime]);

  useEffect(() => {
    if (animationConfig.isPlaying && validation.valid) {
      animationFrameRef.current = requestAnimationFrame(animate);
    }

    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [animationConfig.isPlaying, validation.valid, animate]);

  const play = useCallback(() => {
    if (!validation.valid) return;
    startTimeRef.current = 0;
    setAnimationConfig(prev => ({ ...prev, isPlaying: true }));
  }, [validation.valid]);

  const pause = useCallback(() => {
    setAnimationConfig(prev => ({ ...prev, isPlaying: false }));
  }, []);

  const reset = useCallback(() => {
    startTimeRef.current = 0;
    setAnimationConfig(prev => ({
      ...prev,
      isPlaying: false,
      currentValue: prev.parameterStart
    }));
  }, []);

  const stepForward = useCallback(() => {
    setAnimationConfig(prev => ({
      ...prev,
      currentValue: Math.min(prev.parameterEnd, prev.currentValue + prev.parameterSpeed * 0.1)
    }));
  }, []);

  const stepBackward = useCallback(() => {
    setAnimationConfig(prev => ({
      ...prev,
      currentValue: Math.max(prev.parameterStart, prev.currentValue - prev.parameterSpeed * 0.1)
    }));
  }, []);

  const setParameterValue = useCallback((value: number) => {
    setAnimationConfig(prev => ({
      ...prev,
      currentValue: Math.max(prev.parameterStart, Math.min(prev.parameterEnd, value))
    }));
  }, []);

  return {
    animationConfig,
    setAnimationConfig,
    currentPoints,
    currentExpression,
    isPlaying: animationConfig.isPlaying,
    play,
    pause,
    reset,
    stepForward,
    stepBackward,
    setParameterValue,
    validation,
    compiledFunction
  };
}

interface AnimatedPathProps {
  ctx: CanvasRenderingContext2D;
  points: { x: number; y: number | null }[];
  mathToScreen: (mx: number, my: number) => { x: number; y: number };
  color: string;
  lineWidth?: number;
  showTrail?: boolean;
  trailLength?: number;
}

export function drawAnimatedPath({
  ctx,
  points,
  mathToScreen,
  color,
  lineWidth = 2,
  showTrail = true,
  trailLength = 50
}: AnimatedPathProps): void {
  let firstPoint = true;
  const validPoints: { x: number; y: number }[] = [];

  for (const point of points) {
    if (point.y === null || !Number.isFinite(point.y)) {
      firstPoint = true;
      continue;
    }

    const screen = mathToScreen(point.x, point.y);
    validPoints.push(screen);
  }

  const totalPoints = validPoints.length;
  const fadeStart = Math.max(0, totalPoints - trailLength);

  for (let i = 0; i < validPoints.length - 1; i++) {
    const p1 = validPoints[i];
    const p2 = validPoints[i + 1];

    if (showTrail && i < fadeStart) {
      const alpha = (i / fadeStart) * 0.3;
      ctx.strokeStyle = hexToRgba(color, alpha);
    } else {
      ctx.strokeStyle = color;
    }

    ctx.lineWidth = lineWidth;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';

    ctx.beginPath();
    ctx.moveTo(p1.x, p1.y);
    ctx.lineTo(p2.x, p2.y);
    ctx.stroke();
  }

  if (validPoints.length > 0) {
    const lastPoint = validPoints[validPoints.length - 1];
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.arc(lastPoint.x, lastPoint.y, 5, 0, Math.PI * 2);
    ctx.fill();

    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = 2;
    ctx.stroke();
  }
}

function hexToRgba(hex: string, alpha: number): string {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}
