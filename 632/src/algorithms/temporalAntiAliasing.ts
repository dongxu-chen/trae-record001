import { getPixel, setPixel, clamp, sobelEdgeDetection } from './utils';

export interface FrameHistory {
  frames: ImageData[];
  maxFrames: number;
  motionVectors: Map<string, { dx: number; dy: number }>;
}

export interface TemporalAASettings {
  enabled: boolean;
  frameHistorySize: number;
  motionBlendFactor: number;
  staticBlendFactor: number;
  useClipping: boolean;
  jitterAmount: number;
}

export const DEFAULT_TEMPORAL_SETTINGS: TemporalAASettings = {
  enabled: true,
  frameHistorySize: 5,
  motionBlendFactor: 0.3,
  staticBlendFactor: 0.1,
  useClipping: true,
  jitterAmount: 0.5
};

export function createFrameHistory(maxFrames: number = 5): FrameHistory {
  return {
    frames: [],
    maxFrames,
    motionVectors: new Map()
  };
}

export function addFrame(history: FrameHistory, frame: ImageData): void {
  history.frames.push(frame);
  if (history.frames.length > history.maxFrames) {
    history.frames.shift();
  }

  if (history.frames.length >= 2) {
    const prevFrame = history.frames[history.frames.length - 2];
    const newVectors = estimateMotionVectors(prevFrame, frame);
    history.motionVectors = newVectors;
  }
}

function estimateMotionVectors(
  prevFrame: ImageData,
  currFrame: ImageData,
  blockSize: number = 8,
  searchRadius: number = 4
): Map<string, { dx: number; dy: number }> {
  const vectors = new Map<string, { dx: number; dy: number }>();
  const { width, height } = currFrame;

  for (let by = 0; by < height; by += blockSize) {
    for (let bx = 0; bx < width; bx += blockSize) {
      let bestDx = 0;
      let bestDy = 0;
      let bestSad = Infinity;

      for (let dy = -searchRadius; dy <= searchRadius; dy++) {
        for (let dx = -searchRadius; dx <= searchRadius; dx++) {
          const sad = computeSAD(
            prevFrame, currFrame,
            bx, by,
            bx + dx, by + dy,
            blockSize
          );

          if (sad < bestSad) {
            bestSad = sad;
            bestDx = dx;
            bestDy = dy;
          }
        }
      }

      const key = `${bx},${by}`;
      vectors.set(key, { dx: bestDx, dy: bestDy });
    }
  }

  return vectors;
}

function computeSAD(
  frameA: ImageData,
  frameB: ImageData,
  ax: number, ay: number,
  bx: number, by: number,
  blockSize: number
): number {
  let sad = 0;
  const { width, height } = frameA;

  for (let dy = 0; dy < blockSize; dy++) {
    for (let dx = 0; dx < blockSize; dx++) {
      const apx = ax + dx;
      const apy = ay + dy;
      const bpx = bx + dx;
      const bpy = by + dy;

      if (apx < 0 || apx >= width || apy < 0 || apy >= height) continue;
      if (bpx < 0 || bpx >= width || bpy < 0 || bpy >= height) continue;

      const aPixel = getPixel(frameA, apx, apy);
      const bPixel = getPixel(frameB, bpx, bpy);

      sad += Math.abs(aPixel[0] - bPixel[0]) +
             Math.abs(aPixel[1] - bPixel[1]) +
             Math.abs(aPixel[2] - bPixel[2]);
    }
  }

  return sad;
}

