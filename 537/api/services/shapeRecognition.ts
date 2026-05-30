import type { Point, Point3D, Shape, ShapeType, Shape3D, Shape3DType, ShapeRelation, RelationType } from '../../shared/types';
import { SHAPE3D_COLORS } from '../../shared/types';

const SHAPE_COLORS: Record<ShapeType, string> = {
  rectangle: '#FF6B6B',
  circle: '#4ECDC4',
  triangle: '#FFE66D',
  polygon: '#95E1D3',
};

function generateId(): string {
  return Math.random().toString(36).substring(2, 11);
}

function distance(p1: Point, p2: Point): number {
  return Math.sqrt((p2.x - p1.x) ** 2 + (p2.y - p1.y) ** 2);
}

function polygonArea(points: Point[]): number {
  let area = 0;
  const n = points.length;
  for (let i = 0; i < n; i++) {
    const j = (i + 1) % n;
    area += points[i].x * points[j].y;
    area -= points[j].x * points[i].y;
  }
  return Math.abs(area) / 2;
}

function polygonPerimeter(points: Point[]): number {
  let perimeter = 0;
  const n = points.length;
  for (let i = 0; i < n; i++) {
    const j = (i + 1) % n;
    perimeter += distance(points[i], points[j]);
  }
  return perimeter;
}

function polygonCenter(points: Point[]): Point {
  let cx = 0, cy = 0;
  const n = points.length;
  for (const p of points) {
    cx += p.x;
    cy += p.y;
  }
  return { x: cx / n, y: cy / n };
}

function boundingBox(points: Point[]): { x: number; y: number; width: number; height: number } {
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  for (const p of points) {
    minX = Math.min(minX, p.x);
    minY = Math.min(minY, p.y);
    maxX = Math.max(maxX, p.x);
    maxY = Math.max(maxY, p.y);
  }
  return { x: minX, y: minY, width: maxX - minX, height: maxY - minY };
}

function perpendicularDistance(point: Point, start: Point, end: Point): number {
  const dx = end.x - start.x;
  const dy = end.y - start.y;
  const mag = Math.sqrt(dx * dx + dy * dy);
  if (mag === 0) return distance(point, start);
  return Math.abs(dy * point.x - dx * point.y + end.x * start.y - end.y * start.x) / mag;
}

function rdpRecursive(points: Point[], epsilon: number, startIndex: number, endIndex: number): boolean[] {
  const keep = new Array(points.length).fill(false);
  keep[startIndex] = true;
  keep[endIndex] = true;

  let maxDist = 0;
  let maxIndex = startIndex;

  for (let i = startIndex + 1; i < endIndex; i++) {
    const dist = perpendicularDistance(points[i], points[startIndex], points[endIndex]);
    if (dist > maxDist) {
      maxDist = dist;
      maxIndex = i;
    }
  }

  if (maxDist > epsilon) {
    const left = rdpRecursive(points, epsilon, startIndex, maxIndex);
    const right = rdpRecursive(points, epsilon, maxIndex, endIndex);
    for (let i = 0; i < points.length; i++) {
      if (left[i] || right[i]) keep[i] = true;
    }
  }

  return keep;
}

function ramerDouglasPeucker(points: Point[], epsilon: number, closed = true): Point[] {
  if (points.length < 3) return [...points];

  let workPoints = closed ? ensureClosedPolygon(points) : [...points];

  const n = workPoints.length;
  const keep = rdpRecursive(workPoints, epsilon, 0, n - 1);

  const result = workPoints.filter((_, i) => keep[i]);

  if (closed && result.length > 1) {
    const first = result[0];
    const last = result[result.length - 1];
    if (distance(first, last) < epsilon * 2) {
      result.pop();
    }
  }

  return result.length >= 3 ? result : workPoints;
}

function ensureClosedPolygon(points: Point[]): Point[] {
  if (points.length < 3) return points;
  const first = points[0];
  const last = points[points.length - 1];
  if (distance(first, last) > 1) {
    return [...points, { ...first }];
  }
  return [...points];
}

function detectEdges(imageData: ImageData, width: number, height: number): boolean[][] {
  const sobelX = [[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]];
  const sobelY = [[-1, -2, -1], [0, 0, 0], [1, 2, 1]];

  const grayscale: number[][] = [];
  for (let y = 0; y < height; y++) {
    grayscale[y] = [];
    for (let x = 0; x < width; x++) {
      const idx = (y * width + x) * 4;
      const r = imageData.data[idx];
      const g = imageData.data[idx + 1];
      const b = imageData.data[idx + 2];
      grayscale[y][x] = 0.299 * r + 0.587 * g + 0.114 * b;
    }
  }

  const edges: boolean[][] = [];
  const threshold = 30;

  for (let y = 0; y < height; y++) {
    edges[y] = [];
    for (let x = 0; x < width; x++) {
      if (x === 0 || x === width - 1 || y === 0 || y === height - 1) {
        edges[y][x] = false;
        continue;
      }

      let gx = 0, gy = 0;
      for (let ky = -1; ky <= 1; ky++) {
        for (let kx = -1; kx <= 1; kx++) {
          gx += sobelX[ky + 1][kx + 1] * grayscale[y + ky][x + kx];
          gy += sobelY[ky + 1][kx + 1] * grayscale[y + ky][x + kx];
        }
      }

      const magnitude = Math.sqrt(gx * gx + gy * gy);
      edges[y][x] = magnitude > threshold;
    }
  }

  return edges;
}

function findContours(edges: boolean[][], width: number, height: number): Point[][] {
  const visited: boolean[][] = [];
  for (let y = 0; y < height; y++) {
    visited[y] = [];
    for (let x = 0; x < width; x++) {
      visited[y][x] = false;
    }
  }

  const contours: Point[][] = [];

  for (let y = 1; y < height - 1; y++) {
    for (let x = 1; x < width - 1; x++) {
      if (edges[y][x] && !visited[y][x]) {
        const contour = traceContour(edges, visited, x, y, width, height);
        if (contour.length > 10) {
          contours.push(contour);
        }
      }
    }
  }

  return contours;
}

function traceContour(
  edges: boolean[][],
  visited: boolean[][],
  startX: number,
  startY: number,
  width: number,
  height: number
): Point[] {
  const contour: Point[] = [];
  const directions = [
    [0, -1], [1, -1], [1, 0], [1, 1],
    [0, 1], [-1, 1], [-1, 0], [-1, -1]
  ];

  let x = startX;
  let y = startY;
  let dir = 0;
  let maxIterations = 2000;

  while (maxIterations-- > 0) {
    if (x < 0 || x >= width || y < 0 || y >= height) break;
    if (visited[y][x] && contour.length > 10) {
      if (Math.abs(x - startX) < 3 && Math.abs(y - startY) < 3) {
        break;
      }
    }

    visited[y][x] = true;
    contour.push({ x, y });

    let found = false;
    for (let i = 0; i < 8; i++) {
      const checkDir = (dir + i) % 8;
      const nx = x + directions[checkDir][0];
      const ny = y + directions[checkDir][1];

      if (nx >= 0 && nx < width && ny >= 0 && ny < height && edges[ny][nx]) {
        x = nx;
        y = ny;
        dir = (checkDir + 5) % 8;
        found = true;
        break;
      }
    }

    if (!found) break;
  }

  return contour;
}

function calculateCircularity(area: number, perimeter: number): number {
  if (perimeter === 0) return 0;
  return (4 * Math.PI * area) / (perimeter * perimeter);
}

