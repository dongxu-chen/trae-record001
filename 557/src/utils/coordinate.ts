export interface ViewState {
  xMin: number;
  xMax: number;
  yMin: number;
  yMax: number;
}

export interface GridConfig {
  xMajorStep: number;
  xMinorStep: number;
  yMajorStep: number;
  yMinorStep: number;
  xOrigin: number;
  yOrigin: number;
}

export interface Tick {
  value: number;
  position: number;
  isMajor: boolean;
  label: string;
}

export function mathToScreen(
  mathX: number,
  mathY: number,
  canvasWidth: number,
  canvasHeight: number,
  viewState: ViewState
): { x: number; y: number } {
  const { xMin, xMax, yMin, yMax } = viewState;
  const x = ((mathX - xMin) / (xMax - xMin)) * canvasWidth;
  const y = canvasHeight - ((mathY - yMin) / (yMax - yMin)) * canvasHeight;
  return { x, y };
}

export function screenToMath(
  screenX: number,
  screenY: number,
  canvasWidth: number,
  canvasHeight: number,
  viewState: ViewState
): { x: number; y: number } {
  const { xMin, xMax, yMin, yMax } = viewState;
  const x = (screenX / canvasWidth) * (xMax - xMin) + xMin;
  const y = ((canvasHeight - screenY) / canvasHeight) * (yMax - yMin) + yMin;
  return { x, y };
}

function computeStepFromRange(range: number, targetCount: number = 8): number {
  if (range <= 0 || !Number.isFinite(range)) return 1;

  const rawStep = range / targetCount;
  const magnitude = Math.pow(10, Math.floor(Math.log10(rawStep)));
  const normalized = rawStep / magnitude;

  let step: number;
  if (normalized < 1.2) {
    step = 1;
  } else if (normalized < 1.8) {
    step = 1.5;
  } else if (normalized < 2.5) {
    step = 2;
  } else if (normalized < 3.5) {
    step = 3;
  } else if (normalized < 7.5) {
    step = 5;
  } else {
    step = 10;
  }

  return step * magnitude;
}

export function calculateGridConfig(viewState: ViewState): GridConfig {
  const { xMin, xMax, yMin, yMax } = viewState;

  const xRange = xMax - xMin;
  const yRange = yMax - yMin;

  const xMajorStep = computeStepFromRange(xRange, 8);
  const yMajorStep = computeStepFromRange(yRange, 8);

  const xMinorStep = xMajorStep / 5;
  const yMinorStep = yMajorStep / 5;

  const xOrigin = Math.floor(xMin / xMajorStep) * xMajorStep;
  const yOrigin = Math.floor(yMin / yMajorStep) * yMajorStep;

  return {
    xMajorStep,
    xMinorStep,
    yMajorStep,
    yMinorStep,
    xOrigin,
    yOrigin
  };
}

export function generateXTicks(
  viewState: ViewState,
  canvasWidth: number,
  config?: GridConfig
): Tick[] {
  const { xMin, xMax } = viewState;
  const gridConfig = config || calculateGridConfig(viewState);
  const ticks: Tick[] = [];

  let current = Math.ceil(xMin / gridConfig.xMinorStep) * gridConfig.xMinorStep;
  const end = xMax;

  while (current <= end) {
    const isMajor = Math.abs(Math.round(current / gridConfig.xMajorStep) * gridConfig.xMajorStep - current) < gridConfig.xMinorStep * 0.1;
    const screenX = ((current - xMin) / (xMax - xMin)) * canvasWidth;

    ticks.push({
      value: current,
      position: screenX,
      isMajor,
      label: isMajor ? formatTickLabel(current) : ''
    });

    current += gridConfig.xMinorStep;
  }

  return ticks;
}

export function generateYTicks(
  viewState: ViewState,
  canvasHeight: number,
  config?: GridConfig
): Tick[] {
  const { yMin, yMax } = viewState;
  const gridConfig = config || calculateGridConfig(viewState);
  const ticks: Tick[] = [];

  let current = Math.ceil(yMin / gridConfig.yMinorStep) * gridConfig.yMinorStep;
  const end = yMax;

  while (current <= end) {
    const isMajor = Math.abs(Math.round(current / gridConfig.yMajorStep) * gridConfig.yMajorStep - current) < gridConfig.yMinorStep * 0.1;
    const screenY = canvasHeight - ((current - yMin) / (yMax - yMin)) * canvasHeight;

    ticks.push({
      value: current,
      position: screenY,
      isMajor,
      label: isMajor ? formatTickLabel(current) : ''
    });

    current += gridConfig.yMinorStep;
  }

  return ticks;
}

export function formatTickLabel(value: number): string {
  if (value === 0) return '0';

  const absValue = Math.abs(value);

  if (absValue >= 1e7 || (absValue < 1e-4 && absValue > 0)) {
    const exp = value.toExponential(3);
    return exp.replace(/\.?0+e([+-])0?/, 'e$1');
  }

  const magnitude = Math.pow(10, Math.floor(Math.log10(absValue)));
  const precision = Math.max(0, 3 - Math.floor(Math.log10(absValue)));

  if (absValue >= 1000) {
    const rounded = Math.round(value / 100) * 100;
    return rounded.toLocaleString('en-US', { maximumFractionDigits: 0 });
  }

  const factor = Math.pow(10, precision);
  const rounded = Math.round(value * factor) / factor;

  const str = rounded.toString();

  if (str.indexOf('.') !== -1) {
    const parts = str.split('.');
    if (parts[1].length > 6) {
      return rounded.toFixed(6).replace(/\.?0+$/, '');
    }
  }

  return str;
}

