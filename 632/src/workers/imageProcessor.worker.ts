import { ProcessingParams, WorkerMessage } from '../types';
import { processSSAA } from '../algorithms/ssaa';
import { processEDAA } from '../algorithms/edaa';
import { processMSAA } from '../algorithms/msaa';

const ctx: Worker = self as unknown as Worker;

let isCancelled = false;

ctx.onmessage = (e: MessageEvent<WorkerMessage>) => {
  const message = e.data;

  if (message.type === 'cancel') {
    isCancelled = true;
    return;
  }

  if (message.type === 'process' && message.imageData && message.params) {
    isCancelled = false;
    processImage(message.id, message.imageData, message.params);
  }
};

function processImage(
  id: string,
  imageData: ImageData,
  params: ProcessingParams
): void {
  try {
    const progressCallback = (progress: number) => {
      if (isCancelled) {
        throw new Error('Cancelled');
      }
      ctx.postMessage({
        type: 'progress',
        id,
        progress: Math.round(progress * 100)
      } as WorkerMessage);
    };

    let result: ImageData;

    switch (params.algorithm) {
      case 'ssaa':
        result = processSSAA(imageData, params, progressCallback);
        break;
      case 'edaa':
        result = processEDAA(imageData, params, progressCallback);
        break;
      case 'msaa':
        result = processMSAA(imageData, params, progressCallback);
        break;
      default:
        result = processEDAA(imageData, params, progressCallback);
    }

    if (!isCancelled) {
      ctx.postMessage({
        type: 'result',
        id,
        result
      } as WorkerMessage, [result.data.buffer]);
    }
  } catch (error) {
    if ((error as Error).message === 'Cancelled') {
      return;
    }
    ctx.postMessage({
      type: 'error',
      id,
      error: (error as Error).message
    } as WorkerMessage);
  }
}

export {};
