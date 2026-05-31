export function getPixel(imageData: ImageData, x: number, y: number): [number, number, number, number] {
  if (x < 0 || x >= imageData.width || y < 0 || y >= imageData.height) {
    return [0, 0, 0, 0];
  }
  const index = (y * imageData.width + x) * 4;
  return [
    imageData.data[index],
    imageData.data[index + 1],
    imageData.data[index + 2],
    imageData.data[index + 3]
  ];
}

export function setPixel(imageData: ImageData, x: number, y: number, r: number, g: number, b: number, a: number): void {
  const index = (y * imageData.width + x) * 4;
  imageData.data[index] = r;
  imageData.data[index + 1] = g;
  imageData.data[index + 2] = b;
  imageData.data[index + 3] = a;
}

export function bilinearInterpolate(
  imageData: ImageData,
  x: number,
  y: number
): [number, number, number, number] {
  const x0 = Math.floor(x);
  const y0 = Math.floor(y);
  const x1 = x0 + 1;
  const y1 = y0 + 1;
  const fx = x - x0;
  const fy = y - y0;

  const p00 = getPixel(imageData, x0, y0);
  const p10 = getPixel(imageData, x1, y0);
  const p01 = getPixel(imageData, x0, y1);
  const p11 = getPixel(imageData, x1, y1);

  const invFx = 1 - fx;
  const invFy = 1 - fy;

  return [
    Math.round(p00[0] * invFx * invFy + p10[0] * fx * invFy + p01[0] * invFx * fy + p11[0] * fx * fy),
    Math.round(p00[1] * invFx * invFy + p10[1] * fx * invFy + p01[1] * invFx * fy + p11[1] * fx * fy),
    Math.round(p00[2] * invFx * invFy + p10[2] * fx * invFy + p01[2] * invFx * fy + p11[2] * fx * fy),
    Math.round(p00[3] * invFx * invFy + p10[3] * fx * invFy + p01[3] * invFx * fy + p11[3] * fx * fy)
  ];
}

export function resizeImageData(
  imageData: ImageData,
  newWidth: number,
  newHeight: number
): ImageData {
  const result = new ImageData(newWidth, newHeight);
  const scaleX = imageData.width / newWidth;
  const scaleY = imageData.height / newHeight;

  for (let y = 0; y < newHeight; y++) {
    for (let x = 0; x < newWidth; x++) {
      const srcX = x * scaleX;
      const srcY = y * scaleY;
      const [r, g, b, a] = bilinearInterpolate(imageData, srcX, srcY);
      setPixel(result, x, y, r, g, b, a);
    }
  }

  return result;
}

export function createGaussianKernel(size: number, sigma: number): number[][] {
  const kernel: number[][] = [];
  const half = Math.floor(size / 2);
  let sum = 0;

  for (let y = -half; y <= half; y++) {
    const row: number[] = [];
    for (let x = -half; x <= half; x++) {
      const value = Math.exp(-(x * x + y * y) / (2 * sigma * sigma));
      row.push(value);
      sum += value;
    }
    kernel.push(row);
  }

  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      kernel[y][x] /= sum;
    }
  }

  return kernel;
}

export function applyConvolution(
  imageData: ImageData,
  kernel: number[][],
  progressCallback?: (progress: number) => void
): ImageData {
  const result = new ImageData(imageData.width, imageData.height);
  const kSize = kernel.length;
  const half = Math.floor(kSize / 2);
  const total = imageData.width * imageData.height;
  let processed = 0;

  for (let y = 0; y < imageData.height; y++) {
    for (let x = 0; x < imageData.width; x++) {
      let r = 0, g = 0, b = 0, a = 0;

      for (let ky = 0; ky < kSize; ky++) {
        for (let kx = 0; kx < kSize; kx++) {
          const px = x + kx - half;
          const py = y + ky - half;
          const pixel = getPixel(imageData, px, py);
          const weight = kernel[ky][kx];
          r += pixel[0] * weight;
          g += pixel[1] * weight;
          b += pixel[2] * weight;
          a += pixel[3] * weight;
        }
      }

      setPixel(result, x, y, Math.round(r), Math.round(g), Math.round(b), Math.round(a));

      processed++;
      if (progressCallback && processed % 1000 === 0) {
        progressCallback(processed / total);
      }
    }
  }

  return result;
}

