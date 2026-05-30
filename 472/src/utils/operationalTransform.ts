import type { Annotation } from '../types';

export type OperationType = 'add' | 'update' | 'delete';

export interface AnnotationOperation {
  id: string;
  type: OperationType;
  timestamp: number;
  userId: string;
  projectId: string;
  annotation?: Annotation;
  annotationId?: string;
  version: number;
}

export interface OTEngineOptions {
  autoMerge: boolean;
  conflictResolution: 'latest' | 'userPriority' | 'merge';
}

class OperationalTransformEngine {
  private operations: Map<string, AnnotationOperation[]> = new Map();
  private projectVersions: Map<string, number> = new Map();
  private options: OTEngineOptions = {
    autoMerge: true,
    conflictResolution: 'merge',
  };

  constructor(options?: Partial<OTEngineOptions>) {
    this.options = { ...this.options, ...options };
  }

  getNextVersion(projectId: string): number {
    const current = this.projectVersions.get(projectId) || 0;
    return current + 1;
  }

  createOperation(
    type: OperationType,
    userId: string,
    projectId: string,
    annotation?: Annotation,
    annotationId?: string
  ): AnnotationOperation {
    return {
      id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      type,
      timestamp: Date.now(),
      userId,
      projectId,
      annotation,
      annotationId,
      version: this.getNextVersion(projectId),
    };
  }

  applyOperation(
    operation: AnnotationOperation,
    currentAnnotations: Annotation[]
  ): {
    annotations: Annotation[];
    conflict?: {
      type: string;
      operation: AnnotationOperation;
      existing?: Annotation;
    };
    merged: boolean;
  } {
    const projectOps = this.operations.get(operation.projectId) || [];

    const concurrentOps = projectOps.filter(
      (op) =>
        op.version === operation.version &&
        op.id !== operation.id &&
        op.annotation?.dataPointIndex === operation.annotation?.dataPointIndex
    );

    let conflict:
      | {
          type: string;
          operation: AnnotationOperation;
          existing?: Annotation;
        }
      | undefined;
    let merged = false;

    if (concurrentOps.length > 0 && this.options.autoMerge) {
      const result = this.mergeOperations(operation, concurrentOps, currentAnnotations);
      conflict = result.conflict;
      merged = result.merged;

      if (!merged && this.options.conflictResolution === 'latest') {
        return this.doApplyOperation(operation, currentAnnotations);
      }

      if (result.annotations) {
        projectOps.push(operation);
        this.operations.set(operation.projectId, projectOps);
        this.projectVersions.set(operation.projectId, operation.version);
        return { annotations: result.annotations, conflict, merged };
      }
    }

    const result = this.doApplyOperation(operation, currentAnnotations);
    projectOps.push(operation);
    this.operations.set(operation.projectId, projectOps);
    this.projectVersions.set(operation.projectId, operation.version);

    return { ...result, conflict, merged };
  }

  private mergeOperations(
    newOp: AnnotationOperation,
    concurrentOps: AnnotationOperation[],
    currentAnnotations: Annotation[]
  ): {
    annotations?: Annotation[];
    conflict?: {
      type: string;
      operation: AnnotationOperation;
      existing?: Annotation;
    };
    merged: boolean;
  } {
    if (this.options.conflictResolution === 'merge' && newOp.type === 'add') {
      const existingAnnotation = currentAnnotations.find(
        (a) => a.dataPointIndex === newOp.annotation?.dataPointIndex
      );

      if (existingAnnotation && newOp.annotation) {
        const mergedLabel = this.mergeLabels(existingAnnotation.label, newOp.annotation.label);
        const mergedDescription = this.mergeDescriptions(
          existingAnnotation.description,
          newOp.annotation.description
        );

        const mergedAnnotation: Annotation = {
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

  private mergeLabels(label1: string, label2: string): string {
    const labels1 = label1.split(/[,，]/).map((l) => l.trim());
    const labels2 = label2.split(/[,，]/).map((l) => l.trim());
    const merged = [...new Set([...labels1, ...labels2])];
    return merged.join(', ');
  }

  private mergeDescriptions(desc1?: string, desc2?: string): string {
    const parts: string[] = [];
    if (desc1) parts.push(desc1);
    if (desc2 && desc2 !== desc1) parts.push(desc2);
    return parts.join(' | ');
  }

  private doApplyOperation(
    operation: AnnotationOperation,
    currentAnnotations: Annotation[]
  ): {
    annotations: Annotation[];
    merged: boolean;
  } {
    let annotations: Annotation[];

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

  getProjectOperations(projectId: string): AnnotationOperation[] {
    return this.operations.get(projectId) || [];
  }

  getConflicts(projectId: string): AnnotationOperation[] {
    const ops = this.operations.get(projectId) || [];
    const dataPointOps = new Map<number, AnnotationOperation[]>();

    ops.forEach((op) => {
      if (op.annotation) {
        const dpIndex = op.annotation.dataPointIndex;
        const existing = dataPointOps.get(dpIndex) || [];
        existing.push(op);
        dataPointOps.set(dpIndex, existing);
      }
    });

    const conflicts: AnnotationOperation[] = [];
    dataPointOps.forEach((dpOps) => {
      if (dpOps.length > 1) {
        conflicts.push(...dpOps);
      }
    });

    return conflicts;
  }

  resetProject(projectId: string) {
    this.operations.delete(projectId);
    this.projectVersions.delete(projectId);
  }
}

export const otEngine = new OperationalTransformEngine();
