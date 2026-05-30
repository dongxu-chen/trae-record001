import imageCompression from 'browser-image-compression';
import type { CompressionSettings, ImageFormat, WorkerMessage } from './types';

const ctx: Worker = self as unknown as Worker;

ctx.addEventListener('message', async (e: MessageEvent<WorkerMessage>) => {
  const { type, imageId, file, settings, width, height, targetFormat } = e.data;

  if (type === 'convert' && imageId && file && targetFormat) {
    try {
      ctx.postMessage({ type: 'progress', imageId, progress: 10 });

      const maxDimension = Math.max(width || 4096, height || 4096);
      const options = {
        maxSizeMB: Infinity,
        maxWidthOrHeight: maxDimension,
        useWebWorker: false,
        initialQuality: 1.0,
        alwaysKeepResolution: true,
        fileType: getMimeType(targetFormat),
        onProgress: (progress: number) => {
          ctx.postMessage({
            type: 'progress',
            imageId,
            progress: Math.min(90, 10 + progress * 0.8)
          });
        }
      };

      const convertedFile = await imageCompression(file, options);

      ctx.postMessage({ type: 'progress', imageId, progress: 95 });

      const convertedBlob = new Blob([convertedFile], { type: getMimeType(targetFormat) });

      ctx.postMessage({
        type: 'result',
        imageId,
        success: true,
        compressedBlob: convertedBlob,
        compressedSize: convertedBlob.size
      });
    } catch (error) {
      ctx.postMessage({
        type: 'result',
        imageId,
        success: false,
        error: error instanceof Error ? error.message : '格式转换失败'
      });
    }
  }

  if (type === 'compress' && imageId && file && settings) {
    try {
      ctx.postMessage({ type: 'progress', imageId, progress: 10 });

      const maxDimension = Math.max(width || 4096, height || 4096);
      const options = {
        maxSizeMB: Infinity,
        maxWidthOrHeight: settings.maxWidthOrHeight ?? maxDimension,
        useWebWorker: false,
        initialQuality: settings.quality / 100,
        alwaysKeepResolution: true,
        fileType: getMimeType(settings.format),
        onProgress: (progress: number) => {
          ctx.postMessage({
            type: 'progress',
            imageId,
            progress: Math.min(90, 10 + progress * 0.8)
          });
        }
      };

      const compressedFile = await imageCompression(file, options);

      ctx.postMessage({ type: 'progress', imageId, progress: 95 });

      const compressedBlob = new Blob([compressedFile], { type: getMimeType(settings.format) });

      ctx.postMessage({
        type: 'result',
        imageId,
        success: true,
        compressedBlob,
        compressedSize: compressedBlob.size
      });
    } catch (error) {
      ctx.postMessage({
        type: 'result',
        imageId,
        success: false,
        error: error instanceof Error ? error.message : '压缩失败'
      });
    }
  }
});

function getMimeType(format: string): string {
  switch (format) {
    case 'jpeg':
      return 'image/jpeg';
    case 'png':
      return 'image/png';
    case 'webp':
      return 'image/webp';
    default:
      return 'image/jpeg';
  }
}

export {};
