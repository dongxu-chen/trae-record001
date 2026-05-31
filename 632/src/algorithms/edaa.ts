import { ProcessingParams } from '../types';
import { sobelDirectionalEdgeDetection, anisotropicBlur, createGaussianKernel, applyConvolution, clamp } from './utils';
import { detectTextRegions, textAntiAliasing, SUBPIXEL_RGB, SUBPIXEL_BGR } from './textAntiAliasing';

export function processEDAA(
  imageData: ImageData,
  params: ProcessingParams,
  progressCallback?: (progress: number) => void
): ImageData {
  const { threshold, intensity, edgeBlur, kernelSize, sharpness, textOptimization, subpixelLayout } = params;
  const intensityFactor = intensity / 100;
  
  if (progressCallback) progressCallback(0.05);

  let textDetection = null;
  if (textOptimization) {
    textDetection = detectTextRegions(imageData, (p) => {
      if (progressCallback) progressCallback(0.05 + p * 0.2);
    });
    if (progressCallback) progressCallback(0.25);
  }

  const edgeData = sobelDirectionalEdgeDetection(imageData, threshold, (p) => {
    if (progressCallback) progressCallback(0.25 + p * 0.25);
  });

  if (progressCallback) progressCallback(0.5);

  const sigma = edgeBlur / 2;
  const directionalResult = anisotropicBlur(imageData, edgeData, sigma, intensity, sharpness, (p) => {
    if (progressCallback) progressCallback(0.5 + p * 0.35);
  });

  if (progressCallback) progressCallback(0.85);

  let finalResult = directionalResult;

  if (textOptimization && textDetection && textDetection.isText) {
    const layout = subpixelLayout === 'bgr' ? SUBPIXEL_BGR : 
                   subpixelLayout === 'rgb' ? SUBPIXEL_RGB : null;
    
    if (layout) {
      finalResult = textAntiAliasing(
        directionalResult,
        textDetection,
        intensity,
        sharpness,
        layout,
        (p) => {
          if (progressCallback) progressCallback(0.85 + p * 0.1);
        }
      );
    }
  }

  if (progressCallback) progressCallback(0.95);

  if (kernelSize > 3 && intensityFactor > 0.5 && sharpness < 60) {
    const gaussianKernel = createGaussianKernel(3, sigma * 0.3);
    const lightBlur = applyConvolution(finalResult, gaussianKernel, (p) => {
      if (progressCallback) progressCallback(0.95 + p * 0.04);
    });

    const final = new ImageData(imageData.width, imageData.height);
    const total = imageData.width * imageData.height;

    for (let i = 0; i < total; i++) {
      const idx = i * 4;
      const edgeValue = edgeData.mask[i] / 255;
      const extraBlend = edgeValue * (intensityFactor - 0.5) * 0.3 * (1 - sharpness / 100);

      final.data[idx] = Math.round(clamp(
        finalResult.data[idx] * (1 - extraBlend) + lightBlur.data[idx] * extraBlend, 0, 255
      ));
      final.data[idx + 1] = Math.round(clamp(
        finalResult.data[idx + 1] * (1 - extraBlend) + lightBlur.data[idx + 1] * extraBlend, 0, 255
      ));
      final.data[idx + 2] = Math.round(clamp(
        finalResult.data[idx + 2] * (1 - extraBlend) + lightBlur.data[idx + 2] * extraBlend, 0, 255
      ));
      final.data[idx + 3] = Math.round(clamp(
        finalResult.data[idx + 3] * (1 - extraBlend) + lightBlur.data[idx + 3] * extraBlend, 0, 255
      ));
    }

    if (progressCallback) progressCallback(1.0);
    return final;
  }

  if (progressCallback) progressCallback(1.0);
  return finalResult;
}