function calculateRectangularity(points: Point[], area: number): number {
  const bbox = boundingBox(points);
  const bboxArea = bbox.width * bbox.height;
  return bboxArea > 0 ? area / bboxArea : 0;
}

function lineAngle(p1: Point, p2: Point): number {
  return Math.atan2(p2.y - p1.y, p2.x - p1.x);
}

function angleDiff(a: number, b: number): number {
  let d = ((b - a) % (2 * Math.PI) + 3 * Math.PI) % (2 * Math.PI) - Math.PI;
  return Math.abs(d);
}

function snapAngle(angle: number, tolerance: number = Math.PI / 18): number {
  const snapAngles = [0, Math.PI / 2, Math.PI, -Math.PI / 2, -Math.PI];
  for (const sa of snapAngles) {
    if (angleDiff(angle, sa) < tolerance) return sa;
  }
  const octant = Math.round(angle / (Math.PI / 4)) * (Math.PI / 4);
  if (angleDiff(angle, octant) < tolerance) return octant;
  return angle;
}

function correctRectangle(points: Point[]): Point[] {
  if (points.length !== 4) return points;

  const center = polygonCenter(points);
  const angles = points.map((p, i) => {
    const next = points[(i + 1) % 4];
    return lineAngle(p, next);
  });

  const mainAngle = snapAngle(angles[0]);
  const cos = Math.cos(mainAngle);
  const sin = Math.sin(mainAngle);

  const rotated = points.map(p => ({
    x: (p.x - center.x) * cos + (p.y - center.y) * sin,
    y: -(p.x - center.x) * sin + (p.y - center.y) * cos,
  }));

  const xs = rotated.map(p => p.x);
  const ys = rotated.map(p => p.y);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);

  const correctedRotated = [
    { x: minX, y: minY },
    { x: maxX, y: minY },
    { x: maxX, y: maxY },
    { x: minX, y: maxY },
  ];

  const cosInv = Math.cos(-mainAngle);
  const sinInv = Math.sin(-mainAngle);

  return correctedRotated.map(p => ({
    x: p.x * cosInv - p.y * sinInv + center.x,
    y: p.x * sinInv + p.y * cosInv + center.y,
  }));
}

function correctTriangle(points: Point[]): Point[] {
  if (points.length !== 3) return points;

  for (let i = 0; i < 3; i++) {
    const p1 = points[i];
    const p2 = points[(i + 1) % 3];
    const p3 = points[(i + 2) % 3];

    const edgeAngle = lineAngle(p1, p2);
    const snappedAngle = snapAngle(edgeAngle, Math.PI / 12);

    if (angleDiff(edgeAngle, snappedAngle) < Math.PI / 12) {
      const edgeLen = distance(p1, p2);
      const cosA = Math.cos(snappedAngle);
      const sinA = Math.sin(snappedAngle);
      const newP2 = {
        x: p1.x + edgeLen * cosA,
        y: p1.y + edgeLen * sinA,
      };

      const perpAngle = snappedAngle + Math.PI / 2;
      const dx = p3.x - p2.x;
      const dy = p3.y - p2.y;
      const projPerp = dx * Math.cos(perpAngle) + dy * Math.sin(perpAngle);

      const newP3 = {
        x: newP2.x + projPerp * Math.cos(perpAngle),
        y: newP2.y + projPerp * Math.sin(perpAngle),
      };

      return [p1, newP2, newP3];
    }
  }

  return points;
}

function correctCircle(points: Point[]): Point[] {
  const center = polygonCenter(points);
  let radiusSum = 0;
  let radiusSqSum = 0;
  const n = points.length;

  for (const p of points) {
    const r = distance(p, center);
    radiusSum += r;
    radiusSqSum += r * r;
  }

  const meanRadius = radiusSum / n;
  const variance = radiusSqSum / n - meanRadius * meanRadius;
  const stdDev = Math.sqrt(Math.max(0, variance));

  if (stdDev / meanRadius < 0.15) {
    const radius = meanRadius;
    const circlePoints: Point[] = [];
    const segments = 64;
    for (let i = 0; i < segments; i++) {
      const angle = (2 * Math.PI * i) / segments;
      circlePoints.push({
        x: center.x + radius * Math.cos(angle),
        y: center.y + radius * Math.sin(angle),
      });
    }
    return circlePoints;
  }

  return points;
}

function correctPolygon(points: Point[]): Point[] {
  if (points.length < 3) return points;

  const n = points.length;
  const corrected = [...points];

  for (let i = 0; i < n; i++) {
    const prev = points[(i - 1 + n) % n];
    const curr = points[i];
    const next = points[(i + 1) % n];

    const angle1 = lineAngle(prev, curr);
    const angle2 = lineAngle(curr, next);

    const interiorAngle = angleDiff(angle1 + Math.PI, angle2);
    const isNearStraight = Math.abs(interiorAngle - Math.PI) < Math.PI / 18;

    if (isNearStraight) {
      const edge1Angle = lineAngle(prev, next);
      const snappedAngle = snapAngle(edge1Angle, Math.PI / 18);

      if (angleDiff(edge1Angle, snappedAngle) < Math.PI / 18) {
        const t = ((curr.x - prev.x) * Math.cos(snappedAngle) + (curr.y - prev.y) * Math.sin(snappedAngle))
          / (Math.cos(snappedAngle) ** 2 + Math.sin(snappedAngle) ** 2);

        corrected[i] = {
          x: prev.x + t * Math.cos(snappedAngle),
          y: prev.y + t * Math.sin(snappedAngle),
        };
      }
    }
  }

  return corrected;
}

function correctShape(shape: Shape): Shape {
  if (shape.corrected) return shape;

  let correctedPoints: Point[];
  let radius = shape.radius;

  switch (shape.type) {
    case 'rectangle':
      correctedPoints = correctRectangle(shape.points);
      break;
    case 'triangle':
      correctedPoints = correctTriangle(shape.points);
      break;
    case 'circle':
      correctedPoints = correctCircle(shape.points);
      if (correctedPoints.length !== shape.points.length) {
        const center = polygonCenter(correctedPoints);
        radius = distance(center, correctedPoints[0]);
      }
      break;
    case 'polygon':
      correctedPoints = correctPolygon(shape.points);
      break;
    default:
      correctedPoints = shape.points;
  }

  const area = polygonArea(correctedPoints);
  const perimeter = polygonPerimeter(correctedPoints);
  const center = polygonCenter(correctedPoints);
  const bbox = boundingBox(correctedPoints);

  return {
    ...shape,
    points: correctedPoints,
    area,
    perimeter,
    center,
    boundingBox: bbox,
    radius,
    corrected: true,
  };
}

function fitCircle(points: Point[]): { center: Point; radius: number; points: Point[] } {
  const center = polygonCenter(points);
  let radiusSum = 0;
  for (const p of points) {
    radiusSum += distance(p, center);
  }
  const radius = radiusSum / points.length;

  const circlePoints: Point[] = [];
  const segments = 64;
  for (let i = 0; i < segments; i++) {
    const angle = (2 * Math.PI * i) / segments;
    circlePoints.push({
      x: center.x + radius * Math.cos(angle),
      y: center.y + radius * Math.sin(angle),
    });
  }

  return { center, radius, points: circlePoints };
}

