import { useRef, useCallback } from 'react';
import { useAppStore } from '@/store/useAppStore';
import { useImageProcessor } from '@/hooks/useImageProcessor';
import { getColorblindFilterUrl } from '@/components/ColorblindSvgFilters';

export default function ColorblindPreview() {
  const originalImageRef = useRef<HTMLImageElement>(null);
  const simulatedImageRef = useRef<HTMLImageElement>(null);
  const {
    originalImage,
    selectedType,
    showCompare,
    comparePosition,
    setComparePosition,
  } = useAppStore();
  const { pickColor } = useImageProcessor();

  const handleImageClick = useCallback(
    (e: React.MouseEvent<HTMLImageElement>) => {
      if (!originalImage) return;
      const img = e.currentTarget;
      const rect = img.getBoundingClientRect();
      const scaleX = originalImage.width / rect.width;
      const scaleY = originalImage.height / rect.height;
      const x = Math.floor((e.clientX - rect.left) * scaleX);
      const y = Math.floor((e.clientY - rect.top) * scaleY);
      pickColor(x, y);
    },
    [originalImage, pickColor]
  );

  const handleSliderMouseDown = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      const updatePosition = (clientX: number) => {
        const container = e.currentTarget.closest('.preview-container');
        if (container) {
          const rect = (container as HTMLElement).getBoundingClientRect();
          const pct = Math.min(100, Math.max(0, ((clientX - rect.left) / rect.width) * 100));
          setComparePosition(pct);
        }
      };

      updatePosition(e.clientX);

      const handleMouseMove = (moveEvent: MouseEvent) => {
        updatePosition(moveEvent.clientX);
      };

      const handleMouseUp = () => {
        window.removeEventListener('mousemove', handleMouseMove);
        window.removeEventListener('mouseup', handleMouseUp);
      };

      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleMouseUp);
    },
    [setComparePosition]
  );

  if (!originalImage) return null;

  const canvas = document.createElement('canvas');
  canvas.width = originalImage.width;
  canvas.height = originalImage.height;
  const ctx = canvas.getContext('2d')!;
  ctx.putImageData(originalImage, 0, 0);
  const dataUrl = canvas.toDataURL();

  return (
    <div className="preview-container relative w-full h-full rounded-xl overflow-hidden bg-zinc-900">
      {showCompare ? (
        <div className="relative w-full h-full flex items-center justify-center">
          <div className="relative w-full h-full max-h-[60vh]">
            <img
              ref={simulatedImageRef}
              src={dataUrl}
              alt="色盲模拟视图"
              className="absolute inset-0 w-full h-full object-contain"
              style={{ filter: getColorblindFilterUrl(selectedType), cursor: 'crosshair' }}
              onClick={handleImageClick}
              draggable={false}
            />

            <div
              className="absolute inset-0 overflow-hidden"
              style={{ width: `${comparePosition}%` }}
            >
              <img
                ref={originalImageRef}
                src={dataUrl}
                alt="原始视图"
                className="w-full h-full object-contain"
                style={{ cursor: 'crosshair', minWidth: `${(100 / comparePosition) * 100}%` }}
                onClick={handleImageClick}
                draggable={false}
              />
            </div>

            <div
              className="absolute top-0 bottom-0 w-0.5 bg-white shadow-lg cursor-ew-resize z-10"
              style={{ left: `${comparePosition}%` }}
              onMouseDown={handleSliderMouseDown}
            >
              <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-8 h-8 rounded-full bg-white shadow-lg flex items-center justify-center">
                <div className="flex gap-0.5">
                  <div className="w-0.5 h-3 bg-zinc-800 rounded" />
                  <div className="w-0.5 h-3 bg-zinc-800 rounded" />
                </div>
              </div>
            </div>

            <div className="absolute top-3 left-3 px-2 py-1 rounded bg-black/60 text-xs text-white font-mono">
              原始
            </div>
            <div className="absolute top-3 right-3 px-2 py-1 rounded bg-black/60 text-xs text-[#ff6b35] font-mono">
              {selectedType}
            </div>
          </div>
        </div>
      ) : (
        <div className="w-full h-full flex items-center justify-center max-h-[60vh]">
          <img
            ref={simulatedImageRef}
            src={dataUrl}
            alt="色盲模拟视图"
            className="w-full h-full object-contain"
            style={{ filter: getColorblindFilterUrl(selectedType), cursor: 'crosshair' }}
            onClick={handleImageClick}
            draggable={false}
          />
        </div>
      )}
    </div>
  );
}
