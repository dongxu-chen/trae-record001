import * as THREE from 'three';

export function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

export function lerpVector3(a: THREE.Vector3, b: THREE.Vector3, t: number): THREE.Vector3 {
  return new THREE.Vector3(
    lerp(a.x, b.x, t),
    lerp(a.y, b.y, t),
    lerp(a.z, b.z, t)
  );
}

export function lerpQuaternion(a: THREE.Quaternion, b: THREE.Quaternion, t: number): THREE.Quaternion {
  return a.clone().slerp(b, t);
}

export function inverseLerp(a: number, b: number, value: number): number {
  if (a === b) return 0;
  return (value - a) / (b - a);
}

export function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

export function smoothStep(edge0: number, edge1: number, x: number): number {
  const t = clamp((x - edge0) / (edge1 - edge0), 0, 1);
  return t * t * (3 - 2 * t);
}

export function smootherStep(edge0: number, edge1: number, x: number): number {
  const t = clamp((x - edge0) / (edge1 - edge0), 0, 1);
  return t * t * t * (t * (t * 6 - 15) + 10);
}

export function bezierLinear(p0: number, p1: number, t: number): number {
  return lerp(p0, p1, t);
}

export function bezierQuadratic(p0: number, p1: number, p2: number, t: number): number {
  const mt = 1 - t;
  return mt * mt * p0 + 2 * mt * t * p1 + t * t * p2;
}

export function bezierCubic(p0: number, p1: number, p2: number, p3: number, t: number): number {
  const mt = 1 - t;
  return mt * mt * mt * p0 + 3 * mt * mt * t * p1 + 3 * mt * t * t * p2 + t * t * t * p3;
}

export function bezierQuadraticVector3(
  p0: THREE.Vector3,
  p1: THREE.Vector3,
  p2: THREE.Vector3,
  t: number
): THREE.Vector3 {
  return new THREE.Vector3(
    bezierQuadratic(p0.x, p1.x, p2.x, t),
    bezierQuadratic(p0.y, p1.y, p2.y, t),
    bezierQuadratic(p0.z, p1.z, p2.z, t)
  );
}

export function bezierCubicVector3(
  p0: THREE.Vector3,
  p1: THREE.Vector3,
  p2: THREE.Vector3,
  p3: THREE.Vector3,
  t: number
): THREE.Vector3 {
  return new THREE.Vector3(
    bezierCubic(p0.x, p1.x, p2.x, p3.x, t),
    bezierCubic(p0.y, p1.y, p2.y, p3.y, t),
    bezierCubic(p0.z, p1.z, p2.z, p3.z, t)
  );
}

export function bezierCubicDerivative(
  p0: number,
  p1: number,
  p2: number,
  p3: number,
  t: number
): number {
  const mt = 1 - t;
  return 3 * mt * mt * (p1 - p0) + 6 * mt * t * (p2 - p1) + 3 * t * t * (p3 - p2);
}

export function bezierCubicDerivativeVector3(
  p0: THREE.Vector3,
  p1: THREE.Vector3,
  p2: THREE.Vector3,
  p3: THREE.Vector3,
  t: number
): THREE.Vector3 {
  return new THREE.Vector3(
    bezierCubicDerivative(p0.x, p1.x, p2.x, p3.x, t),
    bezierCubicDerivative(p0.y, p1.y, p2.y, p3.y, t),
    bezierCubicDerivative(p0.z, p1.z, p2.z, p3.z, t)
  );
}

export function catmullRom(
  p0: number,
  p1: number,
  p2: number,
  p3: number,
  t: number,
  alpha: number = 0.5
): number {
  const t2 = t * t;
  const t3 = t2 * t;

  const v0 = (p2 - p0) * alpha;
  const v1 = (p3 - p1) * alpha;

  return (
    (2 * p1 - 2 * p2 + v0 + v1) * t3 +
    (-3 * p1 + 3 * p2 - 2 * v0 - v1) * t2 +
    v0 * t +
    p1
  );
}

export function catmullRomVector3(
  p0: THREE.Vector3,
  p1: THREE.Vector3,
  p2: THREE.Vector3,
  p3: THREE.Vector3,
  t: number,
  alpha: number = 0.5
): THREE.Vector3 {
  return new THREE.Vector3(
    catmullRom(p0.x, p1.x, p2.x, p3.x, t, alpha),
    catmullRom(p0.y, p1.y, p2.y, p3.y, t, alpha),
    catmullRom(p0.z, p1.z, p2.z, p3.z, t, alpha)
  );
}

export interface CubicSplineSegment {
  a: number;
  b: number;
  c: number;
  d: number;
  x: number;
}

