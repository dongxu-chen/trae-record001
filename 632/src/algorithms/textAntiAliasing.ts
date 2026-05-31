import { getPixel, setPixel, clamp, DirectionalEdgeData, sobelDirectionalEdgeDetection } from './utils';

export interface TextDetectionResult {
  isText: boolean;
  confidence: number;
  textMask: Uint8ClampedArray;
  strokeWidth: Float32Array;
  horizontalRatio: number;
  verticalRatio: number;
  contrast: number;
}

export interface SubpixelLayout {
  r: { dx: number; dy: number };
  g: { dx: number; dy: number };
  b: { dx: number; dy: number };
}

const SUBPIXEL_RGB: SubpixelLayout = {
  r: { dx: -1 / 3, dy: 0 },
  g: { dx: 0, dy: 0 },
  b: { dx: 1 / 3, dy: 0 }
};

const SUBPIXEL_BGR: SubpixelLayout = {
  r: { dx: 1 / 3, dy: 0 },
  g: { dx: 0, dy: 0 },
  b: { dx: -1 / 3, dy: 0 }
};

export function detectTextRegions(
  imageData: ImageData,
  progressCallback?: (progress: number) => void
): TextDetectionResult {
  const { width, height, data } = imageData;
  const total = width * height;
  const textMask = new Uint8ClampedArray(total);
  const strokeWidth = new Float32Array(total);

  const edgeData = sobelDirectionalEdgeDetection(imageData, 30, (p) => {
    if (progressCallback) progressCallback(p * 0.3);
  });

  const { magnitude, angle, mask } = edgeData;

  let textPixels = 0;
  let horizontalEdges = 0;
  let verticalEdges = 0;
  let totalContrast = 0;
  let contrastSamples = 0;

  for (let y = 2; y < height - 2; y++) {
    for (let x = 2; x < width - 2; x++) {
      const idx = y * width + x;

      if (mask[idx] === 0) continue;

      const edgeAngle = angle[idx];
      const edgeMag = magnitude[idx];

      const isHorizontal = Math.abs(Math.sin(edgeAngle)) > 0.7;
      const isVertical = Math.abs(Math.cos(edgeAngle)) > 0.7;

      if (isHorizontal) horizontalEdges++;
      if (isVertical) verticalEdges++;

      const stroke = estimateStrokeWidth(imageData, x, y, edgeAngle);
      strokeWidth[idx] = stroke;

      const isThinStroke = stroke >= 0.5 && stroke <= 4;
      const isHighContrast = edgeMag > 80;
      const isOrthogonal = isHorizontal || isVertical;

      const localContrast = calculateLocalContrast(imageData, x, y);
      totalContrast += localContrast;
      contrastSamples++;

      if (isThinStroke && isHighContrast && isOrthogonal && localContrast > 50) {
        textMask[idx] = 255;
        textPixels++;
      }

      if (progressCallback && (y * width + x) % 2000 === 0) {
        progressCallback(0.3 + ((y * width + x) / total) * 0.7);
      }
    }
  }

  const edgePixels = mask.filter(v => v > 0).length;
  const textConfidence = edgePixels > 0 ? textPixels / edgePixels : 0;
  const isText = textConfidence > 0.25;

  const totalEdges = horizontalEdges + verticalEdges || 1;
  const horizontalRatio = horizontalEdges / totalEdges;
  const verticalRatio = verticalEdges / totalEdges;
  const avgContrast = contrastSamples > 0 ? totalContrast / contrastSamples : 0;

  if (progressCallback) progressCallback(1.0);

  return {
    isText,
    confidence: textConfidence,
    textMask,
    strokeWidth,
    horizontalRatio,
    verticalRatio,
    contrast: avgContrast
  };
}