export interface DirectionalEdgeData {
  magnitude: Float32Array;
  angle: Float32Array;
  mask: Uint8ClampedArray;
  width: number;
  height: number;
}

export function sobelEdgeDetection(
  imageData: ImageData,
  threshold: number,
  progressCallback?: (progress: number) => void
): Uint8ClampedArray {
  const result = sobelDirectionalEdgeDetection(imageData, threshold, progressCallback);
  return result.mask;
}

export function sobelDirectionalEdgeDetection(
  imageData: ImageData,
  threshold: number,
  progressCallback?: (progress: number) => void
): DirectionalEdgeData {
  const width = imageData.width;
  const height = imageData.height;
  const magnitude = new Float32Array(width * height);
  const angle = new Float32Array(width * height);
  const mask = new Uint8ClampedArray(width * height);

  const gxKernel = [-1, 0, 1, -2, 0, 2, -1, 0, 1];
  const gyKernel = [-1, -2, -1, 0, 0, 0, 1, 2, 1];

  const grayData = new Float32Array(width * height);
  for (let i = 0, j = 0; i < imageData.data.length; i += 4, j++) {
    grayData[j] = 0.299 * imageData.data[i] + 0.587 * imageData.data[i + 1] + 0.114 * imageData.data[i + 2];
  }

  const total = (width - 2) * (height - 2);
  let processed = 0;

  for (let y = 1; y < height - 1; y++) {
    for (let x = 1; x < width - 1; x++) {
      let gx = 0, gy = 0;

      for (let ky = -1; ky <= 1; ky++) {
        for (let kx = -1; kx <= 1; kx++) {
          const idx = (y + ky) * width + (x + kx);
          const kidx = (ky + 1) * 3 + (kx + 1);
          gx += grayData[idx] * gxKernel[kidx];
          gy += grayData[idx] * gyKernel[kidx];
        }
      }

      const mag = Math.sqrt(gx * gx + gy * gy);
      const pixelIdx = y * width + x;

      magnitude[pixelIdx] = mag;
      angle[pixelIdx] = Math.atan2(gy, gx);
      mask[pixelIdx] = mag > threshold ? 255 : 0;

      processed++;
      if (progressCallback && processed % 1000 === 0) {
        progressCallback(processed / total);
      }
    }
  }

  return { magnitude, angle, mask, width, height };
}

