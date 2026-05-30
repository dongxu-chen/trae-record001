import type { DataPoint, Annotation, QualityAssessment, AnnotationType } from '../types';
import { prepareTrainingData, predictAnnotation } from './preLabel';
import { calculateKappa } from './kappa';

function detectOutliers(dataPoints: DataPoint[]): number[] {
  if (dataPoints.length < 4) return [];

  const yValues = dataPoints.map((dp) => dp.y);
  const sorted = [...yValues].sort((a, b) => a - b);
  const q1 = sorted[Math.floor(sorted.length * 0.25)];
  const q3 = sorted[Math.floor(sorted.length * 0.75)];
  const iqr = q3 - q1;
  const lowerBound = q1 - 1.5 * iqr;
  const upperBound = q3 + 1.5 * iqr;

  const outliers: number[] = [];
  yValues.forEach((y, index) => {
    if (y < lowerBound || y > upperBound) {
      outliers.push(index);
    }
  });

  return outliers;
}

function detectTrendChanges(dataPoints: DataPoint[], windowSize: number = 5): number[] {
  if (dataPoints.length < windowSize * 2) return [];

  const changes: number[] = [];

  for (let i = windowSize; i < dataPoints.length - windowSize; i++) {
    const prevWindow = dataPoints.slice(i - windowSize, i);
    const nextWindow = dataPoints.slice(i + 1, i + windowSize + 1);

    const prevAvg = prevWindow.reduce((sum, dp) => sum + dp.y, 0) / windowSize;
    const nextAvg = nextWindow.reduce((sum, dp) => sum + dp.y, 0) / windowSize;

    const prevStd = Math.sqrt(
      prevWindow.reduce((sum, dp) => sum + Math.pow(dp.y - prevAvg, 2), 0) / windowSize
    );

    if (Math.abs(nextAvg - prevAvg) > prevStd * 1.5) {
      changes.push(i);
    }
  }

  return changes;
}

function detectClusters(dataPoints: DataPoint[]): Map<number, string> {
  const clusters = new Map<number, string>();
  if (dataPoints.length < 3) return clusters;

  const yValues = dataPoints.map((dp) => dp.y);
  const mean = yValues.reduce((a, b) => a + b, 0) / yValues.length;
  const std = Math.sqrt(
    yValues.reduce((sum, y) => sum + Math.pow(y - mean, 2), 0) / yValues.length
  );

  dataPoints.forEach((dp, index) => {
    const zScore = (dp.y - mean) / (std || 1);
    if (zScore > 1) {
      clusters.set(index, 'high');
    } else if (zScore < -1) {
      clusters.set(index, 'low');
    } else {
      clusters.set(index, 'normal');
    }
  });

  return clusters;
}

function checkAnnotationConsistency(
  annotations: Annotation[]
): { annotationId: string; reason: string; confidence: number }[] {
  const issues: { annotationId: string; reason: string; confidence: number }[] = [];
  const typeLabelMap = new Map<AnnotationType, Set<string>>();

  annotations.forEach((a) => {
    const labels = typeLabelMap.get(a.type) || new Set<string>();
    labels.add(a.label.toLowerCase());
    typeLabelMap.set(a.type, labels);
  });

  annotations.forEach((a) => {
    const labelLower = a.label.toLowerCase();
    let otherTypes = 0;
    let thisType = 0;

    typeLabelMap.forEach((labels, type) => {
      if (type === a.type) {
        thisType = annotations.filter((ann) => ann.type === type).length;
      } else if (labels.has(labelLower)) {
        otherTypes++;
      }
    });

    if (otherTypes > 0 && thisType < 3) {
      issues.push({
        annotationId: a.id,
        reason: `标签 "${a.label}" 在 ${otherTypes} 种其他类型中也出现，可能分类错误`,
        confidence: 0.6,
      });
    }
  });

  return issues;
}

function checkLabelConsistency(annotations: Annotation[]): {
  annotationId: string;
  reason: string;
  confidence: number;
}[] {
  const issues: { annotationId: string; reason: string; confidence: number }[] = [];
  const labelTypeMap = new Map<string, AnnotationType[]>();

  annotations.forEach((a) => {
    const labelLower = a.label.toLowerCase();
    const types = labelTypeMap.get(labelLower) || [];
    if (!types.includes(a.type)) {
      types.push(a.type);
      labelTypeMap.set(labelLower, types);
    }
  });

  annotations.forEach((a) => {
    const labelLower = a.label.toLowerCase();
    const types = labelTypeMap.get(labelLower) || [];
    if (types.length > 1) {
      issues.push({
        annotationId: a.id,
        reason: `标签 "${a.label}" 被标记为多种类型: ${types.join(', ')}，建议统一`,
        confidence: 0.7,
      });
    }
  });

  return issues;
}

