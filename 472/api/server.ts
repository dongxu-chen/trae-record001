import { createServer } from 'http';
import { Server } from 'socket.io';
import app from './app.js';

const PORT = process.env.PORT || 3001;

const httpServer = createServer(app);

const io = new Server(httpServer, {
  cors: {
    origin: '*',
    methods: ['GET', 'POST'],
  },
});

const projectRooms: Map<string, Set<string>> = new Map();
const onlineUsers: Map<string, Map<string, { id: string; name: string; color: string }>> = new Map();

const projectAnnotations: Map<string, any[]> = new Map();
const projectOperations: Map<string, any[]> = new Map();
const projectVersions: Map<string, number> = new Map();

function getNextVersion(projectId: string): number {
  const current = projectVersions.get(projectId) || 0;
  return current + 1;
}

function applyOperation(
  operation: any,
  currentAnnotations: any[]
): {
  annotations: any[];
  conflict?: {
    type: string;
    operation: any;
    existing?: any;
  };
  merged: boolean;
} {
  const projectOps = projectOperations.get(operation.projectId) || [];

  const concurrentOps = projectOps.filter(
    (op) =>
      op.version === operation.version &&
      op.id !== operation.id &&
      op.annotation?.dataPointIndex === operation.annotation?.dataPointIndex
  );

  let conflict:
    | {
        type: string;
        operation: any;
        existing?: any;
      }
    | undefined;
  let merged = false;

  if (concurrentOps.length > 0) {
    const result = mergeOperations(operation, concurrentOps, currentAnnotations);
    conflict = result.conflict;
    merged = result.merged;

    if (result.annotations) {
      return { annotations: result.annotations, conflict, merged };
    }
  }

  return doApplyOperation(operation, currentAnnotations);
}

function mergeOperations(
  newOp: any,
  concurrentOps: any[],
  currentAnnotations: any[]
): {
  annotations?: any[];
  conflict?: {
    type: string;
    operation: any;
    existing?: any;
  };
  merged: boolean;
} {
  if (newOp.type === 'add') {
    const existingAnnotation = currentAnnotations.find(
      (a) => a.dataPointIndex === newOp.annotation?.dataPointIndex
    );

    if (existingAnnotation && newOp.annotation) {
      const mergedLabel = mergeLabels(existingAnnotation.label, newOp.annotation.label);
      const mergedDescription = mergeDescriptions(
        existingAnnotation.description,
        newOp.annotation.description
      );

      const mergedAnnotation = {
        ...existingAnnotation,
        label: mergedLabel,
        description: mergedDescription,
        createdAt: new Date().toISOString(),
      };

      const updatedAnnotations = currentAnnotations.map((a) =>
        a.id === existingAnnotation.id ? mergedAnnotation : a
      );

      return {
        annotations: updatedAnnotations,
        conflict: {
          type: 'merge',
          operation: newOp,
          existing: existingAnnotation,
        },
        merged: true,
      };
    }
  }

  return { merged: false };
}

function mergeLabels(label1: string, label2: string): string {
  const labels1 = label1.split(/[,，]/).map((l) => l.trim());
  const labels2 = label2.split(/[,，]/).map((l) => l.trim());
  const merged = [...new Set([...labels1, ...labels2])];
  return merged.join(', ');
}

function mergeDescriptions(desc1?: string, desc2?: string): string {
  const parts: string[] = [];
  if (desc1) parts.push(desc1);
  if (desc2 && desc2 !== desc1) parts.push(desc2);
  return parts.join(' | ');
}

function doApplyOperation(
  operation: any,
  currentAnnotations: any[]
): {
  annotations: any[];
  merged: boolean;
} {
  let annotations: any[];

  switch (operation.type) {
    case 'add':
      if (operation.annotation) {
        const existing = currentAnnotations.find((a) => a.id === operation.annotation!.id);
        if (existing) {
          annotations = currentAnnotations.map((a) =>
            a.id === operation.annotation!.id ? operation.annotation! : a
          );
        } else {
          annotations = [...currentAnnotations, operation.annotation];
        }
      } else {
        annotations = currentAnnotations;
      }
      break;
    case 'update':
      if (operation.annotation) {
        annotations = currentAnnotations.map((a) =>
          a.id === operation.annotation!.id ? operation.annotation! : a
        );
      } else {
        annotations = currentAnnotations;
      }
      break;
    case 'delete':
      if (operation.annotationId) {
        annotations = currentAnnotations.filter((a) => a.id !== operation.annotationId);
      } else {
        annotations = currentAnnotations;
      }
      break;
    default:
      annotations = currentAnnotations;
  }

  return { annotations, merged: false };
}

