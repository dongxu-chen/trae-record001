import { evaluate, parse } from 'mathjs';
import { FunctionConfig, Point, POINT_COUNT, X_RANGE, FunctionType, PolarCurveConfig, PolarPoint, POLAR_POINT_COUNT, FourierConfig } from '../types';

const DISCONTINUITY_THRESHOLD = 1e10;
const JUMP_THRESHOLD = 50;

export function buildFunctionExpression(config: FunctionConfig): string {
  if (config.type === 'custom' && config.expression) {
    return config.expression;
  }

  const { type, frequency, phase, amplitude } = config;
  const f = frequency !== 1 ? `${frequency} * ` : '';
  const p = phase !== 0 ? ` + ${phase}` : '';
  const a = amplitude !== 1 ? `${amplitude} * ` : '';

  return `${a}${type}(${f}x${p})`;
}

export function evaluateFunction(expression: string, x: number): number {
  try {
    const result = evaluate(expression, { x });
    if (typeof result === 'number') {
      return Math.fround(result);
    }
    return NaN;
  } catch {
    return NaN;
  }
}

export function detectDiscontinuity(prevY: number, currY: number): boolean {
  if (!isFinite(prevY) || !isFinite(currY)) {
    return true;
  }

  if (Math.abs(prevY) > DISCONTINUITY_THRESHOLD || Math.abs(currY) > DISCONTINUITY_THRESHOLD) {
    return true;
  }

  if (Math.abs(currY - prevY) > JUMP_THRESHOLD && Math.abs(prevY) < DISCONTINUITY_THRESHOLD) {
    return true;
  }

  return false;
}

export function generatePoints(config: FunctionConfig, xRange: [number, number] = X_RANGE, count: number = POINT_COUNT): Point[] {
  const expression = buildFunctionExpression(config);
  const points: Point[] = [];
  const step = (xRange[1] - xRange[0]) / count;
  let prevY: number | null = null;

  for (let i = 0; i <= count; i++) {
    const x = xRange[0] + i * step;
    const y = evaluateFunction(expression, x);

    if (prevY !== null && detectDiscontinuity(prevY, y)) {
      points.push({ x: points[points.length - 1].x, y: NaN });
    }

    if (isFinite(y) && Math.abs(y) <= DISCONTINUITY_THRESHOLD) {
      points.push({ x: Math.fround(x), y: Math.fround(y) });
    } else {
      points.push({ x: Math.fround(x), y: NaN });
    }

    prevY = isFinite(y) && Math.abs(y) <= DISCONTINUITY_THRESHOLD ? y : null;
  }

  return points;
}

export function computeDerivative(points: Point[]): Point[] {
  const derivative: Point[] = [];

  for (let i = 0; i < points.length; i++) {
    if (i === 0 || i === points.length - 1) {
      derivative.push({ x: points[i].x, y: NaN });
      continue;
    }

    const prev = points[i - 1];
    const next = points[i + 1];

    if (!isFinite(prev.y) || !isFinite(next.y)) {
      derivative.push({ x: points[i].x, y: NaN });
      continue;
    }

    const dx = next.x - prev.x;
    const dy = next.y - prev.y;
    const result = dy / dx;

    if (Math.abs(result) > DISCONTINUITY_THRESHOLD) {
      derivative.push({ x: points[i].x, y: NaN });
    } else {
      derivative.push({ x: points[i].x, y: Math.fround(result) });
    }
  }

  return derivative;
}

export function computeIntegral(points: Point[], startValue: number = 0): Point[] {
  const integral: Point[] = [];
  let sum = Math.fround(startValue);

  for (let i = 0; i < points.length; i++) {
    if (i === 0) {
      integral.push({ x: points[i].x, y: Math.fround(startValue) });
      continue;
    }

    const prev = points[i - 1];
    const curr = points[i];

    if (isFinite(prev.y) && isFinite(curr.y)) {
      const dx = curr.x - prev.x;
      sum = Math.fround(sum + ((prev.y + curr.y) / 2) * dx);
      integral.push({ x: curr.x, y: sum });
    } else {
      integral.push({ x: curr.x, y: NaN });
    }
  }

  return integral;
}