export function temporalAntiAliasing(
  currentFrame: ImageData,
  history: FrameHistory,
  settings: TemporalAASettings,
  edgeMask?: Uint8ClampedArray,
  progressCallback?: (progress: number) => void
): ImageData {
  const { width, height } = currentFrame;
  const result = new ImageData(width, height);
  const total = width * height;

  if (history.frames.length < 2) {
    for (let i = 0; i < total * 4; i++) {
      result.data[i] = currentFrame.data[i];
    }
    return result;
  }

  if (!edgeMask) {
    edgeMask = sobelEdgeDetection(currentFrame, 30);
    if (progressCallback) progressCallback(0.2);
  }

  const prevFrame = history.frames[history.frames.length - 2];
  const motionThreshold = 15;

  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      const idx = y * width + x;
      const pixelIdx = idx * 4;
      const isEdge = edgeMask[idx] > 0;

      const blockKey = `${Math.floor(x / 8) * 8},${Math.floor(y / 8) * 8}`;
      const motion = history.motionVectors.get(blockKey);
      const hasMotion = motion && (Math.abs(motion.dx) + Math.abs(motion.dy)) > 1;

      let blendFactor: number;
      if (hasMotion) {
        blendFactor = settings.motionBlendFactor;
      } else {
        blendFactor = settings.staticBlendFactor;
      }

      if (isEdge) {
        blendFactor *= 0.5;
      }

      const currR = currentFrame.data[pixelIdx];
      const currG = currentFrame.data[pixelIdx + 1];
      const currB = currentFrame.data[pixelIdx + 2];
      const currA = currentFrame.data[pixelIdx + 3];

      let avgR = 0, avgG = 0, avgB = 0, avgA = 0;
      let weightSum = 0;

      for (let f = 0; f < history.frames.length; f++) {
        const histFrame = history.frames[f];
        const age = history.frames.length - 1 - f;
        const weight = Math.exp(-age * 0.5);

        let hx = x;
        let hy = y;
        if (motion && age > 0) {
          hx = clamp(x - motion.dx * age, 0, width - 1);
          hy = clamp(y - motion.dy * age, 0, height - 1);
        }

        const histPixel = getPixel(histFrame, Math.round(hx), Math.round(hy));
        avgR += histPixel[0] * weight;
        avgG += histPixel[1] * weight;
        avgB += histPixel[2] * weight;
        avgA += histPixel[3] * weight;
        weightSum += weight;
      }

      if (weightSum > 0) {
        avgR /= weightSum;
        avgG /= weightSum;
        avgB /= weightSum;
        avgA /= weightSum;
      }

      let finalR = currR * (1 - blendFactor) + avgR * blendFactor;
      let finalG = currG * (1 - blendFactor) + avgG * blendFactor;
      let finalB = currB * (1 - blendFactor) + avgB * blendFactor;
      let finalA = currA * (1 - blendFactor) + avgA * blendFactor;

      if (settings.useClipping && history.frames.length >= 3) {
        const clipped = clipToNeighborhood(
          history.frames,
          x, y,
          currR, currG, currB,
          motion
        );
        finalR = clamp(finalR, clipped.minR, clipped.maxR);
        finalG = clamp(finalG, clipped.minG, clipped.maxG);
        finalB = clamp(finalB, clipped.minB, clipped.maxB);
      }

      result.data[pixelIdx] = Math.round(finalR);
      result.data[pixelIdx + 1] = Math.round(finalG);
      result.data[pixelIdx + 2] = Math.round(finalB);
      result.data[pixelIdx + 3] = Math.round(finalA);

      if (progressCallback && idx % 2000 === 0) {
        progressCallback(0.2 + (idx / total) * 0.8);
      }
    }
  }

  if (progressCallback) progressCallback(1.0);

  return result;
}

function clipToNeighborhood(
  frames: ImageData[],
  x: number, y: number,
  currR: number, currG: number, currB: number,
  motion?: { dx: number; dy: number }
): { minR: number; maxR: number; minG: number; maxG: number; minB: number; maxB: number } {
  let minR = currR, maxR = currR;
  let minG = currG, maxG = currG;
  let minB = currB, maxB = currB;

  const radius = 2;
  const recentFrames = frames.slice(-3);

  for (const frame of recentFrames) {
    for (let ky = -radius; ky <= radius; ky++) {
      for (let kx = -radius; kx <= radius; kx++) {
        let hx = x + kx;
        let hy = y + ky;
        if (motion) {
          hx -= motion.dx;
          hy -= motion.dy;
        }
        hx = Math.round(clamp(hx, 0, frame.width - 1));
        hy = Math.round(clamp(hy, 0, frame.height - 1));

        const pixel = getPixel(frame, hx, hy);
        minR = Math.min(minR, pixel[0]);
        maxR = Math.max(maxR, pixel[0]);
        minG = Math.min(minG, pixel[1]);
        maxG = Math.max(maxG, pixel[1]);
        minB = Math.min(minB, pixel[2]);
        maxB = Math.max(maxB, pixel[2]);
      }
    }
  }

  const padding = 5;
  return {
    minR: Math.max(0, minR - padding),
    maxR: Math.min(255, maxR + padding),
    minG: Math.max(0, minG - padding),
    maxG: Math.min(255, maxG + padding),
    minB: Math.max(0, minB - padding),
    maxB: Math.min(255, maxB + padding)
  };
}

