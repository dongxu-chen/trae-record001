export type AnnotationType = 'text' | 'arrow' | 'highlight';

export interface Point {
  x: number;
  y: number;
  dataIndex?: number;
  seriesIndex?: number;
}

export interface RelativePoint {
  x: number;
  y: number;
}

export interface Annotation {
  id: string;
  type: AnnotationType;
  position: RelativePoint;
  endPosition?: RelativePoint;
  content?: string;
  color: string;
  authorId: string;
  authorName: string;
  createdAt: number;
  updatedAt: number;
  version: number;
}

export interface User {
  id: string;
  name: string;
  color: string;
  cursor?: Point;
}

export interface Session {
  id: string;
  annotations: Annotation[];
  users: User[];
  chartData: any;
  chartType: string;
  createdAt: number;
}

export type OperationType = 'add' | 'update' | 'delete';

export interface Operation {
  id: string;
  type: OperationType;
  annotationId: string;
  version: number;
  timestamp: number;
  userId: string;
  payload: any;
}

export type WSMessageType = 
  | 'user_join' 
  | 'user_leave' 
  | 'cursor_update' 
  | 'operation'
  | 'session_state';

export interface WSMessage {
  type: WSMessageType;
  payload: any;
  userId: string;
  timestamp: number;
}

export interface ShareLink {
  id: string;
  sessionId: string;
  expiresAt: number;
  passwordHash?: string;
  accessCount: number;
  permissions: 'read' | 'write';
}

export const USER_COLORS = [
  '#3b82f6', '#ef4444', '#22c55e', '#f59e0b', '#8b5cf6',
  '#ec4899', '#06b6d4', '#f97316', '#6366f1', '#14b8a6'
];

export const ANNOTATION_COLORS = [
  '#ef4444', '#f97316', '#eab308', '#22c55e', '#06b6d4',
  '#3b82f6', '#8b5cf6', '#ec4899', '#64748b', '#1e293b'
];