function fitRectangle(points: Point[]): { points: Point[]; rotation: number } {
  const bbox = boundingBox(points);
  const center = {
    x: bbox.x + bbox.width / 2,
    y: bbox.y + bbox.height / 2,
  };

  let bestArea = Infinity;
  let bestRotation = 0;
  let bestCorners: Point[] = [];

  for (let angle = 0; angle < Math.PI; angle += Math.PI / 72) {
    const cos = Math.cos(angle);
    const sin = Math.sin(angle);

    let minX = Infinity, maxX = -Infinity;
    let minY = Infinity, maxY = -Infinity;

    for (const p of points) {
      const dx = p.x - center.x;
      const dy = p.y - center.y;
      const rx = dx * cos + dy * sin;
      const ry = -dx * sin + dy * cos;
      minX = Math.min(minX, rx);
      maxX = Math.max(maxX, rx);
      minY = Math.min(minY, ry);
      maxY = Math.max(maxY, ry);
    }

    const area = (maxX - minX) * (maxY - minY);
    if (area < bestArea) {
      bestArea = area;
      bestRotation = angle;

      const corners = [
        { x: center.x + minX * cos - minY * sin, y: center.y + minX * sin + minY * cos },
        { x: center.x + maxX * cos - minY * sin, y: center.y + maxX * sin + minY * cos },
        { x: center.x + maxX * cos - maxY * sin, y: center.y + maxX * sin + maxY * cos },
        { x: center.x + minX * cos - maxY * sin, y: center.y + minX * sin + maxY * cos },
      ];
      bestCorners = corners;
    }
  }

  return { points: bestCorners, rotation: bestRotation };
}

function fitTriangle(points: Point[]): Point[] {
  if (points.length < 3) return points;

  const center = polygonCenter(points);

  const sortedPoints = [...points].sort((a, b) => {
    const angleA = Math.atan2(a.y - center.y, a.x - center.x);
    const angleB = Math.atan2(b.y - center.y, b.x - center.x);
    return angleA - angleB;
  });

  let maxArea = 0;
  let bestTriangle: Point[] = [sortedPoints[0], sortedPoints[Math.floor(sortedPoints.length / 3)], sortedPoints[Math.floor(2 * sortedPoints.length / 3)]];

  for (let i = 0; i < sortedPoints.length; i += Math.max(1, Math.floor(sortedPoints.length / 20))) {
    for (let j = i + 1; j < sortedPoints.length; j += Math.max(1, Math.floor(sortedPoints.length / 20))) {
      for (let k = j + 1; k < sortedPoints.length; k += Math.max(1, Math.floor(sortedPoints.length / 20))) {
        const tri = [sortedPoints[i], sortedPoints[j], sortedPoints[k]];
        const area = polygonArea(tri);
        if (area > maxArea) {
          maxArea = area;
          bestTriangle = tri;
        }
      }
    }
  }

  return bestTriangle;
}

function classifyShape(approxPoints: Point[], contour: Point[]): { type: ShapeType; confidence: number } {
  const n = approxPoints.length;
  const area = polygonArea(contour);
  const perimeter = polygonPerimeter(contour);

  const circularity = calculateCircularity(area, perimeter);
  const rectangularity = calculateRectangularity(contour, area);

  if (circularity > 0.85 && n >= 8) {
    return { type: 'circle', confidence: circularity };
  }

  if (n === 4 && rectangularity > 0.75) {
    return { type: 'rectangle', confidence: rectangularity };
  }

  if (n === 3) {
    return { type: 'triangle', confidence: 0.75 };
  }

  if (n >= 5 && n <= 12) {
    return { type: 'polygon', confidence: 0.6 };
  }

  return { type: 'polygon', confidence: 0.4 };
}

function fitShape(contour: Point[], type: ShapeType): Shape {
  let points: Point[];
  let rotation: number | undefined;
  let radius: number | undefined;

  switch (type) {
    case 'circle': {
      const fit = fitCircle(contour);
      points = fit.points;
      radius = fit.radius;
      break;
    }
    case 'rectangle': {
      const fit = fitRectangle(contour);
      points = fit.points;
      rotation = fit.rotation;
      break;
    }
    case 'triangle':
      points = fitTriangle(contour);
      break;
    case 'polygon':
    default:
      points = contour;
      break;
  }

  const area = polygonArea(type === 'circle' ? contour : points);
  const perimeter = polygonPerimeter(type === 'circle' ? contour : points);
  const center = polygonCenter(points);
  const bbox = boundingBox(points);

  return {
    id: generateId(),
    type,
    points,
    boundingBox: bbox,
    area,
    perimeter,
    center,
    rotation,
    radius,
    confidence: 0.85,
    color: SHAPE_COLORS[type],
  };
}

export function recognizeShapes(
  imageData: ImageData,
  width: number,
  height: number,
  options: { minContourArea?: number; epsilonFactor?: number; enableCorrection?: boolean } = {}
): Shape[] {
  const { minContourArea = 200, epsilonFactor = 0.02, enableCorrection = true } = options;

  const startTime = Date.now();

  const edges = detectEdges(imageData, width, height);
  const contours = findContours(edges, width, height);

  const shapes: Shape[] = [];

  for (const contour of contours) {
    const area = polygonArea(contour);
    if (area < minContourArea) continue;

    const perimeter = polygonPerimeter(contour);
    const epsilon = epsilonFactor * perimeter;
    const approxPoints = ramerDouglasPeucker(contour, epsilon, true);

    if (approxPoints.length < 3) continue;

    const { type, confidence } = classifyShape(approxPoints, contour);
    let shape = fitShape(contour, type);
    shape.confidence = confidence;

    if (enableCorrection) {
      shape = correctShape(shape);
    }

    shapes.push(shape);
  }

  console.log(`识别完成，耗时 ${Date.now() - startTime}ms，找到 ${shapes.length} 个形状`);

  return shapes;
}

export function calculateShapeProperties(shape: Shape): { area: number; perimeter: number; center: Point } {
  return {
    area: polygonArea(shape.points),
    perimeter: polygonPerimeter(shape.points),
    center: polygonCenter(shape.points),
  };
}

function distance3D(p1: Point3D, p2: Point3D): number {
  return Math.sqrt((p2.x - p1.x) ** 2 + (p2.y - p1.y) ** 2 + (p2.z - p1.z) ** 2);
}

function detectParallelogram(points: Point[]): { isParallelogram: boolean; shearAngle: number; aspectRatio: number } {
  if (points.length !== 4) return { isParallelogram: false, shearAngle: 0, aspectRatio: 1 };

  const angles = [
    lineAngle(points[0], points[1]),
    lineAngle(points[1], points[2]),
    lineAngle(points[2], points[3]),
    lineAngle(points[3], points[0]),
  ];

  const oppositeAnglesEqual =
    Math.abs(((angles[2] - angles[0]) % (Math.PI * 2) + Math.PI * 3) % (Math.PI * 2) - Math.PI) < Math.PI / 12 &&
    Math.abs(((angles[3] - angles[1]) % (Math.PI * 2) + Math.PI * 3) % (Math.PI * 2) - Math.PI) < Math.PI / 12;

  const adjacentAnglesNotRight =
    Math.abs(Math.abs(((angles[1] - angles[0]) % (Math.PI * 2) + Math.PI * 3) % (Math.PI * 2) - Math.PI) - Math.PI / 2) > Math.PI / 12;

  const len0 = distance(points[0], points[1]);
  const len1 = distance(points[1], points[2]);

  return {
    isParallelogram: oppositeAnglesEqual && adjacentAnglesNotRight,
    shearAngle: Math.abs(((angles[0] % (Math.PI * 2)) + Math.PI * 2) % (Math.PI * 2) - Math.PI / 2),
    aspectRatio: Math.max(len0, len1) / Math.min(len0, len1),
  };
}

