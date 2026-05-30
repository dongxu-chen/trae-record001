import type { Point, Shape, ShapeType } from '../../shared/types';
import { SHAPE_COLORS } from '../../shared/types';

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

export function ramerDouglasPeucker(points: Point[], epsilon: number, closed = true): Point[] {
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

  const avgAngle = angles.reduce((s, a) => s + a, 0) / 4;
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

  const center = polygonCenter(points);

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
        const perpAngle = snappedAngle + Math.PI / 2;
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

export function correctShape(shape: Shape): Shape {
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

export function pointInPolygon(point: Point, polygon: Point[]): boolean {
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

export function findNearestVertex(point: Point, vertices: Point[], threshold = 10): number | null {
  let minDist = Infinity;
  let nearestIndex = -1;

  vertices.forEach((v, i) => {
    const dist = distance(point, v);
    if (dist < minDist && dist < threshold) {
      minDist = dist;
      nearestIndex = i;
    }
  });

  return nearestIndex >= 0 ? nearestIndex : null;
}

export function transformShape(
  points: Point[],
  scale: number,
  rotation: number,
  translation: Point
): Point[] {
  const center = polygonCenter(points);
  const cos = Math.cos(rotation);
  const sin = Math.sin(rotation);

  return points.map(p => {
    const dx = p.x - center.x;
    const dy = p.y - center.y;

    const scaledX = dx * scale;
    const scaledY = dy * scale;

    const rotatedX = scaledX * cos - scaledY * sin;
    const rotatedY = scaledX * sin + scaledY * cos;

    return {
      x: rotatedX + center.x + translation.x,
      y: rotatedY + center.y + translation.y,
    };
  });
}

export function convertPixelToReal(pixelValue: number, calibration: { pixelLength: number; realLength: number }): number {
  if (calibration.pixelLength <= 0) return pixelValue;
  return pixelValue * (calibration.realLength / calibration.pixelLength);
}
