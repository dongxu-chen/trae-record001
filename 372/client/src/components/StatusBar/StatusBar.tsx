import React, { useState, useEffect } from 'react';
import { useAnnotationStore } from '@/store/useAnnotationStore';
import { screenToImage } from '@/utils/canvas';
import type { Point } from '@/types/annotation';

export const StatusBar: React.FC = () => {
  const { canvasState, annotations, currentTool, currentImageId, images } = useAnnotationStore();
  const [mousePos, setMousePos] = useState<Point | null>(null);
  const [currentTime, setCurrentTime] = useState(new Date());

  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      const canvas = document.querySelector('canvas');
      if (canvas) {
        const rect = canvas.getBoundingClientRect();
        setMousePos({
          x: e.clientX - rect.left,
          y: e.clientY - rect.top,
        });
      }
    };

    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

  const imagePos = mousePos && canvasState.imageWidth > 0
    ? screenToImage(mousePos, canvasState)
    : null;

  const currentImage = images.find(img => img.id === currentImageId);

  const getToolName = () => {
    switch (currentTool) {
      case 'select': return '选择';
      case 'polygon': return '多边形';
      case 'point': return '点';
      case 'rectangle': return '矩形';
      case 'brush': return '画笔';
      case 'sam': return 'SAM点击';
      default: return currentTool;
    }
  };

  return (
    <footer className="h-7 bg-slate-900 border-t border-slate-700 flex items-center justify-between px-4 text-xs text-slate-400">
      <div className="flex items-center gap-4">
        {imagePos && (
          <div className="flex items-center gap-2">
            <span className="text-slate-500">图像坐标:</span>
            <span className="font-mono text-cyan-400">
              ({Math.round(imagePos.x)}, {Math.round(imagePos.y)})
            </span>
          </div>
        )}
        
        {mousePos && (
          <div className="flex items-center gap-2">
            <span className="text-slate-500">屏幕坐标:</span>
            <span className="font-mono">
              ({Math.round(mousePos.x)}, {Math.round(mousePos.y)})
            </span>
          </div>
        )}
      </div>

      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <span className="text-slate-500">工具:</span>
          <span className="text-white">{getToolName()}</span>
        </div>

        <div className="h-4 w-px bg-slate-700" />

        <div className="flex items-center gap-2">
          <span className="text-slate-500">缩放:</span>
          <span className="font-mono text-cyan-400">
            {Math.round(canvasState.scale * 100)}%
          </span>
        </div>

        {currentImage && (
          <>
            <div className="h-4 w-px bg-slate-700" />
            <div className="flex items-center gap-2">
              <span className="text-slate-500">尺寸:</span>
              <span className="font-mono">
                {currentImage.width} × {currentImage.height}
              </span>
            </div>
          </>
        )}

        <div className="h-4 w-px bg-slate-700" />

        <div className="flex items-center gap-2">
          <span className="text-slate-500">标注:</span>
          <span className="text-white font-medium">{annotations.length}</span>
        </div>

        <div className="h-4 w-px bg-slate-700" />

        <div className="font-mono text-slate-500">
          {currentTime.toLocaleTimeString('zh-CN', { hour12: false })}
        </div>
      </div>
    </footer>
  );
};
