import type { Point, Shape, ShapeRelation, RelationType } from '../../shared/types';

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
  const d1 = direction(p3, p4, p1);
  const d2 = direction(p3, p4, p2);
  const d3 = direction(p1, p2, p3);
  const d4 = direction(p1, p2, p4);

  if (((d1 > 0 && d2 < 0) || (d1 < 0 && d2 > 0)) &&
      ((d3 > 0 && d4 < 0) || (d3 < 0 && d4 > 0))) {
    return true;
  }

  if (d1 === 0 && onSegment(p3, p4, p1)) return true;
  if (d2 === 0 && onSegment(p3, p4, p2)) return true;
  if (d3 === 0 && onSegment(p1, p2, p3)) return true;
  if (d4 === 0 && onSegment(p1, p2, p4)) return true;

  return false;
}

function direction(p1: Point, p2: Point, p3: Point): number {
  return (p3.x - p1.x) * (p2.y - p1.y) - (p2.x - p1.x) * (p3.y - p1.y);
}

function onSegment(p1: Point, p2: Point, p: Point): boolean {
  return Math.min(p1.x, p2.x) <= p.x && p.x <= Math.max(p1.x, p2.x) &&
         Math.min(p1.y, p2.y) <= p.y && p.y <= Math.max(p1.y, p2.y);
}

function distanceToPolygon(point: Point, polygon: Point[]): { minDist: number; nearestPoint: Point; edgeIndex: number } {
  let minDist = Infinity;
  let nearestPoint: Point = polygon[0];
  let edgeIndex = 0;

  const n = polygon.length;
  for (let i = 0; i < n; i++) {
    const p1 = polygon[i];
    const p2 = polygon[(i + 1) % n];

    const dist = pointToSegmentDistance(point, p1, p2);
    if (dist.distance < minDist) {
      minDist = dist.distance;
      nearestPoint = dist.nearestPoint;
      edgeIndex = i;
    }
  }

  return { minDist, nearestPoint, edgeIndex };
}

function pointToSegmentDistance(point: Point, segStart: Point, segEnd: Point): {
  distance: number;
  nearestPoint: Point;
  t: number;
} {
  const dx = segEnd.x - segStart.x;
  const dy = segEnd.y - segStart.y;
  const lenSq = dx * dx + dy * dy;

  if (lenSq === 0) {
    return {
      distance: distance(point, segStart),
      nearestPoint: segStart,
      t: 0,
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
    t,
  };
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
      tangentPointA: distInfo.pointOnPoly1,
      tangentPointB: distInfo.pointOnPoly2,
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

  const mirroredA = shapeA.points.map(p => ({ x: 2 * axisX - p.x, y: p.y }));

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
      centerDistance: distance(centerA, { x: mirroredCenterX, y: centerB.y }),
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
      centerDistance: distance(centerA, { x: centerB.x, y: mirroredCenterY }),
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

  if (distance(mirroredCenter, centerB) > 40) return null;

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
    metadata: {
      origin: canvasCenter,
      centerDistance: distance(mirroredCenter, centerB),
    },
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
    metadata: {
      verticalOffset: dy,
      horizontalDistance: Math.abs(centerA.x - centerB.x),
    },
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
    metadata: {
      horizontalOffset: dx,
      verticalDistance: Math.abs(centerA.y - centerB.y),
    },
  };
}

