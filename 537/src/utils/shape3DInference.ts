import type { Point, Point3D, Shape, Shape3D, Shape3DType } from '../../shared/types';
import { SHAPE3D_COLORS } from '../../shared/types';

function generateId(): string {
  return Math.random().toString(36).substring(2, 11);
}

function distance(p1: Point, p2: Point): number {
  return Math.sqrt((p2.x - p1.x) ** 2 + (p2.y - p1.y) ** 2);
}

function distance3D(p1: Point3D, p2: Point3D): number {
  return Math.sqrt((p2.x - p1.x) ** 2 + (p2.y - p1.y) ** 2 + (p2.z - p1.z) ** 2);
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

function polygonCenter(points: Point[]): Point {
  let cx = 0, cy = 0;
  const n = points.length;
  for (const p of points) {
    cx += p.x;
    cy += p.y;
  }
  return { x: cx / n, y: cy / n };
}

function lineAngle(p1: Point, p2: Point): number {
  return Math.atan2(p2.y - p1.y, p2.x - p1.x);
}

function angleDiff(a: number, b: number): number {
  let d = ((b - a) % (2 * Math.PI) + 3 * Math.PI) % (2 * Math.PI) - Math.PI;
  return Math.abs(d);
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
    angleDiff(angles[0], angles[2]) < Math.PI / 12 &&
    angleDiff(angles[1], angles[3]) < Math.PI / 12;

  const adjacentAnglesNotRight =
    Math.abs(angleDiff(angles[0], angles[1]) - Math.PI / 2) > Math.PI / 12;

  const len0 = distance(points[0], points[1]);
  const len1 = distance(points[1], points[2]);

  return {
    isParallelogram: oppositeAnglesEqual && adjacentAnglesNotRight,
    shearAngle: angleDiff(angles[0], 0),
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

function projectTo2D(p3d: Point3D, viewAngle: { x: number; y: number } = { x: -0.615, y: 0.785 }): Point {
  const cosX = Math.cos(viewAngle.x);
  const sinX = Math.sin(viewAngle.x);
  const cosY = Math.cos(viewAngle.y);
  const sinY = Math.sin(viewAngle.y);

  const x = p3d.x * cosY + p3d.z * sinY;
  const y = -p3d.x * sinY * sinX + p3d.y * cosX + p3d.z * cosY * sinX;

  return { x, y };
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

  const { isIsometric, aspectRatio } = detectIsometricCircle(shape);

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
  const { isIsometric, aspectRatio } = detectIsometricCircle(shape);

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

function polygonPerimeter(points: Point[]): number {
  let perimeter = 0;
  const n = points.length;
  for (let i = 0; i < n; i++) {
    const j = (i + 1) % n;
    perimeter += distance(points[i], points[j]);
  }
  return perimeter;
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

export function render3DShape(
  ctx: CanvasRenderingContext2D,
  shape3d: Shape3D,
  isSelected: boolean,
  zoom: number
): void {
  const sortedFaces = [...shape3d.faces].sort((a, b) => a.depth - b.depth);
  const color = shape3d.color || '#888888';

  sortedFaces.forEach((face, faceIndex) => {
    if (face.points.length < 3) return;

    const depthFactor = (face.depth + 200) / 400;
    const alpha = 0.2 + depthFactor * 0.3;

    ctx.fillStyle = `${color}${Math.floor(alpha * 255).toString(16).padStart(2, '0')}`;
    ctx.strokeStyle = color;
    ctx.lineWidth = isSelected ? 2 : 1;

    ctx.beginPath();
    ctx.moveTo(face.points[0].x, face.points[0].y);
    for (let i = 1; i < face.points.length; i++) {
      ctx.lineTo(face.points[i].x, face.points[i].y);
    }
    ctx.closePath();
    ctx.fill();
    ctx.stroke();
  });

  if (isSelected) {
    ctx.strokeStyle = '#00D4FF';
    ctx.lineWidth = 3;
    ctx.setLineDash([8, 4]);

    const allPoints = shape3d.faces.flatMap(f => f.points);
    if (allPoints.length > 0) {
      let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
      for (const p of allPoints) {
        minX = Math.min(minX, p.x);
        minY = Math.min(minY, p.y);
        maxX = Math.max(maxX, p.x);
        maxY = Math.max(maxY, p.y);
      }
      ctx.strokeRect(minX - 10, minY - 10, maxX - minX + 20, maxY - minY + 20);
    }
    ctx.setLineDash([]);

    const vertexRadius = 5 / zoom;
    shape3d.vertices.slice(0, 8).forEach(v => {
      ctx.fillStyle = '#00D4FF';
      ctx.beginPath();
      ctx.arc(v.x, v.y, vertexRadius, 0, Math.PI * 2);
      ctx.fill();
    });
  }
}
