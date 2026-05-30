import type { ImageFormat, SmartSuggestion } from '../types';

const FORMAT_COMPRESSION_RATIOS: Record<ImageFormat, Record<ImageFormat, number>> = {
  jpeg: { jpeg: 1.0, png: 1.5, webp: 0.75 },
  png: { jpeg: 0.35, png: 1.0, webp: 0.45 },
  webp: { jpeg: 1.0, png: 1.3, webp: 0.85 }
};

const COMPLEXITY_QUALITY_MAP = {
  low: { quality: 70, ratio: 0.25 },
  medium: { quality: 80, ratio: 0.45 },
  high: { quality: 85, ratio: 0.60 }
};

export function analyzeImageComplexity(
  canvas: HTMLCanvasElement,
  ctx: CanvasRenderingContext2D
): { hasAlpha: boolean; colorComplexity: 'low' | 'medium' | 'high' } {
  const { width, height } = canvas;
  const sampleSize = Math.min(width, height, 200);
  const sx = Math.floor((width - sampleSize) / 2);
  const sy = Math.floor((height - sampleSize) / 2);
  const imageData = ctx.getImageData(sx, sy, sampleSize, sampleSize);
  const data = imageData.data;

  let hasAlpha = false;
  let totalColorVariance = 0;
  const pixelCount = sampleSize * sampleSize;
  const step = Math.max(1, Math.floor(pixelCount / 500));

  let prevR = 0, prevG = 0, prevB = 0;
  let varianceSamples = 0;

  for (let i = 0; i < data.length; i += step * 4) {
    const a = data[i + 3];
    if (a < 250) {
      hasAlpha = true;
    }

    const r = data[i];
    const g = data[i + 1];
    const b = data[i + 2];

    if (varianceSamples > 0) {
      const diff = Math.abs(r - prevR) + Math.abs(g - prevG) + Math.abs(b - prevB);
      totalColorVariance += diff;
    }
    prevR = r;
    prevG = g;
    prevB = b;
    varianceSamples++;
  }

  const avgVariance = totalColorVariance / Math.max(1, varianceSamples - 1);

  let colorComplexity: 'low' | 'medium' | 'high';
  if (avgVariance < 30) {
    colorComplexity = 'low';
  } else if (avgVariance < 80) {
    colorComplexity = 'medium';
  } else {
    colorComplexity = 'high';
  }

  return { hasAlpha, colorComplexity };
}

export function generateSmartSuggestion(
  originalFormat: ImageFormat,
  originalSize: number,
  width: number,
  height: number,
  hasAlpha: boolean,
  colorComplexity: 'low' | 'medium' | 'high'
): SmartSuggestion {
  const pixelCount = width * height;
  const bytesPerPixel = originalSize / Math.max(1, pixelCount);
  const isLargeImage = pixelCount > 2000000;
  const isPhoto = bytesPerPixel > 0.5;

  let bestFormat: ImageFormat;
  let bestQuality: number;
  let reason: string;
  let estimatedRatio: number;

  if (hasAlpha) {
    if (isLargeImage && isPhoto) {
      bestFormat = 'webp';
      bestQuality = colorComplexity === 'high' ? 85 : 75;
      reason = '含透明通道的大图，WebP 透明度压缩优于 PNG，画质损失极小';
      estimatedRatio = 0.35 + (colorComplexity === 'high' ? 0.15 : 0);
    } else if (colorComplexity === 'low') {
      bestFormat = 'png';
      bestQuality = 90;
      reason = '含透明通道且色彩简单的图标/图形，PNG 无损更优';
      estimatedRatio = 0.7;
    } else {
      bestFormat = 'webp';
      bestQuality = 80;
      reason = '含透明通道的图片，WebP 提供更好的透明度压缩率';
      estimatedRatio = 0.4;
    }
  } else if (isPhoto) {
    if (colorComplexity === 'high') {
      bestFormat = 'webp';
      bestQuality = 85;
      reason = '高复杂度照片，WebP 在保持画质同时压缩率显著优于 JPEG';
      estimatedRatio = 0.4;
    } else if (colorComplexity === 'medium') {
      bestFormat = 'webp';
      bestQuality = 80;
      reason = '中等复杂度照片，WebP 比 JPEG 同画质体积更小';
      estimatedRatio = 0.35;
    } else {
      bestFormat = 'jpeg';
      bestQuality = 75;
      reason = '低复杂度照片，JPEG 高压缩比效果最佳';
      estimatedRatio = 0.2;
    }
  } else {
    if (colorComplexity === 'low') {
      bestFormat = 'png';
      bestQuality = 90;
      reason = '色彩简单的图形/截图，PNG 无损压缩更高效';
      estimatedRatio = 0.6;
    } else {
      bestFormat = 'webp';
      bestQuality = 80;
      reason = '中等复杂度图形，WebP 兼顾画质与体积';
      estimatedRatio = 0.4;
    }
  }

  if (originalFormat === 'png' && !hasAlpha && isPhoto) {
    bestFormat = 'webp';
    reason = 'PNG 照片无透明通道，转为 WebP 可大幅缩小体积';
    estimatedRatio = 0.3;
  }

  return {
    format: bestFormat,
    quality: bestQuality,
    reason,
    estimatedRatio
  };
}