function angleDiff(a: number, b: number): number {
  let d = ((b - a) % (2 * Math.PI) + 3 * Math.PI) % (2 * Math.PI) - Math.PI;
  return Math.abs(d);
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

      const diff = Math.min(
        angleDiff(angleA, angleB),
        angleDiff(angleA, angleB + Math.PI)
      );

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
    metadata: {
      angleDifference: minAngleDiff,
    },
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

      const diff = Math.min(
        angleDiff(angleA, angleB + Math.PI / 2),
        angleDiff(angleA, angleB - Math.PI / 2)
      );

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
    metadata: {
      angleDifference: minAngleDiff,
    },
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
            spacing: avgGap,
            areaCoefficientOfVariation: cv,
            gapCoefficientOfVariation: gapCV,
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
          metadata: {
            connectionPoint: {
              x: (p1.x + p2.x + p3.x + p4.x) / 4,
              y: (p1.y + p2.y + p3.y + p4.y) / 4,
            },
          },
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
        connectionPoint: distInfo.pointOnPoly1,
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

export function renderRelations(
  ctx: CanvasRenderingContext2D,
  relations: ShapeRelation[],
  shapes: Shape[],
  highlightRelationIds: Set<string>
): void {
  const shapeMap = new Map(shapes.map(s => [s.id, s]));

  for (const rel of relations) {
    if (rel.type === 'repeat' && !rel.shapeBId) continue;

    const shapeA = shapeMap.get(rel.shapeAId);
    const shapeB = rel.shapeBId ? shapeMap.get(rel.shapeBId) : null;

    if (!shapeA || (rel.shapeBId && !shapeB)) continue;

    const isHighlighted = highlightRelationIds.has(rel.id);
    const alpha = isHighlighted ? 0.9 : 0.4;

    let color = '#94A3B8';
    let lineWidth = isHighlighted ? 2 : 1;

    switch (rel.type) {
      case 'contains':
      case 'inside':
        color = '#22D3EE';
        break;
      case 'tangent':
        color = '#F59E0B';
        break;
      case 'intersects':
        color = '#EF4444';
        break;
      case 'symmetric_x':
      case 'symmetric_y':
      case 'symmetric_origin':
        color = '#A78BFA';
        lineWidth = isHighlighted ? 3 : 2;
        break;
      case 'aligned_horizontal':
      case 'aligned_vertical':
        color = '#34D399';
        break;
      case 'parallel':
        color = '#60A5FA';
        break;
      case 'perpendicular':
        color = '#F472B6';
        break;
      case 'connected':
        color = '#FBBF24';
        break;
    }

    ctx.strokeStyle = `${color}${Math.floor(alpha * 255).toString(16).padStart(2, '0')}`;
    ctx.lineWidth = lineWidth;
    ctx.setLineDash(isHighlighted ? [] : [4, 4]);

    if (rel.type === 'symmetric_x' && rel.metadata?.axis) {
      ctx.beginPath();
      ctx.moveTo(rel.metadata.axis, shapeA.center.y - 50);
      ctx.lineTo(rel.metadata.axis, shapeA.center.y + 50);
      ctx.stroke();
    } else if (rel.type === 'symmetric_y' && rel.metadata?.axis) {
      ctx.beginPath();
      ctx.moveTo(shapeA.center.x - 50, rel.metadata.axis);
      ctx.lineTo(shapeA.center.x + 50, rel.metadata.axis);
      ctx.stroke();
    } else if (rel.type === 'symmetric_origin' && rel.metadata?.origin) {
      ctx.beginPath();
      ctx.moveTo(shapeA.center.x, shapeA.center.y);
      ctx.lineTo(rel.metadata.origin.x, rel.metadata.origin.y);
      ctx.lineTo(shapeB!.center.x, shapeB!.center.y);
      ctx.stroke();
    } else if (shapeB && rel.type !== 'repeat') {
      ctx.beginPath();
      ctx.moveTo(shapeA.center.x, shapeA.center.y);
      ctx.lineTo(shapeB.center.x, shapeB.center.y);
      ctx.stroke();

      const midX = (shapeA.center.x + shapeB.center.x) / 2;
      const midY = (shapeA.center.y + shapeB.center.y) / 2;

      if (isHighlighted) {
        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.arc(midX, midY, 6, 0, Math.PI * 2);
        ctx.fill();
      }
    }

    ctx.setLineDash([]);
  }
}