export function anisotropicBlur(
  imageData: ImageData,
  edgeData: DirectionalEdgeData,
  sigma: number,
  intensity: number,
  sharpness: number = 50,
  progressCallback?: (progress: number) => void
): ImageData {
  const { magnitude, angle, mask, width, height } = edgeData;
  const result = new ImageData(imageData.width, imageData.height);
  const intensityFactor = intensity / 100;
  const sharpnessFactor = sharpness / 100;
  const total = width * height;
  const maxBlurRadius = Math.ceil(sigma * 3);

  const blurScale = 1 - sharpnessFactor * 0.6;
  const tangentScale = 1 + sharpnessFactor * 0.4;

  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      const idx = y * width + x;
      const edgeValue = mask[idx] / 255;

      if (edgeValue < 0.01) {
        const srcIdx = idx * 4;
        result.data[srcIdx] = imageData.data[srcIdx];
        result.data[srcIdx + 1] = imageData.data[srcIdx + 1];
        result.data[srcIdx + 2] = imageData.data[srcIdx + 2];
        result.data[srcIdx + 3] = imageData.data[srcIdx + 3];
        continue;
      }

      const edgeAngle = angle[idx];
      const perpAngle = edgeAngle + Math.PI / 2;
      const edgeMag = Math.min(magnitude[idx] / 255, 1.0);

      const blurAlong = sigma * edgeMag * intensityFactor * blurScale * tangentScale;
      const blurAcross = sigma * 0.2 * edgeMag * intensityFactor * blurScale;

      let sumR = 0, sumG = 0, sumB = 0, sumA = 0;
      let weightSum = 0;

      const steps = Math.max(Math.ceil(maxBlurRadius * blurScale) * 2, 1);
      for (let s = -steps; s <= steps; s++) {
        const alongX = Math.cos(edgeAngle) * s * (blurAlong / Math.max(steps, 1));
        const alongY = Math.sin(edgeAngle) * s * (blurAlong / Math.max(steps, 1));

        const acrossSteps = sharpnessFactor > 0.7 ? 1 : 3;
        for (let t = -(acrossSteps - 1) / 2; t <= (acrossSteps - 1) / 2; t++) {
          const acrossX = Math.cos(perpAngle) * t * blurAcross;
          const acrossY = Math.sin(perpAngle) * t * blurAcross;

          const sampleX = x + alongX + acrossX;
          const sampleY = y + alongY + acrossY;

          const sx = Math.round(sampleX);
          const sy = Math.round(sampleY);

          if (sx >= 0 && sx < width && sy >= 0 && sy < height) {
            const dist2 = (alongX * alongX + alongY * alongY) / Math.max(blurAlong * blurAlong, 0.01) +
                         (acrossX * acrossX + acrossY * acrossY) / Math.max(blurAcross * blurAcross, 0.01);
            const sharpnessWeight = 1 - sharpnessFactor * 0.5 * Math.min(dist2, 1);
            const w = Math.exp(-dist2 * 0.5) * Math.max(sharpnessWeight, 0.1);

            const srcIdx = (sy * width + sx) * 4;
            sumR += imageData.data[srcIdx] * w;
            sumG += imageData.data[srcIdx + 1] * w;
            sumB += imageData.data[srcIdx + 2] * w;
            sumA += imageData.data[srcIdx + 3] * w;
            weightSum += w;
          }
        }
      }

      if (weightSum > 0) {
        const blendFactor = edgeValue * intensityFactor * (1 - sharpnessFactor * 0.3);
        const origIdx = idx * 4;
        const origR = imageData.data[origIdx];
        const origG = imageData.data[origIdx + 1];
        const origB = imageData.data[origIdx + 2];
        const origA = imageData.data[origIdx + 3];

        const blR = sumR / weightSum;
        const blG = sumG / weightSum;
        const blB = sumB / weightSum;
        const blA = sumA / weightSum;

        let finalR = origR * (1 - blendFactor) + blR * blendFactor;
        let finalG = origG * (1 - blendFactor) + blG * blendFactor;
        let finalB = origB * (1 - blendFactor) + blB * blendFactor;
        const finalA = origA * (1 - blendFactor) + blA * blendFactor;

        if (sharpnessFactor > 0.5) {
          const laplacian = estimateLaplacian(imageData, x, y);
          const sharpenAmount = (sharpnessFactor - 0.5) * 0.3 * edgeValue;
          finalR = clamp(finalR + laplacian * sharpenAmount, 0, 255);
          finalG = clamp(finalG + laplacian * sharpenAmount, 0, 255);
          finalB = clamp(finalB + laplacian * sharpenAmount, 0, 255);
        }

        result.data[origIdx] = Math.round(finalR);
        result.data[origIdx + 1] = Math.round(finalG);
        result.data[origIdx + 2] = Math.round(finalB);
        result.data[origIdx + 3] = Math.round(finalA);
      }

      if (progressCallback && (y * width + x) % 500 === 0) {
        progressCallback((y * width + x) / total);
      }
    }
  }

  return result;
}

function estimateLaplacian(imageData: ImageData, x: number, y: number): number {
  const center = getGrayAt(imageData, x, y);
  const n = getGrayAt(imageData, x, y - 1);
  const s = getGrayAt(imageData, x, y + 1);
  const e = getGrayAt(imageData, x + 1, y);
  const w = getGrayAt(imageData, x - 1, y);
  return 4 * center - n - s - e - w;
}

function getGrayAt(imageData: ImageData, x: number, y: number): number {
  const pixel = getPixel(imageData, x, y);
  return 0.299 * pixel[0] + 0.587 * pixel[1] + 0.114 * pixel[2];
}

export function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

export function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

export function generateId(): string {
  return Math.random().toString(36).substring(2, 15);
}
