import { ProcessingParams } from '../types';
import { getPixel, setPixel, bilinearInterpolate, clamp, createGaussianKernel, applyConvolution } from './utils';

export function processMSAA(
  imageData: ImageData,
  params: ProcessingParams,
  progressCallback?: (progress: number) => void
): ImageData {
  const { sampleRate, intensity, threshold, sharpness } = params;
  const samplesPerPixel = sampleRate;
  const intensityFactor = intensity / 100;
  const thresholdFactor = threshold / 255;
  const sharpnessFactor = sharpness / 100;
  
  const result = new ImageData(imageData.width, imageData.height);
  const total = imageData.width * imageData.height;
  let processed = 0;
  
  const sampleOffsets = generateSampleOffsets(samplesPerPixel);
  
  let tempResult: ImageData = result;
  
  if (sharpnessFactor > 0.4) {
    tempResult = new ImageData(imageData.width, imageData.height);
  }
  
  for (let y = 0; y < imageData.height; y++) {
    for (let x = 0; x < imageData.width; x++) {
      const centerPixel = getPixel(imageData, x, y);
      
      let hasEdge = false;
      const neighbors = [
        getPixel(imageData, x - 1, y),
        getPixel(imageData, x + 1, y),
        getPixel(imageData, x, y - 1),
        getPixel(imageData, x, y + 1)
      ];
      
      for (const neighbor of neighbors) {
        const diff = Math.abs(centerPixel[0] - neighbor[0]) +
                     Math.abs(centerPixel[1] - neighbor[1]) +
                     Math.abs(centerPixel[2] - neighbor[2]);
        if (diff > threshold * 3) {
          hasEdge = true;
          break;
        }
      }
      
      const output = tempResult || result;
      
      if (!hasEdge) {
        setPixel(output, x, y, centerPixel[0], centerPixel[1], centerPixel[2], centerPixel[3]);
      } else {
        let r = 0, g = 0, b = 0, a = 0;
        
        const edgeBias = 1 + sharpnessFactor * 0.5;
        const centerWeight = (sampleOffsets.length * (1 - sharpnessFactor * 0.4)) / sampleOffsets.length;
        
        for (const offset of sampleOffsets) {
          const sampleX = x + offset.x * edgeBias;
          const sampleY = y + offset.y * edgeBias;
          
          const sampledPixel = bilinearInterpolate(imageData, sampleX, sampleY);
          r += sampledPixel[0];
          g += sampledPixel[1];
          b += sampledPixel[2];
          a += sampledPixel[3];
        }
        
        const sampleCount = sampleOffsets.length;
        const avgR = r / sampleCount;
        const avgG = g / sampleCount;
        const avgB = b / sampleCount;
        const avgA = a / sampleCount;
        
        const edgeStrength = calculateEdgeStrength(imageData, x, y) / (255 * 3);
        const sharpnessAdjust = 1 - sharpnessFactor * 0.4;
        const blendFactor = clamp(edgeStrength * intensityFactor * (1 + thresholdFactor) * sharpnessAdjust, 0, 1);
        
        const finalR = Math.round(clamp(
          centerPixel[0] * (1 - blendFactor) + avgR * blendFactor,
          0, 255
        ));
        const finalG = Math.round(clamp(
          centerPixel[1] * (1 - blendFactor) + avgG * blendFactor,
          0, 255
        ));
        const finalB = Math.round(clamp(
          centerPixel[2] * (1 - blendFactor) + avgB * blendFactor,
          0, 255
        ));
        const finalA = Math.round(clamp(
          centerPixel[3] * (1 - blendFactor) + avgA * blendFactor,
          0, 255
        ));
        
        setPixel(output, x, y, finalR, finalG, finalB, finalA);
      }
      
      processed++;
      if (progressCallback && processed % 500 === 0) {
        progressCallback(processed / total * (sharpnessFactor > 0.4 ? 0.85 : 1));
      }
    }
  }
  
  if (sharpnessFactor > 0.4 && tempResult) {
    if (progressCallback) progressCallback(0.85);
    
    const sigma = 1 + (1 - sharpnessFactor) * 1.5;
    const kernel = createGaussianKernel(3, sigma);
    const blurred = applyConvolution(tempResult, kernel);
    
    const sharpAmount = (sharpnessFactor - 0.4) * 1.0;
    for (let i = 0; i < total * 4; i += 4) {
      const unsharpR = tempResult.data[i] * 2 - blurred.data[i];
      const unsharpG = tempResult.data[i + 1] * 2 - blurred.data[i + 1];
      const unsharpB = tempResult.data[i + 2] * 2 - blurred.data[i + 2];
      
      result.data[i] = Math.round(clamp(
        tempResult.data[i] * (1 - sharpAmount) + unsharpR * sharpAmount, 0, 255
      ));
      result.data[i + 1] = Math.round(clamp(
        tempResult.data[i + 1] * (1 - sharpAmount) + unsharpG * sharpAmount, 0, 255
      ));
      result.data[i + 2] = Math.round(clamp(
        tempResult.data[i + 2] * (1 - sharpAmount) + unsharpB * sharpAmount, 0, 255
      ));
      result.data[i + 3] = tempResult.data[i + 3];
    }
    
    if (progressCallback) progressCallback(1.0);
    return result;
  }
  
  if (progressCallback) progressCallback(1.0);
  return result;
}

function generateSampleOffsets(samples: number): Array<{ x: number; y: number }> {
  const offsets: Array<{ x: number; y: number }> = [];
  const half = 0.5;
  
  if (samples <= 2) {
    offsets.push({ x: -half * 0.5, y: -half * 0.5 });
    offsets.push({ x: half * 0.5, y: half * 0.5 });
  } else if (samples <= 4) {
    offsets.push({ x: -half * 0.5, y: -half * 0.5 });
    offsets.push({ x: half * 0.5, y: -half * 0.5 });
    offsets.push({ x: -half * 0.5, y: half * 0.5 });
    offsets.push({ x: half * 0.5, y: half * 0.5 });
  } else {
    for (let i = 0; i < samples; i++) {
      for (let j = 0; j < samples; j++) {
        const x = (j / samples) - half + (1 / samples) * 0.5;
        const y = (i / samples) - half + (1 / samples) * 0.5;
        offsets.push({ x, y });
      }
    }
  }
  
  return offsets;
}

function calculateEdgeStrength(imageData: ImageData, x: number, y: number): number {
  const center = getPixel(imageData, x, y);
  let maxDiff = 0;
  
  const directions = [
    { dx: -1, dy: 0 }, { dx: 1, dy: 0 },
    { dx: 0, dy: -1 }, { dx: 0, dy: 1 },
    { dx: -1, dy: -1 }, { dx: 1, dy: 1 },
    { dx: -1, dy: 1 }, { dx: 1, dy: -1 }
  ];
  
  for (const dir of directions) {
    const neighbor = getPixel(imageData, x + dir.dx, y + dir.dy);
    const diff = Math.abs(center[0] - neighbor[0]) +
                 Math.abs(center[1] - neighbor[1]) +
                 Math.abs(center[2] - neighbor[2]);
    maxDiff = Math.max(maxDiff, diff);
  }
  
  return maxDiff;
}
