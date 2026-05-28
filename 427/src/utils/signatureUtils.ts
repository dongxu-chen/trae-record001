import type { Point, SignatureStroke, SignatureVerificationResult } from '../types';

export const generateId = (): string => {
  return Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);
};

export const dtwDistance = (
  series1: Point[],
  series2: Point[],
  windowSize: number = 10
): number => {
  const n = series1.length;
  const m = series2.length;

  if (n === 0 || m === 0) return Infinity;

  const w = Math.max(windowSize, Math.abs(n - m));
  const dtwMatrix: number[][] = Array(n + 1)
    .fill(null)
    .map(() => Array(m + 1).fill(Infinity));

  dtwMatrix[0][0] = 0;

  for (let i = 1; i <= n; i++) {
    const start = Math.max(1, i - w);
    const end = Math.min(m, i + w);
    for (let j = start; j <= end; j++) {
      const cost = euclideanDistance(series1[i - 1], series2[j - 1]);
      dtwMatrix[i][j] =
        cost +
        Math.min(
          dtwMatrix[i - 1][j],
          dtwMatrix[i][j - 1],
          dtwMatrix[i - 1][j - 1]
        );
    }
  }

  return dtwMatrix[n][m];
};

export const euclideanDistance = (p1: Point, p2: Point): number => {
  const dx = p1.x - p2.x;
  const dy = p1.y - p2.y;
  const dp = (p1.pressure || 0.5) - (p2.pressure || 0.5);
  return Math.sqrt(dx * dx + dy * dy + dp * dp * 100);
};

export const extractStrokeFeatures = (stroke: SignatureStroke) => {
  const points = stroke.points;
  if (points.length < 2) return { directionChanges: 0, speedVariance: 0, totalLength: 0 };

  let totalLength = 0;
  const directions: number[] = [];
  const speeds: number[] = [];

  for (let i = 1; i < points.length; i++) {
    const dx = points[i].x - points[i - 1].x;
    const dy = points[i].y - points[i - 1].y;
    const dt = points[i].time - points[i - 1].time;
    const length = Math.sqrt(dx * dx + dy * dy);

    totalLength += length;
    directions.push(Math.atan2(dy, dx));
    if (dt > 0) speeds.push(length / dt);
  }

  let directionChanges = 0;
  for (let i = 1; i < directions.length; i++) {
    let diff = Math.abs(directions[i] - directions[i - 1]);
    if (diff > Math.PI) diff = 2 * Math.PI - diff;
    if (diff > 0.5) directionChanges++;
  }

  const speedVariance =
    speeds.length > 1
      ? speeds.reduce((sum, s) => sum + Math.pow(s - speeds.reduce((a, b) => a + b, 0) / speeds.length, 2), 0) /
        (speeds.length - 1)
      : 0;

  return { directionChanges, speedVariance, totalLength };
};

export const calculateCurvature = (points: Point[]): number[] => {
  const curvatures: number[] = [];
  for (let i = 1; i < points.length - 1; i++) {
    const dx1 = points[i].x - points[i - 1].x;
    const dy1 = points[i].y - points[i - 1].y;
    const dx2 = points[i + 1].x - points[i].x;
    const dy2 = points[i + 1].y - points[i].y;

    const cross = dx1 * dy2 - dy1 * dx2;
    const dot = dx1 * dx2 + dy1 * dy2;
    const curvature = Math.atan2(Math.abs(cross), dot);
    curvatures.push(curvature);
  }
  return curvatures;
};

export const getBoundingBox = (strokes: SignatureStroke[]): { minX: number; maxX: number; minY: number; maxY: number } => {
  if (strokes.length === 0) {
    return { minX: 0, maxX: 0, minY: 0, maxY: 0 };
  }

  let minX = Infinity;
  let maxX = -Infinity;
  let minY = Infinity;
  let maxY = -Infinity;

  strokes.forEach(stroke => {
    stroke.points.forEach(point => {
      minX = Math.min(minX, point.x);
      maxX = Math.max(maxX, point.x);
      minY = Math.min(minY, point.y);
      maxY = Math.max(maxY, point.y);
    });
  });

  return { minX, maxX, minY, maxY };
};

export const normalizePoints = (strokes: SignatureStroke[], targetWidth: number = 200, targetHeight: number = 100): SignatureStroke[] => {
  const bbox = getBoundingBox(strokes);
  const width = bbox.maxX - bbox.minX;
  const height = bbox.maxY - bbox.minY;

  if (width === 0 || height === 0) return strokes;

  const scaleX = targetWidth / width;
  const scaleY = targetHeight / height;
  const scale = Math.min(scaleX, scaleY);

  const offsetX = (targetWidth - width * scale) / 2 - bbox.minX * scale;
  const offsetY = (targetHeight - height * scale) / 2 - bbox.minY * scale;

  return strokes.map(stroke => ({
    ...stroke,
    points: stroke.points.map(point => ({
      ...point,
      x: point.x * scale + offsetX,
      y: point.y * scale + offsetY,
    })),
  }));
};