export function animateJitteredSampling(
  imageData: ImageData,
  jitterSequence: number[],
  frameIndex: number
): ImageData {
  const jitterX = jitterSequence[(frameIndex * 2) % jitterSequence.length];
  const jitterY = jitterSequence[(frameIndex * 2 + 1) % jitterSequence.length];

  const { width, height } = imageData;
  const result = new ImageData(width, height);

  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      const idx = (y * width + x) * 4;

      const srcX = x + jitterX;
      const srcY = y + jitterY;

      const x0 = Math.floor(srcX);
      const y0 = Math.floor(srcY);
      const fx = srcX - x0;
      const fy = srcY - y0;

      const p00 = getPixel(imageData, x0, y0);
      const p10 = getPixel(imageData, x0 + 1, y0);
      const p01 = getPixel(imageData, x0, y0 + 1);
      const p11 = getPixel(imageData, x0 + 1, y0 + 1);

      const invFx = 1 - fx;
      const invFy = 1 - fy;

      result.data[idx] = Math.round(
        p00[0] * invFx * invFy + p10[0] * fx * invFy + p01[0] * invFx * fy + p11[0] * fx * fy
      );
      result.data[idx + 1] = Math.round(
        p00[1] * invFx * invFy + p10[1] * fx * invFy + p01[1] * invFx * fy + p11[1] * fx * fy
      );
      result.data[idx + 2] = Math.round(
        p00[2] * invFx * invFy + p10[2] * fx * invFy + p01[2] * invFx * fy + p11[2] * fx * fy
      );
      result.data[idx + 3] = Math.round(
        p00[3] * invFx * invFy + p10[3] * fx * invFy + p01[3] * invFx * fy + p11[3] * fx * fy
      );
    }
  }

  return result;
}

export function generateHaltonSequence(length: number, base: number): number[] {
  const sequence: number[] = [];
  for (let i = 1; i <= length; i++) {
    let f = 1;
    let r = 0;
    let n = i;
    while (n > 0) {
      f /= base;
      r += f * (n % base);
      n = Math.floor(n / base);
    }
    sequence.push((r - 0.5) * 2);
  }
  return sequence;
}

export class VideoAntiAliasing {
  private frameHistory: FrameHistory;
  private settings: TemporalAASettings;
  private haltonSequence: number[];
  private frameCount: number;

  constructor(settings?: Partial<TemporalAASettings>) {
    this.settings = { ...DEFAULT_TEMPORAL_SETTINGS, ...settings };
    this.frameHistory = createFrameHistory(this.settings.frameHistorySize);
    this.haltonSequence = generateHaltonSequence(32, 2);
    this.frameCount = 0;
  }

  processFrame(
    frame: ImageData,
    edgeMask?: Uint8ClampedArray,
    progressCallback?: (progress: number) => void
  ): ImageData {
    this.frameCount++;

    if (!this.settings.enabled) {
      return frame;
    }

    const jittered = animateJitteredSampling(
      frame,
      this.haltonSequence,
      this.frameCount
    );

    addFrame(this.frameHistory, jittered);

    return temporalAntiAliasing(
      jittered,
      this.frameHistory,
      this.settings,
      edgeMask,
      progressCallback
    );
  }

  reset(): void {
    this.frameHistory.frames = [];
    this.frameHistory.motionVectors.clear();
    this.frameCount = 0;
  }

  updateSettings(settings: Partial<TemporalAASettings>): void {
    this.settings = { ...this.settings, ...settings };
    this.frameHistory.maxFrames = this.settings.frameHistorySize;
    while (this.frameHistory.frames.length > this.frameHistory.maxFrames) {
      this.frameHistory.frames.shift();
    }
  }

  getFrameCount(): number {
    return this.frameCount;
  }

  getHistoryLength(): number {
    return this.frameHistory.frames.length;
  }
}
