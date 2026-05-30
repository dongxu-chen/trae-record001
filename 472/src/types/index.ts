export type ChartType = 'timeSeries' | 'scatter' | 'bar';

export type AnnotationType = 'classification' | 'anomaly' | 'trend';

export interface DataPoint {
  x: number | string | Date;
  y: number;
  [key: string]: any;
}

export interface Project {
  id: string;
  name: string;
  description: string;
  chartType: ChartType;
  createdAt: string;
  updatedAt: string;
  dataPoints: DataPoint[];
  dataFileName?: string;
}

export interface Annotation {
  id: string;
  projectId: string;
  type: AnnotationType;
  dataPointIndex: number;
  label: string;
  description?: string;
  color?: string;
  createdBy: string;
  createdAt: string;
  isAutoLabeled?: boolean;
  confidence?: number;
}

export interface User {
  id: string;
  name: string;
  avatar?: string;
  color: string;
}

export interface OnlineUser extends User {
  cursor?: { x: number; y: number };
}

export interface ExportOptions {
  format: 'json' | 'csv' | 'excel';
  includeDataPoints?: boolean;
}

export interface Statistics {
  totalAnnotations: number;
  byType: {
    classification: number;
    anomaly: number;
    trend: number;
  };
  byUser: {
    userId: string;
    userName: string;
    count: number;
  }[];
  recentAnnotations: Annotation[];
  dataPointCoverage: number;
}

export interface AnnotationVersion {
  id: string;
  projectId: string;
  version: number;
  name: string;
  description: string;
  annotations: Annotation[];
  createdBy: string;
  createdAt: string;
}

export interface VersionDiff {
  added: Annotation[];
  removed: Annotation[];
  modified: {
    old: Annotation;
    new: Annotation;
  }[];
}

export interface PreLabelResult {
  dataPointIndex: number;
  predictedType: AnnotationType;
  predictedLabel: string;
  confidence: number;
  neighbors: number[];
}

export interface QualityAssessment {
  missingAnnotations: {
    dataPointIndex: number;
    reason: string;
    severity: 'low' | 'medium' | 'high';
  }[];
  suspiciousAnnotations: {
    annotationId: string;
    dataPointIndex: number;
    reason: string;
    confidence: number;
  }[];
  overallQuality: number;
  coverageScore: number;
  consistencyScore: number;
}

export interface TrainingSample {
  features: number[];
  label: string;
  type: AnnotationType;
  dataPointIndex: number;
}
