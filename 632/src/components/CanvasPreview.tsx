import { useRef, useEffect, useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ZoomIn, ZoomOut, Move, Eye, EyeOff, Maximize2 } from 'lucide-react';
import { useImageStore } from '../store/useImageStore';

interface CanvasPreviewProps {
  onImageLoaded?: (imageData: ImageData) => void;
}

export function CanvasPreview({ onImageLoaded }: CanvasPreviewProps) {
  const { images, currentImageId } = useImageStore();
  const containerRef = useRef<HTMLDivElement>(null);
  const originalCanvasRef = useRef<HTMLCanvasElement>(null);
  const processedCanvasRef = useRef<HTMLCanvasElement>(null);
  
  const [splitPosition, setSplitPosition] = useState(50);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState(false);
  const [panStart, setPanStart] = useState({ x: 0, y: 0 });
  const [showOriginal, setShowOriginal] = useState(true);
  const [isDraggingSplit, setIsDraggingSplit] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);

  const currentImage = images.find((img) => img.id === currentImageId);

  const drawImage = useCallback(() => {
    if (!currentImage) return;
    
    const originalCanvas = originalCanvasRef.current;
    const processedCanvas = processedCanvasRef.current;
    
    if (!originalCanvas || !processedCanvas) return;

    const img = new Image();
    img.onload = () => {
      const container = containerRef.current;
      if (!container) return;

      const containerWidth = container.clientWidth;
      const containerHeight = container.clientHeight;
      
      const imgRatio = img.width / img.height;
      const containerRatio = containerWidth / containerHeight;
      
      let drawWidth, drawHeight;
      if (imgRatio > containerRatio) {
        drawWidth = containerWidth * zoom;
        drawHeight = drawWidth / imgRatio;
      } else {
        drawHeight = containerHeight * zoom;
        drawWidth = drawHeight * imgRatio;
      }

      const offsetX = (containerWidth - drawWidth) / 2 + pan.x;
      const offsetY = (containerHeight - drawHeight) / 2 + pan.y;

      originalCanvas.width = containerWidth;
      originalCanvas.height = containerHeight;
      processedCanvas.width = containerWidth;
      processedCanvas.height = containerHeight;

      const origCtx = originalCanvas.getContext('2d');
      const procCtx = processedCanvas.getContext('2d');
      
      if (!origCtx || !procCtx) return;

      origCtx.clearRect(0, 0, containerWidth, containerHeight);
      procCtx.clearRect(0, 0, containerWidth, containerHeight);

      origCtx.imageSmoothingEnabled = false;
      procCtx.imageSmoothingEnabled = false;

      origCtx.drawImage(img, offsetX, offsetY, drawWidth, drawHeight);

      if (currentImage.processedData) {
        const tempCanvas = document.createElement('canvas');
        tempCanvas.width = currentImage.processedData.width;
        tempCanvas.height = currentImage.processedData.height;
        const tempCtx = tempCanvas.getContext('2d');
        if (tempCtx) {
          tempCtx.putImageData(currentImage.processedData, 0, 0);
          procCtx.drawImage(tempCanvas, offsetX, offsetY, drawWidth, drawHeight);
        }
      }

      if (onImageLoaded && currentImage.originalData) {
        onImageLoaded(currentImage.originalData);
      }
    };
    img.src = currentImage.originalUrl;
  }, [currentImage, zoom, pan, onImageLoaded]);

  useEffect(() => {
    drawImage();
  }, [drawImage]);

  useEffect(() => {
    const handleResize = () => drawImage();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [drawImage]);

  const handleMouseDown = (e: React.MouseEvent) => {
    if (e.button === 1 || (e.button === 0 && e.altKey)) {
      setIsPanning(true);
      setPanStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
    }
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (isPanning) {
      setPan({
        x: e.clientX - panStart.x,
        y: e.clientY - panStart.y
      });
    } else if (isDraggingSplit) {
      const container = containerRef.current;
      if (container) {
        const rect = container.getBoundingClientRect();
        const newPosition = ((e.clientX - rect.left) / rect.width) * 100;
        setSplitPosition(Math.max(0, Math.min(100, newPosition)));
      }
    }
  };

  const handleMouseUp = () => {
    setIsPanning(false);
    setIsDraggingSplit(false);
  };

  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? -0.1 : 0.1;
    setZoom((z) => Math.max(0.1, Math.min(5, z + delta)));
  };

  const handleZoomIn = () => setZoom((z) => Math.min(5, z + 0.25));
  const handleZoomOut = () => setZoom((z) => Math.max(0.1, z - 0.25));
  const handleResetView = () => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  };

  const toggleFullscreen = () => {
    const container = containerRef.current;
    if (!container) return;

    if (!isFullscreen) {
      if (container.requestFullscreen) {
        container.requestFullscreen();
      }
    } else {
      if (document.exitFullscreen) {
        document.exitFullscreen();
      }
    }
    setIsFullscreen(!isFullscreen);
  };

  if (!currentImage) {
    return (
      <div className="h-full flex items-center justify-center canvas-grid rounded-xl border border-deep-space-700">
        <div className="text-center">
          <motion.div
            className="w-24 h-24 mx-auto mb-4 rounded-2xl bg-deep-space-800/50 flex items-center justify-center border border-deep-space-700"
            animate={{ y: [0, -5, 0] }}
            transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
          >
            <svg className="w-12 h-12 text-deep-space-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
          </motion.div>
          <p className="text-deep-space-400 text-lg font-medium">上传图片开始处理</p>
          <p className="text-deep-space-500 text-sm mt-1">支持拖拽或点击上传</p>
        </div>
      </div>
    );
  }

  const clipRight = `${100 - splitPosition}%`;

  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center justify-between px-4 py-2 bg-deep-space-800/50 border-b border-deep-space-700">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-deep-space-200 truncate max-w-[200px]">
            {currentImage.name}
          </span>
          <span className="text-xs text-deep-space-500 font-mono">
            {currentImage.width} × {currentImage.height}
          </span>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={() => setShowOriginal(!showOriginal)}
            className={`p-2 rounded-lg transition-colors ${
              showOriginal ? 'bg-neon-blue-500/20 text-neon-blue-400' : 'text-deep-space-400 hover:text-deep-space-200'
            }`}
            title={showOriginal ? '隐藏原图对比' : '显示原图对比'}
          >
            {showOriginal ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
          </button>
          <button
            onClick={handleZoomOut}
            className="p-2 rounded-lg text-deep-space-400 hover:text-deep-space-200 hover:bg-deep-space-700 transition-colors"
            title="缩小"
          >
            <ZoomOut className="w-4 h-4" />
          </button>
          <span className="text-xs text-deep-space-400 font-mono w-12 text-center">
            {Math.round(zoom * 100)}%
          </span>
          <button
            onClick={handleZoomIn}
            className="p-2 rounded-lg text-deep-space-400 hover:text-deep-space-200 hover:bg-deep-space-700 transition-colors"
            title="放大"
          >
            <ZoomIn className="w-4 h-4" />
          </button>
          <button
            onClick={handleResetView}
            className="p-2 rounded-lg text-deep-space-400 hover:text-deep-space-200 hover:bg-deep-space-700 transition-colors"
            title="重置视图"
          >
            <Move className="w-4 h-4" />
          </button>
          <button
            onClick={toggleFullscreen}
            className="p-2 rounded-lg text-deep-space-400 hover:text-deep-space-200 hover:bg-deep-space-700 transition-colors"
            title="全屏"
          >
            <Maximize2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      <div
        ref={containerRef}
        className="flex-1 relative canvas-grid overflow-hidden cursor-crosshair select-none"
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onWheel={handleWheel}
      >
        <canvas
          ref={originalCanvasRef}
          className="absolute inset-0 w-full h-full"
        />
        
        <AnimatePresence>
          {showOriginal && currentImage.processedData && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute inset-0"
              style={{ clipPath: `inset(0 ${clipRight} 0 0)` }}
            >
              <canvas
                ref={processedCanvasRef}
                className="w-full h-full"
              />
            </motion.div>
          )}
        </AnimatePresence>

        {showOriginal && currentImage.processedData && (
          <>
            <div
              className="absolute top-0 bottom-0 w-0.5 bg-neon-blue-400 cursor-col-resize split-handle z-10"
              style={{ left: `${splitPosition}%`, transform: 'translateX(-50%)' }}
              onMouseDown={(e) => {
                e.stopPropagation();
                setIsDraggingSplit(true);
              }}
            >
              <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-8 h-12 bg-neon-blue-400 rounded-lg flex flex-col items-center justify-center gap-1 shadow-lg">
                <div className="w-4 h-0.5 bg-white rounded-full" />
                <div className="w-4 h-0.5 bg-white rounded-full" />
                <div className="w-4 h-0.5 bg-white rounded-full" />
              </div>
            </div>

            <div className="absolute top-4 left-4 px-3 py-1.5 bg-deep-space-900/80 backdrop-blur-sm rounded-lg text-xs text-deep-space-300 border border-deep-space-700">
              原图
            </div>
            <div className="absolute top-4 right-4 px-3 py-1.5 bg-neon-blue-500/80 backdrop-blur-sm rounded-lg text-xs text-white border border-neon-blue-400">
              处理后
            </div>
          </>
        )}

        <AnimatePresence>
          {currentImage.status === 'processing' && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute inset-0 bg-deep-space-900/70 backdrop-blur-sm flex items-center justify-center z-20"
            >
              <div className="text-center">
                <div className="w-16 h-16 border-4 border-neon-blue-400/30 border-t-neon-blue-400 rounded-full animate-spin mx-auto mb-4" />
                <p className="text-neon-blue-400 font-medium">正在处理...</p>
                <p className="text-deep-space-400 text-sm mt-1">{currentImage.progress}%</p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <div className="px-4 py-2 bg-deep-space-800/50 border-t border-deep-space-700 flex items-center justify-between text-xs text-deep-space-500">
        <span>拖拽分割线对比效果 • 滚轮缩放 • Alt+拖拽平移</span>
        <span className="font-mono">
          算法: {currentImage.params?.algorithm.toUpperCase() || '未设置'}
        </span>
      </div>
    </div>
  );
}
