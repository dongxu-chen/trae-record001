import { ContentType, ProcessingParams } from '../types';
import { detectTextRegions } from './textAntiAliasing';

export type ComplexityLevel = 'simple' | 'medium' | 'complex';

export interface ComplexityResult {
  level: ComplexityLevel;
  score: number;
  edgeDensity: number;
  colorVariance: number;
  detailLevel: number;
  dominantDirections: number[];
}

export function analyzeComplexity(imageData: ImageData): ComplexityResult {
  const { width, height, data } = imageData;
  const totalPixels = width * height;

  const edgeDensity = computeEdgeDensity(imageData);
  const colorVariance = computeColorVariance(imageData);
  const detailLevel = computeDetailLevel(imageData);
  const dominantDirections = computeDominantDirections(imageData);

  const normalizedEdge = edgeDensity;
  const normalizedColor = Math.min(colorVariance / 8000, 1);
  const normalizedDetail = detailLevel;

  const score = normalizedEdge * 0.4 + normalizedColor * 0.3 + normalizedDetail * 0.3;

  let level: ComplexityLevel;
  if (score < 0.3) {
    level = 'simple';
  } else if (score < 0.6) {
    level = 'medium';
  } else {
    level = 'complex';
  }

  return {
    level,
    score,
    edgeDensity,
    colorVariance,
    detailLevel,
    dominantDirections
  };
}

export function detectContentType(imageData: ImageData): {
  contentType: ContentType;
  textConfidence: number;
  isAnimated: boolean;
} {
  const textDetection = detectTextRegions(imageData);
  const complexity = analyzeComplexity(imageData);

  let contentType: ContentType = 'photo';
  let textConfidence = textDetection.confidence;
  let isAnimated = false;

  if (textConfidence > 0.4 && textDetection.contrast > 80) {
    contentType = 'text';
  } else if (complexity.colorVariance < 2000 && complexity.edgeDensity > 0.15) {
    contentType = 'illustration';
  } else if (imageData.width <= 512 && imageData.height <= 512 && complexity.detailLevel > 0.3) {
    isAnimated = true;
    contentType = 'video';
  }

  return {
    contentType,
    textConfidence,
    isAnimated
  };
}

export function getRecommendedParams(complexity: ComplexityResult): Partial<ProcessingParams> {
  switch (complexity.level) {
    case 'simple':
      return {
        algorithm: 'edaa',
        threshold: 40,
        intensity: 50,
        sampleRate: 2,
        kernelSize: 3,
        edgeBlur: 2,
        sharpness: 60,
        textOptimization: true,
        subpixelLayout: 'rgb',
        contentMode: 'photo',
        temporalAA: false,
        frameBlend: 20
      };
    case 'medium':
      return {
        algorithm: 'msaa',
        threshold: 50,
        intensity: 65,
        sampleRate: 4,
        kernelSize: 5,
        edgeBlur: 3,
        sharpness: 50,
        textOptimization: true,
        subpixelLayout: 'rgb',
        contentMode: 'photo',
        temporalAA: false,
        frameBlend: 30
      };
    case 'complex':
      return {
        algorithm: 'ssaa',
        threshold: 60,
        intensity: 80,
        sampleRate: 4,
        kernelSize: 5,
        edgeBlur: 4,
        sharpness: 40,
        textOptimization: true,
        subpixelLayout: 'rgb',
        contentMode: 'photo',
        temporalAA: false,
        frameBlend: 40
      };
  }
}

export function getParamsForContentType(
  contentType: ContentType,
  textConfidence: number = 0
): Partial<ProcessingParams> {
  switch (contentType) {
    case 'text':
      return {
        algorithm: 'edaa',
        threshold: 30,
        intensity: textConfidence > 0.6 ? 85 : 65,
        sampleRate: 2,
        kernelSize: 3,
        edgeBlur: 2,
        sharpness: 70,
        textOptimization: true,
        subpixelLayout: 'rgb',
        contentMode: 'text',
        temporalAA: false,
        frameBlend: 20
      };
    case 'illustration':
      return {
        algorithm: 'msaa',
        threshold: 45,
        intensity: 70,
        sampleRate: 4,
        kernelSize: 3,
        edgeBlur: 3,
        sharpness: 55,
        textOptimization: true,
        subpixelLayout: 'rgb',
        contentMode: 'illustration',
        temporalAA: false,
        frameBlend: 30
      };
    case 'video':
      return {
        algorithm: 'ssaa',
        threshold: 55,
        intensity: 60,
        sampleRate: 2,
        kernelSize: 5,
        edgeBlur: 2,
        sharpness: 50,
        textOptimization: false,
        subpixelLayout: 'none',
        contentMode: 'video',
        temporalAA: true,
        frameBlend: 50
      };
    case 'photo':
    default:
      return {
        algorithm: 'msaa',
        threshold: 50,
        intensity: 65,
        sampleRate: 2,
        kernelSize: 5,
        edgeBlur: 3,
        sharpness: 50,
        textOptimization: true,
        subpixelLayout: 'rgb',
        contentMode: 'photo',
        temporalAA: false,
        frameBlend: 30
      };
  }
}

