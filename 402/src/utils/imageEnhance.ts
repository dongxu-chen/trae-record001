export function calculateBrightness(imageData: ImageData): number {
  let totalBrightness = 0;
  const data = imageData.data;
  
  for (let i = 0; i < data.length; i += 4) {
    const brightness = (data[i] + data[i + 1] + data[i + 2]) / 3;
    totalBrightness += brightness;
  }
  
  return totalBrightness / (data.length / 4);
}

export function isLowLight(imageData: ImageData, threshold: number = 80): boolean {
  return calculateBrightness(imageData) < threshold;
}

export function adaptiveGammaCorrection(imageData: ImageData): ImageData {
  const data = imageData.data;
  const width = imageData.width;
  const height = imageData.height;
  
  const histogram = new Array(256).fill(0);
  
  for (let i = 0; i < data.length; i += 4) {
    const gray = Math.floor(0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2]);
    histogram[gray]++;
  }
  
  let cumulative = 0;
  const totalPixels = width * height;
  const percentile = 0.05;
  let lowPercentile = 0;
  let highPercentile = 255;
  
  for (let i = 0; i < 256; i++) {
    cumulative += histogram[i];
    if (cumulative >= totalPixels * percentile) {
      lowPercentile = i;
      break;
    }
  }
  
  cumulative = 0;
  for (let i = 255; i >= 0; i--) {
    cumulative += histogram[i];
    if (cumulative >= totalPixels * percentile) {
      highPercentile = i;
      break;
    }
  }
  
  const midGray = 128;
  let averageBrightness = 0;
  for (let i = 0; i < data.length; i += 4) {
    averageBrightness += (data[i] + data[i + 1] + data[i + 2]) / 3;
  }
  averageBrightness /= totalPixels;
  
  const gamma = Math.log2(midGray) / Math.log2(averageBrightness || 1);
  const clampedGamma = Math.max(0.5, Math.min(2.5, gamma));
  
  const range = highPercentile - lowPercentile;
  const scale = range > 0 ? 255 / range : 1;
  const offset = -lowPercentile * scale;
  
  for (let i = 0; i < data.length; i += 4) {
    for (let j = 0; j < 3; j++) {
      let value = data[i + j];
      
      value = value * scale + offset;
      value = Math.max(0, Math.min(255, value));
      
      value = 255 * Math.pow(value / 255, clampedGamma);
      value = Math.floor(value);
      
      data[i + j] = Math.max(0, Math.min(255, value));
    }
  }
  
  return imageData;
}

export function noiseReduction(imageData: ImageData): ImageData {
  const data = imageData.data;
  const width = imageData.width;
  const height = imageData.height;
  const temp = new Uint8ClampedArray(data);
  
  const kernel = [
    [1, 2, 1],
    [2, 4, 2],
    [1, 2, 1],
  ];
  const kernelWeight = 16;
  
  for (let y = 1; y < height - 1; y++) {
    for (let x = 1; x < width - 1; x++) {
      for (let c = 0; c < 3; c++) {
        let sum = 0;
        
        for (let ky = -1; ky <= 1; ky++) {
          for (let kx = -1; kx <= 1; kx++) {
            const pixelIndex = ((y + ky) * width + (x + kx)) * 4 + c;
            sum += temp[pixelIndex] * kernel[ky + 1][kx + 1];
          }
        }
        
        const pixelIndex = (y * width + x) * 4 + c;
        data[pixelIndex] = Math.floor(sum / kernelWeight);
      }
    }
  }
  
  return imageData;
}

export function enhanceLowLight(imageData: ImageData): ImageData {
  imageData = adaptiveGammaCorrection(imageData);
  imageData = noiseReduction(imageData);
  return imageData;
}

export function adjustContrast(
  imageData: ImageData,
  contrast: number,
  brightness: number
): ImageData {
  const data = imageData.data;
  const factor = (259 * (contrast + 255)) / (255 * (259 - contrast));
  
  for (let i = 0; i < data.length; i += 4) {
    for (let j = 0; j < 3; j++) {
      let value = data[i + j] + brightness;
      value = factor * (value - 128) + 128;
      data[i + j] = Math.max(0, Math.min(255, Math.floor(value)));
    }
  }
  
  return imageData;
}

export function histogramEqualization(imageData: ImageData): ImageData {
  const data = imageData.data;
  const histogram = new Array(256).fill(0);
  
  for (let i = 0; i < data.length; i += 4) {
    const gray = Math.floor(0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2]);
    histogram[gray]++;
  }
  
  const cdf = new Array(256).fill(0);
  cdf[0] = histogram[0];
  for (let i = 1; i < 256; i++) {
    cdf[i] = cdf[i - 1] + histogram[i];
  }
  
  const cdfMin = cdf.find((v) => v > 0) || 0;
  const totalPixels = data.length / 4;
  
  const lookupTable = new Array(256).fill(0);
  for (let i = 0; i < 256; i++) {
    lookupTable[i] = Math.round(((cdf[i] - cdfMin) / (totalPixels - cdfMin)) * 255);
  }
  
  for (let i = 0; i < data.length; i += 4) {
    for (let j = 0; j < 3; j++) {
      data[i + j] = lookupTable[data[i + j]];
    }
  }
  
  return imageData;
}