function estimateStrokeWidth(
  imageData: ImageData,
  x: number,
  y: number,
  edgeAngle: number
): number {
  const perpAngle = edgeAngle + Math.PI / 2;
  const dx = Math.cos(perpAngle);
  const dy = Math.sin(perpAngle);

  const grayCenter = getGray(imageData, x, y);
  let minDist = Infinity;

  for (let step = 1; step <= 10; step++) {
    const posX = x + dx * step;
    const posY = y + dy * step;
    const negX = x - dx * step;
    const negY = y - dy * step;

    const grayPos = getGray(imageData, Math.round(posX), Math.round(posY));
    const grayNeg = getGray(imageData, Math.round(negX), Math.round(negY));

    const diffPos = Math.abs(grayPos - grayCenter);
    const diffNeg = Math.abs(grayNeg - grayCenter);

    if (diffPos < 20) {
      minDist = Math.min(minDist, step * 2);
      break;
    }
    if (diffNeg < 20) {
      minDist = Math.min(minDist, step * 2);
      break;
    }
  }

  return minDist === Infinity ? 0 : minDist;
}

function calculateLocalContrast(imageData: ImageData, x: number, y: number): number {
  let maxVal = 0;
  let minVal = 255;

  for (let ky = -2; ky <= 2; ky++) {
    for (let kx = -2; kx <= 2; kx++) {
      const gray = getGray(imageData, x + kx, y + ky);
      maxVal = Math.max(maxVal, gray);
      minVal = Math.min(minVal, gray);
    }
  }

  return maxVal - minVal;
}

function getGray(imageData: ImageData, x: number, y: number): number {
  const pixel = getPixel(imageData, x, y);
  return 0.299 * pixel[0] + 0.587 * pixel[1] + 0.114 * pixel[2];
}

export function textAntiAliasing(
  imageData: ImageData,
  textDetection: TextDetectionResult,
  intensity: number,
  sharpness: number,
  subpixelLayout: SubpixelLayout = SUBPIXEL_RGB,
  progressCallback?: (progress: number) => void
): ImageData {
  const { width, height } = imageData;
  const result = new ImageData(width, height);
  const { textMask, strokeWidth } = textDetection;
  const intensityFactor = intensity / 100;
  const sharpnessFactor = sharpness / 100;

  const edgeData = sobelDirectionalEdgeDetection(imageData, 20, (p) => {
    if (progressCallback) progressCallback(p * 0.2);
  });

  const total = width * height;
  for (let i = 0; i < total; i++) {
    const idx = i * 4;
    result.data[idx] = imageData.data[idx];
    result.data[idx + 1] = imageData.data[idx + 1];
    result.data[idx + 2] = imageData.data[idx + 2];
    result.data[idx + 3] = imageData.data[idx + 3];
  }

  for (let y = 2; y < height - 2; y++) {
    for (let x = 2; x < width - 2; x++) {
      const idx = y * width + x;

      if (textMask[idx] === 0) continue;

      const edgeValue = edgeData.mask[idx] / 255;
      const stroke = strokeWidth[idx];

      if (edgeValue < 0.1) continue;

      const subpixelResult = applySubpixelRendering(
        imageData, x, y, edgeData.angle[idx], subpixelLayout
      );

      const originalPixel = getPixel(imageData, x, y);

      const blendFactor = clamp(
        edgeValue * intensityFactor * (1 + 0.5 * sharpnessFactor),
        0,
        0.9
      );

      const strokeAdjust = stroke < 2 ? 0.7 : 1.0;
      const finalBlend = blendFactor * strokeAdjust;

      const finalR = Math.round(clamp(
        originalPixel[0] * (1 - finalBlend) + subpixelResult[0] * finalBlend,
        0, 255
      ));
      const finalG = Math.round(clamp(
        originalPixel[1] * (1 - finalBlend) + subpixelResult[1] * finalBlend,
        0, 255
      ));
      const finalB = Math.round(clamp(
        originalPixel[2] * (1 - finalBlend) + subpixelResult[2] * finalBlend,
        0, 255
      ));

      setPixel(result, x, y, finalR, finalG, finalB, originalPixel[3]);

      if (progressCallback && (y * width + x) % 2000 === 0) {
        progressCallback(0.2 + ((y * width + x) / total) * 0.8);
      }
    }
  }

  if (progressCallback) progressCallback(1.0);

  return result;
}

