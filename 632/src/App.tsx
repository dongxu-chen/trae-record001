import { useEffect, useCallback, useRef } from 'react';
import { motion } from 'framer-motion';
import { Sparkles } from 'lucide-react';
import { ImageUploader } from './components/ImageUploader';
import { CanvasPreview } from './components/CanvasPreview';
import { ControlPanel } from './components/ControlPanel';
import { BatchQueue } from './components/BatchQueue';
import { useImageStore } from './store/useImageStore';
import { useWorkerPool } from './hooks/useWorkerPool';
import { ProcessingParams } from './types';

function App() {
  const { 
    images, 
    currentImageId, 
    params, 
    updateImage, 
    setCurrentImage,
    imageDataToUrl,
    outputFormat,
    outputQuality,
    autoParamsEnabled,
    applyRecommendedParams
  } = useImageStore();

  const processingQueueRef = useRef<string[]>([]);
  const isProcessingRef = useRef(false);

  const { 
    processImage, 
    hasIdleWorker, 
    setCallbacks 
  } = useWorkerPool(2);

  const handleProgress = useCallback((id: string, progress: number) => {
    updateImage(id, { progress });
  }, [updateImage]);

  const handleResult = useCallback((id: string, result: ImageData) => {
    const processedUrl = imageDataToUrl(result, outputFormat, outputQuality);
    updateImage(id, { 
      processedData: result, 
      processedUrl,
      status: 'completed', 
      progress: 100 
    });
    isProcessingRef.current = false;
    processNextInQueue();
  }, [updateImage, imageDataToUrl, outputFormat, outputQuality]);

  const handleError = useCallback((id: string, error: string) => {
    updateImage(id, { status: 'error', error, progress: 0 });
    isProcessingRef.current = false;
    processNextInQueue();
  }, [updateImage]);

  useEffect(() => {
    setCallbacks({
      onProgress: handleProgress,
      onResult: handleResult,
      onError: handleError
    });
  }, [setCallbacks, handleProgress, handleResult, handleError]);

  const getProcessingParams = useCallback((imageId: string): ProcessingParams => {
    const image = images.find((img) => img.id === imageId);
    if (image && image.useAutoParams && image.params) {
      return image.params;
    }
    return params;
  }, [images, params]);

  const processNextInQueue = useCallback(() => {
    if (processingQueueRef.current.length === 0 || !hasIdleWorker()) {
      return;
    }

    const nextId = processingQueueRef.current.shift();
    if (!nextId) return;

    const image = images.find((img) => img.id === nextId);
    if (!image || !image.originalData) {
      processNextInQueue();
      return;
    }

    isProcessingRef.current = true;
    const processingParams = getProcessingParams(nextId);
    updateImage(nextId, { status: 'processing', progress: 0, params: processingParams });

    const queued = processImage(nextId, image.originalData, processingParams);
    if (!queued) {
      processingQueueRef.current.unshift(nextId);
      isProcessingRef.current = false;
    }
  }, [images, processImage, hasIdleWorker, updateImage, getProcessingParams]);

  const startProcessing = useCallback((imageId: string) => {
    if (processingQueueRef.current.includes(imageId)) {
      return;
    }

    const image = images.find((img) => img.id === imageId);
    if (!image || !image.originalData) {
      return;
    }

    processingQueueRef.current.push(imageId);
    
    if (!isProcessingRef.current) {
      processNextInQueue();
    }
  }, [images, processNextInQueue]);

  useEffect(() => {
    if (!currentImageId) return;
    
    const currentImage = images.find((img) => img.id === currentImageId);
    if (!currentImage) return;

    if (autoParamsEnabled && currentImage.complexity && currentImage.useAutoParams && currentImage.params) {
      const hasDifferentParams = JSON.stringify(currentImage.params) !== JSON.stringify(params);
      if (hasDifferentParams) {
        return;
      }
    }

    const currentParams = getProcessingParams(currentImageId);
    const needsProcessing = 
      currentImage.status === 'pending' || 
      !currentImage.processedData ||
      JSON.stringify(currentImage.params) !== JSON.stringify(currentParams);

    if (needsProcessing && currentImage.originalData) {
      const debounceTimer = setTimeout(() => {
        startProcessing(currentImageId);
      }, 300);

      return () => clearTimeout(debounceTimer);
    }
  }, [currentImageId, params, images, startProcessing, autoParamsEnabled, getProcessingParams]);

  useEffect(() => {
    const pendingImages = images.filter((img) => img.status === 'pending');
    for (const img of pendingImages) {
      if (!processingQueueRef.current.includes(img.id)) {
        startProcessing(img.id);
      }
    }
  }, [images, startProcessing]);

  useEffect(() => {
    if (currentImageId && autoParamsEnabled) {
      const currentImage = images.find((img) => img.id === currentImageId);
      if (currentImage && currentImage.complexity && currentImage.useAutoParams && currentImage.params) {
        const hasDifferentParams = JSON.stringify(currentImage.params) !== JSON.stringify(params);
        if (hasDifferentParams) {
          applyRecommendedParams(currentImageId);
        }
      }
    }
  }, [currentImageId]);

  const currentImage = images.find((img) => img.id === currentImageId);

  return (
    <div className="h-screen flex flex-col bg-deep-space-900">
      <motion.header
        initial={{ y: -50, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.5 }}
        className="flex-shrink-0 h-14 px-6 bg-deep-space-900/80 backdrop-blur-sm border-b border-deep-space-700 flex items-center justify-between z-50"
      >
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-neon-blue-400 to-neon-purple-500 flex items-center justify-center">
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-deep-space-100 font-display tracking-tight">
              图像抗锯齿工具
            </h1>
            <p className="text-[10px] text-deep-space-500 font-mono">
              GPU加速 · 方向性平滑 · 智能分类
            </p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          {currentImage && (
            <div className="hidden md:flex items-center gap-4 text-xs">
              {currentImage.complexity && (
                <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border ${
                  currentImage.complexity.level === 'simple' ? 'bg-green-500/10 border-green-500/30' :
                  currentImage.complexity.level === 'medium' ? 'bg-yellow-500/10 border-yellow-500/30' :
                  'bg-red-500/10 border-red-500/30'
                }`}>
                  <span className="text-deep-space-400">复杂度:</span>
                  <span className={`font-mono font-medium ${
                    currentImage.complexity.level === 'simple' ? 'text-green-400' :
                    currentImage.complexity.level === 'medium' ? 'text-yellow-400' :
                    'text-red-400'
                  }`}>
                    {currentImage.complexity.level === 'simple' ? '简单' :
                     currentImage.complexity.level === 'medium' ? '中等' : '复杂'}
                  </span>
                </div>
              )}
              <div className="flex items-center gap-2 px-3 py-1.5 bg-deep-space-800 rounded-lg border border-deep-space-700">
                <span className="text-deep-space-400">算法:</span>
                <span className="text-neon-blue-400 font-mono font-medium">
                  {params.algorithm.toUpperCase()}
                </span>
              </div>
              <div className="flex items-center gap-2 px-3 py-1.5 bg-deep-space-800 rounded-lg border border-deep-space-700">
                <span className="text-deep-space-400">强度:</span>
                <span className="text-neon-purple-400 font-mono font-medium">
                  {params.intensity}%
                </span>
              </div>
              {autoParamsEnabled && (
                <div className="flex items-center gap-2 px-3 py-1.5 bg-neon-blue-500/10 rounded-lg border border-neon-blue-500/30">
                  <span className="text-neon-blue-400 font-mono font-medium text-xs">
                    自动参数
                  </span>
                </div>
              )}
            </div>
          )}
        </div>
      </motion.header>

      <div className="flex-1 flex overflow-hidden">
        <motion.aside
          initial={{ x: -300, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="w-[280px] flex-shrink-0 bg-deep-space-800/30 border-r border-deep-space-700 overflow-hidden"
        >
          <ControlPanel />
        </motion.aside>

        <main className="flex-1 flex flex-col overflow-hidden">
          <div className="flex-1 flex flex-col overflow-hidden">
            {!currentImage ? (
              <div className="flex-1 p-6 overflow-auto">
                <ImageUploader />
              </div>
            ) : (
              <div className="flex-1 overflow-hidden">
                <CanvasPreview />
              </div>
            )}

            {currentImage && (
              <div className="flex-shrink-0 p-4 border-t border-deep-space-700 bg-deep-space-800/30">
                <ImageUploader />
              </div>
            )}
          </div>
        </main>

        <motion.aside
          initial={{ x: 300, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          transition={{ duration: 0.5, delay: 0.2 }}
          className="w-[320px] flex-shrink-0 overflow-hidden"
        >
          <BatchQueue />
        </motion.aside>
      </div>
    </div>
  );
}

export default App;
