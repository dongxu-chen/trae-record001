import { useRef, useCallback, useEffect } from 'react';
import { WorkerMessage, ProcessingParams } from '../types';

type WorkerState = 'idle' | 'busy';

interface PoolWorker {
  worker: Worker;
  state: WorkerState;
  currentId?: string;
}

interface WorkerPoolCallbacks {
  onProgress: (id: string, progress: number) => void;
  onResult: (id: string, result: ImageData) => void;
  onError: (id: string, error: string) => void;
}

export function useWorkerPool(poolSize: number = 2) {
  const workersRef = useRef<PoolWorker[]>([]);
  const callbacksRef = useRef<WorkerPoolCallbacks | null>(null);

  useEffect(() => {
    workersRef.current = Array.from({ length: poolSize }, () => ({
      worker: new Worker(new URL('../workers/imageProcessor.worker.ts', import.meta.url), {
        type: 'module'
      }),
      state: 'idle'
    }));

    workersRef.current.forEach((poolWorker) => {
      poolWorker.worker.onmessage = (e: MessageEvent<WorkerMessage>) => {
        const message = e.data;
        const callbacks = callbacksRef.current;

        if (!callbacks) return;

        if (message.type === 'progress' && message.progress !== undefined) {
          callbacks.onProgress(message.id, message.progress);
        } else if (message.type === 'result' && message.result) {
          poolWorker.state = 'idle';
          poolWorker.currentId = undefined;
          callbacks.onResult(message.id, message.result);
        } else if (message.type === 'error' && message.error) {
          poolWorker.state = 'idle';
          poolWorker.currentId = undefined;
          callbacks.onError(message.id, message.error);
        }
      };
    });

    return () => {
      workersRef.current.forEach((pw) => pw.worker.terminate());
    };
  }, [poolSize]);

  const setCallbacks = useCallback((callbacks: WorkerPoolCallbacks) => {
    callbacksRef.current = callbacks;
  }, []);

  const processImage = useCallback((
    id: string,
    imageData: ImageData,
    params: ProcessingParams
  ): boolean => {
    const idleWorker = workersRef.current.find((pw) => pw.state === 'idle');
    
    if (!idleWorker) {
      return false;
    }

    idleWorker.state = 'busy';
    idleWorker.currentId = id;

    const imageDataCopy = new ImageData(
      new Uint8ClampedArray(imageData.data),
      imageData.width,
      imageData.height
    );

    idleWorker.worker.postMessage({
      type: 'process',
      id,
      imageData: imageDataCopy,
      params
    } as WorkerMessage, [imageDataCopy.data.buffer]);

    return true;
  }, []);

  const cancelProcessing = useCallback((id: string) => {
    const worker = workersRef.current.find((pw) => pw.currentId === id);
    if (worker) {
      worker.worker.postMessage({ type: 'cancel', id } as WorkerMessage);
      worker.state = 'idle';
      worker.currentId = undefined;
    }
  }, []);

  const hasIdleWorker = useCallback(() => {
    return workersRef.current.some((pw) => pw.state === 'idle');
  }, []);

  const getBusyCount = useCallback(() => {
    return workersRef.current.filter((pw) => pw.state === 'busy').length;
  }, []);

  return {
    processImage,
    cancelProcessing,
    hasIdleWorker,
    getBusyCount,
    setCallbacks
  };
}
