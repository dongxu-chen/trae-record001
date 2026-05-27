import React, { useEffect, useRef, useState, useCallback } from 'react';
import type { Point, CanvasState, Annotation } from '@/types/annotation';
import { useAnnotationStore } from '@/store/useAnnotationStore';
import { getMousePos, drawGrid, drawCrosshair, hexToRgba, imageToScreen, createMaskCanvas } from '@/utils/canvas';
import { BaseTool } from '@/tools/BaseTool';
import { SelectTool } from '@/tools/SelectTool';
import { PolygonTool } from '@/tools/PolygonTool';
import { PointTool } from '@/tools/PointTool';
import { RectangleTool } from '@/tools/RectangleTool';
import { BrushTool } from '@/tools/BrushTool';
import { SAMTool } from '@/tools/SAMTool';
import { wsClient } from '@/services/wsClient';

interface AnnotationCanvasProps {
  imageUrl: string | null;
}

export const AnnotationCanvas: React.FC<AnnotationCanvasProps> = ({ imageUrl }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const imageRef = useRef<HTMLImageElement | null>(null);
  const [isImageLoaded, setIsImageLoaded] = useState(false);
  const [isSpacePressed, setIsSpacePressed] = useState(false);
  const [isPanning, setIsPanning] = useState(false);
  const panStartRef = useRef<{ x: number; y: number; offsetX: number; offsetY: number } | null>(null);
  const [mousePos, setMousePos] = useState<Point | null>(null);

  const {
    annotations,
    currentTool,
    selectedAnnotationId,
    canvasState,
    setCanvasState,
    addAnnotation,
    updateAnnotation,
    selectAnnotation,
    brushSize,
    samLoading,
    currentImageId,
    currentColor,
  } = useAnnotationStore();

  const currentToolRef = useRef<BaseTool | null>(null);
  const selectToolRef = useRef<SelectTool | null>(null);
  const samToolRef = useRef<SAMTool | null>(null);

  const toolCallbacks = {
    onAnnotationStart: () => {},
    onAnnotationComplete: (annotationData: Partial<Annotation>) => {
      if (annotationData.id) {
        updateAnnotation(annotationData.id, annotationData);
      } else {
        addAnnotation(annotationData as any);
      }
    },
    onPreviewUpdate: () => {
      requestRender();
    },
    getCanvasState: () => canvasState,
  };

  const initTools = useCallback(() => {
    selectToolRef.current = new SelectTool(toolCallbacks);
    samToolRef.current = new SAMTool(toolCallbacks);
  }, []);

  useEffect(() => {
    initTools();
    wsClient.connect().catch(() => {});
    return () => {
      wsClient.disconnect();
    };
  }, [initTools]);

  useEffect(() => {
    if (currentTool === 'select') {
      currentToolRef.current = selectToolRef.current;
    } else if (currentTool === 'sam') {
      currentToolRef.current = samToolRef.current;
      if (samToolRef.current) {
        samToolRef.current.setImageId(currentImageId);
      }
    } else if (currentTool === 'polygon') {
      currentToolRef.current = new PolygonTool(toolCallbacks);
    } else if (currentTool === 'point') {
      currentToolRef.current = new PointTool(toolCallbacks);
    } else if (currentTool === 'rectangle') {
      currentToolRef.current = new RectangleTool(toolCallbacks);
    } else if (currentTool === 'brush') {
      currentToolRef.current = new BrushTool(toolCallbacks, brushSize);
    }
    requestRender();
  }, [currentTool, brushSize, currentImageId]);

  useEffect(() => {
    if (selectToolRef.current) {
      selectToolRef.current.setAnnotations(annotations);
      selectToolRef.current.setSelectedId(selectedAnnotationId);
    }
    requestRender();
  }, [annotations, selectedAnnotationId]);

  useEffect(() => {
    if (!imageUrl) {
      setIsImageLoaded(false);
      return;
    }

    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.onload = () => {
      imageRef.current = img;
      setIsImageLoaded(true);
      fitImageToCanvas();
    };
    img.onerror = () => {
      setIsImageLoaded(false);
    };
    img.src = imageUrl;
  }, [imageUrl]);

  const fitImageToCanvas = () => {
    if (!containerRef.current || !imageRef.current) return;
    
    const container = containerRef.current;
    const img = imageRef.current;
    const containerWidth = container.clientWidth;
    const containerHeight = container.clientHeight;
    
    const scaleX = containerWidth / img.width;
    const scaleY = containerHeight / img.height;
    const scale = Math.min(scaleX, scaleY, 1);
    
    const offsetX = (containerWidth - img.width * scale) / 2;
    const offsetY = (containerHeight - img.height * scale) / 2;
    
    setCanvasState({
      scale,
      offsetX,
      offsetY,
      imageWidth: img.width,
      imageHeight: img.height,
    });
  };

  const requestRender = useCallback(() => {
    requestAnimationFrame(render);
  }, []);

  const render = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    
    const container = containerRef.current;
    if (!container) return;
    
    const dpr = window.devicePixelRatio || 1;
    const rect = container.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    canvas.style.width = `${rect.width}px`;
    canvas.style.height = `${rect.height}px`;
    ctx.scale(dpr, dpr);
    
    ctx.fillStyle = '#0f172a';
    ctx.fillRect(0, 0, rect.width, rect.height);
    
    drawGrid(ctx, rect.width, rect.height, 20);
    
    if (isImageLoaded && imageRef.current) {
      ctx.save();
      ctx.drawImage(
        imageRef.current,
        canvasState.offsetX,
        canvasState.offsetY,
        canvasState.imageWidth * canvasState.scale,
        canvasState.imageHeight * canvasState.scale
      );
      ctx.restore();
      
      renderAnnotations(ctx);
    }
    
    if (currentToolRef.current && isImageLoaded) {
      currentToolRef.current.render(ctx, canvasState);
    }
    
    if (mousePos && isImageLoaded && currentTool !== 'select') {
      drawCrosshair(ctx, mousePos.x, mousePos.y, 15);
    }
    
    if (samLoading) {
      ctx.fillStyle = 'rgba(0, 0, 0, 0.5)';
      ctx.fillRect(0, 0, rect.width, rect.height);
      ctx.fillStyle = '#06b6d4';
      ctx.font = '16px sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText('SAM 模型正在分割...', rect.width / 2, rect.height / 2);
    }
  }, [isImageLoaded, canvasState, annotations, mousePos, samLoading, currentTool]);

  const renderAnnotations = (ctx: CanvasRenderingContext2D) => {
    annotations.forEach((annotation) => {
      if (!annotation.visible) return;
      
      ctx.save();
      const color = annotation.color;
      const fillStyle = hexToRgba(color, 0.4);
      const strokeStyle = color;
      
      switch (annotation.type) {
        case 'polygon': {
          const points = annotation.points.map(p => imageToScreen(p, canvasState));
          if (points.length < 2) break;
          
          ctx.fillStyle = fillStyle;
          ctx.strokeStyle = strokeStyle;
          ctx.lineWidth = 2;
          
          ctx.beginPath();
          ctx.moveTo(points[0].x, points[0].y);
          for (let i = 1; i < points.length; i++) {
            ctx.lineTo(points[i].x, points[i].y);
          }
          if (annotation.closed) {
            ctx.closePath();
          }
          ctx.fill();
          ctx.stroke();
          
          points.forEach((p, i) => {
            if (selectedAnnotationId === annotation.id) {
              ctx.fillStyle = i === 0 ? '#22c55e' : strokeStyle;
              ctx.beginPath();
              ctx.arc(p.x, p.y, 5, 0, Math.PI * 2);
              ctx.fill();
            }
          });
          break;
        }
        
        case 'rectangle': {
          const x = annotation.x * canvasState.scale + canvasState.offsetX;
          const y = annotation.y * canvasState.scale + canvasState.offsetY;
          const w = annotation.width * canvasState.scale;
          const h = annotation.height * canvasState.scale;
          
          ctx.fillStyle = fillStyle;
          ctx.strokeStyle = strokeStyle;
          ctx.lineWidth = 2;
          ctx.fillRect(x, y, w, h);
          ctx.strokeRect(x, y, w, h);
          break;
        }
        
        case 'point': {
          const pos = imageToScreen(annotation.position, canvasState);
          const r = annotation.radius * canvasState.scale;
          
          ctx.fillStyle = fillStyle;
          ctx.strokeStyle = strokeStyle;
          ctx.lineWidth = 2;
          ctx.beginPath();
          ctx.arc(pos.x, pos.y, r, 0, Math.PI * 2);
          ctx.fill();
          ctx.stroke();
          break;
        }
        
        case 'brush': {
          const points = annotation.points.map(p => imageToScreen(p, canvasState));
          if (points.length < 2) break;
          
          ctx.strokeStyle = hexToRgba(color, 0.8);
          ctx.lineWidth = annotation.strokeWidth * canvasState.scale;
          ctx.lineCap = 'round';
          ctx.lineJoin = 'round';
          
          ctx.beginPath();
          ctx.moveTo(points[0].x, points[0].y);
          for (let i = 1; i < points.length; i++) {
            ctx.lineTo(points[i].x, points[i].y);
          }
          ctx.stroke();
          break;
        }
        
        case 'sam': {
          const maskCanvas = createMaskCanvas(
            annotation.mask,
            annotation.width,
            annotation.height,
            color
          );
          
          ctx.globalAlpha = 0.5;
          ctx.drawImage(
            maskCanvas,
            canvasState.offsetX,
            canvasState.offsetY,
            annotation.width * canvasState.scale,
            annotation.height * canvasState.scale
          );
          ctx.globalAlpha = 1;
          
          ctx.strokeStyle = strokeStyle;
          ctx.lineWidth = 1.5;
          ctx.strokeRect(
            canvasState.offsetX,
            canvasState.offsetY,
            annotation.width * canvasState.scale,
            annotation.height * canvasState.scale
          );
          break;
        }
      }
      
      ctx.restore();
    });
  };

  useEffect(() => {
    const handleResize = () => {
      requestRender();
    };
    
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [requestRender]);

  useEffect(() => {
    requestRender();
  }, [requestRender, isImageLoaded]);

  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!isImageLoaded) return;
    
    if (isSpacePressed || e.button === 1) {
      setIsPanning(true);
      panStartRef.current = {
        x: e.clientX,
        y: e.clientY,
        offsetX: canvasState.offsetX,
        offsetY: canvasState.offsetY,
      };
      return;
    }
    
    if (e.button === 2) {
      if (currentToolRef.current) {
        currentToolRef.current.reset();
        requestRender();
      }
      return;
    }
    
    const pos = getMousePos(e);
    if (currentToolRef.current) {
      currentToolRef.current.onMouseDown(e, pos);
    }
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const pos = getMousePos(e);
    setMousePos(pos);
    
    if (isPanning && panStartRef.current) {
      const dx = e.clientX - panStartRef.current.x;
      const dy = e.clientY - panStartRef.current.y;
      setCanvasState({
        offsetX: panStartRef.current.offsetX + dx,
        offsetY: panStartRef.current.offsetY + dy,
      });
      return;
    }
    
    if (!isImageLoaded) return;
    
    if (currentToolRef.current) {
      currentToolRef.current.onMouseMove(e, pos);
    }
  };

  const handleMouseUp = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (isPanning) {
      setIsPanning(false);
      panStartRef.current = null;
      return;
    }
    
    if (!isImageLoaded) return;
    
    const pos = getMousePos(e);
    if (currentToolRef.current) {
      currentToolRef.current.onMouseUp(e, pos);
    }
  };

  const handleMouseLeave = (e: React.MouseEvent<HTMLCanvasElement>) => {
    setMousePos(null);
    
    if (isPanning) {
      setIsPanning(false);
      panStartRef.current = null;
    }
    
    if (currentToolRef.current) {
      currentToolRef.current.onMouseLeave(e);
    }
  };

  const handleWheel = (e: React.WheelEvent<HTMLCanvasElement>) => {
    if (!isImageLoaded) return;
    
    e.preventDefault();
    
    const pos = getMousePos(e);
    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    const newScale = Math.max(0.1, Math.min(10, canvasState.scale * delta));
    
    const imageX = (pos.x - canvasState.offsetX) / canvasState.scale;
    const imageY = (pos.y - canvasState.offsetY) / canvasState.scale;
    
    const newOffsetX = pos.x - imageX * newScale;
    const newOffsetY = pos.y - imageY * newScale;
    
    setCanvasState({
      scale: newScale,
      offsetX: newOffsetX,
      offsetY: newOffsetY,
    });
  };

  const handleContextMenu = (e: React.MouseEvent) => {
    e.preventDefault();
  };

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.code === 'Space' && !e.repeat) {
        setIsSpacePressed(true);
        if (containerRef.current) {
          containerRef.current.style.cursor = 'grab';
        }
      }
      
      if (e.code === 'Escape') {
        if (currentToolRef.current) {
          currentToolRef.current.reset();
          selectAnnotation(null);
          requestRender();
        }
      }
      
      if ((e.ctrlKey || e.metaKey) && e.code === 'KeyZ' && !e.shiftKey) {
        e.preventDefault();
        useAnnotationStore.getState().undo();
      }
      
      if ((e.ctrlKey || e.metaKey) && (e.code === 'KeyY' || (e.code === 'KeyZ' && e.shiftKey))) {
        e.preventDefault();
        useAnnotationStore.getState().redo();
      }
    };
    
    const handleKeyUp = (e: KeyboardEvent) => {
      if (e.code === 'Space') {
        setIsSpacePressed(false);
        if (containerRef.current) {
          containerRef.current.style.cursor = currentToolRef.current?.getCursor() || 'crosshair';
        }
      }
    };
    
    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('keyup', handleKeyUp);
    
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('keyup', handleKeyUp);
    };
  }, [requestRender, selectAnnotation]);

  return (
    <div
      ref={containerRef}
      className="relative w-full h-full overflow-hidden bg-slate-900"
      style={{ cursor: isPanning ? 'grabbing' : (isSpacePressed ? 'grab' : (currentToolRef.current?.getCursor() || 'crosshair')) }}
    >
      <canvas
        ref={canvasRef}
        className="absolute inset-0"
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseLeave}
        onWheel={handleWheel}
        onContextMenu={handleContextMenu}
      />
      
      {!imageUrl && (
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="text-center text-slate-400">
            <div className="text-6xl mb-4">🖼️</div>
            <p className="text-lg">请上传一张图像开始标注</p>
            <p className="text-sm mt-2">支持 JPG、PNG、BMP、WebP 等格式</p>
          </div>
        </div>
      )}
    </div>
  );
};