function detectIsometricCircle(shape: Shape): { isIsometric: boolean; aspectRatio: number } {
  if (shape.type !== 'circle' && shape.type !== 'polygon') return { isIsometric: false, aspectRatio: 1 };

  const bbox = shape.boundingBox;
  const aspectRatio = bbox.width / bbox.height;

  const isIsometricEllipse =
    aspectRatio > 1.15 && aspectRatio < 2.0 &&
    shape.area < (Math.PI * bbox.width * bbox.height) / 4 * 0.9;

  return {
    isIsometric: isIsometricEllipse,
    aspectRatio,
  };
}

function createCubeVertices(center: Point3D, size: { width: number; height: number; depth: number }, rotation: Point3D): Point3D[] {
  const hw = size.width / 2;
  const hh = size.height / 2;
  const hd = size.depth / 2;

  const baseVertices: Point3D[] = [
    { x: -hw, y: -hh, z: -hd },
    { x: hw, y: -hh, z: -hd },
    { x: hw, y: -hh, z: hd },
    { x: -hw, y: -hh, z: hd },
    { x: -hw, y: hh, z: -hd },
    { x: hw, y: hh, z: -hd },
    { x: hw, y: hh, z: hd },
    { x: -hw, y: hh, z: hd },
  ];

  const cosX = Math.cos(rotation.x);
  const sinX = Math.sin(rotation.x);
  const cosY = Math.cos(rotation.y);
  const sinY = Math.sin(rotation.y);
  const cosZ = Math.cos(rotation.z);
  const sinZ = Math.sin(rotation.z);

  return baseVertices.map(v => {
    let x = v.x * cosY - v.z * sinY;
    let z = v.x * sinY + v.z * cosY;
    let y = v.y;

    const y1 = y * cosX - z * sinX;
    z = y * sinX + z * cosX;
    y = y1;

    const x1 = x * cosZ - y * sinZ;
    y = x * sinZ + y * cosZ;
    x = x1;

    return {
      x: x + center.x,
      y: y + center.y,
      z: z + center.z,
    };
  });
}

function createCubeFaces(vertices: Point3D[]): { points: Point[]; depth: number }[] {
  const faces = [
    [0, 1, 2, 3],
    [4, 7, 6, 5],
    [0, 4, 5, 1],
    [2, 6, 7, 3],
    [0, 3, 7, 4],
    [1, 5, 6, 2],
  ];

  return faces.map(face => ({
    points: face.map(i => ({ x: vertices[i].x, y: vertices[i].y })),
    depth: vertices[face[0]].z,
  }));
}

function inferCubeFromRectangle(shape: Shape): Shape3D | null {
  if (shape.type !== 'rectangle') return null;

  const { isParallelogram, shearAngle, aspectRatio } = detectParallelogram(shape.points);

  const bbox = shape.boundingBox;
  const center = shape.center;
  const area = shape.area;

  let width: number, height: number, depth: number;
  let rotationY: number;

  if (isParallelogram) {
    rotationY = Math.min(Math.abs(shearAngle), Math.PI / 3);
    const projectedArea = area;
    const actualArea = projectedArea / Math.cos(rotationY);

    const avgSide = Math.sqrt(actualArea);
    width = avgSide * (aspectRatio > 1 ? aspectRatio : 1);
    height = avgSide / (aspectRatio > 1 ? 1 : aspectRatio);
    depth = avgSide * 0.8;
  } else {
    width = bbox.width;
    height = bbox.height;
    depth = Math.min(width, height) * 0.6;
    rotationY = Math.PI / 6;
  }

  const center3D: Point3D = { x: center.x, y: center.y, z: 0 };
  const rotation: Point3D = { x: -Math.PI / 6, y: rotationY, z: 0 };

  const size = { width, height, depth };
  const vertices = createCubeVertices(center3D, size, rotation);
  const faces = createCubeFaces(vertices);

  return {
    id: generateId(),
    type: 'cube',
    sourceShapeId: shape.id,
    center: center3D,
    size,
    rotation,
    vertices,
    faces,
    confidence: isParallelogram ? 0.85 : 0.65,
    color: SHAPE3D_COLORS.cube,
    volume: width * height * depth,
    surfaceArea: 2 * (width * height + width * depth + height * depth),
  };
}

function inferSphereFromCircle(shape: Shape): Shape3D | null {
  if (shape.type !== 'circle' && shape.points.length < 8) return null;

  const { isIsometric } = detectIsometricCircle(shape);

  const center = shape.center;
  const bbox = shape.boundingBox;
  const avgRadius = shape.radius || (bbox.width + bbox.height) / 4;

  const actualRadius = isIsometric
    ? Math.max(bbox.width, bbox.height) / 2
    : avgRadius;

  const center3D: Point3D = { x: center.x, y: center.y, z: 0 };
  const rotation: Point3D = { x: -Math.PI / 6, y: Math.PI / 6, z: 0 };

  const size = { width: actualRadius * 2, height: actualRadius * 2, depth: actualRadius * 2 };

  const sphereVertices: Point3D[] = [];
  const latSegments = 16;
  const longSegments = 32;

  for (let lat = 0; lat <= latSegments; lat++) {
    const theta = (lat * Math.PI) / latSegments;
    const sinTheta = Math.sin(theta);
    const cosTheta = Math.cos(theta);

    for (let lon = 0; lon <= longSegments; lon++) {
      const phi = (lon * 2 * Math.PI) / longSegments;
      const sinPhi = Math.sin(phi);
      const cosPhi = Math.cos(phi);

      sphereVertices.push({
        x: center3D.x + actualRadius * sinTheta * cosPhi,
        y: center3D.y + actualRadius * cosTheta,
        z: center3D.z + actualRadius * sinTheta * sinPhi,
      });
    }
  }

  const sphereFaces: { points: Point[]; depth: number }[] = [];
  for (let lon = 0; lon < longSegments; lon++) {
    const circle: Point[] = [];
    for (let lat = 0; lat <= latSegments; lat++) {
      const idx = lat * (longSegments + 1) + lon;
      circle.push({ x: sphereVertices[idx].x, y: sphereVertices[idx].y });
    }
    sphereFaces.push({ points: circle, depth: 0 });
  }

  return {
    id: generateId(),
    type: 'sphere',
    sourceShapeId: shape.id,
    center: center3D,
    size,
    rotation,
    vertices: sphereVertices.slice(0, 64),
    faces: sphereFaces,
    confidence: isIsometric ? 0.8 : 0.55,
    color: SHAPE3D_COLORS.sphere,
    volume: (4 / 3) * Math.PI * actualRadius ** 3,
    surfaceArea: 4 * Math.PI * actualRadius ** 2,
  };
}

