import sharp from 'sharp';
import path from 'path';
import fs from 'fs/promises';
import { ProcessingParams } from '../../src/types/index.js';

export interface ProcessResult {
  id: string;
  originalPath: string;
  processedPath: string;
  success: boolean;
  error?: string;
}

export async function processImage(
  inputPath: string,
  outputPath: string,
  params: ProcessingParams
): Promise<ProcessResult> {
  const id = path.basename(inputPath, path.extname(inputPath));
  
  try {
    let pipeline = sharp(inputPath);

    switch (params.algorithm) {
      case 'ssaa':
        pipeline = await applySSAA(pipeline, params);
        break;
      case 'edaa':
        pipeline = await applyEDAA(pipeline, params);
        break;
      case 'msaa':
        pipeline = await applyMSAA(pipeline, params);
        break;
      default:
        pipeline = await applyEDAA(pipeline, params);
    }

    await pipeline.toFile(outputPath);

    return {
      id,
      originalPath: inputPath,
      processedPath: outputPath,
      success: true
    };
  } catch (error) {
    return {
      id,
      originalPath: inputPath,
      processedPath: outputPath,
      success: false,
      error: (error as Error).message
    };
  }
}

async function applySSAA(
  pipeline: sharp.Sharp,
  params: ProcessingParams
): Promise<sharp.Sharp> {
  const metadata = await pipeline.metadata();
  const width = metadata.width || 0;
  const height = metadata.height || 0;
  const scale = params.sampleRate;

  return pipeline
    .resize(width * scale, height * scale, {
      kernel: sharp.kernel.lanczos3
    })
    .blur(params.edgeBlur * 0.3)
    .resize(width, height, {
      kernel: sharp.kernel.lanczos3
    });
}

async function applyEDAA(
  pipeline: sharp.Sharp,
  params: ProcessingParams
): Promise<sharp.Sharp> {
  const { data, info } = await pipeline
    .raw()
    .toBuffer({ resolveWithObject: true });

  const edgeMask = detectEdges(data, info.width, info.height, params.threshold);
  const blurred = await pipeline.blur(params.edgeBlur).raw().toBuffer();

  const result = blendWithEdgeMask(
    data,
    blurred,
    edgeMask,
    info.width,
    info.height,
    info.channels,
    params.intensity
  );

  return sharp(result, {
    raw: {
      width: info.width,
      height: info.height,
      channels: info.channels
    }
  });
}

async function applyMSAA(
  pipeline: sharp.Sharp,
  params: ProcessingParams
): Promise<sharp.Sharp> {
  const metadata = await pipeline.metadata();
  const width = metadata.width || 0;
  const height = metadata.height || 0;
  const scale = Math.min(params.sampleRate, 4);

  return pipeline
    .resize(width * scale, height * scale, {
      kernel: sharp.kernel.lanczos2
    })
    .resize(width, height, {
      kernel: sharp.kernel.cubic
    });
}

function detectEdges(
  data: Buffer,
  width: number,
  height: number,
  threshold: number
): Uint8Array {
  const edgeMask = new Uint8Array(width * height);
  const grayData = new Uint8Array(width * height);

  for (let i = 0, j = 0; i < data.length; i += 4, j++) {
    grayData[j] = Math.round(
      0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2]
    );
  }

  const gx = [-1, 0, 1, -2, 0, 2, -1, 0, 1];
  const gy = [-1, -2, -1, 0, 0, 0, 1, 2, 1];

  for (let y = 1; y < height - 1; y++) {
    for (let x = 1; x < width - 1; x++) {
      let sumX = 0, sumY = 0;

      for (let ky = -1; ky <= 1; ky++) {
        for (let kx = -1; kx <= 1; kx++) {
          const idx = (y + ky) * width + (x + kx);
          const kidx = (ky + 1) * 3 + (kx + 1);
          sumX += grayData[idx] * gx[kidx];
          sumY += grayData[idx] * gy[kidx];
        }
      }

      const magnitude = Math.sqrt(sumX * sumX + sumY * sumY);
      edgeMask[y * width + x] = magnitude > threshold ? 255 : 0;
    }
  }

  return edgeMask;
}

function blendWithEdgeMask(
  original: Buffer,
  blurred: Buffer,
  edgeMask: Uint8Array,
  width: number,
  height: number,
  channels: number,
  intensity: number
): Buffer {
  const result = Buffer.alloc(original.length);
  const intensityFactor = intensity / 100;

  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      const pixelIdx = (y * width + x) * channels;
      const maskIdx = y * width + x;
      const edgeValue = edgeMask[maskIdx] / 255;
      const blendFactor = edgeValue * intensityFactor;

      for (let c = 0; c < channels; c++) {
        const origVal = original[pixelIdx + c];
        const blurVal = blurred[pixelIdx + c];
        result[pixelIdx + c] = Math.round(
          origVal * (1 - blendFactor) + blurVal * blendFactor
        );
      }
    }
  }

  return result;
}

export async function cleanupOldFiles(dir: string, maxAge: number = 24 * 60 * 60 * 1000) {
  try {
    const files = await fs.readdir(dir);
    const now = Date.now();

    for (const file of files) {
      const filePath = path.join(dir, file);
      const stats = await fs.stat(filePath);
      
      if (now - stats.mtimeMs > maxAge) {
        await fs.unlink(filePath);
      }
    }
  } catch (error) {
    console.error('清理旧文件失败:', error);
  }
}
