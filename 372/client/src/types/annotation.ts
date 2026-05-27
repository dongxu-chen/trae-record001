export type AnnotationType = 'polygon' | 'point' | 'rectangle' | 'brush' | 'sam';
export type ToolType = AnnotationType | 'select';

export interface Point {
  x: number;
  y: number;
}

export interface BaseAnnotation {
  id: string;
  type: AnnotationType;
  label: string;
  color: string;
  visible: boolean;
  createdAt: number;
  pixelArea?: number;
  pixelPercentage?: number;
}

export interface PolygonAnnotation extends BaseAnnotation {
  type: 'polygon';
  points: Point[];
  closed: boolean;
}

export interface PointAnnotation extends BaseAnnotation {
  type: 'point';
  position: Point;
  radius: number;
}

export interface RectangleAnnotation extends BaseAnnotation {
  type: 'rectangle';
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface BrushAnnotation extends BaseAnnotation {
  type: 'brush';
  points: Point[];
  strokeWidth: number;
}

export interface SAMAnnotation extends BaseAnnotation {
  type: 'sam';
  mask: number[];
  width: number;
  height: number;
}

export type Annotation =
  | PolygonAnnotation
  | PointAnnotation
  | RectangleAnnotation
  | BrushAnnotation
  | SAMAnnotation;

export interface SAMRequest {
  imageId: string;
  point: Point;
  mode: 'click' | 'box';
}

export interface SAMResponse {
  mask: number[];
  width: number;
  height: number;
  confidence: number;
}

export interface ImageInfo {
  id: string;
  filename: string;
  width: number;
  height: number;
  uploadedAt: number;
  url?: string;
}

export interface CanvasState {
  scale: number;
  offsetX: number;
  offsetY: number;
  imageWidth: number;
  imageHeight: number;
}

export interface Label {
  id: string;
  name: string;
  color: string;
}

export type WsClientMessage =
  | { type: 'sam_predict'; payload: SAMRequest }
  | { type: 'sam_reset'; payload: { imageId: string } }
  | { type: 'ping'; payload: null };

export type WsServerMessage =
  | { type: 'sam_result'; payload: SAMResponse }
  | { type: 'sam_progress'; payload: { progress: number } }
  | { type: 'sam_error'; payload: { error: string } }
  | { type: 'pong'; payload: null };

export const PRESET_COLORS = [
  '#ef4444',
  '#f97316',
  '#eab308',
  '#22c55e',
  '#06b6d4',
  '#3b82f6',
  '#8b5cf6',
  '#ec4899',
  '#f43f5e',
  '#14b8a6',
];

export interface VideoInfo {
  id: string;
  filename: string;
  width: number;
  height: number;
  fps: number;
  total_frames: number;
  duration: number;
  uploaded_at: number;
  frames_dir: string;
}

export interface VideoFrameInfo {
  frame_index: number;
  timestamp: number;
  is_keyframe: boolean;
  image_id: string | null;
}

export interface QualityIssue {
  type: string;
  severity: 'critical' | 'warning' | 'info';
  description: string;
  frame_idx: number | null;
  annotation_id: string | null;
  details: Record<string, any>;
}

export interface QualityReport {
  quality_score: number;
  total_annotations: number;
  issues: QualityIssue[];
  overlap_regions: any[];
  missing_regions: any[];
  details: Record<string, any>;
}

export interface AnnotationVersion {
  version_id: string;
  image_id: string;
  annotations: Annotation[];
  created_at: number;
  description: string;
  author: string;
  metadata: Record<string, any>;
}

export interface VersionDiff {
  added: Annotation[];
  removed: Annotation[];
  modified: any[];
  unchanged: number;
}
