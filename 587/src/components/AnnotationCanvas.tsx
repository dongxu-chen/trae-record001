import React, { useRef, useEffect, useCallback, useMemo } from 'react';
import { Annotation, Point, AnnotationType, RelativePoint } from '../../shared/types';
import { useStore } from '../store/useStore';
import { toRelative, toAbsolute, getDefaultChartBounds, ChartBounds } from '../utils/coordinateUtils';

interface AnnotationCanvasProps {
  width: number;
  height: number;
  onAddAnnotation: (annotation: Omit<Annotation, 'id' | 'createdAt' | 'updatedAt' | 'version'>) => void;
  onUpdateAnnotation: (annotationId: string, updates: Partial<Annotation>) => void;
}

const AnnotationCanvas: React.FC<AnnotationCanvasProps> = ({
  width,
  height,
  onAddAnnotation,
  onUpdateAnnotation,
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const {
    annotations,
    activeTool,
    selectedColor,
    selectedAnnotationId,
    setSelectedAnnotationId,
    currentUser,
    isCreating,
    setIsCreating,
    tempAnnotation,
    setTempAnnotation,
    users,
    permissions,
    chartBounds,
    setChartBounds,
  } = useStore();

  const bounds = useMemo(() => {
    if (chartBounds) return chartBounds;
    return getDefaultChartBounds(width, height);
  }, [width, height, chartBounds]);

  useEffect(() => {
    setChartBounds(bounds);
  }, [bounds, setChartBounds]);

  const dragState = useRef<{
    isDragging: boolean;
    annotationId: string | null;
    startPoint: Point | null;
    startRelativePosition: RelativePoint | null;
    startRelativeEndPosition: RelativePoint | null;
    type: 'move' | 'resize' | 'create' | null;
  }>({
    isDragging: false,
    annotationId: null,
    startPoint: null,
    startRelativePosition: null,
    startRelativeEndPosition: null,
    type: null,
  });

  const render = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.clearRect(0, 0, width, height);

    annotations.forEach((annotation) => {
      const absAnnotation = {
        ...annotation,
        position: toAbsolute(annotation.position, bounds),
        endPosition: annotation.endPosition ? toAbsolute(annotation.endPosition, bounds) : undefined,
      };
      drawAnnotation(ctx, absAnnotation as Annotation, annotation.id === selectedAnnotationId);
    });

    if (tempAnnotation) {
      const absTemp = {
        ...tempAnnotation,
        position: tempAnnotation.position ? toAbsolute(tempAnnotation.position as RelativePoint, bounds) : { x: 0, y: 0 },
        endPosition: tempAnnotation.endPosition ? toAbsolute(tempAnnotation.endPosition as RelativePoint, bounds) : undefined,
      };
      drawAnnotation(ctx, absTemp as Annotation, true);
    }

    users.forEach((user) => {
      if (user.cursor && user.id !== currentUser?.id) {
        drawCursor(ctx, user.cursor, user.color, user.name);
      }
    });
  }, [annotations, selectedAnnotationId, tempAnnotation, users, currentUser, width, height, bounds]);

  const drawAnnotation = (
    ctx: CanvasRenderingContext2D,
    annotation: Annotation,
    isSelected: boolean
  ) => {
    ctx.save();

    if (annotation.type === 'text') {
      drawTextAnnotation(ctx, annotation, isSelected);
    } else if (annotation.type === 'arrow') {
      drawArrowAnnotation(ctx, annotation, isSelected);
    } else if (annotation.type === 'highlight') {
      drawHighlightAnnotation(ctx, annotation, isSelected);
    }

    ctx.restore();
  };

  const drawTextAnnotation = (
    ctx: CanvasRenderingContext2D,
    annotation: Annotation,
    isSelected: boolean
  ) => {
    const { position, color, content = '' } = annotation;
    
    ctx.font = '14px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
    const textMetrics = ctx.measureText(content);
    const padding = 8;
    const textWidth = textMetrics.width + padding * 2;
    const textHeight = 28;

    ctx.fillStyle = color + '20';
    ctx.strokeStyle = color;
    ctx.lineWidth = isSelected ? 2 : 1;
    ctx.beginPath();
    ctx.roundRect(position.x, position.y - textHeight, textWidth, textHeight, 6);
    ctx.fill();
    ctx.stroke();

    ctx.fillStyle = '#1f2937';
    ctx.fillText(content, position.x + padding, position.y - 8);

    if (isSelected) {
      drawHandles(ctx, position.x, position.y - textHeight, textWidth, textHeight, color);
    }
  };

  const drawArrowAnnotation = (
    ctx: CanvasRenderingContext2D,
    annotation: Annotation,
    isSelected: boolean
  ) => {
    const { position, endPosition, color } = annotation;
    if (!endPosition) return;

    ctx.strokeStyle = color;
    ctx.lineWidth = isSelected ? 3 : 2;
    ctx.lineCap = 'round';

    ctx.beginPath();
    ctx.moveTo(position.x, position.y);
    ctx.lineTo(endPosition.x, endPosition.y);
    ctx.stroke();

    const angle = Math.atan2(endPosition.y - position.y, endPosition.x - position.x);
    const arrowLength = 12;
    const arrowAngle = Math.PI / 6;

    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.moveTo(endPosition.x, endPosition.y);
    ctx.lineTo(
      endPosition.x - arrowLength * Math.cos(angle - arrowAngle),
      endPosition.y - arrowLength * Math.sin(angle - arrowAngle)
    );
    ctx.lineTo(
      endPosition.x - arrowLength * Math.cos(angle + arrowAngle),
      endPosition.y - arrowLength * Math.sin(angle + arrowAngle)
    );
    ctx.closePath();
    ctx.fill();

    if (isSelected) {
      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.arc(position.x, position.y, 5, 0, Math.PI * 2);
      ctx.fill();
      ctx.beginPath();
      ctx.arc(endPosition.x, endPosition.y, 5, 0, Math.PI * 2);
      ctx.fill();
    }
  };

  const drawHighlightAnnotation = (
    ctx: CanvasRenderingContext2D,
    annotation: Annotation,
    isSelected: boolean
  ) => {
    const { position, endPosition, color } = annotation;
    if (!endPosition) return;

    const x = Math.min(position.x, endPosition.x);
    const y = Math.min(position.y, endPosition.y);
    const w = Math.abs(endPosition.x - position.x);
    const h = Math.abs(endPosition.y - position.y);

    ctx.fillStyle = color + '40';
    ctx.strokeStyle = color;
    ctx.lineWidth = isSelected ? 2 : 1;
    ctx.setLineDash([5, 3]);
    ctx.beginPath();
    ctx.roundRect(x, y, w, h, 4);
    ctx.fill();
    ctx.stroke();
    ctx.setLineDash([]);

    if (isSelected) {
      drawHandles(ctx, x, y, w, h, color);
    }
  };

  const drawHandles = (
    ctx: CanvasRenderingContext2D,
    x: number,
    y: number,
    w: number,
    h: number,
    color: string
  ) => {
    const handleSize = 8;
    const positions = [
      [x - handleSize / 2, y - handleSize / 2],
      [x + w - handleSize / 2, y - handleSize / 2],
      [x - handleSize / 2, y + h - handleSize / 2],
      [x + w - handleSize / 2, y + h - handleSize / 2],
    ];

    ctx.fillStyle = '#fff';
    ctx.strokeStyle = color;
    ctx.lineWidth = 2;

    positions.forEach(([hx, hy]) => {
      ctx.fillRect(hx, hy, handleSize, handleSize);
      ctx.strokeRect(hx, hy, handleSize, handleSize);
    });
  };

  const drawCursor = (
    ctx: CanvasRenderingContext2D,
    cursor: Point,
    color: string,
    name: string
  ) => {
    ctx.save();
    ctx.strokeStyle = color;
    ctx.lineWidth = 2;

    ctx.beginPath();
    ctx.moveTo(cursor.x, cursor.y);
    ctx.lineTo(cursor.x + 12, cursor.y + 16);
    ctx.lineTo(cursor.x + 4, cursor.y + 12);
    ctx.lineTo(cursor.x + 8, cursor.y + 20);
    ctx.lineTo(cursor.x, cursor.y + 16);
    ctx.closePath();
    ctx.fillStyle = color;
    ctx.fill();
    ctx.stroke();

    ctx.font = '12px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
    const textMetrics = ctx.measureText(name);
    const padding = 4;
    
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.roundRect(cursor.x + 12, cursor.y, textMetrics.width + padding * 2, 20, 4);
    ctx.fill();
    
    ctx.fillStyle = '#fff';
    ctx.fillText(name, cursor.x + 12 + padding, cursor.y + 14);

    ctx.restore();
  };

  const hitTest = (x: number, y: number): string | null => {
    for (let i = annotations.length - 1; i >= 0; i--) {
      const annotation = annotations[i];
      const absAnnotation = {
        ...annotation,
        position: toAbsolute(annotation.position, bounds),
        endPosition: annotation.endPosition ? toAbsolute(annotation.endPosition, bounds) : undefined,
      };
      if (isPointInAnnotation(x, y, absAnnotation as Annotation)) {
        return annotation.id;
      }
    }
    return null;
  };

  const isPointInAnnotation = (x: number, y: number, annotation: Annotation): boolean => {
    const hitRadius = 10;
    
    if (annotation.type === 'text') {
      const ctx = canvasRef.current?.getContext('2d');
      if (!ctx) return false;
      ctx.font = '14px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
      const textMetrics = ctx.measureText(annotation.content || '');
      const padding = 8;
      const textWidth = textMetrics.width + padding * 2;
      const textHeight = 28;
      
      return (
        x >= annotation.position.x &&
        x <= annotation.position.x + textWidth &&
        y >= annotation.position.y - textHeight &&
        y <= annotation.position.y
      );
    } else if (annotation.type === 'arrow' && annotation.endPosition) {
      const dist = distanceToLine(
        x,
        y,
        annotation.position.x,
        annotation.position.y,
        annotation.endPosition.x,
        annotation.endPosition.y
      );
      return dist < hitRadius;
    } else if (annotation.type === 'highlight' && annotation.endPosition) {
      const minX = Math.min(annotation.position.x, annotation.endPosition.x);
      const maxX = Math.max(annotation.position.x, annotation.endPosition.x);
      const minY = Math.min(annotation.position.y, annotation.endPosition.y);
      const maxY = Math.max(annotation.position.y, annotation.endPosition.y);
      return x >= minX && x <= maxX && y >= minY && y <= maxY;
    }
    return false;
  };

  const distanceToLine = (
    px: number,
    py: number,
    x1: number,
    y1: number,
    x2: number,
    y2: number
  ): number => {
    const A = px - x1;
    const B = py - y1;
    const C = x2 - x1;
    const D = y2 - y1;

    const dot = A * C + B * D;
    const lenSq = C * C + D * D;
    let param = -1;
    if (lenSq !== 0) param = dot / lenSq;

    let xx, yy;

    if (param < 0) {
      xx = x1;
      yy = y1;
    } else if (param > 1) {
      xx = x2;
      yy = y2;
    } else {
      xx = x1 + param * C;
      yy = y1 + param * D;
    }

    const dx = px - xx;
    const dy = py - yy;
    return Math.sqrt(dx * dx + dy * dy);
  };

  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (permissions === 'read') return;
    
    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;

    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    if (activeTool !== 'select') {
      dragState.current = {
        isDragging: true,
        annotationId: null,
        startPoint: { x, y },
        startRelativePosition: null,
        startRelativeEndPosition: null,
        type: 'create',
      };
      setIsCreating(true);

      const relativePos = toRelative({ x, y }, bounds);
      const newAnnotation: Partial<Annotation> = {
        type: activeTool as AnnotationType,
        position: relativePos,
        endPosition: relativePos,
        color: selectedColor,
        content: activeTool === 'text' ? 'New note' : undefined,
        authorId: currentUser?.id || '',
        authorName: currentUser?.name || '',
      };
      setTempAnnotation(newAnnotation);
      return;
    }

    const hitAnnotationId = hitTest(x, y);
    
    if (hitAnnotationId) {
      const annotation = annotations.find((a) => a.id === hitAnnotationId);
      if (annotation) {
        setSelectedAnnotationId(hitAnnotationId);
        dragState.current = {
          isDragging: true,
          annotationId: hitAnnotationId,
          startPoint: { x, y },
          startRelativePosition: { ...annotation.position },
          startRelativeEndPosition: annotation.endPosition ? { ...annotation.endPosition } : null,
          type: 'move',
        };
      }
    } else {
      setSelectedAnnotationId(null);
    }
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;

    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    if (dragState.current.isDragging && dragState.current.type === 'create') {
      const relativePos = toRelative({ x, y }, bounds);
      setTempAnnotation((prev) => {
        if (!prev) return null;
        return {
          ...prev,
          endPosition: relativePos,
        };
      });
    } else if (dragState.current.isDragging && dragState.current.type === 'move' && dragState.current.annotationId) {
      const annotation = annotations.find((a) => a.id === dragState.current.annotationId);
      if (annotation && dragState.current.startPoint && dragState.current.startRelativePosition) {
        const startAbs = toAbsolute(dragState.current.startRelativePosition, bounds);
        const dx = x - dragState.current.startPoint.x;
        const dy = y - dragState.current.startPoint.y;

        const newAbsPosition = {
          x: startAbs.x + dx,
          y: startAbs.y + dy,
        };

        const updates: Partial<Annotation> = {
          position: toRelative(newAbsPosition, bounds),
        };

        if (annotation.endPosition && dragState.current.startRelativeEndPosition) {
          const startAbsEnd = toAbsolute(dragState.current.startRelativeEndPosition, bounds);
          const newAbsEndPosition = {
            x: startAbsEnd.x + dx,
            y: startAbsEnd.y + dy,
          };
          updates.endPosition = toRelative(newAbsEndPosition, bounds);
        }

        onUpdateAnnotation(annotation.id, updates);
      }
    }
  };

  const handleMouseUp = () => {
    if (permissions === 'read') return;
    
    if (dragState.current.type === 'create' && tempAnnotation && currentUser) {
      const finalAnnotation = {
        ...tempAnnotation,
        type: tempAnnotation.type as AnnotationType,
        position: tempAnnotation.position as RelativePoint,
        color: tempAnnotation.color as string,
        authorId: currentUser.id,
        authorName: currentUser.name,
      };
      onAddAnnotation(finalAnnotation as Omit<Annotation, 'id' | 'createdAt' | 'updatedAt' | 'version'>);
    }

    dragState.current = {
      isDragging: false,
      annotationId: null,
      startPoint: null,
      startRelativePosition: null,
      startRelativeEndPosition: null,
      type: null,
    };
    setIsCreating(false);
    setTempAnnotation(null);
  };

  const handleDoubleClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (permissions === 'read') return;
    
    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;

    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    const hitAnnotationId = hitTest(x, y);
    if (hitAnnotationId) {
      const annotation = annotations.find((a) => a.id === hitAnnotationId);
      if (annotation?.type === 'text') {
        const newContent = prompt('Edit annotation text:', annotation.content);
        if (newContent !== null) {
          onUpdateAnnotation(annotation.id, { content: newContent });
        }
      }
    }
  };

  useEffect(() => {
    render();
  }, [render]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (permissions === 'read') return;
      
      if (e.key === 'Delete' || e.key === 'Backspace') {
        if (selectedAnnotationId) {
          const isInputFocused = document.activeElement?.tagName === 'INPUT' || 
                                 document.activeElement?.tagName === 'TEXTAREA';
          if (!isInputFocused) {
            e.preventDefault();
            const annotation = annotations.find((a) => a.id === selectedAnnotationId);
            if (annotation) {
              onUpdateAnnotation(annotation.id, { content: '' });
            }
          }
        }
      }
      if (e.key === 'Escape') {
        setSelectedAnnotationId(null);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [selectedAnnotationId, annotations, onUpdateAnnotation, setSelectedAnnotationId, permissions]);

  const cursorStyle = permissions === 'read' ? 'not-allowed' : (activeTool !== 'select' ? 'crosshair' : 'default');

  return (
    <canvas
      ref={canvasRef}
      width={width}
      height={height}
      className="absolute top-0 left-0"
      style={{ zIndex: 10, cursor: cursorStyle }}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
      onDoubleClick={handleDoubleClick}
    />
  );
};

export default AnnotationCanvas;
