import { useRef, useEffect, useCallback, useState, forwardRef, useImperativeHandle } from 'react';
import type { Point, SignatureStroke } from '../types';

export interface SignaturePadHandle {
  clear: () => void;
  undo: () => void;
  isEmpty: () => boolean;
  getCanvas: () => HTMLCanvasElement | null;
  getStrokes: () => SignatureStroke[];
  loadStrokes: (strokes: SignatureStroke[]) => void;
}

interface SignaturePadComponentProps {
  onSignatureChange?: (strokes: SignatureStroke[]) => void;
  onBeginStroke?: () => void;
  onEndStroke?: () => void;
  penColor?: string;
  penWidth?: number;
  backgroundColor?: string;
  width?: number;
  height?: number;
  readOnly?: boolean;
  pressureSensitivity?: boolean;
}

const SignaturePadComponent = forwardRef<SignaturePadHandle, SignaturePadComponentProps>(({
  onSignatureChange,
  onBeginStroke,
  onEndStroke,
  penColor = '#1a1a1a',
  penWidth = 3,
  backgroundColor = '#ffffff',
  width = 800,
  height = 400,
  readOnly = false,
  pressureSensitivity = true,
}, ref) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [strokes, setStrokes] = useState<SignatureStroke[]>([]);
  const isDrawingRef = useRef(false);
  const lastPointRef = useRef<Point | null>(null);
  const currentStrokeRef = useRef<Point[]>([]);
  const lastVelocityRef = useRef(0);
  const lastWidthRef = useRef(penWidth);

  const calculateVelocity = (p1: Point, p2: Point): number => {
    const dx = p2.x - p1.x;
    const dy = p2.y - p1.y;
    const distance = Math.sqrt(dx * dx + dy * dy);
    const time = Math.max(p2.time - p1.time, 1);
    return distance / time;
  };

  const calculateWidth = useCallback((velocity: number, baseWidth: number): number => {
    if (!pressureSensitivity) return baseWidth;

    const smoothedVelocity = lastVelocityRef.current * 0.7 + velocity * 0.3;
    lastVelocityRef.current = smoothedVelocity;

    const minWidth = baseWidth * 0.3;
    const maxWidth = baseWidth * 2.0;

    const maxVelocity = 2;
    const normalizedVelocity = Math.min(smoothedVelocity / maxVelocity, 1);

    const targetWidth = maxWidth - normalizedVelocity * (maxWidth - minWidth);
    const smoothedWidth = lastWidthRef.current * 0.6 + targetWidth * 0.4;
    lastWidthRef.current = smoothedWidth;

    return smoothedWidth;
  }, [pressureSensitivity]);

  const drawCurve = useCallback((ctx: CanvasRenderingContext2D, from: Point, to: Point, currentWidth: number) => {
    const midX = (from.x + to.x) / 2;
    const midY = (from.y + to.y) / 2;
    const cpX1 = from.x + (midX - from.x) * 0.5;
    const cpY1 = from.y + (midY - from.y) * 0.5;

    ctx.beginPath();
    ctx.strokeStyle = penColor;
    ctx.lineWidth = currentWidth;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';

    if (from.pressure !== undefined && to.pressure !== undefined) {
      const widthDiff = currentWidth - lastWidthRef.current;
      const steps = 5;
      for (let i = 0; i < steps; i++) {
        const t = i / steps;
        const x = from.x + (to.x - from.x) * t;
        const y = from.y + (to.y - from.y) * t;
        const w = lastWidthRef.current + widthDiff * t;
        ctx.beginPath();
        ctx.arc(x, y, w / 2, 0, Math.PI * 2);
        ctx.fillStyle = penColor;
        ctx.fill();
      }
    } else {
      ctx.moveTo(from.x, from.y);
      ctx.quadraticCurveTo(cpX1, cpY1, midX, midY);
      ctx.stroke();
    }
  }, [penColor]);

  const getCanvasPoint = useCallback((e: MouseEvent | TouchEvent): Point | null => {
    const canvas = canvasRef.current;
    if (!canvas) return null;

    const rect = canvas.getBoundingClientRect();
    let clientX: number, clientY: number, pressure: number;

    if ('touches' in e) {
      if (e.touches.length === 0) return null;
      const touch = e.touches[0];
      clientX = touch.clientX;
      clientY = touch.clientY;
      pressure = (touch as Touch & { force?: number }).force || 0.5;
    } else {
      clientX = e.clientX;
      clientY = e.clientY;
      pressure = 0.5;
    }

    return {
      x: clientX - rect.left,
      y: clientY - rect.top,
      pressure,
      time: Date.now(),
    };
  }, []);

  const startDrawing = useCallback((e: MouseEvent | TouchEvent) => {
    if (readOnly) return;
    e.preventDefault();

    const point = getCanvasPoint(e);
    if (!point) return;

    isDrawingRef.current = true;
    lastPointRef.current = point;
    currentStrokeRef.current = [point];
    lastVelocityRef.current = 0;
    lastWidthRef.current = penWidth;

    const canvas = canvasRef.current;
    const ctx = canvas?.getContext('2d');
    if (ctx) {
      ctx.beginPath();
      ctx.arc(point.x, point.y, penWidth / 2, 0, Math.PI * 2);
      ctx.fillStyle = penColor;
      ctx.fill();
    }

    onBeginStroke?.();
  }, [readOnly, getCanvasPoint, penColor, penWidth, onBeginStroke]);

  const draw = useCallback((e: MouseEvent | TouchEvent) => {
    if (!isDrawingRef.current || readOnly || !lastPointRef.current) return;
    e.preventDefault();

    const point = getCanvasPoint(e);
    if (!point) return;

    const velocity = calculateVelocity(lastPointRef.current, point);
    const currentWidth = calculateWidth(velocity, penWidth);

    point.pressure = Math.max(0.2, Math.min(1, 1 - velocity * 0.3));

    const canvas = canvasRef.current;
    const ctx = canvas?.getContext('2d');
    if (ctx) {
      drawCurve(ctx, lastPointRef.current, point, currentWidth);
    }

    currentStrokeRef.current.push(point);
    lastPointRef.current = point;
  }, [readOnly, getCanvasPoint, calculateWidth, penWidth, drawCurve]);

  const stopDrawing = useCallback(() => {
    if (!isDrawingRef.current) return;

    isDrawingRef.current = false;

    if (currentStrokeRef.current.length > 1) {
      const newStroke: SignatureStroke = {
        points: [...currentStrokeRef.current],
        color: penColor,
        width: penWidth,
      };

      setStrokes(prev => {
        const updated = [...prev, newStroke];
        onSignatureChange?.(updated);
        return updated;
      });
    }

    lastPointRef.current = null;
    currentStrokeRef.current = [];
    onEndStroke?.();
  }, [penColor, penWidth, onSignatureChange, onEndStroke]);

  const handleResize = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ratio = Math.max(window.devicePixelRatio || 1, 1);
    const rect = canvas.getBoundingClientRect();

    const imageData = strokes.length > 0 ? canvas.getContext('2d')?.getImageData(0, 0, canvas.width, canvas.height) : null;

    canvas.width = rect.width * ratio;
    canvas.height = rect.height * ratio;
    const ctx = canvas.getContext('2d');
    if (ctx) {
      ctx.scale(ratio, ratio);

      ctx.fillStyle = backgroundColor;
      ctx.fillRect(0, 0, rect.width, rect.height);

      if (imageData) {
        ctx.putImageData(imageData, 0, 0);
      } else {
        strokes.forEach(stroke => {
          if (stroke.points.length < 2) return;
          ctx.beginPath();
          ctx.strokeStyle = stroke.color;
          ctx.lineWidth = stroke.width;
          ctx.lineCap = 'round';
          ctx.lineJoin = 'round';

          stroke.points.forEach((point, i) => {
            if (i === 0) {
              ctx.moveTo(point.x, point.y);
            } else {
              const midX = (stroke.points[i - 1].x + point.x) / 2;
              const midY = (stroke.points[i - 1].y + point.y) / 2;
              ctx.quadraticCurveTo(stroke.points[i - 1].x, stroke.points[i - 1].y, midX, midY);
            }
          });
          ctx.stroke();
        });
      }
    }
  }, [strokes, backgroundColor]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (ctx) {
      ctx.fillStyle = backgroundColor;
      ctx.fillRect(0, 0, canvas.width, canvas.height);
    }

    handleResize();
    window.addEventListener('resize', handleResize);

    canvas.addEventListener('mousedown', startDrawing);
    canvas.addEventListener('mousemove', draw);
    canvas.addEventListener('mouseup', stopDrawing);
    canvas.addEventListener('mouseleave', stopDrawing);

    canvas.addEventListener('touchstart', startDrawing, { passive: false });
    canvas.addEventListener('touchmove', draw, { passive: false });
    canvas.addEventListener('touchend', stopDrawing);
    canvas.addEventListener('touchcancel', stopDrawing);

    return () => {
      window.removeEventListener('resize', handleResize);
      canvas.removeEventListener('mousedown', startDrawing);
      canvas.removeEventListener('mousemove', draw);
      canvas.removeEventListener('mouseup', stopDrawing);
      canvas.removeEventListener('mouseleave', stopDrawing);
      canvas.removeEventListener('touchstart', startDrawing);
      canvas.removeEventListener('touchmove', draw);
      canvas.removeEventListener('touchend', stopDrawing);
      canvas.removeEventListener('touchcancel', stopDrawing);
    };
  }, [startDrawing, draw, stopDrawing, handleResize, backgroundColor]);

  useEffect(() => {
    if (readOnly) {
      stopDrawing();
    }
  }, [readOnly, stopDrawing]);

  const clear = useCallback(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext('2d');
    if (ctx && canvas) {
      const rect = canvas.getBoundingClientRect();
      ctx.fillStyle = backgroundColor;
      ctx.fillRect(0, 0, rect.width, rect.height);
    }
    setStrokes([]);
    onSignatureChange?.([]);
  }, [backgroundColor, onSignatureChange]);

  const undo = useCallback(() => {
    if (strokes.length === 0) return;

    setStrokes(prev => {
      const updated = prev.slice(0, -1);
      const canvas = canvasRef.current;
      const ctx = canvas?.getContext('2d');
      if (ctx && canvas) {
        const rect = canvas.getBoundingClientRect();
        ctx.fillStyle = backgroundColor;
        ctx.fillRect(0, 0, rect.width, rect.height);

        updated.forEach(stroke => {
          if (stroke.points.length < 2) return;
          ctx.beginPath();
          ctx.strokeStyle = stroke.color;
          ctx.lineWidth = stroke.width;
          ctx.lineCap = 'round';
          ctx.lineJoin = 'round';

          stroke.points.forEach((point, i) => {
            if (i === 0) {
              ctx.moveTo(point.x, point.y);
            } else {
              const midX = (stroke.points[i - 1].x + point.x) / 2;
              const midY = (stroke.points[i - 1].y + point.y) / 2;
              ctx.quadraticCurveTo(stroke.points[i - 1].x, stroke.points[i - 1].y, midX, midY);
            }
          });
          ctx.stroke();
        });
      }

      onSignatureChange?.(updated);
      return updated;
    });
  }, [strokes.length, backgroundColor, onSignatureChange]);

  const isEmpty = useCallback(() => {
    return strokes.length === 0;
  }, [strokes]);

  const getCanvas = useCallback(() => {
    return canvasRef.current;
  }, []);

  const getStrokes = useCallback(() => {
    return strokes;
  }, [strokes]);

  const loadStrokes = useCallback((newStrokes: SignatureStroke[]) => {
    setStrokes(newStrokes);
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext('2d');
    if (ctx && canvas) {
      const rect = canvas.getBoundingClientRect();
      ctx.fillStyle = backgroundColor;
      ctx.fillRect(0, 0, rect.width, rect.height);

      newStrokes.forEach(stroke => {
        if (stroke.points.length < 2) return;
        ctx.beginPath();
        ctx.strokeStyle = stroke.color;
        ctx.lineWidth = stroke.width;
        ctx.lineCap = 'round';
        ctx.lineJoin = 'round';

        stroke.points.forEach((point, i) => {
          if (i === 0) {
            ctx.moveTo(point.x, point.y);
          } else {
            const midX = (stroke.points[i - 1].x + point.x) / 2;
            const midY = (stroke.points[i - 1].y + point.y) / 2;
            ctx.quadraticCurveTo(stroke.points[i - 1].x, stroke.points[i - 1].y, midX, midY);
          }
        });
        ctx.stroke();
      });
    }
  }, [backgroundColor]);

  useImperativeHandle(
    ref,
    () => ({
      clear,
      undo,
      isEmpty,
      getCanvas,
      getStrokes,
      loadStrokes,
    }),
    [clear, undo, isEmpty, getCanvas, getStrokes, loadStrokes]
  );

  return (
    <div 
      ref={containerRef}
      className="signature-pad-container"
      style={{
        position: 'relative',
        width: '100%',
        maxWidth: width,
        height,
        border: '2px solid #e0e0e0',
        borderRadius: '8px',
        backgroundColor,
        overflow: 'hidden',
        touchAction: 'none',
      }}
    >
      <canvas
        ref={canvasRef}
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          cursor: readOnly ? 'default' : 'crosshair',
        }}
      />
      {readOnly && (
        <div
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            width: '100%',
            height: '100%',
            backgroundColor: 'rgba(255, 255, 255, 0.1)',
            pointerEvents: 'none',
          }}
        />
      )}
    </div>
  );
});

SignaturePadComponent.displayName = 'SignaturePadComponent';

export default SignaturePadComponent;
