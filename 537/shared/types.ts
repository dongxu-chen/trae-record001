export interface Point {
  x: number;
  y: number;
}

export interface Point3D {
  x: number;
  y: number;
  z: number;
}

export type ShapeType = 'rectangle' | 'circle' | 'triangle' | 'polygon';

export type Shape3DType = 'cube' | 'sphere' | 'cylinder' | 'cone' | 'pyramid' | 'prism';

export type RelationType =
  | 'contains'
  | 'inside'
  | 'tangent'
  | 'intersects'
  | 'symmetric_x'
  | 'symmetric_y'
  | 'symmetric_origin'
  | 'aligned_horizontal'
  | 'aligned_vertical'
  | 'parallel'
  | 'perpendicular'
  | 'repeat'
  | 'connected';

export interface Shape {
  id: string;
  type: ShapeType;
  points: Point[];
  boundingBox: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
  area: number;
  perimeter: number;
  center: Point;
  rotation?: number;
  radius?: number;
  confidence: number;
  color?: string;
  corrected?: boolean;
  shape3DId?: string;
}

export interface Shape3D {
  id: string;
  type: Shape3DType;
  sourceShapeId: string;
  center: Point3D;
  size: {
    width: number;
    height: number;
    depth: number;
  };
  rotation: Point3D;
  vertices: Point3D[];
  faces: {
    points: Point[];
    depth: number;
  }[];
  confidence: number;
  color?: string;
  volume?: number;
  surfaceArea?: number;
}

export interface ShapeRelation {
  id: string;
  type: RelationType;
  shapeAId: string;
  shapeBId?: string;
  confidence: number;
  metadata?: Record<string, any>;
}

export interface RecognizeRequest {
  imageData: string;
  options?: {
    minContourArea?: number;
    epsilonFactor?: number;
    enableCorrection?: boolean;
    enable3DInference?: boolean;
    enableRelationDetection?: boolean;
  };
}

export interface RecognizeResponse {
  success: boolean;
  shapes: Shape[];
  shapes3D: Shape3D[];
  relations: ShapeRelation[];
  processingTime: number;
  error?: string;
}

export interface UploadResponse {
  success: boolean;
  imageUrl: string;
  width: number;
  height: number;
}

export interface DrawPath {
  points: Point[];
  color: string;
  lineWidth: number;
}

export interface CalibrationData {
  enabled: boolean;
  pixelLength: number;
  realLength: number;
  unit: string;
  startPoint: Point | null;
  endPoint: Point | null;
}

export interface DXFExportOptions {
  unit?: string;
  scale?: number;
  separateLayers?: boolean;
  includeConstructionLines?: boolean;
}

export const SHAPE_COLORS: Record<ShapeType, string> = {
  rectangle: '#FF6B6B',
  circle: '#4ECDC4',
  triangle: '#FFE66D',
  polygon: '#95E1D3',
};

export const SHAPE_NAMES: Record<ShapeType, string> = {
  rectangle: '矩形',
  circle: '圆形',
  triangle: '三角形',
  polygon: '多边形',
};

export const SHAPE3D_NAMES: Record<Shape3DType, string> = {
  cube: '立方体',
  sphere: '球体',
  cylinder: '圆柱体',
  cone: '圆锥体',
  pyramid: '棱锥体',
  prism: '棱柱体',
};

export const SHAPE3D_COLORS: Record<Shape3DType, string> = {
  cube: '#A78BFA',
  sphere: '#F472B6',
  cylinder: '#34D399',
  cone: '#FBBF24',
  pyramid: '#FB7185',
  prism: '#60A5FA',
};

export const RELATION_NAMES: Record<RelationType, string> = {
  contains: '包含',
  inside: '被包含',
  tangent: '相切',
  intersects: '相交',
  symmetric_x: 'X轴对称',
  symmetric_y: 'Y轴对称',
  symmetric_origin: '中心对称',
  aligned_horizontal: '水平对齐',
  aligned_vertical: '垂直对齐',
  parallel: '平行',
  perpendicular: '垂直',
  repeat: '重复排列',
  connected: '连接',
};

export const RELATION_ICONS: Record<RelationType, string> = {
  contains: '🔲',
  inside: '🔳',
  tangent: '⭕',
  intersects: '✖️',
  symmetric_x: '↔️',
  symmetric_y: '↕️',
  symmetric_origin: '🔄',
  aligned_horizontal: '📏',
  aligned_vertical: '📐',
  parallel: '∥',
  perpendicular: '⊥',
  repeat: '🔁',
  connected: '🔗',
};
