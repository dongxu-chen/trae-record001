import { useEffect, useState, useCallback, useRef } from 'react';
import { FILTER_DEFINITIONS } from '@/utils/shaderManager';
import { useShader } from '@/contexts/ShaderContext';
import useFilterStore from '@/store/filterStore';
import { ZoomIn, ZoomOut, RotateCcw, Split, Compass } from 'lucide-react';
import { cn } from '@/lib/utils';

interface PreviewCanvasProps {
  className?: string;
}

export default function PreviewCanvas({ className = '' }: PreviewCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [isInitialized, setIsInitialized] = useState(false);
  const { shaderManager, init } = useShader();
  const {
    images,
    selectedImageId,
    activeFilter,
    filterIntensity,
    filterParams,
    compareMode,
    zoomLevel,
    setZoomLevel,
    toggleCompareMode,
  } = useFilterStore();

  const selectedImage = images.find((img) => img.id === selectedImageId);
  const brightnessAnalysis = shaderManager?.getBrightnessAnalysis();
  const showDirectionIndicator = activeFilter === 'starburst' && brightnessAnalysis;

  useEffect(() => {
    if (canvasRef.current && !shaderManager) {
      init(canvasRef.current);
      setIsInitialized(true);
    }
  }, [init, shaderManager]);

  const loadImageToTexture = useCallback(async () => {
    if (!shaderManager || !selectedImage || !canvasRef.current) return;

    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.onload = () => {
      if (!shaderManager || !canvasRef.current) return;

      const canvas = canvasRef.current;
      const container = containerRef.current;
      const containerWidth = container?.clientWidth || 800;
      const containerHeight = container?.clientHeight || 600;

      const imgAspect = img.width / img.height;
      const containerAspect = containerWidth / containerHeight;

      let drawWidth, drawHeight;
      if (imgAspect > containerAspect) {
        drawWidth = containerWidth * 0.9;
        drawHeight = drawWidth / imgAspect;
      } else {
        drawHeight = containerHeight * 0.9;
        drawWidth = drawHeight * imgAspect;
      }

      canvas.width = drawWidth;
      canvas.height = drawHeight;

      shaderManager.loadTexture(img);
      renderFilter();
    };
    img.src = selectedImage.src;
  }, [selectedImage, shaderManager]);

  const renderFilter = useCallback(() => {
    if (!shaderManager) return;

    shaderManager.switchFilter(activeFilter);
    shaderManager.setUniform('uIntensity', filterIntensity);

    const filterDef = FILTER_DEFINITIONS.find((f) => f.id === activeFilter);
    if (filterDef) {
      for (const uniform of filterDef.uniforms) {
        const value = filterParams[uniform.name] ?? uniform.defaultValue;
        shaderManager.setUniform(uniform.name, value);
      }
    }

    shaderManager.render();
  }, [activeFilter, filterIntensity, filterParams, shaderManager]);

  useEffect(() => {
    if (isInitialized && selectedImage) {
      loadImageToTexture();
    }
  }, [isInitialized, selectedImage, loadImageToTexture]);

  useEffect(() => {
    if (isInitialized && selectedImage) {
      renderFilter();
    }
  }, [isInitialized, activeFilter, filterIntensity, filterParams, renderFilter]);

  const handleZoomIn = () => {
    setZoomLevel(Math.min(zoomLevel + 0.25, 3));
  };

  const handleZoomOut = () => {
    setZoomLevel(Math.max(zoomLevel - 0.25, 0.25));
  };

  const handleResetZoom = () => {
    setZoomLevel(1);
  };

  return (
    <div
      ref={containerRef}
      className={`relative w-full h-full flex items-center justify-center ${className}`}
    >
      {selectedImage ? (
        <>
          <div
            className="relative overflow-hidden rounded-lg"
            style={{ transform: `scale(${zoomLevel})`, transition: 'transform 0.2s' }}
          >
            <canvas
              ref={canvasRef}
              className="rounded-lg shadow-2xl neon-glow"
            />
            {compareMode && (
              <div className="absolute inset-0 flex">
                <div className="w-1/2 h-full overflow-hidden border-r-2 border-white/30">
                  <img
                    src={selectedImage.src}
                    alt="Original"
                    className="h-full object-cover"
                    style={{
                      width: `${canvasRef.current?.width || 0}px`,
                      height: `${canvasRef.current?.height || 0}px`,
                    }}
                  />
                </div>
              </div>
            )}

            {showDirectionIndicator && (
              <div
                className="absolute w-8 h-8 flex items-center justify-center pointer-events-none animate-pulse"
                style={{
                  left: `${brightnessAnalysis.center.x * 100}%`,
                  top: `${brightnessAnalysis.center.y * 100}%`,
                  transform: 'translate(-50%, -50%)',
                }}
              >
                <div className="relative">
                  <Compass
                    size={24}
                    className="text-neon-amber drop-shadow-lg"
                    style={{
                      transform: `rotate(${brightnessAnalysis.angle}rad)`,
                    }}
                  />
                  <div className="absolute inset-0 w-full h-full bg-neon-amber/30 rounded-full animate-ping" />
                </div>
              </div>
            )}
          </div>

          <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex items-center gap-2 glass-panel rounded-lg px-3 py-2">
            <button
              onClick={handleZoomOut}
              className="p-2 rounded-md hover:bg-surface-hover transition-colors"
              title="缩小"
            >
              <ZoomOut size={18} />
            </button>
            <span className="text-sm font-medium min-w-[50px] text-center">
              {Math.round(zoomLevel * 100)}%
            </span>
            <button
              onClick={handleZoomIn}
              className="p-2 rounded-md hover:bg-surface-hover transition-colors"
              title="放大"
            >
              <ZoomIn size={18} />
            </button>
            <div className="w-px h-6 bg-surface-border mx-1" />
            <button
              onClick={handleResetZoom}
              className="p-2 rounded-md hover:bg-surface-hover transition-colors"
              title="重置缩放"
            >
              <RotateCcw size={18} />
            </button>
            <button
              onClick={toggleCompareMode}
              className={cn(
                'p-2 rounded-md transition-colors',
                compareMode
                  ? 'bg-neon-cyan/20 text-neon-cyan'
                  : 'hover:bg-surface-hover'
              )}
              title="对比原图"
            >
              <Split size={18} />
            </button>
          </div>

          {showDirectionIndicator && (
            <div className="absolute top-4 left-4 glass-panel rounded-lg px-3 py-2 text-xs">
              <div className="flex items-center gap-2">
                <Compass size={14} className="text-neon-amber" />
                <span className="text-gray-300">自动方向检测</span>
              </div>
              <div className="mt-1 text-gray-500">
                亮区: ({brightnessAnalysis.center.x.toFixed(2)}, {brightnessAnalysis.center.y.toFixed(2)}) · 角度: {(brightnessAnalysis.angle * 180 / Math.PI).toFixed(0)}°
              </div>
            </div>
          )}
        </>
      ) : (
        <div className="text-center text-gray-400">
          <div className="w-32 h-32 mx-auto mb-4 rounded-full bg-surface-card flex items-center justify-center">
            <svg
              className="w-16 h-16 text-gray-500"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
              />
            </svg>
          </div>
          <p className="text-lg font-display">请上传图片开始编辑</p>
          <p className="text-sm mt-2">支持 JPG、PNG、WebP 格式</p>
        </div>
      )}
    </div>
  );
}
