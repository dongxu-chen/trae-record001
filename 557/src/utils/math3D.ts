import type { Point3D, Point2D, Rotation3D, View3D } from '../types';

export function rotatePoint(point: Point3D, rotation: Rotation3D): Point3D {
  let { x, y, z } = point;

  const cosX = Math.cos(rotation.x);
  const sinX = Math.sin(rotation.x);
  const y1 = y * cosX - z * sinX;
  const z1 = y * sinX + z * cosX;
  y = y1;
  z = z1;

  const cosY = Math.cos(rotation.y);
  const sinY = Math.sin(rotation.y);
  const x1 = x * cosY + z * sinY;
  const z2 = -x * sinY + z * cosY;
  x = x1;
  z = z2;

  const cosZ = Math.cos(rotation.z);
  const sinZ = Math.sin(rotation.z);
  const x2 = x * cosZ - y * sinZ;
  const y2 = x * sinZ + y * cosZ;
  x = x2;
  y = y2;

  return { x, y, z };
}

export function projectPoint(
  point: Point3D,
  view: View3D,
  canvasWidth: number,
  canvasHeight: number
): Point2D & { depth: number } {
  const { rotation, scale, distance, centerX, centerY, centerZ } = view;

  const translated = {
    x: point.x - centerX,
    y: point.y - centerY,
    z: point.z - centerZ
  };

  const rotated = rotatePoint(translated, rotation);

  const perspective = distance / (distance + rotated.z + 0.001);

  return {
    x: canvasWidth / 2 + rotated.x * scale * perspective,
    y: canvasHeight / 2 - rotated.y * scale * perspective,
    depth: rotated.z
  };
}

export function generateSurfaceGrid(
  xMin: number,
  xMax: number,
  yMin: number,
  yMax: number,
  resolution: number,
  evaluator: (x: number, y: number) => number | null
): { vertices: Point3D[][]; faces: [number, number, number][]; colors: string[][] } {
  const vertices: Point3D[][] = [];
  const colors: string[][] = [];
  const faces: [number, number, number][] = [];

  const xStep = (xMax - xMin) / (resolution - 1);
  const yStep = (yMax - yMin) / (resolution - 1);

  let zMin = Infinity;
  let zMax = -Infinity;

  for (let i = 0; i < resolution; i++) {
    vertices[i] = [];
    colors[i] = [];
    for (let j = 0; j < resolution; j++) {
      const x = xMin + i * xStep;
      const y = yMin + j * yStep;
      const z = evaluator(x, y) ?? 0;
      vertices[i][j] = { x, y, z };
      if (z < zMin) zMin = z;
      if (z > zMax) zMax = z;
    }
  }

  const zRange = zMax - zMin || 1;
  for (let i = 0; i < resolution; i++) {
    for (let j = 0; j < resolution; j++) {
      const z = vertices[i][j].z;
      const normalized = (z - zMin) / zRange;
      colors[i][j] = heightToColor(normalized);
    }
  }

  for (let i = 0; i < resolution - 1; i++) {
    for (let j = 0; j < resolution - 1; j++) {
      const idx00 = i * resolution + j;
      const idx10 = (i + 1) * resolution + j;
      const idx01 = i * resolution + (j + 1);
      const idx11 = (i + 1) * resolution + (j + 1);

      faces.push([idx00, idx10, idx11]);
      faces.push([idx00, idx11, idx01]);
    }
  }

  return { vertices, faces, colors };
}

export function heightToColor(t: number): string {
  t = Math.max(0, Math.min(1, t));

  const r = Math.round(255 * (t < 0.5 ? t * 2 : 1));
  const g = Math.round(255 * (t < 0.5 ? t * 2 : 2 - t * 2));
  const b = Math.round(255 * (t < 0.5 ? 1 : 2 - t * 2));

  return `rgb(${r}, ${g}, ${b})`;
}

export function calculateSurfaceBounds(
  xMin: number,
  xMax: number,
  yMin: number,
  yMax: number,
  resolution: number,
  evaluator: (x: number, y: number) => number | null
): { xMin: number; xMax: number; yMin: number; yMax: number; zMin: number; zMax: number } {
  let zMin = Infinity;
  let zMax = -Infinity;

  const xStep = (xMax - xMin) / (resolution - 1);
  const yStep = (yMax - yMin) / (resolution - 1);

  for (let i = 0; i < resolution; i++) {
    for (let j = 0; j < resolution; j++) {
      const x = xMin + i * xStep;
      const y = yMin + j * yStep;
      const z = evaluator(x, y);
      if (z !== null && Number.isFinite(z)) {
        if (z < zMin) zMin = z;
        if (z > zMax) zMax = z;
      }
    }
  }

  if (!Number.isFinite(zMin)) zMin = -1;
  if (!Number.isFinite(zMax)) zMax = 1;
  if (zMin === zMax) {
    zMin -= 1;
    zMax += 1;
  }

  return { xMin, xMax, yMin, yMax, zMin, zMax };
}