export function validateExpression(expression: string): boolean {
  try {
    parse(expression);
    return true;
  } catch {
    return false;
  }
}

export function formatPi(x: number): string {
  if (!isFinite(x)) return '∞';

  const piMultiple = x / Math.PI;
  const tolerance = 0.001;

  if (Math.abs(piMultiple) < tolerance) return '0';
  if (Math.abs(piMultiple - 1) < tolerance) return 'π';
  if (Math.abs(piMultiple + 1) < tolerance) return '-π';
  if (Math.abs(piMultiple - 2) < tolerance) return '2π';
  if (Math.abs(piMultiple + 2) < tolerance) return '-2π';
  if (Math.abs(piMultiple - 0.5) < tolerance) return 'π/2';
  if (Math.abs(piMultiple + 0.5) < tolerance) return '-π/2';
  if (Math.abs(piMultiple - 1.5) < tolerance) return '3π/2';
  if (Math.abs(piMultiple + 1.5) < tolerance) return '-3π/2';

  return formatNumber(x);
}

export function formatNumber(value: number, precision: number = 4): string {
  if (!isFinite(value)) return '∞';

  if (Math.abs(value) < 1e-6 && Math.abs(value) > 0) {
    return value.toExponential(2);
  }

  if (Math.abs(value) >= 1e6) {
    return value.toExponential(2);
  }

  return value.toFixed(precision).replace(/\.?0+$/, '');
}

export function getFunctionDiscontinuities(type: FunctionType, frequency: number, phase: number): number[] {
  const discontinuities: number[] = [];
  const period = Math.PI / frequency;

  switch (type) {
    case 'tan':
    case 'sec': {
      for (let k = -4; k <= 4; k++) {
        const x = (Math.PI / 2 - phase + k * period) / frequency;
        if (x >= -2 * Math.PI && x <= 2 * Math.PI) {
          discontinuities.push(x);
        }
      }
      break;
    }
    case 'cot':
    case 'csc': {
      for (let k = -4; k <= 4; k++) {
        const x = (-phase + k * period) / frequency;
        if (x >= -2 * Math.PI && x <= 2 * Math.PI) {
          discontinuities.push(x);
        }
      }
      break;
    }
    default:
      break;
  }

  return discontinuities;
}

export function polarToCartesian(r: number, theta: number): Point {
  return {
    x: r * Math.cos(theta),
    y: r * Math.sin(theta),
  };
}

export function evaluatePolarCurve(config: PolarCurveConfig, theta: number): number {
  const { type, a, b, n } = config;

  switch (type) {
    case 'cardioid':
      return a * (1 + Math.cos(theta));
    case 'limacon':
      return a + b * Math.cos(theta);
    case 'rose':
      return a * Math.cos(n * theta);
    case 'lemniscate':
      const cos2t = Math.cos(2 * theta);
      return cos2t >= 0 ? a * Math.sqrt(cos2t) : NaN;
    case 'spiral':
      return a * theta;
    case 'circle':
      return a;
    default:
      return a;
  }
}

export function generatePolarPoints(config: PolarCurveConfig, thetaRange: [number, number] = [0, 2 * Math.PI], count: number = POLAR_POINT_COUNT): Point[] {
  const points: Point[] = [];
  const step = (thetaRange[1] - thetaRange[0]) / count;
  let prevR: number | null = null;

  for (let i = 0; i <= count; i++) {
    const theta = thetaRange[0] + i * step;
    const r = evaluatePolarCurve(config, theta);

    if (prevR !== null && (!isFinite(r) || !isFinite(prevR) || Math.abs(r - prevR) > JUMP_THRESHOLD)) {
      points.push({ x: NaN, y: NaN });
    }

    if (isFinite(r)) {
      const cartesian = polarToCartesian(r, theta);
      points.push({ x: Math.fround(cartesian.x), y: Math.fround(cartesian.y) });
    } else {
      points.push({ x: NaN, y: NaN });
    }

    prevR = isFinite(r) ? r : null;
  }

  return points;
}

