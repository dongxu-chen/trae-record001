import React, { useState, useCallback, useRef, useEffect } from 'react';
import type { ImageItem, CompressionSettings, ImageFormat, OperationMode, WorkerMessage, SmartSuggestion } from './types';
import { generateId, formatFileSize, calculateSavings } from './utils/format';
import { downloadAsMultiPartZip } from './utils/zipDownload';
import {
  analyzeImageFromFile,
  generateSmartSuggestion,
  estimateCompressedSize,
  detectImageFormat
} from './utils/imageAnalyzer';
import { FileUpload } from './components/FileUpload';
import { SettingsPanel } from './components/SettingsPanel';
import { ImageCard } from './components/ImageCard';
import CompressWorker from './compress.worker?worker';

const MAX_WORKERS = Math.min(navigator.hardwareConcurrency || 4, 8);
const MAX_TASKS_PER_WORKER = 10;
const SETTINGS_DEBOUNCE_MS = 500;
const CHUNK_SIZE_THRESHOLD = 500 * 1024 * 1024;

interface WorkerWithStats {
  worker: Worker;
  tasksProcessed: number;
  imageId: string;
}

function App() {
  const [images, setImages] = useState<ImageItem[]>([]);
  const [settings, setSettings] = useState<CompressionSettings>({
    quality: 80,
    format: 'jpeg'
  });
  const [mode, setMode] = useState<OperationMode>('compress');
  const [isDragOver, setIsDragOver] = useState(false);
  const [isCompressing, setIsCompressing] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const [downloadProgress, setDownloadProgress] = useState<{ current: number; total: number } | null>(null);
  const [aggregateSuggestion, setAggregateSuggestion] = useState<SmartSuggestion | undefined>();

  const workersRef = useRef<Map<string, WorkerWithStats>>(new Map());
  const pendingQueueRef = useRef<string[]>([]);
  const activeWorkersRef = useRef<number>(0);
  const settingsDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const updateAggregateSuggestion = useCallback((imageList: ImageItem[]) => {
    const analyzed = imageList.filter(img => img.suggestion);
    if (analyzed.length === 0) {
      setAggregateSuggestion(undefined);
      return;
    }
    const formatCounts: Record<string, number> = {};
    let totalQuality = 0;
    let totalRatio = 0;
    for (const img of analyzed) {
      const s = img.suggestion!;
      formatCounts[s.format] = (formatCounts[s.format] || 0) + 1;
      totalQuality += s.quality;
      totalRatio += s.estimatedRatio;
    }
    const bestFormat = Object.entries(formatCounts).sort((a, b) => b[1] - a[1])[0][0] as ImageFormat;
    const avgQuality = Math.round(totalQuality / analyzed.length);
    const avgRatio = totalRatio / analyzed.length;
    const reasons = new Set(analyzed.map(img => img.suggestion!.reason));
    const topReason = [...reasons][0];
    setAggregateSuggestion({
      format: bestFormat,
      quality: avgQuality,
      reason: topReason,
      estimatedRatio: avgRatio
    });
  }, []);

  const handleFilesSelected = useCallback(async (files: File[]) => {
    const newImages: ImageItem[] = [];

    for (const file of files) {
      const originalFormat = detectImageFormat(file);
      const imageUrl = URL.createObjectURL(file);
      const analysisResult = await analyzeImageFromFile(file, imageUrl);

      const suggestion = generateSmartSuggestion(
        originalFormat,
        file.size,
        analysisResult.width,
        analysisResult.height,
        analysisResult.hasAlpha,
        analysisResult.colorComplexity
      );

      const estimatedSize = estimateCompressedSize(
        file.size,
        originalFormat,
        settings.format,
        settings.quality,
        analysisResult.hasAlpha,
        analysisResult.colorComplexity
      );

      const imageItem: ImageItem = {
        id: generateId(),
        file,
        originalUrl: imageUrl,
        originalSize: file.size,
        originalFormat,
        status: 'pending',
        progress: 0,
        width: analysisResult.width,
        height: analysisResult.height,
        hasAlpha: analysisResult.hasAlpha,
        colorComplexity: analysisResult.colorComplexity,
        estimatedSize,
        suggestion
      };
      newImages.push(imageItem);
    }

    setImages(prev => {
      const updated = [...prev, ...newImages];
      setTimeout(() => updateAggregateSuggestion(updated), 0);
      return updated;
    });
  }, [settings, updateAggregateSuggestion]);

  const handleRemoveImage = useCallback((id: string) => {
    setImages(prev => {
      const image = prev.find(img => img.id === id);
      if (image) {
        URL.revokeObjectURL(image.originalUrl);
        if (image.compressedUrl) {
          URL.revokeObjectURL(image.compressedUrl);
        }
        const workerEntry = workersRef.current.get(id);
        if (workerEntry) {
          workerEntry.worker.terminate();
          workersRef.current.delete(id);
        }
      }
      const updated = prev.filter(img => img.id !== id);
      setTimeout(() => updateAggregateSuggestion(updated), 0);
      return updated;
    });
  }, [updateAggregateSuggestion]);

  const handleClearAll = useCallback(() => {
    images.forEach(image => {
      URL.revokeObjectURL(image.originalUrl);
      if (image.compressedUrl) {
        URL.revokeObjectURL(image.compressedUrl);
      }
    });
    workersRef.current.forEach(entry => entry.worker.terminate());
    workersRef.current.clear();
    pendingQueueRef.current = [];
    activeWorkersRef.current = 0;
    if (settingsDebounceRef.current) {
      clearTimeout(settingsDebounceRef.current);
    }
    setImages([]);
    setIsCompressing(false);
    setAggregateSuggestion(undefined);
  }, [images]);

  const createWorker = useCallback((imageId: string): Worker => {
    const worker = new CompressWorker();
    workersRef.current.set(imageId, { worker, tasksProcessed: 0, imageId });
    return worker;
  }, []);

  const recycleWorker = useCallback((imageId: string, worker: Worker): Worker => {
    const entry = workersRef.current.get(imageId);
    if (entry && entry.tasksProcessed >= MAX_TASKS_PER_WORKER) {
      worker.terminate();
      const newWorker = new CompressWorker();
      workersRef.current.set(imageId, { worker: newWorker, tasksProcessed: 0, imageId });
      return newWorker;
    }
    if (entry) {
      entry.tasksProcessed++;
    }
    return worker;
  }, []);

  const processNextInQueue = useCallback(() => {
    if (pendingQueueRef.current.length === 0 || activeWorkersRef.current >= MAX_WORKERS) {
      if (activeWorkersRef.current === 0) {
        setIsCompressing(false);
      }
      return;
    }

    const imageId = pendingQueueRef.current.shift()!;
    activeWorkersRef.current++;

    setImages(prev => prev.map(img =>
      img.id === imageId ? { ...img, status: 'compressing', progress: 0 } : img
    ));

    let worker = createWorker(imageId);

    const handleMessage = (e: MessageEvent<WorkerMessage>) => {
      const { type, imageId: msgImageId, progress, success, compressedBlob, compressedSize, error } = e.data;

      if (msgImageId !== imageId) return;

      if (type === 'progress' && progress !== undefined) {
        setImages(prev => prev.map(img =>
          img.id === imageId ? { ...img, progress } : img
        ));
      } else if (type === 'result') {
        worker.removeEventListener('message', handleMessage);
        worker.removeEventListener('error', handleError);

        worker = recycleWorker(imageId, worker);
        workersRef.current.delete(imageId);
        activeWorkersRef.current--;

        if (success && compressedBlob && compressedSize !== undefined) {
          const compressedUrl = URL.createObjectURL(compressedBlob);
          setImages(prev => prev.map(img =>
            img.id === imageId
              ? { ...img, status: 'completed', progress: 100, compressedUrl, compressedSize }
              : img
          ));
        } else {
          setImages(prev => prev.map(img =>
            img.id === imageId ? { ...img, status: 'error', error } : img
          ));
        }

        processNextInQueue();
      }
    };

    const handleError = (e: ErrorEvent) => {
      console.error('Worker error:', e);
      worker.removeEventListener('message', handleMessage);
      worker.removeEventListener('error', handleError);
      worker.terminate();
      workersRef.current.delete(imageId);
      activeWorkersRef.current--;

      setImages(prev => prev.map(img =>
        img.id === imageId ? { ...img, status: 'error', error: 'Worker 错误' } : img
      ));

      processNextInQueue();
    };

    worker.addEventListener('message', handleMessage);
    worker.addEventListener('error', handleError);

    const image = images.find(img => img.id === imageId);
    if (image) {
      if (mode === 'convert') {
        worker.postMessage({
          type: 'convert',
          imageId,
          file: image.file,
          targetFormat: settings.format,
          width: image.width,
          height: image.height
        });
      } else {
        worker.postMessage({
          type: 'compress',
          imageId,
          file: image.file,
          settings,
          width: image.width,
          height: image.height
        });
      }
    }
  }, [images, settings, mode, createWorker, recycleWorker]);

  const handleStartCompression = useCallback(() => {
    const pendingImages = images.filter(img => img.status === 'pending');
    if (pendingImages.length === 0) return;

    setIsCompressing(true);
    pendingQueueRef.current = pendingImages.map(img => img.id);

    for (let i = 0; i < MAX_WORKERS && pendingQueueRef.current.length > 0; i++) {
      processNextInQueue();
    }
  }, [images, processNextInQueue]);

  const handleSettingsChange = useCallback((newSettings: CompressionSettings) => {
    setSettings(newSettings);

    if (settingsDebounceRef.current) {
      clearTimeout(settingsDebounceRef.current);
    }

    settingsDebounceRef.current = setTimeout(() => {
      setImages(prev => prev.map(img => {
        if (img.compressedUrl) {
          URL.revokeObjectURL(img.compressedUrl);
        }
        const estimatedSize = estimateCompressedSize(
          img.originalSize,
          img.originalFormat,
          newSettings.format,
          newSettings.quality,
          img.hasAlpha,
          img.colorComplexity
        );
        return {
          ...img,
          status: 'pending',
          progress: 0,
          compressedUrl: undefined,
          compressedSize: undefined,
          error: undefined,
          estimatedSize
        };
      }));
    }, SETTINGS_DEBOUNCE_MS);
  }, []);

  const handleApplySuggestion = useCallback((suggestion: SmartSuggestion) => {
    setSettings({
      format: suggestion.format,
      quality: suggestion.quality
    });

    setImages(prev => prev.map(img => {
      if (img.compressedUrl) {
        URL.revokeObjectURL(img.compressedUrl);
      }
      const estimatedSize = estimateCompressedSize(
        img.originalSize,
        img.originalFormat,
        suggestion.format,
        suggestion.quality,
        img.hasAlpha,
        img.colorComplexity
      );
      return {
        ...img,
        status: 'pending',
        progress: 0,
        compressedUrl: undefined,
        compressedSize: undefined,
        error: undefined,
        estimatedSize
      };
    }));
  }, []);

  const handleDownloadZip = useCallback(async () => {
    const completedImages = images.filter(img => img.status === 'completed' && img.compressedUrl);
    if (completedImages.length === 0) return;

    setIsDownloading(true);
    setDownloadProgress({ current: 0, total: 1 });

    try {
      await downloadAsMultiPartZip(
        images,
        settings.format,
        CHUNK_SIZE_THRESHOLD,
        (current, total) => setDownloadProgress({ current, total })
      );
    } catch (error) {
      console.error('ZIP download failed:', error);
    } finally {
      setIsDownloading(false);
      setDownloadProgress(null);
    }
  }, [images, settings.format]);

  const completedCount = images.filter(img => img.status === 'completed').length;
  const pendingCount = images.filter(img => img.status === 'pending').length;
  const compressingCount = images.filter(img => img.status === 'compressing').length;
  const totalOriginalSize = images.reduce((sum, img) => sum + img.originalSize, 0);
  const totalCompressedSize = images
    .filter(img => img.compressedSize !== undefined)
    .reduce((sum, img) => sum + (img.compressedSize || 0), 0);
  const totalEstimatedSize = images
    .filter(img => img.estimatedSize !== undefined && img.status !== 'completed')
    .reduce((sum, img) => sum + (img.estimatedSize || 0), 0);
  const totalSavings = totalOriginalSize > 0
    ? calculateSavings(totalOriginalSize, totalCompressedSize || totalEstimatedSize)
    : 0;

  useEffect(() => {
    return () => {
      workersRef.current.forEach(entry => entry.worker.terminate());
      workersRef.current.clear();
      if (settingsDebounceRef.current) {
        clearTimeout(settingsDebounceRef.current);
      }
      images.forEach(image => {
        URL.revokeObjectURL(image.originalUrl);
        if (image.compressedUrl) {
          URL.revokeObjectURL(image.compressedUrl);
        }
      });
    };
  }, []);

  const actionLabel = mode === 'convert' ? '转换' : '压缩';

  return (
    <div className="app">
      <header className="app-header">
        <h1>🖼️ 图片批量压缩工具</h1>
        <p>支持 JPEG、PNG、WebP 格式 · 智能建议 · 压缩预测 · 格式转换</p>
      </header>

      <main className="app-main">
        <div className="sidebar">
          <SettingsPanel
            settings={settings}
            onSettingsChange={handleSettingsChange}
            mode={mode}
            onModeChange={setMode}
            suggestion={aggregateSuggestion}
            onApplySuggestion={handleApplySuggestion}
          />

          <div className="control-panel">
            <button
              className="btn btn-primary"
              onClick={handleStartCompression}
              disabled={pendingCount === 0 || isCompressing}
            >
              {isCompressing
                ? `${actionLabel}中 (${compressingCount}/${pendingCount + compressingCount})`
                : `开始${actionLabel}`}
            </button>

            <button
              className="btn btn-success"
              onClick={handleDownloadZip}
              disabled={completedCount === 0 || isDownloading}
            >
              {isDownloading
                ? (downloadProgress ? `打包中... (${downloadProgress.current}/${downloadProgress.total})` : '打包中...')
                : `下载 ZIP (${completedCount})`}
            </button>

            <button
              className="btn btn-danger"
              onClick={handleClearAll}
              disabled={images.length === 0 || isCompressing}
            >
              清空全部
            </button>
          </div>

          {images.length > 0 && (
            <div className="stats-panel">
              <h4>压缩统计</h4>
              <div className="stats-grid">
                <div className="stat-card">
                  <span className="stat-card-label">总文件数</span>
                  <span className="stat-card-value">{images.length}</span>
                </div>
                <div className="stat-card">
                  <span className="stat-card-label">已完成</span>
                  <span className="stat-card-value">{completedCount}</span>
                </div>
                <div className="stat-card">
                  <span className="stat-card-label">原始大小</span>
                  <span className="stat-card-value">{formatFileSize(totalOriginalSize)}</span>
                </div>
                {totalEstimatedSize > 0 && totalCompressedSize === 0 && (
                  <div className="stat-card estimated-card">
                    <span className="stat-card-label">预估大小</span>
                    <span className="stat-card-value">~{formatFileSize(totalEstimatedSize)}</span>
                  </div>
                )}
                {totalCompressedSize > 0 && (
                  <>
                    <div className="stat-card">
                      <span className="stat-card-label">{actionLabel}后</span>
                      <span className="stat-card-value">{formatFileSize(totalCompressedSize)}</span>
                    </div>
                    <div className="stat-card highlight">
                      <span className="stat-card-label">节省空间</span>
                      <span className="stat-card-value">-{totalSavings}%</span>
                    </div>
                  </>
                )}
              </div>
              <div className="worker-info">
                <small>Worker 自动回收 · 设置防抖 {SETTINGS_DEBOUNCE_MS}ms · 智能分析</small>
              </div>
            </div>
          )}
        </div>

        <div className="content">
          {images.length === 0 ? (
            <FileUpload
              onFilesSelected={handleFilesSelected}
              isDragOver={isDragOver}
              onDragOverChange={setIsDragOver}
            />
          ) : (
            <>
              <div className="content-header">
                <FileUpload
                  onFilesSelected={handleFilesSelected}
                  isDragOver={isDragOver}
                  onDragOverChange={setIsDragOver}
                />
              </div>
              <div className="images-grid">
                {images.map(image => (
                  <ImageCard
                    key={image.id}
                    image={image}
                    format={settings.format}
                    mode={mode}
                    onRemove={handleRemoveImage}
                  />
                ))}
              </div>
            </>
          )}
        </div>
      </main>

      <footer className="app-footer">
        <p>多线程压缩 · {MAX_WORKERS} 个 Worker · 智能建议 · 压缩预测 · 本地处理</p>
      </footer>
    </div>
  );
}

export default App;