export const resamplePoints = (points: Point[], numSamples: number = 50): Point[] => {
  if (points.length < 2) return points;

  const totalDistance = points.reduce((sum, point, i) => {
    if (i === 0) return 0;
    const dx = point.x - points[i - 1].x;
    const dy = point.y - points[i - 1].y;
    return sum + Math.sqrt(dx * dx + dy * dy);
  }, 0);

  if (totalDistance === 0) return points;

  const interval = totalDistance / (numSamples - 1);
  const resampled: Point[] = [points[0]];
  let currentDistance = 0;

  for (let i = 1; i < points.length; i++) {
    const dx = points[i].x - points[i - 1].x;
    const dy = points[i].y - points[i - 1].y;
    const distance = Math.sqrt(dx * dx + dy * dy);

    if (currentDistance + distance >= interval) {
      const t = (interval - currentDistance) / distance;
      const newPoint: Point = {
        x: points[i - 1].x + t * dx,
        y: points[i - 1].y + t * dy,
        pressure: points[i - 1].pressure + t * (points[i].pressure - points[i - 1].pressure),
        time: points[i - 1].time + t * (points[i].time - points[i - 1].time),
      };
      resampled.push(newPoint);
      points.splice(i, 0, newPoint);
      currentDistance = 0;
    } else {
      currentDistance += distance;
    }
  }

  while (resampled.length < numSamples) {
    resampled.push(points[points.length - 1]);
  }

  return resampled.slice(0, numSamples);
};

export const calculateStrokeSimilarity = (stroke1: SignatureStroke, stroke2: SignatureStroke): number => {
  const points1 = resamplePoints(stroke1.points, 100);
  const points2 = resamplePoints(stroke2.points, 100);

  const dtwDist = dtwDistance(points1, points2, 15);
  const normalizedDtw = dtwDist / Math.max(points1.length, points2.length);
  const maxDtw = 50;
  const dtwSimilarity = Math.max(0, 1 - normalizedDtw / maxDtw);

  const features1 = extractStrokeFeatures(stroke1);
  const features2 = extractStrokeFeatures(stroke2);

  const lengthDiff = Math.abs(features1.totalLength - features2.totalLength);
  const maxLength = Math.max(features1.totalLength, features2.totalLength, 1);
  const lengthSimilarity = Math.max(0, 1 - lengthDiff / maxLength);

  const directionDiff = Math.abs(features1.directionChanges - features2.directionChanges);
  const maxDirection = Math.max(features1.directionChanges, features2.directionChanges, 1);
  const directionSimilarity = Math.max(0, 1 - directionDiff / maxDirection);

  const maxSpeedVar = Math.max(features1.speedVariance, features2.speedVariance, 1);
  const speedVarDiff = Math.abs(features1.speedVariance - features2.speedVariance);
  const speedSimilarity = Math.max(0, 1 - speedVarDiff / maxSpeedVar);

  const curvature1 = calculateCurvature(stroke1.points);
  const curvature2 = calculateCurvature(stroke2.points);
  let curvatureSimilarity = 0.5;

  if (curvature1.length > 0 && curvature2.length > 0) {
    const avgCurv1 = curvature1.reduce((a, b) => a + b, 0) / curvature1.length;
    const avgCurv2 = curvature2.reduce((a, b) => a + b, 0) / curvature2.length;
    const maxCurv = Math.max(avgCurv1, avgCurv2, 0.1);
    curvatureSimilarity = Math.max(0, 1 - Math.abs(avgCurv1 - avgCurv2) / maxCurv);
  }

  const similarity =
    dtwSimilarity * 0.45 +
    lengthSimilarity * 0.2 +
    directionSimilarity * 0.15 +
    speedSimilarity * 0.1 +
    curvatureSimilarity * 0.1;

  return similarity;
};

export const calculateBBoxSimilarity = (strokes1: SignatureStroke[], strokes2: SignatureStroke[]): number => {
  const bbox1 = getBoundingBox(strokes1);
  const bbox2 = getBoundingBox(strokes2);

  const width1 = bbox1.maxX - bbox1.minX;
  const height1 = bbox1.maxY - bbox1.minY;
  const width2 = bbox2.maxX - bbox2.minX;
  const height2 = bbox2.maxY - bbox2.minY;

  if (width1 === 0 || height1 === 0 || width2 === 0 || height2 === 0) return 0;

  const widthRatio = Math.min(width1, width2) / Math.max(width1, width2);
  const heightRatio = Math.min(height1, height2) / Math.max(height1, height2);
  const aspectRatio1 = width1 / height1;
  const aspectRatio2 = width2 / height2;
  const aspectRatioSimilarity = Math.min(aspectRatio1, aspectRatio2) / Math.max(aspectRatio1, aspectRatio2);

  return (widthRatio + heightRatio + aspectRatioSimilarity) / 3;
};