io.on('connection', (socket) => {
  console.log('Client connected:', socket.id);

  socket.on('joinProject', ({ projectId, userId, userName }) => {
    socket.join(projectId);

    if (!projectRooms.has(projectId)) {
      projectRooms.set(projectId, new Set());
      onlineUsers.set(projectId, new Map());
      projectAnnotations.set(projectId, []);
      projectOperations.set(projectId, []);
      projectVersions.set(projectId, 0);
    }

    projectRooms.get(projectId)?.add(socket.id);
    onlineUsers.get(projectId)?.set(socket.id, {
      id: userId,
      name: userName,
      color: '#' + Math.floor(Math.random() * 16777215).toString(16).padStart(6, '0'),
    });

    const users = Array.from(onlineUsers.get(projectId)?.values() || []);
    io.to(projectId).emit('onlineUsers', users);
    console.log(`User ${userName} joined project ${projectId}`);
  });

  socket.on('annotationOperation', (operation) => {
    const rooms = Array.from(socket.rooms);
    const projectId = rooms.find((room) => room !== socket.id);

    if (projectId) {
      const currentAnnotations = projectAnnotations.get(projectId) || [];
      const result = applyOperation(operation, currentAnnotations);

      projectAnnotations.set(projectId, result.annotations);

      const ops = projectOperations.get(projectId) || [];
      ops.push(operation);
      projectOperations.set(projectId, ops);
      projectVersions.set(projectId, operation.version || getNextVersion(projectId));

      socket.to(projectId).emit('annotationOperation', operation);

      if (result.conflict) {
        io.to(projectId).emit('conflictResolved', {
          merged: result.merged,
          annotations: result.annotations,
          conflict: result.conflict,
        });
      }
    }
  });

  socket.on('annotationAdded', (annotation) => {
    const rooms = Array.from(socket.rooms);
    const projectId = rooms.find((room) => room !== socket.id);
    if (projectId) {
      const annotations = projectAnnotations.get(projectId) || [];
      annotations.push(annotation);
      projectAnnotations.set(projectId, annotations);

      socket.to(projectId).emit('annotationAdded', annotation);
      console.log('Annotation broadcasted:', annotation.id);
    }
  });

  socket.on('annotationUpdated', (annotation) => {
    const rooms = Array.from(socket.rooms);
    const projectId = rooms.find((room) => room !== socket.id);
    if (projectId) {
      const annotations = projectAnnotations.get(projectId) || [];
      const index = annotations.findIndex((a) => a.id === annotation.id);
      if (index >= 0) {
        annotations[index] = annotation;
        projectAnnotations.set(projectId, annotations);
      }

      socket.to(projectId).emit('annotationUpdated', annotation);
    }
  });

  socket.on('annotationDeleted', ({ annotationId }) => {
    const rooms = Array.from(socket.rooms);
    const projectId = rooms.find((room) => room !== socket.id);
    if (projectId) {
      const annotations = projectAnnotations.get(projectId) || [];
      const filtered = annotations.filter((a) => a.id !== annotationId);
      projectAnnotations.set(projectId, filtered);

      socket.to(projectId).emit('annotationDeleted', annotationId);
    }
  });

  socket.on('userCursor', ({ x, y }) => {
    const rooms = Array.from(socket.rooms);
    const projectId = rooms.find((room) => room !== socket.id);
    if (projectId) {
      const user = onlineUsers.get(projectId)?.get(socket.id);
      if (user) {
        socket.to(projectId).emit('userCursor', { userId: user.id, x, y });
      }
    }
  });

  socket.on('disconnect', () => {
    console.log('Client disconnected:', socket.id);

    projectRooms.forEach((users, projectId) => {
      if (users.has(socket.id)) {
        users.delete(socket.id);
        onlineUsers.get(projectId)?.delete(socket.id);

        const remainingUsers = Array.from(onlineUsers.get(projectId)?.values() || []);
        io.to(projectId).emit('onlineUsers', remainingUsers);
      }
    });
  });
});

httpServer.listen(PORT, () => {
  console.log(`Server ready on port ${PORT}`);
  console.log(`WebSocket server running with OT support`);
});

process.on('SIGTERM', () => {
  console.log('SIGTERM signal received');
  httpServer.close(() => {
    console.log('Server closed');
    process.exit(0);
  });
});

process.on('SIGINT', () => {
  console.log('SIGINT signal received');
  httpServer.close(() => {
    console.log('Server closed');
    process.exit(0);
  });
});

export default app;
