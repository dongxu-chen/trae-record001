import { FILTER_DEFINITIONS, FilterType } from './shaderManager';

export interface ImageAnalysis {
  avgBrightness: number;
  contrast: number;
  colorTemp: 'warm' | 'cool' | 'neutral';
  saturation: number;
  hasStrongHighlights: boolean;
  edgeDensity: number;
  dominantHue: number;
  colorVariance: number;
}

export interface FilterRecommendation {
  filterId: FilterType | string;
  filterName: string;
  score: number;
  reason: string;
  suggestedIntensity: number;
  suggestedParams: Record<string, number | number[]>;
}

const ANALYSIS_SIZE = 64;

export function analyzeImageContent(image: HTMLImageElement | HTMLCanvasElement): ImageAnalysis {
  const canvas = document.createElement('canvas');
  canvas.width = ANALYSIS_SIZE;
  canvas.height = ANALYSIS_SIZE;
  const ctx = canvas.getContext('2d');
  if (!ctx) {
    return {
      avgBrightness: 0.5,
      contrast: 0.5,
      colorTemp: 'neutral',
      saturation: 0.5,
      hasStrongHighlights: false,
      edgeDensity: 0,
      dominantHue: 0,
      colorVariance: 0,
    };
  }

  ctx.drawImage(image, 0, 0, ANALYSIS_SIZE, ANALYSIS_SIZE);
  const imageData = ctx.getImageData(0, 0, ANALYSIS_SIZE, ANALYSIS_SIZE);
  const data = imageData.data;
  const pixelCount = ANALYSIS_SIZE * ANALYSIS_SIZE;

  let totalR = 0, totalG = 0, totalB = 0;
  let totalBrightness = 0;
  let totalSaturation = 0;
  let minBrightness = 1;
  let maxBrightness = 0;
  let highlightCount = 0;
  let edgeSum = 0;
  let hueHist = new Float32Array(360);

  const brightnesses: number[] = [];

  for (let y = 0; y < ANALYSIS_SIZE; y++) {
    for (let x = 0; x < ANALYSIS_SIZE; x++) {
      const i = (y * ANALYSIS_SIZE + x) * 4;
      const r = data[i] / 255;
      const g = data[i + 1] / 255;
      const b = data[i + 2] / 255;

      totalR += r;
      totalG += g;
      totalB += b;

      const brightness = 0.299 * r + 0.587 * g + 0.114 * b;
      totalBrightness += brightness;
      brightnesses.push(brightness);

      if (brightness < minBrightness) minBrightness = brightness;
      if (brightness > maxBrightness) maxBrightness = brightness;

      if (brightness > 0.85) highlightCount++;

      const maxC = Math.max(r, g, b);
      const minC = Math.min(r, g, b);
      const sat = maxC > 0 ? (maxC - minC) / maxC : 0;
      totalSaturation += sat;

      if (maxC > 0.01 && maxC - minC > 0.01) {
        let hue = 0;
        if (maxC === r) {
          hue = 60 * ((g - b) / (maxC - minC));
        } else if (maxC === g) {
          hue = 60 * (2 + (b - r) / (maxC - minC));
        } else {
          hue = 60 * (4 + (r - g) / (maxC - minC));
        }
        if (hue < 0) hue += 360;
        hueHist[Math.floor(hue) % 360] += 1;
      }
    }
  }

  for (let y = 1; y < ANALYSIS_SIZE - 1; y++) {
    for (let x = 1; x < ANALYSIS_SIZE - 1; x++) {
      const idx = (y * ANALYSIS_SIZE + x) * 4;
      const c = 0.299 * data[idx] + 0.587 * data[idx + 1] + 0.114 * data[idx + 2];
      const l = 0.299 * data[(y * ANALYSIS_SIZE + x - 1) * 4] + 0.587 * data[(y * ANALYSIS_SIZE + x - 1) * 4 + 1] + 0.114 * data[(y * ANALYSIS_SIZE + x - 1) * 4 + 2];
      const r2 = 0.299 * data[(y * ANALYSIS_SIZE + x + 1) * 4] + 0.587 * data[(y * ANALYSIS_SIZE + x + 1) * 4 + 1] + 0.114 * data[(y * ANALYSIS_SIZE + x + 1) * 4 + 2];
      const u = 0.299 * data[((y - 1) * ANALYSIS_SIZE + x) * 4] + 0.587 * data[((y - 1) * ANALYSIS_SIZE + x) * 4 + 1] + 0.114 * data[((y - 1) * ANALYSIS_SIZE + x) * 4 + 2];
      const d = 0.299 * data[((y + 1) * ANALYSIS_SIZE + x) * 4] + 0.587 * data[((y + 1) * ANALYSIS_SIZE + x) * 4 + 1] + 0.114 * data[((y + 1) * ANALYSIS_SIZE + x) * 4 + 2];
      const gx = Math.abs(r2 - l);
      const gy = Math.abs(d - u);
      edgeSum += Math.sqrt(gx * gx + gy * gy);
    }
  }

  const avgBrightness = totalBrightness / pixelCount;
  const contrast = maxBrightness - minBrightness;
  const avgSaturation = totalSaturation / pixelCount;
  const edgeDensity = edgeSum / ((ANALYSIS_SIZE - 2) * (ANALYSIS_SIZE - 2));
  const hasStrongHighlights = highlightCount > pixelCount * 0.05;

  const avgR = totalR / pixelCount;
  const avgG = totalG / pixelCount;
  const avgB = totalB / pixelCount;
  let colorTemp: 'warm' | 'cool' | 'neutral';
  if (avgR > avgB * 1.2) colorTemp = 'warm';
  else if (avgB > avgR * 1.2) colorTemp = 'cool';
  else colorTemp = 'neutral';

  let maxHueCount = 0;
  let dominantHue = 0;
  for (let i = 0; i < 360; i++) {
    if (hueHist[i] > maxHueCount) {
      maxHueCount = hueHist[i];
      dominantHue = i;
    }
  }

  let varianceSum = 0;
  for (const b of brightnesses) {
    varianceSum += (b - avgBrightness) ** 2;
  }
  const colorVariance = Math.sqrt(varianceSum / pixelCount);

  return {
    avgBrightness,
    contrast,
    colorTemp,
    saturation: avgSaturation,
    hasStrongHighlights,
    edgeDensity: Math.min(edgeDensity / 255, 1),
    dominantHue,
    colorVariance,
  };
}