export function computeCubicSpline(
  xValues: number[],
  yValues: number[]
): CubicSplineSegment[] {
  const n = xValues.length - 1;
  const segments: CubicSplineSegment[] = [];

  if (n < 1) return segments;

  const h: number[] = [];
  const alpha: number[] = [];
  const l: number[] = [1];
  const mu: number[] = [0];
  const z: number[] = [0];

  for (let i = 0; i < n; i++) {
    h[i] = xValues[i + 1] - xValues[i];
  }

  for (let i = 1; i < n; i++) {
    alpha[i] =
      (3 / h[i]) * (yValues[i + 1] - yValues[i]) -
      (3 / h[i - 1]) * (yValues[i] - yValues[i - 1]);
  }

  for (let i = 1; i < n; i++) {
    l[i] = 2 * (xValues[i + 1] - xValues[i - 1]) - h[i - 1] * mu[i - 1];
    mu[i] = h[i] / l[i];
    z[i] = (alpha[i] - h[i - 1] * z[i - 1]) / l[i];
  }

  const c: number[] = new Array(n + 1).fill(0);
  const b: number[] = new Array(n).fill(0);
  const d: number[] = new Array(n).fill(0);

  l[n] = 1;
  z[n] = 0;
  c[n] = 0;

  for (let j = n - 1; j >= 0; j--) {
    c[j] = z[j] - mu[j] * c[j + 1];
    b[j] = (yValues[j + 1] - yValues[j]) / h[j] - (h[j] * (c[j + 1] + 2 * c[j])) / 3;
    d[j] = (c[j + 1] - c[j]) / (3 * h[j]);
  }

  for (let i = 0; i < n; i++) {
    segments.push({
      a: yValues[i],
      b: b[i],
      c: c[i],
      d: d[i],
      x: xValues[i],
    });
  }

  return segments;
}

export function evaluateCubicSpline(
  segments: CubicSplineSegment[],
  x: number
): number {
  if (segments.length === 0) return 0;

  let segment = segments[0];
  for (let i = segments.length - 1; i >= 0; i--) {
    if (x >= segments[i].x) {
      segment = segments[i];
      break;
    }
  }

  const dx = x - segment.x;
  return segment.a + segment.b * dx + segment.c * dx * dx + segment.d * dx * dx * dx;
}

export function evaluateCubicSplineDerivative(
  segments: CubicSplineSegment[],
  x: number
): number {
  if (segments.length === 0) return 0;

  let segment = segments[0];
  for (let i = segments.length - 1; i >= 0; i--) {
    if (x >= segments[i].x) {
      segment = segments[i];
      break;
    }
  }

  const dx = x - segment.x;
  return segment.b + 2 * segment.c * dx + 3 * segment.d * dx * dx;
}

export function remap(
  value: number,
  inMin: number,
  inMax: number,
  outMin: number,
  outMax: number
): number {
  const t = inverseLerp(inMin, inMax, value);
  return lerp(outMin, outMax, t);
}

export function remapClamped(
  value: number,
  inMin: number,
  inMax: number,
  outMin: number,
  outMax: number
): number {
  const t = clamp(inverseLerp(inMin, inMax, value), 0, 1);
  return lerp(outMin, outMax, t);
}

export function pingPong(t: number, length: number): number {
  const period = length * 2;
  const mod = ((t % period) + period) % period;
  return mod < length ? mod : period - mod;
}

export function easeInOutCubic(t: number): number {
  return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
}

export function easeInOutQuad(t: number): number {
  return t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
}

export function easeOutElastic(t: number): number {
  const c4 = (2 * Math.PI) / 3;
  return t === 0 ? 0 : t === 1 ? 1 : Math.pow(2, -10 * t) * Math.sin((t * 10 - 0.75) * c4) + 1;
}

export function easeOutBounce(t: number): number {
  const n1 = 7.5625;
  const d1 = 2.75;

  if (t < 1 / d1) {
    return n1 * t * t;
  } else if (t < 2 / d1) {
    return n1 * (t -= 1.5 / d1) * t + 0.75;
  } else if (t < 2.5 / d1) {
    return n1 * (t -= 2.25 / d1) * t + 0.9375;
  } else {
    return n1 * (t -= 2.625 / d1) * t + 0.984375;
  }
}

export function curveLength(
  curveFunction: (t: number) => THREE.Vector3,
  startT: number = 0,
  endT: number = 1,
  samples: number = 100
): number {
  let length = 0;
  let prevPoint = curveFunction(startT);

  for (let i = 1; i <= samples; i++) {
    const t = startT + (endT - startT) * (i / samples);
    const point = curveFunction(t);
    length += prevPoint.distanceTo(point);
    prevPoint = point;
  }

  return length;
}

export function arcLengthParameterize(
  curveFunction: (t: number) => THREE.Vector3,
  targetLength: number,
  startT: number = 0,
  endT: number = 1,
  tolerance: number = 0.001,
  maxIterations: number = 20
): number {
  let low = startT;
  let high = endT;

  for (let i = 0; i < maxIterations; i++) {
    const mid = (low + high) / 2;
    const currentLength = curveLength(curveFunction, startT, mid);

    if (Math.abs(currentLength - targetLength) < tolerance) {
      return mid;
    }

    if (currentLength < targetLength) {
      low = mid;
    } else {
      high = mid;
    }
  }

  return (low + high) / 2;
}