function inferCylinderFromEllipse(shape: Shape): Shape3D | null {
  const { isIsometric } = detectIsometricCircle(shape);

  if (!isIsometric && shape.type !== 'circle' && shape.type !== 'polygon') return null;
  if (shape.points.length < 8) return null;

  const bbox = shape.boundingBox;
  const center = shape.center;

  const radius = Math.max(bbox.width, bbox.height) / 2;
  const height = radius * 1.5;

  const center3D: Point3D = { x: center.x, y: center.y, z: 0 };
  const rotation: Point3D = { x: -Math.PI / 4, y: Math.PI / 6, z: 0 };

  const size = { width: radius * 2, height, depth: radius * 2 };

  const cylinderVertices: Point3D[] = [];
  const segments = 32;

  for (let i = 0; i <= segments; i++) {
    const angle = (i * 2 * Math.PI) / segments;
    cylinderVertices.push({
      x: center3D.x + radius * Math.cos(angle),
      y: center3D.y - height / 2,
      z: center3D.z + radius * Math.sin(angle),
    });
  }
  for (let i = 0; i <= segments; i++) {
    const angle = (i * 2 * Math.PI) / segments;
    cylinderVertices.push({
      x: center3D.x + radius * Math.cos(angle),
      y: center3D.y + height / 2,
      z: center3D.z + radius * Math.sin(angle),
    });
  }

  const cylinderFaces: { points: Point[]; depth: number }[] = [];

  const bottomFace: Point[] = [];
  const topFace: Point[] = [];
  for (let i = 0; i <= segments; i++) {
    bottomFace.push({ x: cylinderVertices[i].x, y: cylinderVertices[i].y });
    topFace.push({ x: cylinderVertices[i + segments + 1].x, y: cylinderVertices[i + segments + 1].y });
  }
  cylinderFaces.push({ points: bottomFace, depth: -height / 2 });
  cylinderFaces.push({ points: topFace, depth: height / 2 });

  for (let i = 0; i < segments; i++) {
    const sideFace: Point[] = [
      { x: cylinderVertices[i].x, y: cylinderVertices[i].y },
      { x: cylinderVertices[i + 1].x, y: cylinderVertices[i + 1].y },
      { x: cylinderVertices[i + segments + 2].x, y: cylinderVertices[i + segments + 2].y },
      { x: cylinderVertices[i + segments + 1].x, y: cylinderVertices[i + segments + 1].y },
    ];
    cylinderFaces.push({ points: sideFace, depth: 0 });
  }

  return {
    id: generateId(),
    type: 'cylinder',
    sourceShapeId: shape.id,
    center: center3D,
    size,
    rotation,
    vertices: cylinderVertices,
    faces: cylinderFaces,
    confidence: isIsometric ? 0.75 : 0.5,
    color: SHAPE3D_COLORS.cylinder,
    volume: Math.PI * radius * radius * height,
    surfaceArea: 2 * Math.PI * radius * (radius + height),
  };
}

function inferConeFromTriangle(shape: Shape): Shape3D | null {
  if (shape.type !== 'triangle') return null;

  const bbox = shape.boundingBox;
  const center = shape.center;

  const baseWidth = bbox.width;
  const height = bbox.height;
  const radius = baseWidth / 2;

  const center3D: Point3D = { x: center.x, y: center.y, z: 0 };
  const rotation: Point3D = { x: -Math.PI / 6, y: 0, z: 0 };

  const size = { width: baseWidth, height, depth: baseWidth };

  const coneVertices: Point3D[] = [];
  const segments = 32;

  for (let i = 0; i <= segments; i++) {
    const angle = (i * 2 * Math.PI) / segments;
    coneVertices.push({
      x: center3D.x + radius * Math.cos(angle),
      y: center3D.y + height / 2,
      z: center3D.z + radius * Math.sin(angle),
    });
  }
  coneVertices.push({ x: center3D.x, y: center3D.y - height / 2, z: center3D.z });

  const coneFaces: { points: Point[]; depth: number }[] = [];

  const baseFace: Point[] = [];
  for (let i = 0; i <= segments; i++) {
    baseFace.push({ x: coneVertices[i].x, y: coneVertices[i].y });
  }
  coneFaces.push({ points: baseFace, depth: height / 2 });

  const apex = { x: coneVertices[segments + 1].x, y: coneVertices[segments + 1].y };
  for (let i = 0; i < segments; i++) {
    coneFaces.push({
      points: [
        { x: coneVertices[i].x, y: coneVertices[i].y },
        { x: coneVertices[i + 1].x, y: coneVertices[i + 1].y },
        apex,
      ],
      depth: 0,
    });
  }

  return {
    id: generateId(),
    type: 'cone',
    sourceShapeId: shape.id,
    center: center3D,
    size,
    rotation,
    vertices: coneVertices,
    faces: coneFaces,
    confidence: 0.7,
    color: SHAPE3D_COLORS.cone,
    volume: (1 / 3) * Math.PI * radius * radius * height,
    surfaceArea: Math.PI * radius * (radius + Math.sqrt(radius * radius + height * height)),
  };
}

function inferPyramidFromPolygon(shape: Shape): Shape3D | null {
  if (shape.type !== 'polygon' || shape.points.length < 5 || shape.points.length > 8) return null;

  const bbox = shape.boundingBox;
  const center = shape.center;
  const basePoints = shape.points;

  const height = Math.max(bbox.width, bbox.height) * 0.8;

  const center3D: Point3D = { x: center.x, y: center.y, z: 0 };
  const rotation: Point3D = { x: -Math.PI / 6, y: 0, z: 0 };

  const size = { width: bbox.width, height, depth: bbox.height };

  const pyramidVertices: Point3D[] = [
    ...basePoints.map(p => ({ x: p.x, y: p.y, z: height / 2 })),
    { x: center.x, y: center.y - height, z: 0 },
  ];

  const pyramidFaces: { points: Point[]; depth: number }[] = [];

  pyramidFaces.push({
    points: basePoints,
    depth: height / 2,
  });

  const apex = { x: center.x, y: center.y - height };
  const n = basePoints.length;
  for (let i = 0; i < n; i++) {
    pyramidFaces.push({
      points: [
        { x: basePoints[i].x, y: basePoints[i].y },
        { x: basePoints[(i + 1) % n].x, y: basePoints[(i + 1) % n].y },
        apex,
      ],
      depth: 0,
    });
  }

  const baseArea = polygonArea(basePoints);

  return {
    id: generateId(),
    type: 'pyramid',
    sourceShapeId: shape.id,
    center: center3D,
    size,
    rotation,
    vertices: pyramidVertices,
    faces: pyramidFaces,
    confidence: 0.65,
    color: SHAPE3D_COLORS.pyramid,
    volume: (1 / 3) * baseArea * height,
    surfaceArea: baseArea * 2,
  };
}

function inferPrismFromPolygon(shape: Shape): Shape3D | null {
  if (shape.type !== 'polygon' || shape.points.length < 3 || shape.points.length > 8) return null;

  const bbox = shape.boundingBox;
  const center = shape.center;
  const basePoints = shape.points;

  const depth = Math.min(bbox.width, bbox.height) * 0.6;

  const center3D: Point3D = { x: center.x, y: center.y, z: 0 };
  const rotation: Point3D = { x: -Math.PI / 6, y: Math.PI / 8, z: 0 };

  const size = { width: bbox.width, height: bbox.height, depth };

  const cosY = Math.cos(rotation.y);
  const sinY = Math.sin(rotation.y);
  const offset = { x: depth * sinY * 0.5, y: -depth * cosY * 0.3 };

  const topPoints = basePoints.map(p => ({
    x: p.x + offset.x,
    y: p.y + offset.y,
  }));

  const prismVertices: Point3D[] = [
    ...basePoints.map(p => ({ x: p.x, y: p.y, z: -depth / 2 })),
    ...topPoints.map(p => ({ x: p.x, y: p.y, z: depth / 2 })),
  ];

  const prismFaces: { points: Point[]; depth: number }[] = [];
  prismFaces.push({ points: basePoints, depth: -depth / 2 });
  prismFaces.push({ points: topPoints, depth: depth / 2 });

  const n = basePoints.length;
  for (let i = 0; i < n; i++) {
    prismFaces.push({
      points: [
        { x: basePoints[i].x, y: basePoints[i].y },
        { x: basePoints[(i + 1) % n].x, y: basePoints[(i + 1) % n].y },
        { x: topPoints[(i + 1) % n].x, y: topPoints[(i + 1) % n].y },
        { x: topPoints[i].x, y: topPoints[i].y },
      ],
      depth: 0,
    });
  }

  const baseArea = polygonArea(basePoints);

  return {
    id: generateId(),
    type: 'prism',
    sourceShapeId: shape.id,
    center: center3D,
    size,
    rotation,
    vertices: prismVertices,
    faces: prismFaces,
    confidence: 0.6,
    color: SHAPE3D_COLORS.prism,
    volume: baseArea * depth,
    surfaceArea: 2 * baseArea + polygonPerimeter(basePoints) * depth,
  };
}

