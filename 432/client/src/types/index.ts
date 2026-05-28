export type AnnotationType = 'highlight' | 'underline' | 'strikeout' | 'comment' | 'rectangle' | 'circle' | 'arrow' | 'select';

export interface RelativePosition {
  x: number;
  y: number;
  width?: number;
  height?: number;
}

export interface Annotation {
  id: string;
  type: AnnotationType;
  pageIndex: number;
  position: RelativePosition;
  color: string;
  content?: string;
  createdAt: number;
}

export interface OutlineNode {
  id: string;
  title: string;
  pageIndex: number;
  children: OutlineNode[];
}

export interface PdfDocument {
  id: string;
  name: string;
  file: File;
  numPages: number;
  annotations: Annotation[];
  outlines: OutlineNode[];
  pageSizes: { width: number; height: number }[];
}

export type ExportStatus = 'pending' | 'processing' | 'completed' | 'failed';

export interface ExportTask {
  taskId: string;
  fileId: string;
  status: ExportStatus;
  downloadUrl?: string;
  progress: number;
  createdAt: number;
  completedAt?: number;
}

export interface ToolState {
  currentTool: AnnotationType;
  currentColor: string;
}

export interface ViewerState {
  currentPage: number;
  zoom: number;
  sidebarOpen: boolean;
  sidebarTab: 'outline' | 'search' | 'annotations' | 'reviewers';
}

export interface SearchResult {
  pageIndex: number;
  text: string;
  position: RelativePosition;
}

export interface OcrResult {
  pageIndex: number;
  text: string;
  position: RelativePosition;
  confidence: number;
}

export interface OcrTask {
  taskId: string;
  fileId: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;
  results: OcrResult[];
}

export interface AnnotationTemplate {
  id: string;
  name: string;
  type: AnnotationType;
  color: string;
  content?: string;
  shortcut?: string;
  isGlobal: boolean;
  createdAt: number;
  updatedAt: number;
}

export interface Reviewer {
  id: string;
  name: string;
  color: string;
  role: 'owner' | 'reviewer';
}

export interface ReviewSession {
  sessionId: string;
  fileId: string;
  ownerId: string;
  reviewers: Reviewer[];
  annotations: (Annotation & { reviewerId: string })[];
  status: 'active' | 'merged' | 'completed';
  createdAt: number;
}

export interface MergeConflict {
  annotationA: Annotation;
  annotationB: Annotation;
  type: 'overlap' | 'position' | 'content';
}
