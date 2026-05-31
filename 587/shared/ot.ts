import { Operation, Annotation } from './types';
import { v4 as uuidv4 } from 'uuid';

export interface OTOperation extends Operation {
  prevVersion: number;
}

export interface OTState {
  annotations: Annotation[];
  operations: OTOperation[];
  version: number;
}

export const createInitialOTState = (): OTState => ({
  annotations: [],
  operations: [],
  version: 0,
});

export const createOperation = (
  type: 'add' | 'update' | 'delete',
  annotationId: string,
  payload: any,
  userId: string,
  prevVersion: number
): OTOperation => ({
  id: uuidv4(),
  type,
  annotationId,
  version: prevVersion + 1,
  prevVersion,
  timestamp: Date.now(),
  userId,
  payload,
});

export const isConcurrent = (op1: OTOperation, op2: OTOperation): boolean => {
  return op1.prevVersion === op2.prevVersion && op1.id !== op2.id;
};

export const hasConflicts = (op1: OTOperation, op2: OTOperation): boolean => {
  if (op1.annotationId !== op2.annotationId) return false;
  
  if (op1.type === 'delete' || op2.type === 'delete') {
    return true;
  }
  
  if (op1.type === 'add' || op2.type === 'add') {
    return op1.type === op2.type;
  }
  
  const fields1 = Object.keys(op1.payload || {});
  const fields2 = Object.keys(op2.payload || {});
  return fields1.some(f => fields2.includes(f));
};

export const transformOperation = (
  incomingOp: OTOperation,
  concurrentOp: OTOperation
): OTOperation => {
  if (!hasConflicts(incomingOp, concurrentOp)) {
    return {
      ...incomingOp,
      prevVersion: concurrentOp.version,
      version: concurrentOp.version + 1,
    };
  }

  if (concurrentOp.type === 'delete') {
    return {
      ...incomingOp,
      type: 'update',
      payload: {},
      prevVersion: concurrentOp.version,
      version: concurrentOp.version + 1,
    };
  }

  if (incomingOp.type === 'delete' && concurrentOp.type === 'update') {
    return incomingOp;
  }

  if (incomingOp.type === 'update' && concurrentOp.type === 'update') {
    const mergedPayload = { ...incomingOp.payload };
    const concurrentFields = Object.keys(concurrentOp.payload || {});
    
    concurrentFields.forEach(field => {
      if (mergedPayload[field] !== undefined) {
        if (incomingOp.timestamp < concurrentOp.timestamp) {
          delete mergedPayload[field];
        }
      }
    });

    return {
      ...incomingOp,
      payload: mergedPayload,
      prevVersion: concurrentOp.version,
      version: concurrentOp.version + 1,
    };
  }

  return {
    ...incomingOp,
    prevVersion: concurrentOp.version,
    version: concurrentOp.version + 1,
  };
};

export const applyOperation = (
  state: OTState,
  operation: OTOperation
): { state: OTState; transformedOp: OTOperation } => {
  let currentOp = operation;
  
  const concurrentOps = state.operations.filter(
    op => op.prevVersion === currentOp.prevVersion && op.id !== currentOp.id
  );

  for (const concurrentOp of concurrentOps) {
    currentOp = transformOperation(currentOp, concurrentOp);
  }

  let newAnnotations = [...state.annotations];

  switch (currentOp.type) {
    case 'add':
      const existingIndex = newAnnotations.findIndex(a => a.id === currentOp.annotationId);
      if (existingIndex === -1) {
        newAnnotations.push({
          id: currentOp.annotationId,
          ...currentOp.payload,
          version: currentOp.version,
          createdAt: currentOp.timestamp,
          updatedAt: currentOp.timestamp,
        });
      }
      break;

    case 'update':
      const updateIndex = newAnnotations.findIndex(a => a.id === currentOp.annotationId);
      if (updateIndex !== -1) {
        newAnnotations[updateIndex] = {
          ...newAnnotations[updateIndex],
          ...currentOp.payload,
          version: currentOp.version,
          updatedAt: currentOp.timestamp,
        };
      }
      break;

    case 'delete':
      newAnnotations = newAnnotations.filter(a => a.id !== currentOp.annotationId);
      break;
  }

  return {
    state: {
      annotations: newAnnotations,
      operations: [...state.operations, currentOp],
      version: currentOp.version,
    },
    transformedOp: currentOp,
  };
};

export const applyOperations = (
  state: OTState,
  operations: OTOperation[]
): { state: OTState; transformedOps: OTOperation[] } => {
  let currentState = state;
  const transformedOps: OTOperation[] = [];

  const sortedOps = [...operations].sort((a, b) => {
    if (a.prevVersion !== b.prevVersion) {
      return a.prevVersion - b.prevVersion;
    }
    return a.timestamp - b.timestamp;
  });

  for (const op of sortedOps) {
    const result = applyOperation(currentState, op);
    currentState = result.state;
    transformedOps.push(result.transformedOp);
  }

  return { state: currentState, transformedOps };
};

export const getAnnotationAtVersion = (
  state: OTState,
  annotationId: string,
  version: number
): Annotation | undefined => {
  let annotation: Annotation | undefined;
  
  const relevantOps = state.operations
    .filter(op => op.annotationId === annotationId && op.version <= version)
    .sort((a, b) => a.version - b.version);

  for (const op of relevantOps) {
    switch (op.type) {
      case 'add':
        annotation = {
          id: annotationId,
          ...op.payload,
          version: op.version,
          createdAt: op.timestamp,
          updatedAt: op.timestamp,
        };
        break;
      case 'update':
        if (annotation) {
          annotation = {
            ...annotation,
            ...op.payload,
            version: op.version,
            updatedAt: op.timestamp,
          };
        }
        break;
      case 'delete':
        annotation = undefined;
        break;
    }
  }

  return annotation;
};