export function recommendFilters(analysis: ImageAnalysis): FilterRecommendation[] {
  const recommendations: FilterRecommendation[] = [];

  const dreamyScore = calculateDreamyScore(analysis);
  if (dreamyScore > 0.3) {
    recommendations.push({
      filterId: 'dreamy',
      filterName: '梦幻',
      score: dreamyScore,
      reason: getDreamyReason(analysis),
      suggestedIntensity: dreamyScore * 0.7 + 0.2,
      suggestedParams: {
        uBlurRadius: analysis.avgBrightness > 0.6 ? 0.3 : 0.6,
        uGlowColor: analysis.colorTemp === 'warm'
          ? [1.0, 0.85, 0.9]
          : analysis.colorTemp === 'cool'
          ? [0.8, 0.9, 1.0]
          : [1.0, 0.8, 0.95],
      },
    });
  }

  const backlightScore = calculateBacklightScore(analysis);
  if (backlightScore > 0.3) {
    recommendations.push({
      filterId: 'backlight',
      filterName: '逆光',
      score: backlightScore,
      reason: getBacklightReason(analysis),
      suggestedIntensity: backlightScore * 0.6 + 0.3,
      suggestedParams: {
        uLightPos: [0.5, 0.3],
        uFlareSize: analysis.hasStrongHighlights ? 0.8 : 0.5,
      },
    });
  }

  const neonScore = calculateNeonScore(analysis);
  if (neonScore > 0.3) {
    recommendations.push({
      filterId: 'neon',
      filterName: '霓虹',
      score: neonScore,
      reason: getNeonReason(analysis),
      suggestedIntensity: neonScore * 0.5 + 0.3,
      suggestedParams: {
        uGlowWidth: Math.max(1.0, analysis.edgeDensity * 5),
        uNeonColor: analysis.colorTemp === 'warm'
          ? [1.0, 0.4, 0.2]
          : analysis.colorTemp === 'cool'
          ? [0.0, 0.96, 0.83]
          : [0.5, 0.2, 1.0],
      },
    });
  }

  const starburstScore = calculateStarburstScore(analysis);
  if (starburstScore > 0.3) {
    recommendations.push({
      filterId: 'starburst',
      filterName: '星芒',
      score: starburstScore,
      reason: getStarburstReason(analysis),
      suggestedIntensity: starburstScore * 0.5 + 0.3,
      suggestedParams: {
        uRayCount: analysis.hasStrongHighlights ? 16 : 8,
        uRayLength: analysis.contrast > 0.6 ? 1.0 : 0.5,
      },
    });
  }

  recommendations.sort((a, b) => b.score - a.score);

  return recommendations.slice(0, 3);
}