export function infer3DShape(shape: Shape): Shape3D | null {
  switch (shape.type) {
    case 'rectangle':
      return inferCubeFromRectangle(shape);
    case 'circle':
      const cylinder = inferCylinderFromEllipse(shape);
      if (cylinder && cylinder.confidence > 0.6) return cylinder;
      return inferSphereFromCircle(shape);
    case 'triangle':
      return inferConeFromTriangle(shape);
    case 'polygon':
      if (shape.points.length >= 5 && shape.points.length <= 6) {
        const pyramid = inferPyramidFromPolygon(shape);
        if (pyramid) return pyramid;
      }
      return inferPrismFromPolygon(shape);
    default:
      return null;
  }
}

export function infer3DShapes(shapes: Shape[]): Shape3D[] {
  const result: Shape3D[] = [];

  for (const shape of shapes) {
    const shape3d = infer3DShape(shape);
    if (shape3d) {
      result.push(shape3d);
    }
  }

  return result;
}

function pointInPolygon(point: Point, polygon: Point[]): boolean {
  let inside = false;
  const n = polygon.length;
  for (let i = 0, j = n - 1; i < n; j = i++) {
    const xi = polygon[i].x, yi = polygon[i].y;
    const xj = polygon[j].x, yj = polygon[j].y;

    if (((yi > point.y) !== (yj > point.y)) &&
        (point.x < (xj - xi) * (point.y - yi) / (yj - yi) + xi)) {
      inside = !inside;
    }
  }
  return inside;
}

function polygonIntersectsPolygon(poly1: Point[], poly2: Point[]): boolean {
  for (const p of poly1) {
    if (pointInPolygon(p, poly2)) return true;
  }
  for (const p of poly2) {
    if (pointInPolygon(p, poly1)) return true;
  }
  return false;
}

function segmentsIntersect(
  p1: Point, p2: Point, p3: Point, p4: Point
): boolean {
  const d1 = (p3.x - p1.x) * (p2.y - p1.y) - (p2.x - p1.x) * (p3.y - p1.y);
  const d2 = (p4.x - p1.x) * (p2.y - p1.y) - (p2.x - p1.x) * (p4.y - p1.y);
  const d3 = (p1.x - p3.x) * (p4.y - p3.y) - (p4.x - p3.x) * (p1.y - p3.y);
  const d4 = (p2.x - p3.x) * (p4.y - p3.y) - (p4.x - p3.x) * (p2.y - p3.y);

  if (((d1 > 0 && d2 < 0) || (d1 < 0 && d2 > 0)) &&
      ((d3 > 0 && d4 < 0) || (d3 < 0 && d4 > 0))) {
    return true;
  }

  if (d1 === 0 && Math.min(p1.x, p2.x) <= p3.x && p3.x <= Math.max(p1.x, p2.x) &&
      Math.min(p1.y, p2.y) <= p3.y && p3.y <= Math.max(p1.y, p2.y)) return true;
  if (d2 === 0 && Math.min(p1.x, p2.x) <= p4.x && p4.x <= Math.max(p1.x, p2.x) &&
      Math.min(p1.y, p2.y) <= p4.y && p4.y <= Math.max(p1.y, p2.y)) return true;
  if (d3 === 0 && Math.min(p3.x, p4.x) <= p1.x && p1.x <= Math.max(p3.x, p4.x) &&
      Math.min(p3.y, p4.y) <= p1.y && p1.y <= Math.max(p3.y, p4.y)) return true;
  if (d4 === 0 && Math.min(p3.x, p4.x) <= p2.x && p2.x <= Math.max(p3.x, p4.x) &&
      Math.min(p3.y, p4.y) <= p2.y && p2.y <= Math.max(p3.y, p4.y)) return true;

  return false;
}

function pointToSegmentDistance(point: Point, segStart: Point, segEnd: Point): {
  distance: number;
  nearestPoint: Point;
} {
  const dx = segEnd.x - segStart.x;
  const dy = segEnd.y - segStart.y;
  const lenSq = dx * dx + dy * dy;

  if (lenSq === 0) {
    return {
      distance: distance(point, segStart),
      nearestPoint: segStart,
    };
  }

  let t = ((point.x - segStart.x) * dx + (point.y - segStart.y) * dy) / lenSq;
  t = Math.max(0, Math.min(1, t));

  const nearestPoint = {
    x: segStart.x + t * dx,
    y: segStart.y + t * dy,
  };

  return {
    distance: distance(point, nearestPoint),
    nearestPoint,
  };
}

function distanceToPolygon(point: Point, polygon: Point[]): { minDist: number; nearestPoint: Point } {
  let minDist = Infinity;
  let nearestPoint: Point = polygon[0];

  const n = polygon.length;
  for (let i = 0; i < n; i++) {
    const p1 = polygon[i];
    const p2 = polygon[(i + 1) % n];

    const dist = pointToSegmentDistance(point, p1, p2);
    if (dist.distance < minDist) {
      minDist = dist.distance;
      nearestPoint = dist.nearestPoint;
    }
  }

  return { minDist, nearestPoint };
}

function polygonDistance(poly1: Point[], poly2: Point[]): { minDist: number; pointOnPoly1: Point; pointOnPoly2: Point } {
  let minDist = Infinity;
  let pointOnPoly1: Point = poly1[0];
  let pointOnPoly2: Point = poly2[0];

  for (const p of poly1) {
    const dist = distanceToPolygon(p, poly2);
    if (dist.minDist < minDist) {
      minDist = dist.minDist;
      pointOnPoly1 = p;
      pointOnPoly2 = dist.nearestPoint;
    }
  }

  for (const p of poly2) {
    const dist = distanceToPolygon(p, poly1);
    if (dist.minDist < minDist) {
      minDist = dist.minDist;
      pointOnPoly1 = dist.nearestPoint;
      pointOnPoly2 = p;
    }
  }

  return { minDist, pointOnPoly1, pointOnPoly2 };
}

function detectContains(shapeA: Shape, shapeB: Shape): ShapeRelation | null {
  if (shapeA.area < shapeB.area * 1.1) return null;

  const bboxA = shapeA.boundingBox;
  const bboxB = shapeB.boundingBox;

  if (bboxB.x < bboxA.x || bboxB.y < bboxA.y ||
      bboxB.x + bboxB.width > bboxA.x + bboxA.width ||
      bboxB.y + bboxB.height > bboxA.y + bboxA.height) {
    return null;
  }

  let allInside = true;
  for (const p of shapeB.points) {
    if (!pointInPolygon(p, shapeA.points)) {
      allInside = false;
      break;
    }
  }

  if (!allInside) return null;

  const distInfo = polygonDistance(shapeA.points, shapeB.points);
  const gapRatio = distInfo.minDist / Math.sqrt(shapeA.area);

  return {
    id: generateId(),
    type: 'contains',
    shapeAId: shapeA.id,
    shapeBId: shapeB.id,
    confidence: Math.min(0.95, 0.7 + gapRatio * 2),
    metadata: {
      gapDistance: distInfo.minDist,
      containmentRatio: shapeB.area / shapeA.area,
    },
  };
}