export function autoScale3D(
  bounds: { zMin: number; zMax: number },
  canvasWidth: number,
  canvasHeight: number
): number {
  const zRange = bounds.zMax - bounds.zMin;
  const minDim = Math.min(canvasWidth, canvasHeight);
  return Math.max(1, minDim / (zRange * 3));
}

export function draw3DAxes(
  ctx: CanvasRenderingContext2D,
  view: View3D,
  bounds: { xMin: number; xMax: number; yMin: number; yMax: number; zMin: number; zMax: number },
  canvasWidth: number,
  canvasHeight: number
): void {
  const { xMin, xMax, yMin, yMax, zMin, zMax } = bounds;
  const centerX = (xMin + xMax) / 2;
  const centerY = (yMin + yMax) / 2;
  const centerZ = (zMin + zMax) / 2;

  const axisLength = Math.min(xMax - xMin, yMax - yMin, zMax - zMin) * 0.8;

  const origin = projectPoint({ x: centerX, y: centerY, z: centerZ }, view, canvasWidth, canvasHeight);
  const xEnd = projectPoint({ x: centerX + axisLength, y: centerY, z: centerZ }, view, canvasWidth, canvasHeight);
  const yEnd = projectPoint({ x: centerX, y: centerY + axisLength, z: centerZ }, view, canvasWidth, canvasHeight);
  const zEnd = projectPoint({ x: centerX, y: centerY, z: centerZ + axisLength }, view, canvasWidth, canvasHeight);

  ctx.lineWidth = 2;

  ctx.strokeStyle = '#ef4444';
  ctx.beginPath();
  ctx.moveTo(origin.x, origin.y);
  ctx.lineTo(xEnd.x, xEnd.y);
  ctx.stroke();
  ctx.fillStyle = '#ef4444';
  ctx.fillText('X', xEnd.x + 5, xEnd.y);

  ctx.strokeStyle = '#22c55e';
  ctx.beginPath();
  ctx.moveTo(origin.x, origin.y);
  ctx.lineTo(yEnd.x, yEnd.y);
  ctx.stroke();
  ctx.fillStyle = '#22c55e';
  ctx.fillText('Y', yEnd.x + 5, yEnd.y);

  ctx.strokeStyle = '#3b82f6';
  ctx.beginPath();
  ctx.moveTo(origin.x, origin.y);
  ctx.lineTo(zEnd.x, zEnd.y);
  ctx.stroke();
  ctx.fillStyle = '#3b82f6';
  ctx.fillText('Z', zEnd.x + 5, zEnd.y);
}

export function draw3DGrid(
  ctx: CanvasRenderingContext2D,
  view: View3D,
  bounds: { xMin: number; xMax: number; yMin: number; yMax: number; zMin: number; zMax: number },
  canvasWidth: number,
  canvasHeight: number
): void {
  const { xMin, xMax, yMin, yMax, zMin, zMax } = bounds;
  const centerZ = zMin;

  ctx.strokeStyle = 'rgba(148, 163, 184, 0.3)';
  ctx.lineWidth = 0.5;

  const steps = 10;
  const xStep = (xMax - xMin) / steps;
  const yStep = (yMax - yMin) / steps;

  for (let i = 0; i <= steps; i++) {
    const x = xMin + i * xStep;
    const p1 = projectPoint({ x, y: yMin, z: centerZ }, view, canvasWidth, canvasHeight);
    const p2 = projectPoint({ x, y: yMax, z: centerZ }, view, canvasWidth, canvasHeight);
    ctx.beginPath();
    ctx.moveTo(p1.x, p1.y);
    ctx.lineTo(p2.x, p2.y);
    ctx.stroke();
  }

  for (let j = 0; j <= steps; j++) {
    const y = yMin + j * yStep;
    const p1 = projectPoint({ x: xMin, y, z: centerZ }, view, canvasWidth, canvasHeight);
    const p2 = projectPoint({ x: xMax, y, z: centerZ }, view, canvasWidth, canvasHeight);
    ctx.beginPath();
    ctx.moveTo(p1.x, p1.y);
    ctx.lineTo(p2.x, p2.y);
    ctx.stroke();
  }
}

export function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

export function easeInOut(t: number): number {
  return t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
}

export function easeOutElastic(t: number): number {
  const c4 = (2 * Math.PI) / 3;
  return t === 0 ? 0 : t === 1 ? 1 : Math.pow(2, -10 * t) * Math.sin((t * 10 - 0.75) * c4) + 1;
}