function calculateDreamyScore(a: ImageAnalysis): number {
  let score = 0;
  if (a.avgBrightness > 0.4 && a.avgBrightness < 0.8) score += 0.3;
  if (a.saturation < 0.5) score += 0.2;
  if (a.contrast < 0.7) score += 0.2;
  if (a.colorTemp === 'warm') score += 0.15;
  if (a.colorVariance < 0.25) score += 0.15;
  return Math.min(score, 1);
}

function calculateBacklightScore(a: ImageAnalysis): number {
  let score = 0;
  if (a.hasStrongHighlights) score += 0.35;
  if (a.contrast > 0.5) score += 0.25;
  if (a.colorTemp === 'warm') score += 0.2;
  if (a.avgBrightness > 0.5) score += 0.1;
  if (a.colorVariance > 0.2) score += 0.1;
  return Math.min(score, 1);
}

function calculateNeonScore(a: ImageAnalysis): number {
  let score = 0;
  if (a.edgeDensity > 0.05) score += 0.3;
  if (a.saturation > 0.4) score += 0.2;
  if (a.contrast > 0.6) score += 0.2;
  if (a.colorTemp === 'cool') score += 0.15;
  if (a.avgBrightness < 0.6) score += 0.15;
  return Math.min(score, 1);
}

function calculateStarburstScore(a: ImageAnalysis): number {
  let score = 0;
  if (a.hasStrongHighlights) score += 0.4;
  if (a.contrast > 0.5) score += 0.2;
  if (a.avgBrightness > 0.45) score += 0.15;
  if (a.colorVariance > 0.15) score += 0.15;
  if (a.edgeDensity < 0.1) score += 0.1;
  return Math.min(score, 1);
}

function getDreamyReason(a: ImageAnalysis): string {
  const reasons: string[] = [];
  if (a.saturation < 0.5) reasons.push('低饱和度');
  if (a.contrast < 0.7) reasons.push('柔和对比');
  if (a.colorTemp === 'warm') reasons.push('暖色调');
  if (reasons.length === 0) reasons.push('柔和画面');
  return `${reasons.join('、')}适合梦幻效果`;
}

function getBacklightReason(a: ImageAnalysis): string {
  const reasons: string[] = [];
  if (a.hasStrongHighlights) reasons.push('强高光');
  if (a.contrast > 0.5) reasons.push('高对比度');
  if (a.colorTemp === 'warm') reasons.push('暖色调');
  if (reasons.length === 0) reasons.push('明暗对比');
  return `${reasons.join('、')}适合逆光效果`;
}

function getNeonReason(a: ImageAnalysis): string {
  const reasons: string[] = [];
  if (a.edgeDensity > 0.05) reasons.push('丰富边缘');
  if (a.saturation > 0.4) reasons.push('高饱和度');
  if (a.contrast > 0.6) reasons.push('强对比');
  if (reasons.length === 0) reasons.push('鲜明线条');
  return `${reasons.join('、')}适合霓虹效果`;
}

function getStarburstReason(a: ImageAnalysis): string {
  const reasons: string[] = [];
  if (a.hasStrongHighlights) reasons.push('点光源');
  if (a.contrast > 0.5) reasons.push('明暗对比强');
  if (a.avgBrightness > 0.45) reasons.push('亮度充足');
  if (reasons.length === 0) reasons.push('亮区明显');
  return `${reasons.join('、')}适合星芒效果`;
}