function detectTangent(shapeA: Shape, shapeB: Shape): ShapeRelation | null {
  if (polygonIntersectsPolygon(shapeA.points, shapeB.points)) return null;

  const distInfo = polygonDistance(shapeA.points, shapeB.points);
  const avgSize = (Math.sqrt(shapeA.area) + Math.sqrt(shapeB.area)) / 2;
  const distanceRatio = distInfo.minDist / avgSize;

  if (distanceRatio > 0.15) return null;

  return {
    id: generateId(),
    type: 'tangent',
    shapeAId: shapeA.id,
    shapeBId: shapeB.id,
    confidence: Math.max(0.5, 0.9 - distanceRatio * 3),
    metadata: {
      distance: distInfo.minDist,
    },
  };
}

function detectIntersects(shapeA: Shape, shapeB: Shape): ShapeRelation | null {
  if (!polygonIntersectsPolygon(shapeA.points, shapeB.points)) return null;

  const bboxA = shapeA.boundingBox;
  const bboxB = shapeB.boundingBox;
  const overlapArea = Math.max(0, Math.min(bboxA.x + bboxA.width, bboxB.x + bboxB.width) - Math.max(bboxA.x, bboxB.x)) *
                     Math.max(0, Math.min(bboxA.y + bboxA.height, bboxB.y + bboxB.height) - Math.max(bboxA.y, bboxB.y));

  const minArea = Math.min(shapeA.area, shapeB.area);
  const overlapRatio = overlapArea / minArea;

  if (overlapRatio < 0.05) return null;

  return {
    id: generateId(),
    type: 'intersects',
    shapeAId: shapeA.id,
    shapeBId: shapeB.id,
    confidence: Math.min(0.9, 0.5 + overlapRatio),
    metadata: {
      overlapBBoxArea: overlapArea,
      overlapRatio,
    },
  };
}

function detectSymmetryX(shapeA: Shape, shapeB: Shape, canvasWidth: number): ShapeRelation | null {
  const axisX = canvasWidth / 2;

  const centerA = shapeA.center;
  const centerB = shapeB.center;
  const mirroredCenterX = 2 * axisX - centerA.x;

  if (Math.abs(mirroredCenterX - centerB.x) > 30 || Math.abs(centerA.y - centerB.y) > 20) {
    return null;
  }

  const sizeA = Math.sqrt(shapeA.area);
  const sizeB = Math.sqrt(shapeB.area);
  const sizeRatio = Math.min(sizeA, sizeB) / Math.max(sizeA, sizeB);
  if (sizeRatio < 0.8) return null;

  if (shapeA.type !== shapeB.type && !(shapeA.type === 'polygon' && shapeB.type === 'polygon')) {
    return null;
  }

  return {
    id: generateId(),
    type: 'symmetric_x',
    shapeAId: shapeA.id,
    shapeBId: shapeB.id,
    confidence: 0.7 + sizeRatio * 0.2,
    metadata: {
      axis: axisX,
    },
  };
}

function detectSymmetryY(shapeA: Shape, shapeB: Shape, canvasHeight: number): ShapeRelation | null {
  const axisY = canvasHeight / 2;

  const centerA = shapeA.center;
  const centerB = shapeB.center;
  const mirroredCenterY = 2 * axisY - centerA.y;

  if (Math.abs(mirroredCenterY - centerB.y) > 30 || Math.abs(centerA.x - centerB.x) > 20) {
    return null;
  }

  const sizeA = Math.sqrt(shapeA.area);
  const sizeB = Math.sqrt(shapeB.area);
  const sizeRatio = Math.min(sizeA, sizeB) / Math.max(sizeA, sizeB);
  if (sizeRatio < 0.8) return null;

  if (shapeA.type !== shapeB.type && !(shapeA.type === 'polygon' && shapeB.type === 'polygon')) {
    return null;
  }

  return {
    id: generateId(),
    type: 'symmetric_y',
    shapeAId: shapeA.id,
    shapeBId: shapeB.id,
    confidence: 0.7 + sizeRatio * 0.2,
    metadata: {
      axis: axisY,
    },
  };
}

function detectSymmetryOrigin(shapeA: Shape, shapeB: Shape, canvasCenter: Point): ShapeRelation | null {
  const centerA = shapeA.center;
  const centerB = shapeB.center;

  const mirroredCenter = {
    x: 2 * canvasCenter.x - centerA.x,
    y: 2 * canvasCenter.y - centerA.y,
  };

  const dist = Math.sqrt((mirroredCenter.x - centerB.x) ** 2 + (mirroredCenter.y - centerB.y) ** 2);
  if (dist > 40) return null;

  const sizeA = Math.sqrt(shapeA.area);
  const sizeB = Math.sqrt(shapeB.area);
  const sizeRatio = Math.min(sizeA, sizeB) / Math.max(sizeA, sizeB);
  if (sizeRatio < 0.8) return null;

  if (shapeA.type !== shapeB.type && !(shapeA.type === 'polygon' && shapeB.type === 'polygon')) {
    return null;
  }

  return {
    id: generateId(),
    type: 'symmetric_origin',
    shapeAId: shapeA.id,
    shapeBId: shapeB.id,
    confidence: 0.65 + sizeRatio * 0.2,
    metadata: {},
  };
}

function detectAlignedHorizontal(shapeA: Shape, shapeB: Shape): ShapeRelation | null {
  const centerA = shapeA.center;
  const centerB = shapeB.center;

  const dy = Math.abs(centerA.y - centerB.y);
  const avgSize = (Math.sqrt(shapeA.area) + Math.sqrt(shapeB.area)) / 2;

  if (dy > avgSize * 0.4) return null;

  return {
    id: generateId(),
    type: 'aligned_horizontal',
    shapeAId: shapeA.id,
    shapeBId: shapeB.id,
    confidence: Math.max(0.6, 0.9 - dy / avgSize),
    metadata: {},
  };
}

function detectAlignedVertical(shapeA: Shape, shapeB: Shape): ShapeRelation | null {
  const centerA = shapeA.center;
  const centerB = shapeB.center;

  const dx = Math.abs(centerA.x - centerB.x);
  const avgSize = (Math.sqrt(shapeA.area) + Math.sqrt(shapeB.area)) / 2;

  if (dx > avgSize * 0.4) return null;

  return {
    id: generateId(),
    type: 'aligned_vertical',
    shapeAId: shapeA.id,
    shapeBId: shapeB.id,
    confidence: Math.max(0.6, 0.9 - dx / avgSize),
    metadata: {},
  };
}

function detectParallel(shapeA: Shape, shapeB: Shape): ShapeRelation | null {
  if (shapeA.points.length < 4 || shapeB.points.length < 4) return null;

  let minAngleDiff = Infinity;

  for (let i = 0; i < shapeA.points.length; i++) {
    const p1 = shapeA.points[i];
    const p2 = shapeA.points[(i + 1) % shapeA.points.length];
    const angleA = Math.atan2(p2.y - p1.y, p2.x - p1.x);

    for (let j = 0; j < shapeB.points.length; j++) {
      const p3 = shapeB.points[j];
      const p4 = shapeB.points[(j + 1) % shapeB.points.length];
      const angleB = Math.atan2(p4.y - p3.y, p4.x - p3.x);

      let diff = Math.abs(angleA - angleB);
      diff = Math.min(diff, Math.abs(diff - Math.PI), Math.abs(diff + Math.PI));
      diff = Math.min(diff, Math.abs(diff - Math.PI * 2), Math.abs(diff + Math.PI * 2));

      if (diff < minAngleDiff) {
        minAngleDiff = diff;
      }
    }
  }

  if (minAngleDiff > Math.PI / 18) return null;

  return {
    id: generateId(),
    type: 'parallel',
    shapeAId: shapeA.id,
    shapeBId: shapeB.id,
    confidence: Math.max(0.6, 0.9 - minAngleDiff * 3),
    metadata: {},
  };
}

