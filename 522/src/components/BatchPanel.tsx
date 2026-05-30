import { useState, useCallback } from 'react';
import {
  X,
  Play,
  Check,
  Loader2,
  Layers,
  Download,
  Plus,
  Trash2,
  Zap,
  FileImage,
} from 'lucide-react';
import { useShader } from '@/contexts/ShaderContext';
import useFilterStore from '@/store/filterStore';
import { FILTER_DEFINITIONS, BatchProcessItem } from '@/utils/shaderManager';
import { cn } from '@/lib/utils';

interface BatchPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function BatchPanel({
  isOpen,
  onClose,
}: BatchPanelProps) {
  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [processedResults, setProcessedResults] = useState<
    Map<string, Uint8ClampedArray>
  >(new Map());
  const { batchProcess } = useShader();
  const {
    images,
    batchQueue,
    activeFilter,
    filterIntensity,
    filterParams,
    addToBatch,
    removeFromBatch,
    updateBatchItemStatus,
  } = useFilterStore();

  const filterName =
    FILTER_DEFINITIONS.find((f) => f.id === activeFilter)?.name || '自定义';

  const pixelsToBlob = (
    pixels: Uint8ClampedArray,
    width: number,
    height: number
  ): Promise<Blob> => {
    return new Promise((resolve) => {
      const canvas = document.createElement('canvas');
      canvas.width = width;
      canvas.height = height;
      const ctx = canvas.getContext('2d');
      if (!ctx) {
        resolve(new Blob());
        return;
      }

      const imageData = ctx.createImageData(width, height);
      imageData.data.set(pixels);
      ctx.putImageData(imageData, 0, 0);

      canvas.toBlob((blob) => {
        resolve(blob || new Blob());
      }, 'image/png');
    });
  };

  const downloadBlob = (blob: Blob, filename: string) => {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleProcess = useCallback(async () => {
    const pendingItems = batchQueue.filter((b) => b.status !== 'done');
    if (pendingItems.length === 0) return;

    setIsProcessing(true);
    setProgress(0);
    setProcessedResults(new Map());

    try {
      const processItems: BatchProcessItem[] = [];

      for (const batchItem of pendingItems) {
        const image = images.find((img) => img.id === batchItem.imageId);
        if (!image) continue;

        const img = new Image();
        img.crossOrigin = 'anonymous';
        await new Promise((resolve, reject) => {
          img.onload = resolve;
          img.onerror = reject;
          img.src = image.src;
        });

        processItems.push({
          image: img,
          filterType: batchItem.config.filterType,
          intensity: batchItem.config.intensity,
          params: { ...batchItem.config.customParams },
        });

        updateBatchItemStatus(batchItem.imageId, 'processing');
      }

      const results = await batchProcess(processItems, (index, total) => {
        setProgress((index / total) * 100);
        const processedItem = pendingItems[index - 1];
        if (processedItem) {
          updateBatchItemStatus(processedItem.imageId, 'done');
        }
      });

      const newResults = new Map<string, Uint8ClampedArray>();
      results.forEach((result, index) => {
        const batchItem = pendingItems[index];
        if (batchItem && result.length > 0) {
          newResults.set(batchItem.imageId, result);
        }
      });
      setProcessedResults(newResults);

      const pendingResults = pendingItems.filter(
        (b) => b.status === 'processing'
      );
      for (const item of pendingResults) {
        updateBatchItemStatus(item.imageId, 'done');
      }
    } catch (error) {
      console.error('Batch processing failed:', error);
      for (const item of pendingItems) {
        if (item.status === 'processing') {
          updateBatchItemStatus(item.imageId, 'error');
        }
      }
    } finally {
      setIsProcessing(false);
    }
  }, [batchQueue, images, batchProcess, updateBatchItemStatus]);

  const handleDownloadSingle = useCallback(
    async (imageId: string) => {
      const result = processedResults.get(imageId);
      const image = images.find((img) => img.id === imageId);
      if (!result || !image) return;

      const blob = await pixelsToBlob(result, image.width, image.height);
      const baseName = image.name.replace(/\.[^/.]+$/, '');
      downloadBlob(blob, `${baseName}_${activeFilter}_batch.png`);
    },
    [processedResults, images, activeFilter]
  );

  const handleDownloadAll = useCallback(async () => {
    for (const [imageId, pixels] of processedResults) {
      const image = images.find((img) => img.id === imageId);
      if (!image) continue;

      const blob = await pixelsToBlob(pixels, image.width, image.height);
      const baseName = image.name.replace(/\.[^/.]+$/, '');
      downloadBlob(blob, `${baseName}_${activeFilter}_batch.png`);
    }
  }, [processedResults, images, activeFilter]);

  const addAllToBatch = () => {
    images.forEach((img) => addToBatch(img.id));
  };

  if (!isOpen) return null;

  const doneCount = batchQueue.filter((b) => b.status === 'done').length;
  const pendingCount = batchQueue.filter((b) => b.status === 'pending').length;
  const processingCount = batchQueue.filter((b) => b.status === 'processing').length;

  return (
    <div className="fixed bottom-0 left-0 right-0 z-40 glass-panel border-t border-surface-border animate-slide-in">
      <div className="max-w-7xl mx-auto">
        <div className="flex items-center justify-between p-4 border-b border-surface-border/50">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-neon-amber/20 flex items-center justify-center">
              <Layers size={20} className="text-neon-amber" />
            </div>
            <div>
              <h3 className="font-display font-semibold">批量处理</h3>
              <p className="text-sm text-gray-400">
                共享WebGL上下文 · {filterName} · 强度:{' '}
                {Math.round(filterIntensity * 100)}%
              </p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            {isProcessing && (
              <div className="flex items-center gap-3 min-w-[200px]">
                <div className="flex-1 h-2 bg-surface-card rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-neon-amber to-neon-pink transition-all duration-300"
                    style={{ width: `${progress}%` }}
                  />
                </div>
                <span className="text-xs font-mono text-neon-amber">
                  {Math.round(progress)}%
                </span>
              </div>
            )}

            <div className="flex items-center gap-2 text-sm">
              <span className="flex items-center gap-1">
                <FileImage size={14} className="text-gray-400" />
                <span className="text-gray-400">等待: {pendingCount}</span>
              </span>
              <span className="flex items-center gap-1">
                <Zap size={14} className="text-neon-amber" />
                <span className="text-neon-amber">处理: {processingCount}</span>
              </span>
              <span className="flex items-center gap-1">
                <Check size={14} className="text-green-400" />
                <span className="text-green-400">完成: {doneCount}</span>
              </span>
            </div>

            <button
              onClick={onClose}
              className="p-2 rounded-lg hover:bg-surface-hover transition-colors"
            >
              <X size={18} />
            </button>
          </div>
        </div>

        <div className="p-4">
          {images.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              请先上传图片到工作台
            </div>
          ) : (
            <>
              <div className="flex items-center gap-2 mb-4">
                <button
                  onClick={addAllToBatch}
                  className="px-3 py-1.5 bg-surface-card rounded-md text-sm hover:bg-surface-hover transition-colors flex items-center gap-2"
                >
                  <Plus size={14} />
                  全部添加到队列
                </button>

                {doneCount > 0 && (
                  <button
                    onClick={handleDownloadAll}
                    className="px-3 py-1.5 bg-neon-cyan/20 text-neon-cyan rounded-md text-sm hover:bg-neon-cyan/30 transition-colors flex items-center gap-2"
                  >
                    <Download size={14} />
                    下载全部 ({doneCount})
                  </button>
                )}
              </div>

              <div className="flex gap-3 overflow-x-auto pb-2">
                {images.map((image) => {
                  const batchItem = batchQueue.find(
                    (b) => b.imageId === image.id
                  );
                  const hasResult = processedResults.has(image.id);

                  return (
                    <div
                      key={image.id}
                      className={cn(
                        'relative flex-shrink-0 w-28 h-28 rounded-lg overflow-hidden transition-all',
                        batchItem
                          ? 'ring-2 ring-neon-amber'
                          : 'ring-1 ring-surface-border hover:ring-neon-amber/50'
                      )}
                    >
                      <img
                        src={image.src}
                        alt={image.name}
                        className="w-full h-full object-cover"
                      />

                      {batchItem ? (
                        <div className="absolute inset-0 bg-black/60 flex flex-col items-center justify-center gap-1">
                          {batchItem.status === 'processing' && (
                            <>
                              <Loader2
                                size={20}
                                className="animate-spin text-neon-amber"
                              />
                              <span className="text-xs text-neon-amber">
                                处理中
                              </span>
                            </>
                          )}
                          {batchItem.status === 'done' && (
                            <>
                              <Check size={20} className="text-green-400" />
                              <span className="text-xs text-green-400">
                                已完成
                              </span>
                              {hasResult && (
                                <button
                                  onClick={() => handleDownloadSingle(image.id)}
                                  className="mt-1 px-2 py-0.5 bg-neon-cyan/20 rounded text-xs text-neon-cyan hover:bg-neon-cyan/30 transition-colors flex items-center gap-1"
                                >
                                  <Download size={12} />
                                  下载
                                </button>
                              )}
                            </>
                          )}
                          {batchItem.status === 'error' && (
                            <>
                              <X size={20} className="text-red-400" />
                              <span className="text-xs text-red-400">失败</span>
                            </>
                          )}
                          {batchItem.status === 'pending' && (
                            <>
                              <span className="text-xs text-gray-300">
                                待处理
                              </span>
                              <button
                                onClick={() => removeFromBatch(image.id)}
                                className="absolute top-1 right-1 w-5 h-5 bg-red-500/80 rounded-full flex items-center justify-center hover:bg-red-500 transition-colors"
                              >
                                <X size={12} className="text-white" />
                              </button>
                            </>
                          )}
                        </div>
                      ) : (
                        <button
                          onClick={() => addToBatch(image.id)}
                          className="absolute inset-0 bg-black/0 hover:bg-black/40 transition-colors flex items-center justify-center opacity-0 hover:opacity-100"
                        >
                          <span className="text-xs text-white bg-neon-amber/80 px-2 py-1 rounded">
                            加入队列
                          </span>
                        </button>
                      )}
                    </div>
                  );
                })}
              </div>

              <div className="flex justify-end gap-3 mt-4 pt-4 border-t border-surface-border/50">
                <button
                  onClick={onClose}
                  className="px-4 py-2 bg-surface-card rounded-lg text-sm font-medium hover:bg-surface-hover transition-colors"
                >
                  关闭
                </button>
                <button
                  onClick={handleProcess}
                  disabled={isProcessing || pendingCount === 0}
                  className="px-6 py-2 bg-gradient-to-r from-neon-amber to-neon-pink rounded-lg text-sm font-medium text-white hover:shadow-lg hover:shadow-neon-amber/25 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                >
                  {isProcessing ? (
                    <>
                      <Loader2 size={16} className="animate-spin" />
                      处理中...
                    </>
                  ) : (
                    <>
                      <Zap size={16} />
                      开始批量处理 ({pendingCount} 张)
                    </>
                  )}
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