function applySubpixelRendering(
  imageData: ImageData,
  x: number,
  y: number,
  edgeAngle: number,
  layout: SubpixelLayout
): [number, number, number, number] {
  const perpAngle = edgeAngle + Math.PI / 2;
  const isHorizontalEdge = Math.abs(Math.sin(edgeAngle)) > 0.5;

  if (isHorizontalEdge) {
    return subpixelHorizontal(imageData, x, y, perpAngle, layout);
  } else {
    return subpixelVertical(imageData, x, y, perpAngle, layout);
  }
}

function subpixelHorizontal(
  imageData: ImageData,
  x: number,
  y: number,
  perpAngle: number,
  layout: SubpixelLayout
): [number, number, number, number] {
  const samples = 3;
  const half = 1.5;

  let r = 0, g = 0, b = 0, a = 0;
  let weightSum = 0;

  for (let i = 0; i < samples; i++) {
    const t = (i - half) / half;
    const baseX = x + Math.cos(perpAngle) * t;
    const baseY = y + Math.sin(perpAngle) * t;

    const rPx = getPixelBilinear(imageData, baseX + layout.r.dx, baseY + layout.r.dy);
    const gPx = getPixelBilinear(imageData, baseX + layout.g.dx, baseY + layout.g.dy);
    const bPx = getPixelBilinear(imageData, baseX + layout.b.dx, baseY + layout.b.dy);

    const weight = Math.exp(-t * t * 2);

    r += rPx[0] * weight;
    g += gPx[1] * weight;
    b += bPx[2] * weight;
    a += rPx[3] * weight;
    weightSum += weight;
  }

  if (weightSum > 0) {
    return [
      r / weightSum,
      g / weightSum,
      b / weightSum,
      a / weightSum
    ];
  }

  return getPixelBilinear(imageData, x, y);
}

function subpixelVertical(
  imageData: ImageData,
  x: number,
  y: number,
  perpAngle: number,
  layout: SubpixelLayout
): [number, number, number, number] {
  const samples = 5;
  const half = 2;

  let r = 0, g = 0, b = 0, a = 0;
  let weightSum = 0;

  for (let i = 0; i < samples; i++) {
    const t = (i - half) / half;
    const baseX = x + Math.cos(perpAngle) * t;
    const baseY = y + Math.sin(perpAngle) * t;

    const pixel = getPixelBilinear(imageData, baseX, baseY);
    const weight = Math.exp(-t * t * 1.5);

    r += pixel[0] * weight;
    g += pixel[1] * weight;
    b += pixel[2] * weight;
    a += pixel[3] * weight;
    weightSum += weight;
  }

  if (weightSum > 0) {
    return [
      r / weightSum,
      g / weightSum,
      b / weightSum,
      a / weightSum
    ];
  }

  return getPixelBilinear(imageData, x, y);
}

function getPixelBilinear(
  imageData: ImageData,
  x: number,
  y: number
): [number, number, number, number] {
  const x0 = Math.floor(x);
  const y0 = Math.floor(y);
  const fx = x - x0;
  const fy = y - y0;

  const p00 = getPixel(imageData, x0, y0);
  const p10 = getPixel(imageData, x0 + 1, y0);
  const p01 = getPixel(imageData, x0, y0 + 1);
  const p11 = getPixel(imageData, x0 + 1, y0 + 1);

  const invFx = 1 - fx;
  const invFy = 1 - fy;

  return [
    p00[0] * invFx * invFy + p10[0] * fx * invFy + p01[0] * invFx * fy + p11[0] * fx * fy,
    p00[1] * invFx * invFy + p10[1] * fx * invFy + p01[1] * invFx * fy + p11[1] * fx * fy,
    p00[2] * invFx * invFy + p10[2] * fx * invFy + p01[2] * invFx * fy + p11[2] * fx * fy,
    p00[3] * invFx * invFy + p10[3] * fx * invFy + p01[3] * invFx * fy + p11[3] * fx * fy
  ];
}

export { SUBPIXEL_RGB, SUBPIXEL_BGR };