export function generatePolarCurveWithAnimation(config: PolarCurveConfig, time: number): Point[] {
  const animatedConfig = { ...config };
  animatedConfig.a = config.a * (1 + 0.3 * Math.sin(time));
  return generatePolarPoints(animatedConfig);
}

export function fourierSquareWave(x: number, harmonics: number, frequency: number = 1, amplitude: number = 1): number {
  let sum = 0;
  for (let n = 1; n <= harmonics; n += 2) {
    sum += (1 / n) * Math.sin(n * frequency * x);
  }
  return amplitude * (4 / Math.PI) * sum;
}

export function fourierSawtoothWave(x: number, harmonics: number, frequency: number = 1, amplitude: number = 1): number {
  let sum = 0;
  for (let n = 1; n <= harmonics; n++) {
    sum += (Math.pow(-1, n + 1) / n) * Math.sin(n * frequency * x);
  }
  return amplitude * (2 / Math.PI) * sum;
}

export function fourierTriangleWave(x: number, harmonics: number, frequency: number = 1, amplitude: number = 1): number {
  let sum = 0;
  for (let n = 1; n <= harmonics; n += 2) {
    sum += (Math.pow(-1, (n - 1) / 2) / (n * n)) * Math.sin(n * frequency * x);
  }
  return amplitude * (8 / (Math.PI * Math.PI)) * sum;
}

export function evaluateFourier(config: FourierConfig, x: number): number {
  const { type, harmonics, frequency, amplitude } = config;

  switch (type) {
    case 'square':
      return fourierSquareWave(x, harmonics, frequency, amplitude);
    case 'sawtooth':
      return fourierSawtoothWave(x, harmonics, frequency, amplitude);
    case 'triangle':
      return fourierTriangleWave(x, harmonics, frequency, amplitude);
    default:
      return fourierSquareWave(x, harmonics, frequency, amplitude);
  }
}

export function generateFourierPoints(config: FourierConfig, xRange: [number, number] = X_RANGE, count: number = POINT_COUNT): Point[] {
  const points: Point[] = [];
  const step = (xRange[1] - xRange[0]) / count;

  for (let i = 0; i <= count; i++) {
    const x = xRange[0] + i * step;
    const y = evaluateFourier(config, x);
    points.push({ x: Math.fround(x), y: Math.fround(y) });
  }

  return points;
}

export function generateFourierHarmonics(config: FourierConfig, xRange: [number, number] = X_RANGE, count: number = POINT_COUNT): Point[][] {
  const harmonics: Point[][] = [];
  const { type, frequency, amplitude } = config;

  const maxHarmonic = type === 'square' || type === 'triangle' ? config.harmonics * 2 : config.harmonics;

  for (let n = 1; n <= config.harmonics; n++) {
    const harmonicNumber = type === 'square' || type === 'triangle' ? 2 * n - 1 : n;
    const points: Point[] = [];
    const step = (xRange[1] - xRange[0]) / count;

    let waveFunction: (x: number) => number;

    switch (type) {
      case 'square':
        waveFunction = (x) => amplitude * (4 / Math.PI) * (1 / harmonicNumber) * Math.sin(harmonicNumber * frequency * x);
        break;
      case 'sawtooth':
        waveFunction = (x) => amplitude * (2 / Math.PI) * (Math.pow(-1, harmonicNumber + 1) / harmonicNumber) * Math.sin(harmonicNumber * frequency * x);
        break;
      case 'triangle':
        waveFunction = (x) => amplitude * (8 / (Math.PI * Math.PI)) * (Math.pow(-1, (harmonicNumber - 1) / 2) / (harmonicNumber * harmonicNumber)) * Math.sin(harmonicNumber * frequency * x);
        break;
      default:
        waveFunction = (x) => 0;
    }

    for (let i = 0; i <= count; i++) {
      const x = xRange[0] + i * step;
      points.push({ x: Math.fround(x), y: Math.fround(waveFunction(x)) });
    }

    harmonics.push(points);
  }

  return harmonics;
}

export const HARMONIC_COLORS = [
  '#165DFF',
  '#0FC6C2',
  '#722ED1',
  '#F53F3F',
  '#FF7D00',
  '#14C9C9',
  '#F7BA1E',
  '#CB26A0',
];
