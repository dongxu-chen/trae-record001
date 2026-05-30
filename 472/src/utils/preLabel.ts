import type { DataPoint, Annotation, AnnotationType, PreLabelResult, TrainingSample } from '../types';
import { getAnnotationColor } from './export';

function extractFeatures(dataPoint: DataPoint, allDataPoints: DataPoint[]): number[] {
  const features: number[] = [];
  const index = allDataPoints.findIndex((dp) => dp === dataPoint);

  const yValues = allDataPoints.map((dp) => dp.y);
  const meanY = yValues.reduce((a, b) => a + b, 0) / yValues.length;
  const stdY = Math.sqrt(yValues.reduce((sum, y) => sum + Math.pow(y - meanY, 2), 0) / yValues.length);

  features.push(Number(dataPoint.y));
  features.push((Number(dataPoint.y) - meanY) / (stdY || 1));

  if (index > 0) {
    features.push(Number(dataPoint.y) - Number(allDataPoints[index - 1].y));
  } else {
    features.push(0);
  }

  if (index < allDataPoints.length - 1) {
    features.push(Number(allDataPoints[index + 1].y) - Number(dataPoint.y));
  } else {
    features.push(0);
  }

  if (index > 1) {
    const prevDiff = Number(allDataPoints[index - 1].y) - Number(allDataPoints[index - 2].y);
    const currDiff = Number(dataPoint.y) - Number(allDataPoints[index - 1].y);
    features.push(currDiff - prevDiff);
  } else {
    features.push(0);
  }

  const windowSize = Math.min(5, index, allDataPoints.length - 1 - index);
  if (windowSize > 0) {
    let localSum = 0;
    for (let i = index - windowSize; i <= index + windowSize; i++) {
      localSum += Number(allDataPoints[i].y);
    }
    const localMean = localSum / (windowSize * 2 + 1);
    features.push(Number(dataPoint.y) - localMean);
  } else {
    features.push(0);
  }

  features.push(index / allDataPoints.length);

  return features;
}

function euclideanDistance(a: number[], b: number[]): number {
  return Math.sqrt(a.reduce((sum, val, i) => sum + Math.pow(val - b[i], 2), 0));
}

function normalizeFeatures(samples: TrainingSample[]): TrainingSample[] {
  if (samples.length === 0) return samples;

  const featureCount = samples[0].features.length;
  const means: number[] = new Array(featureCount).fill(0);
  const stds: number[] = new Array(featureCount).fill(0);

  samples.forEach((sample) => {
    sample.features.forEach((val, i) => {
      means[i] += val;
    });
  });

  means.forEach((_, i) => {
    means[i] /= samples.length;
  });

  samples.forEach((sample) => {
    sample.features.forEach((val, i) => {
      stds[i] += Math.pow(val - means[i], 2);
    });
  });

  stds.forEach((_, i) => {
    stds[i] = Math.sqrt(stds[i] / samples.length) || 1;
  });

  return samples.map((sample) => ({
    ...sample,
    features: sample.features.map((val, i) => (val - means[i]) / stds[i]),
  }));
}

export function prepareTrainingData(
  dataPoints: DataPoint[],
  annotations: Annotation[]
): TrainingSample[] {
  const annotationMap = new Map<number, Annotation>();
  annotations.forEach((a) => annotationMap.set(a.dataPointIndex, a));

  const samples: TrainingSample[] = [];

  dataPoints.forEach((dp, index) => {
    const annotation = annotationMap.get(index);
    if (annotation) {
      samples.push({
        features: extractFeatures(dp, dataPoints),
        label: annotation.label,
        type: annotation.type,
        dataPointIndex: index,
      });
    }
  });

  return normalizeFeatures(samples);
}

