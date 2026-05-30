import { io, Socket } from 'socket.io-client';
import type { Annotation, OnlineUser } from '../types';
import type { AnnotationOperation } from '../utils/operationalTransform';

class WebSocketService {
  private socket: Socket | null = null;
  private projectId: string | null = null;

  connect(projectId: string, userId: string, userName: string) {
    this.projectId = projectId;
    this.socket = io('http://localhost:3001', {
      transports: ['websocket', 'polling'],
    });

    this.socket.on('connect', () => {
      console.log('WebSocket connected');
      this.socket?.emit('joinProject', { projectId, userId, userName });
    });

    this.socket.on('disconnect', () => {
      console.log('WebSocket disconnected');
    });
  }

  disconnect() {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }
    this.projectId = null;
  }

  onOperation(callback: (operation: AnnotationOperation) => void) {
    this.socket?.on('annotationOperation', callback);
  }

  onAnnotationAdded(callback: (annotation: Annotation) => void) {
    this.socket?.on('annotationAdded', callback);
  }

  onAnnotationUpdated(callback: (annotation: Annotation) => void) {
    this.socket?.on('annotationUpdated', callback);
  }

  onAnnotationDeleted(callback: (annotationId: string) => void) {
    this.socket?.on('annotationDeleted', callback);
  }

  onConflictResolved(callback: (result: { merged: boolean; annotations: Annotation[] }) => void) {
    this.socket?.on('conflictResolved', callback);
  }

  onOnlineUsers(callback: (users: OnlineUser[]) => void) {
    this.socket?.on('onlineUsers', callback);
  }

  onUserCursor(callback: (userId: string, x: number, y: number) => void) {
    this.socket?.on('userCursor', ({ userId, x, y }) => callback(userId, x, y));
  }

  emitAnnotationOperation(operation: AnnotationOperation) {
    this.socket?.emit('annotationOperation', operation);
  }

  emitAnnotationAdded(annotation: Annotation) {
    this.socket?.emit('annotationAdded', annotation);
  }

  emitAnnotationUpdated(annotation: Annotation) {
    this.socket?.emit('annotationUpdated', annotation);
  }

  emitAnnotationDeleted(annotationId: string) {
    this.socket?.emit('annotationDeleted', { annotationId });
  }

  emitCursorPosition(x: number, y: number) {
    this.socket?.emit('userCursor', { x, y });
  }

  off(event: string) {
    this.socket?.off(event);
  }
}

export const wsService = new WebSocketService();