export function assessQuality(
  dataPoints: DataPoint[],
  annotations: Annotation[]
): QualityAssessment {
  const missingAnnotations: QualityAssessment['missingAnnotations'] = [];
  const suspiciousAnnotations: QualityAssessment['suspiciousAnnotations'] = [];

  const annotatedIndices = new Set(annotations.map((a) => a.dataPointIndex));

  const outliers = detectOutliers(dataPoints);
  outliers.forEach((index) => {
    if (!annotatedIndices.has(index)) {
      missingAnnotations.push({
        dataPointIndex: index,
        reason: '该数据点是统计异常值（IQR方法），建议标注',
        severity: 'high',
      });
    }
  });

  const trendChanges = detectTrendChanges(dataPoints);
  trendChanges.forEach((index) => {
    if (!annotatedIndices.has(index)) {
      missingAnnotations.push({
        dataPointIndex: index,
        reason: '该数据点附近存在趋势变化，建议标注',
        severity: 'medium',
      });
    }
  });

  const clusters = detectClusters(dataPoints);
  const clusterCounts: Record<string, { total: number; annotated: number }> = {
    high: { total: 0, annotated: 0 },
    low: { total: 0, annotated: 0 },
    normal: { total: 0, annotated: 0 },
  };

  clusters.forEach((cluster, index) => {
    clusterCounts[cluster].total++;
    if (annotatedIndices.has(index)) {
      clusterCounts[cluster].annotated++;
    }
  });

  Object.entries(clusterCounts).forEach(([cluster, counts]) => {
    if (counts.total > 0 && counts.annotated === 0) {
      const sampleIndex = Array.from(clusters.entries()).find(
        ([_, c]) => c === cluster
      )?.[0];
      if (sampleIndex !== undefined && !annotatedIndices.has(sampleIndex)) {
        missingAnnotations.push({
          dataPointIndex: sampleIndex,
          reason: `"${cluster}" 聚类的 ${counts.total} 个数据点都未标注，建议至少标注代表性样本`,
          severity: 'medium',
        });
      }
    }
  });

  const labelConsistencyIssues = checkLabelConsistency(annotations);
  labelConsistencyIssues.forEach((issue) => {
    const annotation = annotations.find((a) => a.id === issue.annotationId);
    if (annotation) {
      suspiciousAnnotations.push({
        annotationId: issue.annotationId,
        dataPointIndex: annotation.dataPointIndex,
        reason: issue.reason,
        confidence: issue.confidence,
      });
    }
  });

  const consistencyIssues = checkAnnotationConsistency(annotations);
  consistencyIssues.forEach((issue) => {
    const annotation = annotations.find((a) => a.id === issue.annotationId);
    if (annotation) {
      suspiciousAnnotations.push({
        annotationId: issue.annotationId,
        dataPointIndex: annotation.dataPointIndex,
        reason: issue.reason,
        confidence: issue.confidence,
      });
    }
  });

  const trainingSamples = prepareTrainingData(dataPoints, annotations);
  if (trainingSamples.length >= 5) {
    annotations.forEach((annotation) => {
      const prediction = predictAnnotation(
        annotation.dataPointIndex,
        dataPoints,
        trainingSamples,
        3
      );

      if (prediction) {
        if (prediction.predictedType !== annotation.type && prediction.confidence > 0.7) {
          suspiciousAnnotations.push({
            annotationId: annotation.id,
            dataPointIndex: annotation.dataPointIndex,
            reason: `KNN模型预测类型为 "${prediction.predictedType}"，置信度 ${(prediction.confidence * 100).toFixed(0)}%，与当前类型 "${annotation.type}" 不符`,
            confidence: prediction.confidence,
          });
        }
      }
    });
  }

  const coverageScore =
    dataPoints.length > 0
      ? new Set(annotations.map((a) => a.dataPointIndex)).size / dataPoints.length
      : 0;

  const kappaResult = calculateKappa(annotations, dataPoints.length);
  const consistencyScore = Math.max(0, kappaResult.kappa);

  const suspiciousRatio =
    annotations.length > 0 ? suspiciousAnnotations.length / annotations.length : 0;
  const missingRatio =
    dataPoints.length > 0 ? missingAnnotations.length / dataPoints.length : 0;

  const overallQuality = Math.max(
    0,
    Math.min(
      1,
      1 - (suspiciousRatio * 0.4 + missingRatio * 0.3 + (1 - consistencyScore) * 0.3)
    )
  );

  return {
    missingAnnotations: missingAnnotations.sort((a, b) => {
      const severityOrder = { high: 0, medium: 1, low: 2 };
      return severityOrder[a.severity] - severityOrder[b.severity];
    }),
    suspiciousAnnotations: suspiciousAnnotations.sort((a, b) => b.confidence - a.confidence),
    overallQuality,
    coverageScore,
    consistencyScore,
  };
}

export function getQualityLevel(score: number): {
  level: string;
  color: string;
  description: string;
} {
  if (score >= 0.9) {
    return { level: '优秀', color: '#10b981', description: '标注质量很高，一致性和覆盖率都很好' };
  } else if (score >= 0.75) {
    return { level: '良好', color: '#22c55e', description: '标注质量良好，只有少量问题需要关注' };
  } else if (score >= 0.6) {
    return { level: '一般', color: '#eab308', description: '标注质量一般，建议检查一些可疑标注' };
  } else if (score >= 0.4) {
    return { level: '较差', color: '#f97316', description: '标注质量较差，存在较多不一致或漏标' };
  } else {
    return { level: '差', color: '#ef4444', description: '标注质量差，需要全面检查和改进' };
  }
}

export function getSeverityColor(severity: 'low' | 'medium' | 'high'): string {
  switch (severity) {
    case 'high':
      return '#ef4444';
    case 'medium':
      return '#f97316';
    case 'low':
      return '#eab308';
  }
}

export function getConfidenceColor(confidence: number): string {
  if (confidence >= 0.8) return '#ef4444';
  if (confidence >= 0.6) return '#f97316';
  return '#eab308';
}
