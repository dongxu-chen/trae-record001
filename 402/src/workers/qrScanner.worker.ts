import { BrowserMultiFormatReader, NotFoundException } from '@zxing/library';

interface WorkerMessage {
  type: 'scan' | 'init';
  imageData?: ImageData;
  enableLowLight?: boolean;
}

interface WorkerResponse {
  success: boolean;
  content?: string;
  format?: string;
  error?: string;
}

let reader: BrowserMultiFormatReader | null = null;

function initReader() {
  if (!reader) {
    reader = new BrowserMultiFormatReader();
  }
}

function adaptiveGammaCorrection(imageData: ImageData): ImageData {
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

function noiseReduction(imageData: ImageData): ImageData {
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

self.onmessage = async function(e: MessageEvent<WorkerMessage>) {
  const message = e.data;
  
  if (message.type === 'init') {
    try {
      initReader();
      self.postMessage({ success: true });
    } catch (error) {
      self.postMessage({
        success: false,
        error: error instanceof Error ? error.message : 'Init failed',
      });
    }
    return;
  }
  
  if (message.type === 'scan' && message.imageData) {
    try {
      initReader();
      
      let imageData = message.imageData;
      
      if (message.enableLowLight) {
        imageData = adaptiveGammaCorrection(imageData);
        imageData = noiseReduction(imageData);
      }
      
      if (!reader) {
        throw new Error('Reader not initialized');
      }
      
      const canvas = new OffscreenCanvas(imageData.width, imageData.height);
      const ctx = canvas.getContext('2d');
      if (ctx) {
        ctx.putImageData(imageData, 0, 0);
      }
      
      const result = await reader.decodeFromImage(canvas as any);
      
      if (result) {
        const response: WorkerResponse = {
          success: true,
          content: result.getText(),
          format: result.getBarcodeFormat().toString(),
        };
        self.postMessage(response);
      } else {
        self.postMessage({ success: false });
      }
    } catch (error) {
      if (error instanceof NotFoundException) {
        self.postMessage({ success: false });
      } else {
        self.postMessage({
          success: false,
          error: error instanceof Error ? error.message : 'Unknown error',
        });
      }
    }
  }
};

export {};