function detectPerpendicular(shapeA: Shape, shapeB: Shape): ShapeRelation | null {
  if (shapeA.points.length < 4 || shapeB.points.length < 4) return null;

  let minAngleDiff = Infinity;

  for (let i = 0; i < shapeA.points.length; i++) {
    const p1 = shapeA.points[i];
    const p2 = shapeA.points[(i + 1) % shapeA.points.length];
    const angleA = Math.atan2(p2.y - p1.y, p2.x - p1.x);

    for (let j = 0; j < shapeB.points.length; j++) {
      const p3 = shapeB.points[j];
      const p4 = shapeB.points[(j + 1) % shapeB.points.length];
      const angleB = Math.atan2(p4.y - p3.y, p4.x - p3.x);

      let diff = Math.abs(angleA - angleB + Math.PI / 2);
      diff = Math.min(diff, Math.abs(diff - Math.PI), Math.abs(diff + Math.PI));
      diff = Math.min(diff, Math.abs(diff - Math.PI * 2), Math.abs(diff + Math.PI * 2));

      if (diff < minAngleDiff) {
        minAngleDiff = diff;
      }
    }
  }

  if (minAngleDiff > Math.PI / 12) return null;

  return {
    id: generateId(),
    type: 'perpendicular',
    shapeAId: shapeA.id,
    shapeBId: shapeB.id,
    confidence: Math.max(0.6, 0.9 - minAngleDiff * 2),
    metadata: {},
  };
}

function detectRepeat(shapes: Shape[]): ShapeRelation[] {
  const relations: ShapeRelation[] = [];
  if (shapes.length < 3) return relations;

  const byType: Record<string, Shape[]> = {};
  for (const s of shapes) {
    if (!byType[s.type]) byType[s.type] = [];
    byType[s.type].push(s);
  }

  for (const type in byType) {
    const group = byType[type];
    if (group.length < 3) continue;

    const areas = group.map(s => s.area);
    const avgArea = areas.reduce((a, b) => a + b, 0) / areas.length;
    const variance = areas.reduce((a, b) => a + (b - avgArea) ** 2, 0) / areas.length;
    const stdDev = Math.sqrt(variance);
    const cv = stdDev / avgArea;

    if (cv > 0.3) continue;

    const sortedByX = [...group].sort((a, b) => a.center.x - b.center.x);
    const gaps: number[] = [];
    for (let i = 1; i < sortedByX.length; i++) {
      gaps.push(sortedByX[i].center.x - sortedByX[i - 1].center.x);
    }
    const avgGap = gaps.reduce((a, b) => a + b, 0) / gaps.length;
    const gapVariance = gaps.reduce((a, b) => a + (b - avgGap) ** 2, 0) / gaps.length;
    const gapStdDev = Math.sqrt(gapVariance);
    const gapCV = gapStdDev / avgGap;

    if (gapCV < 0.3) {
      for (const s of group) {
        relations.push({
          id: generateId(),
          type: 'repeat',
          shapeAId: s.id,
          confidence: 0.7 + (1 - cv) * 0.2,
          metadata: {
            groupType: type,
            groupSize: group.length,
          },
        });
      }
    }
  }

  return relations;
}

function detectConnected(shapeA: Shape, shapeB: Shape): ShapeRelation | null {
  const distInfo = polygonDistance(shapeA.points, shapeB.points);
  const avgSize = (Math.sqrt(shapeA.area) + Math.sqrt(shapeB.area)) / 2;

  if (distInfo.minDist > avgSize * 0.2) return null;

  for (let i = 0; i < shapeA.points.length; i++) {
    const p1 = shapeA.points[i];
    const p2 = shapeA.points[(i + 1) % shapeA.points.length];

    for (let j = 0; j < shapeB.points.length; j++) {
      const p3 = shapeB.points[j];
      const p4 = shapeB.points[(j + 1) % shapeB.points.length];

      if (segmentsIntersect(p1, p2, p3, p4)) {
        return {
          id: generateId(),
          type: 'connected',
          shapeAId: shapeA.id,
          shapeBId: shapeB.id,
          confidence: 0.85,
          metadata: {},
        };
      }
    }
  }

  if (distInfo.minDist < avgSize * 0.05) {
    return {
      id: generateId(),
      type: 'connected',
      shapeAId: shapeA.id,
      shapeBId: shapeB.id,
      confidence: 0.7,
      metadata: {
        distance: distInfo.minDist,
      },
    };
  }

  return null;
}

export function detectShapeRelations(
  shapes: Shape[],
  canvasWidth: number,
  canvasHeight: number
): ShapeRelation[] {
  const relations: ShapeRelation[] = [];

  if (shapes.length < 2) return relations;

  const canvasCenter: Point = { x: canvasWidth / 2, y: canvasHeight / 2 };
  const processPairs = new Set<string>();

  for (let i = 0; i < shapes.length; i++) {
    for (let j = i + 1; j < shapes.length; j++) {
      const shapeA = shapes[i];
      const shapeB = shapes[j];
      const pairKey = `${shapeA.id}-${shapeB.id}`;

      if (processPairs.has(pairKey)) continue;
      processPairs.add(pairKey);

      const containsAB = detectContains(shapeA, shapeB);
      if (containsAB) {
        relations.push(containsAB);
        relations.push({
          ...containsAB,
          id: generateId(),
          type: 'inside',
          shapeAId: shapeB.id,
          shapeBId: shapeA.id,
        });
        continue;
      }

      const containsBA = detectContains(shapeB, shapeA);
      if (containsBA) {
        relations.push(containsBA);
        relations.push({
          ...containsBA,
          id: generateId(),
          type: 'inside',
          shapeAId: shapeA.id,
          shapeBId: shapeB.id,
        });
        continue;
      }

      const intersects = detectIntersects(shapeA, shapeB);
      if (intersects) {
        relations.push(intersects);
        continue;
      }

      const tangent = detectTangent(shapeA, shapeB);
      if (tangent) {
        relations.push(tangent);
      }

      const connected = detectConnected(shapeA, shapeB);
      if (connected) {
        relations.push(connected);
      }

      const symX = detectSymmetryX(shapeA, shapeB, canvasWidth);
      if (symX) relations.push(symX);

      const symY = detectSymmetryY(shapeA, shapeB, canvasHeight);
      if (symY) relations.push(symY);

      const symOrigin = detectSymmetryOrigin(shapeA, shapeB, canvasCenter);
      if (symOrigin) relations.push(symOrigin);

      const alignedH = detectAlignedHorizontal(shapeA, shapeB);
      if (alignedH) relations.push(alignedH);

      const alignedV = detectAlignedVertical(shapeA, shapeB);
      if (alignedV) relations.push(alignedV);

      const parallel = detectParallel(shapeA, shapeB);
      if (parallel) relations.push(parallel);

      const perpendicular = detectPerpendicular(shapeA, shapeB);
      if (perpendicular) relations.push(perpendicular);
    }
  }

  const repeatRelations = detectRepeat(shapes);
  relations.push(...repeatRelations);

  const uniqueRelations = relations.filter((r, index, self) =>
    index === self.findIndex(x =>
      x.type === r.type &&
      x.shapeAId === r.shapeAId &&
      x.shapeBId === r.shapeBId
    )
  );

  return uniqueRelations.filter(r => r.confidence > 0.55);
}