export function predictAnnotation(
  dataPointIndex: number,
  dataPoints: DataPoint[],
  trainingSamples: TrainingSample[],
  k: number = 5
): PreLabelResult | null {
  if (trainingSamples.length < k) return null;

  const dataPoint = dataPoints[dataPointIndex];
  if (!dataPoint) return null;

  const rawFeatures = extractFeatures(dataPoint, dataPoints);

  const featureCount = trainingSamples[0].features.length;
  const means: number[] = new Array(featureCount).fill(0);
  const stds: number[] = new Array(featureCount).fill(0);

  trainingSamples.forEach((sample) => {
    sample.features.forEach((val, i) => {
      means[i] += val;
    });
  });

  means.forEach((_, i) => {
    means[i] /= trainingSamples.length;
  });

  trainingSamples.forEach((sample) => {
    sample.features.forEach((val, i) => {
      stds[i] += Math.pow(val - means[i], 2);
    });
  });

  stds.forEach((_, i) => {
    stds[i] = Math.sqrt(stds[i] / trainingSamples.length) || 1;
  });

  const normalizedFeatures = rawFeatures.map((val, i) => (val - means[i]) / stds[i]);

  const distances = trainingSamples.map((sample, idx) => ({
    index: idx,
    sample,
    distance: euclideanDistance(normalizedFeatures, sample.features),
  }));

  distances.sort((a, b) => a.distance - b.distance);

  const neighbors = distances.slice(0, k);

  const typeVotes = new Map<AnnotationType, number>();
  const labelVotes = new Map<string, number>();
  const weightSum = neighbors.reduce((sum, n) => sum + 1 / (n.distance + 1e-6), 0);

  neighbors.forEach((neighbor) => {
    const weight = 1 / (neighbor.distance + 1e-6);
    typeVotes.set(neighbor.sample.type, (typeVotes.get(neighbor.sample.type) || 0) + weight);
    labelVotes.set(neighbor.sample.label, (labelVotes.get(neighbor.sample.label) || 0) + weight);
  });

  let predictedType: AnnotationType = 'classification';
  let maxTypeVote = 0;
  typeVotes.forEach((vote, type) => {
    if (vote > maxTypeVote) {
      maxTypeVote = vote;
      predictedType = type;
    }
  });

  let predictedLabel = '';
  let maxLabelVote = 0;
  labelVotes.forEach((vote, label) => {
    if (vote > maxLabelVote) {
      maxLabelVote = vote;
      predictedLabel = label;
    }
  });

  const confidence = (maxTypeVote + maxLabelVote) / (2 * weightSum);

  return {
    dataPointIndex,
    predictedType,
    predictedLabel,
    confidence,
    neighbors: neighbors.map((n) => n.sample.dataPointIndex),
  };
}

export function batchPreLabel(
  dataPoints: DataPoint[],
  annotations: Annotation[],
  threshold: number = 0.6,
  k: number = 5
): PreLabelResult[] {
  const trainingSamples = prepareTrainingData(dataPoints, annotations);
  if (trainingSamples.length < k) return [];

  const annotatedIndices = new Set(annotations.map((a) => a.dataPointIndex));
  const results: PreLabelResult[] = [];

  dataPoints.forEach((_, index) => {
    if (!annotatedIndices.has(index)) {
      const prediction = predictAnnotation(index, dataPoints, trainingSamples, k);
      if (prediction && prediction.confidence >= threshold) {
        results.push(prediction);
      }
    }
  });

  return results.sort((a, b) => b.confidence - a.confidence);
}

export function createAutoAnnotation(
  projectId: string,
  result: PreLabelResult,
  createdBy: string
): Annotation {
  return {
    id: Math.random().toString(36).substr(2, 9),
    projectId,
    type: result.predictedType,
    dataPointIndex: result.dataPointIndex,
    label: result.predictedLabel,
    description: `自动预标注，置信度: ${(result.confidence * 100).toFixed(1)}%，基于 ${result.neighbors.length} 个最近邻`,
    color: getAnnotationColor(result.predictedType),
    createdBy,
    createdAt: new Date().toISOString(),
    isAutoLabeled: true,
    confidence: result.confidence,
  };
}

export function getTrainingStats(annotations: Annotation[]): {
  totalSamples: number;
  byType: Record<AnnotationType, number>;
  uniqueLabels: string[];
  canPreLabel: boolean;
} {
  const byType: Record<AnnotationType, number> = {
    classification: 0,
    anomaly: 0,
    trend: 0,
  };

  const labels = new Set<string>();

  annotations.forEach((a) => {
    byType[a.type]++;
    labels.add(a.label);
  });

  return {
    totalSamples: annotations.length,
    byType,
    uniqueLabels: Array.from(labels),
    canPreLabel: annotations.length >= 5,
  };
}