export function syncViewState(
  currentView: ViewState,
  targetView: ViewState,
  alpha: number = 0.15
): ViewState {
  return {
    xMin: currentView.xMin + (targetView.xMin - currentView.xMin) * alpha,
    xMax: currentView.xMax + (targetView.xMax - currentView.xMax) * alpha,
    yMin: currentView.yMin + (targetView.yMin - currentView.yMin) * alpha,
    yMax: currentView.yMax + (targetView.yMax - currentView.yMax) * alpha
  };
}

export function isViewStable(
  currentView: ViewState,
  targetView: ViewState,
  tolerance: number = 1e-6
): boolean {
  const dxMin = Math.abs(currentView.xMin - targetView.xMin);
  const dxMax = Math.abs(currentView.xMax - targetView.xMax);
  const dyMin = Math.abs(currentView.yMin - targetView.yMin);
  const dyMax = Math.abs(currentView.yMax - targetView.yMax);

  const maxDiff = Math.max(dxMin, dxMax, dyMin, dyMax);
  const range = Math.max(currentView.xMax - currentView.xMin, currentView.yMax - currentView.yMin);

  return maxDiff / range < tolerance;
}

export function calculateZoomCenter(
  viewState: ViewState,
  screenX: number,
  screenY: number,
  canvasWidth: number,
  canvasHeight: number,
  zoomFactor: number
): ViewState {
  const mathPos = screenToMath(screenX, screenY, canvasWidth, canvasHeight, viewState);

  const { xMin, xMax, yMin, yMax } = viewState;
  const xRange = xMax - xMin;
  const yRange = yMax - yMin;

  const newXRange = xRange * zoomFactor;
  const newYRange = yRange * zoomFactor;

  const mouseXRatio = (mathPos.x - xMin) / xRange;
  const mouseYRatio = (yMax - mathPos.y) / yRange;

  const newXMin = mathPos.x - newXRange * mouseXRatio;
  const newXMax = newXMin + newXRange;

  const newYMax = mathPos.y + newYRange * (1 - mouseYRatio);
  const newYMin = newYMax - newYRange;

  return { xMin: newXMin, xMax: newXMax, yMin: newYMin, yMax: newYMax };
}

export function constrainViewState(
  viewState: ViewState,
  minZoom: number = 1e-4,
  maxZoom: number = 1e6
): ViewState {
  let { xMin, xMax, yMin, yMax } = viewState;

  let xRange = xMax - xMin;
  let yRange = yMax - yMin;

  const avgRange = (xRange + yRange) / 2;

  if (avgRange < minZoom) {
    const scale = minZoom / avgRange;
    xRange *= scale;
    yRange *= scale;
  }

  if (avgRange > maxZoom) {
    const scale = maxZoom / avgRange;
    xRange *= scale;
    yRange *= scale;
  }

  const xCenter = (xMin + xMax) / 2;
  const yCenter = (yMin + yMax) / 2;

  return {
    xMin: xCenter - xRange / 2,
    xMax: xCenter + xRange / 2,
    yMin: yCenter - yRange / 2,
    yMax: yCenter + yRange / 2
  };
}

export function calculateOptimalYRange(
  viewState: ViewState,
  functions: Array<(x: number) => number | null>,
  padding: number = 0.1
): ViewState {
  const { xMin, xMax } = viewState;
  const samples = 200;
  let yMin = Infinity;
  let yMax = -Infinity;

  for (let i = 0; i <= samples; i++) {
    const x = xMin + (xMax - xMin) * (i / samples);
    for (const fn of functions) {
      const y = fn(x);
      if (y !== null && Number.isFinite(y)) {
        if (y < yMin) yMin = y;
        if (y > yMax) yMax = y;
      }
    }
  }

  if (!Number.isFinite(yMin) || !Number.isFinite(yMax) || yMin === yMax) {
    return { ...viewState };
  }

  const yRange = yMax - yMin;
  const paddedYMin = yMin - yRange * padding;
  const paddedYMax = yMax + yRange * padding;

  return {
    xMin,
    xMax,
    yMin: paddedYMin,
    yMax: paddedYMax
  };
}

export function getViewInfo(viewState: ViewState): {
  xRange: number;
  yRange: number;
  xCenter: number;
  yCenter: number;
  zoomLevel: number;
} {
  const { xMin, xMax, yMin, yMax } = viewState;
  const xRange = xMax - xMin;
  const yRange = yMax - yMin;
  const xCenter = (xMin + xMax) / 2;
  const yCenter = (yMin + yMax) / 2;

  const baseRange = 20;
  const zoomLevel = baseRange / Math.max(xRange, yRange);

  return { xRange, yRange, xCenter, yCenter, zoomLevel };
}

export function formatZoomLevel(zoomLevel: number): string {
  if (zoomLevel >= 1000) {
    return (zoomLevel / 1000).toFixed(1) + 'k x';
  }
  if (zoomLevel >= 1) {
    return zoomLevel.toFixed(zoomLevel >= 100 ? 0 : 1) + ' x';
  }
  if (zoomLevel >= 0.001) {
    return (zoomLevel * 100).toFixed(2) + '%';
  }
  return zoomLevel.toExponential(2) + ' x';
}