export function estimateCompressedSize(
  originalSize: number,
  originalFormat: ImageFormat,
  targetFormat: ImageFormat,
  quality: number,
  hasAlpha: boolean,
  colorComplexity: 'low' | 'medium' | 'high'
): number {
  const formatRatio = FORMAT_COMPRESSION_RATIOS[originalFormat]?.[targetFormat] ?? 1.0;
  const qualityFactor = quality / 100;
  const complexityFactor = COMPLEXITY_QUALITY_MAP[colorComplexity].ratio;
  const alphaPenalty = hasAlpha && targetFormat === 'jpeg' ? 1.3 : 1.0;

  const estimatedRatio = formatRatio * (0.3 + qualityFactor * 0.7) * complexityFactor * alphaPenalty;

  return Math.round(originalSize * Math.max(0.05, Math.min(1.5, estimatedRatio)));
}

export function detectImageFormat(file: File): ImageFormat {
  const type = file.type.toLowerCase();
  if (type.includes('jpeg') || type.includes('jpg')) return 'jpeg';
  if (type.includes('png')) return 'png';
  if (type.includes('webp')) return 'webp';
  const ext = file.name.split('.').pop()?.toLowerCase() ?? '';
  if (ext === 'jpg' || ext === 'jpeg') return 'jpeg';
  if (ext === 'png') return 'png';
  if (ext === 'webp') return 'webp';
  return 'jpeg';
}

export function analyzeImageFromFile(
  file: File,
  imageUrl: string
): Promise<{ hasAlpha: boolean; colorComplexity: 'low' | 'medium' | 'high'; width: number; height: number }> {
  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => {
      try {
        const canvas = document.createElement('canvas');
        const maxSampleDim = 300;
        const scale = Math.min(1, maxSampleDim / Math.max(img.width, img.height));
        canvas.width = Math.round(img.width * scale);
        canvas.height = Math.round(img.height * scale);
        const ctx = canvas.getContext('2d', { willReadFrequently: true });
        if (!ctx) {
          resolve({ hasAlpha: false, colorComplexity: 'medium', width: img.width, height: img.height });
          return;
        }
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
        const result = analyzeImageComplexity(canvas, ctx);
        resolve({ ...result, width: img.width, height: img.height });
      } catch {
        resolve({ hasAlpha: false, colorComplexity: 'medium', width: img.width, height: img.height });
      }
    };
    img.onerror = () => {
      resolve({ hasAlpha: false, colorComplexity: 'medium', width: 0, height: 0 });
    };
    img.src = imageUrl;
  });
}