function computeEdgeDensity(imageData: ImageData): number {
  const { width, height, data } = imageData;
  let edgeCount = 0;
  const total = (width - 2) * (height - 2);

  for (let y = 1; y < height - 1; y++) {
    for (let x = 1; x < width - 1; x++) {
      const idx = (y * width + x) * 4;
      const center = grayAt(data, idx);

      const right = grayAt(data, ((y * width) + x + 1) * 4);
      const below = grayAt(data, ((y + 1) * width + x) * 4);

      const dx = Math.abs(center - right);
      const dy = Math.abs(center - below);
      const gradient = Math.sqrt(dx * dx + dy * dy);

      if (gradient > 30) {
        edgeCount++;
      }
    }
  }

  return edgeCount / total;
}

function computeColorVariance(imageData: ImageData): number {
  const { data } = imageData;
  const pixelCount = data.length / 4;
  const sampleStep = Math.max(1, Math.floor(pixelCount / 10000));

  let sumR = 0, sumG = 0, sumB = 0;
  let count = 0;

  for (let i = 0; i < data.length; i += sampleStep * 4) {
    sumR += data[i];
    sumG += data[i + 1];
    sumB += data[i + 2];
    count++;
  }

  const avgR = sumR / count;
  const avgG = sumG / count;
  const avgB = sumB / count;

  let variance = 0;
  for (let i = 0; i < data.length; i += sampleStep * 4) {
    const dr = data[i] - avgR;
    const dg = data[i + 1] - avgG;
    const db = data[i + 2] - avgB;
    variance += dr * dr + dg * dg + db * db;
  }
  variance /= count;

  return variance;
}

function computeDetailLevel(imageData: ImageData): number {
  const { width, height, data } = imageData;
  let highFreqCount = 0;
  const total = (width - 4) * (height - 4);

  for (let y = 2; y < height - 2; y++) {
    for (let x = 2; x < width - 2; x++) {
      const idx = (y * width + x) * 4;
      const center = grayAt(data, idx);

      const neighbors = [
        grayAt(data, (y * width + x - 2) * 4),
        grayAt(data, (y * width + x + 2) * 4),
        grayAt(data, ((y - 2) * width + x) * 4),
        grayAt(data, ((y + 2) * width + x) * 4)
      ];

      const laplacian = Math.abs(
        4 * center - neighbors[0] - neighbors[1] - neighbors[2] - neighbors[3]
      );

      if (laplacian > 20) {
        highFreqCount++;
      }
    }
  }

  return highFreqCount / total;
}

function computeDominantDirections(imageData: ImageData): number[] {
  const { width, height, data } = imageData;
  const bins = 8;
  const histogram = new Float32Array(bins);

  for (let y = 1; y < height - 1; y += 2) {
    for (let x = 1; x < width - 1; x += 2) {
      const idx = (y * width + x) * 4;
      const center = grayAt(data, idx);

      const gx = grayAt(data, (y * width + x + 1) * 4) - grayAt(data, (y * width + x - 1) * 4);
      const gy = grayAt(data, ((y + 1) * width + x) * 4) - grayAt(data, ((y - 1) * width + x) * 4);

      const mag = Math.sqrt(gx * gx + gy * gy);
      if (mag < 20) continue;

      let angle = Math.atan2(gy, gx);
      if (angle < 0) angle += Math.PI;

      const bin = Math.floor((angle / Math.PI) * bins) % bins;
      histogram[bin] += mag;
    }
  }

  const totalMag = histogram.reduce((a, b) => a + b, 0);
  if (totalMag === 0) return [0, 1, 2, 3, 4, 5, 6, 7];

  const threshold = totalMag / bins * 1.5;
  const dominant: number[] = [];
  for (let i = 0; i < bins; i++) {
    if (histogram[i] > threshold) {
      dominant.push(i);
    }
  }

  return dominant.length > 0 ? dominant : [0];
}

function grayAt(data: Uint8ClampedArray, idx: number): number {
  return 0.299 * data[idx] + 0.587 * data[idx + 1] + 0.114 * data[idx + 2];
}

export interface BatchGroup {
  level: ComplexityLevel;
  images: Array<{
    id: string;
    name: string;
    complexity: ComplexityResult;
  }>;
  recommendedParams: ReturnType<typeof getRecommendedParams>;
  label: string;
  color: string;
}

export function groupByComplexity(
  images: Array<{ id: string; name: string; imageData: ImageData }>
): BatchGroup[] {
  const groups: Record<ComplexityLevel, BatchGroup> = {
    simple: {
      level: 'simple',
      images: [],
      recommendedParams: getRecommendedParams({ level: 'simple', score: 0, edgeDensity: 0, colorVariance: 0, detailLevel: 0, dominantDirections: [] }),
      label: '简单图像',
      color: 'green'
    },
    medium: {
      level: 'medium',
      images: [],
      recommendedParams: getRecommendedParams({ level: 'medium', score: 0, edgeDensity: 0, colorVariance: 0, detailLevel: 0, dominantDirections: [] }),
      label: '中等图像',
      color: 'yellow'
    },
    complex: {
      level: 'complex',
      images: [],
      recommendedParams: getRecommendedParams({ level: 'complex', score: 0, edgeDensity: 0, colorVariance: 0, detailLevel: 0, dominantDirections: [] }),
      label: '复杂图像',
      color: 'red'
    }
  };

  for (const img of images) {
    const complexity = analyzeComplexity(img.imageData);
    groups[complexity.level].images.push({
      id: img.id,
      name: img.name,
      complexity
    });
  }

  return [groups.simple, groups.medium, groups.complex].filter(g => g.images.length > 0);
}
