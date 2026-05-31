import type { CompiledExpression } from '../utils/recursiveParser';

export interface FunctionItem {
  id: string;
  expression: string;
  compiledFunction: CompiledExpression;
  color: string;
  visible: boolean;
  showDerivative: boolean;
  derivativeExpression?: string;
  derivativeCompiled?: CompiledExpression;
}

export interface ViewState {
  xMin: number;
  xMax: number;
  yMin: number;
  yMax: number;
  gridVisible: boolean;
  axisVisible: boolean;
}

export interface DrawConfig {
  lineWidth: number;
  gridColor: string;
  axisColor: string;
  backgroundColor: string;
}

export interface Point3D {
  x: number;
  y: number;
  z: number;
}

export interface Point2D {
  x: number;
  y: number;
}

export interface Rotation3D {
  x: number;
  y: number;
  z: number;
}

export interface View3D {
  rotation: Rotation3D;
  scale: number;
  distance: number;
  centerX: number;
  centerY: number;
  centerZ: number;
}

export interface Surface3D {
  id: string;
  expression: string;
  color: string;
  visible: boolean;
  xMin: number;
  xMax: number;
  yMin: number;
  yMax: number;
  resolution: number;
  showWireframe: boolean;
  showSurface: boolean;
}

export interface AnimationConfig {
  enabled: boolean;
  parameterName: string;
  parameterStart: number;
  parameterEnd: number;
  parameterSpeed: number;
  currentValue: number;
  isPlaying: boolean;
  loop: boolean;
  duration: number;
}

export interface IntegrationConfig {
  enabled: boolean;
  functionId: string;
  lowerBound: number;
  upperBound: number;
  result: number;
  showArea: boolean;
  fillColor: string;
  fillOpacity: number;
}

export interface CompiledBinaryFunction {
  evaluate: (x: number, y: number) => number | null;
}

export interface MouseState {
  x: number;
  y: number;
  mathX: number;
  mathY: number;
  isDragging: boolean;
}

export interface ValidateRequest {
  expression: string;
}

export interface ValidateResponse {
  valid: boolean;
  error?: string;
}

export interface DerivativeRequest {
  expression: string;
  variable?: string;
}

export interface DerivativeResponse {
  success: boolean;
  derivative?: string;
  error?: string;
}

export interface EvaluateRequest {
  expression: string;
  xValues: number[];
}

export interface EvaluateResponse {
  success: boolean;
  yValues: number[];
  error?: string;
}

export interface ExportRequest {
  imageData: string;
  width: number;
  height: number;
}

export interface ExportResponse {
  success: boolean;
  downloadUrl?: string;
  error?: string;
}
