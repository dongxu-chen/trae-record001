import { ProcessingParams } from '../types';
import { gpuSSAAUpscale } from './gpuResample';
import { resizeImageData, getPixel, setPixel, clamp, createGaussianKernel, applyConvolution } from './utils';

export function processSSAA(
  imageData: ImageData,
  params: ProcessingParams,
  progressCallback?: (progress: number) => void
): ImageData {
  const { sampleRate, intensity, sharpness } = params;
  const intensityFactor = intensity / 100;
  const sharpnessFactor = sharpness / 100;

  if (progressCallback) progressCallback(0.05);

  let downscaled: ImageData;
  try {
    downscaled = gpuSSAAUpscale(imageData, sampleRate);
    if (progressCallback) progressCallback(0.85);
  } catch {
    downscaled = cpuSSAAFallback(imageData, sampleRate, progressCallback);
  }

  if (sharpnessFactor > 0.3) {
    const sigma = 1 + (1 - sharpnessFactor) * 2;
    const kernel = createGaussianKernel(3, sigma);
    const blurred = applyConvolution(downscaled, kernel);
    
    const total = imageData.width * imageData.height;

    for (let i = 0; i < total; i++) {
      const idx = i * 4;
      const unsharpMaskR = downscaled.data[idx] * 2 - blurred.data[idx];
      const unsharpMaskG = downscaled.data[idx + 1] * 2 - blurred.data[idx + 1];
      const unsharpMaskB = downscaled.data[idx + 2] * 2 - blurred.data[idx + 2];

      const sharpAmount = (sharpnessFactor - 0.3) * 0.8;
      downscaled.data[idx] = Math.round(clamp(
        downscaled.data[idx] * (1 - sharpAmount) + unsharpMaskR * sharpAmount, 0, 255
      ));
      downscaled.data[idx + 1] = Math.round(clamp(
        downscaled.data[idx + 1] * (1 - sharpAmount) + unsharpMaskG * sharpAmount, 0, 255
      ));
      downscaled.data[idx + 2] = Math.round(clamp(
        downscaled.data[idx + 2] * (1 - sharpAmount) + unsharpMaskB * sharpAmount, 0, 255
      ));
    }

    if (progressCallback) progressCallback(0.92);
  }

  const result = new ImageData(imageData.width, imageData.height);
  const total = imageData.width * imageData.height;

  for (let i = 0; i < total; i++) {
    const idx = i * 4;
    const origR = imageData.data[idx];
    const origG = imageData.data[idx + 1];
    const origB = imageData.data[idx + 2];
    const origA = imageData.data[idx + 3];

    const dsR = downscaled.data[idx];
    const dsG = downscaled.data[idx + 1];
    const dsB = downscaled.data[idx + 2];
    const dsA = downscaled.data[idx + 3];

    result.data[idx] = Math.round(clamp(origR * (1 - intensityFactor) + dsR * intensityFactor, 0, 255));
    result.data[idx + 1] = Math.round(clamp(origG * (1 - intensityFactor) + dsG * intensityFactor, 0, 255));
    result.data[idx + 2] = Math.round(clamp(origB * (1 - intensityFactor) + dsB * intensityFactor, 0, 255));
    result.data[idx + 3] = Math.round(clamp(origA * (1 - intensityFactor) + dsA * intensityFactor, 0, 255));
  }

  if (progressCallback) progressCallback(1.0);
  return result;
}

function cpuSSAAFallback(
  imageData: ImageData,
  scale: number,
  progressCallback?: (progress: number) => void
): ImageData {
  const upW = imageData.width * scale;
  const upH = imageData.height * scale;
  const upscaled = resizeImageData(imageData, upW, upH);

  if (progressCallback) progressCallback(0.4);

  const result = new ImageData(imageData.width, imageData.height);
  const total = imageData.width * imageData.height;

  for (let y = 0; y < imageData.height; y++) {
    for (let x = 0; x < imageData.width; x++) {
      let r = 0, g = 0, b = 0, a = 0;
      for (let sy = 0; sy < scale; sy++) {
        for (let sx = 0; sx < scale; sx++) {
          const pixel = getPixel(upscaled, x * scale + sx, y * scale + sy);
          r += pixel[0]; g += pixel[1]; b += pixel[2]; a += pixel[3];
        }
      }
      const n = scale * scale;
      setPixel(result, x, y, Math.round(r / n), Math.round(g / n), Math.round(b / n), Math.round(a / n));

      if (progressCallback && (y * imageData.width + x) % 500 === 0) {
        progressCallback(0.4 + ((y * imageData.width + x) / total) * 0.45);
      }
    }
  }

  return result;
}