export const detectForgery = (
  newSignature: SignatureStroke[],
  referenceSignature: SignatureStroke[]
): { isSuspicious: boolean; forgeryScore: number } => {
  let forgeryScore = 0;

  const strokeCountDiff = Math.abs(newSignature.length - referenceSignature.length);
  if (strokeCountDiff > 1) forgeryScore += 0.15 * strokeCountDiff;

  const totalPoints1 = newSignature.reduce((sum, s) => sum + s.points.length, 0);
  const totalPoints2 = referenceSignature.reduce((sum, s) => sum + s.points.length, 0);
  const pointRatio = Math.min(totalPoints1, totalPoints2) / Math.max(totalPoints1, totalPoints2);
  if (pointRatio < 0.5) forgeryScore += 0.2;

  const avgPressure1 =
    newSignature.reduce((sum, s) => sum + s.points.reduce((ps, p) => ps + (p.pressure || 0.5), 0), 0) /
    Math.max(totalPoints1, 1);
  const avgPressure2 =
    referenceSignature.reduce((sum, s) => sum + s.points.reduce((ps, p) => ps + (p.pressure || 0.5), 0), 0) /
    Math.max(totalPoints2, 1);
  const pressureDiff = Math.abs(avgPressure1 - avgPressure2);
  if (pressureDiff > 0.3) forgeryScore += 0.15;

  let totalTime1 = 0;
  newSignature.forEach((s) => {
    if (s.points.length >= 2) {
      totalTime1 += s.points[s.points.length - 1].time - s.points[0].time;
    }
  });
  let totalTime2 = 0;
  referenceSignature.forEach((s) => {
    if (s.points.length >= 2) {
      totalTime2 += s.points[s.points.length - 1].time - s.points[0].time;
    }
  });
  const timeRatio = Math.min(totalTime1, totalTime2) / Math.max(totalTime1, totalTime2, 1);
  if (timeRatio < 0.4 && totalTime1 > 0 && totalTime2 > 0) forgeryScore += 0.2;

  return {
    isSuspicious: forgeryScore > 0.3,
    forgeryScore,
  };
};

export const verifySignature = (
  newSignature: SignatureStroke[],
  referenceSignature: SignatureStroke[],
  threshold: number = 0.75
): SignatureVerificationResult => {
  const normalized1 = normalizePoints(newSignature);
  const normalized2 = normalizePoints(referenceSignature);

  const strokeCountMatch = normalized1.length === normalized2.length;

  const strokeSimilarities: number[] = [];
  const minStrokes = Math.min(normalized1.length, normalized2.length);

  for (let i = 0; i < minStrokes; i++) {
    const similarity = calculateStrokeSimilarity(normalized1[i], normalized2[i]);
    strokeSimilarities.push(similarity);
  }

  const averageSimilarity =
    strokeSimilarities.length > 0
      ? strokeSimilarities.reduce((a, b) => a + b, 0) / strokeSimilarities.length
      : 0;

  const minSimilarity =
    strokeSimilarities.length > 0 ? Math.min(...strokeSimilarities) : 0;

  const bboxSimilarity = calculateBBoxSimilarity(normalized1, normalized2);

  const forgery = detectForgery(newSignature, referenceSignature);

  const strokeCountPenalty = strokeCountMatch ? 1 : 0.7;
  const forgeryPenalty = Math.max(0, 1 - forgery.forgeryScore * 1.5);

  let overallSimilarity =
    (averageSimilarity * 0.5 + minSimilarity * 0.15 + bboxSimilarity * 0.35) *
    strokeCountPenalty *
    forgeryPenalty;

  overallSimilarity = Math.max(0, Math.min(1, overallSimilarity));

  const verified = overallSimilarity >= threshold && !forgery.isSuspicious;

  return {
    isVerified: verified,
    similarity: overallSimilarity,
    details: {
      strokeCountMatch,
      averageSimilarity,
      boundingBoxSimilarity: bboxSimilarity,
    },
  };
};

export const exportToPNG = (canvas: HTMLCanvasElement): string => {
  return canvas.toDataURL('image/png');
};

export const exportToSVG = (strokes: SignatureStroke[], width: number, height: number): string => {
  const svgContent = `
    <svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">
      <rect width="100%" height="100%" fill="white"/>
      ${strokes.map(stroke => {
        if (stroke.points.length < 2) return '';
        const pathData = stroke.points.reduce((path, point, i) => {
          return path + (i === 0 ? `M ${point.x} ${point.y}` : ` L ${point.x} ${point.y}`);
        }, '');
        return `<path d="${pathData}" fill="none" stroke="${stroke.color}" stroke-width="${stroke.width}" stroke-linecap="round" stroke-linejoin="round"/>`;
      }).join('')}
    </svg>
  `;
  return svgContent;
};

export const downloadFile = (content: string, filename: string, mimeType: string): void => {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
};
