export type FunctionType = 'sin' | 'cos' | 'tan' | 'cot' | 'sec' | 'csc' | 'custom';

export type PolarCurveType = 'cardioid' | 'limacon' | 'rose' | 'lemniscate' | 'spiral' | 'circle';

export type DisplayMode = 'cartesian' | 'polar' | 'fourier';

export interface FunctionConfig {
  id: string;
  type: FunctionType;
  expression?: string;
  frequency: number;
  phase: number;
  amplitude: number;
  color: string;
  visible: boolean;
  showDerivative: boolean;
  showIntegral: boolean;
}

export interface Point {
  x: number;
  y: number;
}

export interface PolarPoint {
  r: number;
  theta: number;
}

export interface PolarCurveConfig {
  id: string;
  type: PolarCurveType;
  a: number;
  b: number;
  n: number;
  color: string;
  visible: boolean;
}

export interface AnimationState {
  isPlaying: boolean;
  speed: number;
  currentTime: number;
  animationParam: 'phase' | 'frequency' | 'amplitude';
}

export interface FourierConfig {
  type: 'square' | 'sawtooth' | 'triangle';
  harmonics: number;
  frequency: number;
  amplitude: number;
  showComponents: boolean;
  showSum: boolean;
}

export interface ChartState {
  functions: FunctionConfig[];
  xRange: [number, number];
  yRange: [number, number];
  mousePosition: Point | null;
  markedPoints: Point[];
  zoom: number;
}

export const FUNCTION_COLORS: Record<FunctionType, string> = {
  sin: '#165DFF',
  cos: '#0FC6C2',
  tan: '#722ED1',
  cot: '#F53F3F',
  sec: '#FF7D00',
  csc: '#14C9C9',
  custom: '#86909C',
};

export const POLAR_CURVE_COLORS: Record<PolarCurveType, string> = {
  cardioid: '#FF7D00',
  limacon: '#722ED1',
  rose: '#F53F3F',
  lemniscate: '#0FC6C2',
  spiral: '#165DFF',
  circle: '#14C9C9',
};

export const POLAR_CURVE_NAMES: Record<PolarCurveType, string> = {
  cardioid: '心形线',
  limacon: '蚶线',
  rose: '玫瑰线',
  lemniscate: '双纽线',
  spiral: '阿基米德螺线',
  circle: '圆',
};

export const DEFAULT_FUNCTIONS: FunctionConfig[] = [
  {
    id: 'func-1',
    type: 'sin',
    frequency: 1,
    phase: 0,
    amplitude: 1,
    color: '#165DFF',
    visible: true,
    showDerivative: false,
    showIntegral: false,
  },
];

export const DEFAULT_POLAR_CURVES: PolarCurveConfig[] = [
  {
    id: 'polar-1',
    type: 'cardioid',
    a: 1,
    b: 1,
    n: 3,
    color: '#FF7D00',
    visible: true,
  },
];

export const DEFAULT_FOURIER_CONFIG: FourierConfig = {
  type: 'square',
  harmonics: 5,
  frequency: 1,
  amplitude: 1,
  showComponents: true,
  showSum: true,
};

export const X_RANGE: [number, number] = [-2 * Math.PI, 2 * Math.PI];
export const Y_RANGE: [number, number] = [-3, 3];
export const POINT_COUNT = 500;
export const POLAR_POINT_COUNT = 1000;
