import { useRef, useEffect, useCallback, useState, useMemo } from 'react';
import type { View3D, Surface3D, CompiledBinaryFunction } from '../types';
import {
  generateSurfaceGrid,
  projectPoint,
  calculateSurfaceBounds,
  autoScale3D,
  draw3DAxes,
  draw3DGrid,
  lerp,
  easeInOut
} from '../utils/math3D';
import { compileBinaryExpression } from '../utils/binaryParser';

interface UseCanvas3DProps {
  canvasWidth: number;
  canvasHeight: number;
  surfaces: Surface3D[];
}

interface UseCanvas3DReturn {
  canvasRef: React.RefObject<HTMLCanvasElement>;
  view3D: View3D;
  setView3D: React.Dispatch<React.SetStateAction<View3D>>;
  isDragging: boolean;
  handleMouseDown: (e: React.MouseEvent) => void;
  handleMouseMove: (e: React.MouseEvent) => void;
  handleMouseUp: () => void;
  handleWheel: (e: React.WheelEvent) => void;
  autoRotate: boolean;
  setAutoRotate: React.Dispatch<React.SetStateAction<boolean>>;
}

export function useCanvas3D({
  canvasWidth,
  canvasHeight,
  surfaces
}: UseCanvas3DProps): UseCanvas3DReturn {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationRef = useRef<number | null>(null);
  const lastTimeRef = useRef<number>(0);
  const [isDragging, setIsDragging] = useState(false);
  const lastMouseRef = useRef({ x: 0, y: 0 });
  const [autoRotate, setAutoRotate] = useState(false);

  const [view3D, setView3D] = useState<View3D>({
    rotation: { x: -0.5, y: 0.6, z: 0 },
    scale: 50,
    distance: 400,
    centerX: 0,
    centerY: 0,
    centerZ: 0
  });

  const compiledSurfaces = useMemo(() => {
    return surfaces.map(surface => {
      const result = compileBinaryExpression(surface.expression);
      return {
        ...surface,
        compiled: result.success ? result.compiled : null,
        error: result.error
      };
    });
  }, [surfaces]);

  const surfaceBounds = useMemo(() => {
    return compiledSurfaces.map(surface => {
      if (!surface.compiled) return null;
      return calculateSurfaceBounds(
        surface.xMin,
        surface.xMax,
        surface.yMin,
        surface.yMax,
        Math.min(surface.resolution, 30),
        surface.compiled.evaluate
      );
    });
  }, [compiledSurfaces]);

  const unifiedBounds = useMemo(() => {
    let xMin = Infinity, xMax = -Infinity;
    let yMin = Infinity, yMax = -Infinity;
    let zMin = Infinity, zMax = -Infinity;

    for (const bounds of surfaceBounds) {
      if (bounds) {
        xMin = Math.min(xMin, bounds.xMin);
        xMax = Math.max(xMax, bounds.xMax);
        yMin = Math.min(yMin, bounds.yMin);
        yMax = Math.max(yMax, bounds.yMax);
        zMin = Math.min(zMin, bounds.zMin);
        zMax = Math.max(zMax, bounds.zMax);
      }
    }

    if (xMin === Infinity) {
      xMin = -5; xMax = 5;
      yMin = -5; yMax = 5;
      zMin = -5; zMax = 5;
    }

    return { xMin, xMax, yMin, yMax, zMin, zMax };
  }, [surfaceBounds]);

  const autoScale = useMemo(() => {
    return autoScale3D(unifiedBounds, canvasWidth, canvasHeight);
  }, [unifiedBounds, canvasWidth, canvasHeight]);

  const currentView = useMemo<View3D>(() => ({
    ...view3D,
    scale: view3D.scale * autoScale,
    centerX: (unifiedBounds.xMin + unifiedBounds.xMax) / 2,
    centerY: (unifiedBounds.yMin + unifiedBounds.yMax) / 2,
    centerZ: (unifiedBounds.zMin + unifiedBounds.zMax) / 2
  }), [view3D, autoScale, unifiedBounds]);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    setIsDragging(true);
    lastMouseRef.current = { x: e.clientX, y: e.clientY };
  }, []);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (!isDragging) return;

    const dx = e.clientX - lastMouseRef.current.x;
    const dy = e.clientY - lastMouseRef.current.y;

    setView3D(prev => ({
      ...prev,
      rotation: {
        x: prev.rotation.x + dy * 0.01,
        y: prev.rotation.y + dx * 0.01,
        z: prev.rotation.z
      }
    }));

    lastMouseRef.current = { x: e.clientX, y: e.clientY };
  }, [isDragging]);

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault();
    setView3D(prev => ({
      ...prev,
      scale: Math.max(0.1, prev.scale * (e.deltaY > 0 ? 0.9 : 1.1))
    }));
  }, []);

  const drawSurface = useCallback((
    ctx: CanvasRenderingContext2D,
    surface: Surface3D & { compiled?: CompiledBinaryFunction | null },
    view: View3D,
    width: number,
    height: number
  ) => {
    if (!surface.visible || !surface.compiled) return;

    const { vertices, faces, colors } = generateSurfaceGrid(
      surface.xMin,
      surface.xMax,
      surface.yMin,
      surface.yMax,
      surface.resolution,
      surface.compiled.evaluate
    );

    const flatVertices = vertices.flat();

    const projected = flatVertices.map(v =>
      projectPoint(v, view, width, height)
    );

    const faceDepths = faces.map(face => {
      const avgDepth = face.reduce((sum, idx) => sum + projected[idx].depth, 0) / 3;
      return { face, avgDepth };
    });

    faceDepths.sort((a, b) => a.avgDepth - b.avgDepth);

    if (surface.showSurface) {
      for (const { face } of faceDepths) {
        const [i0, i1, i2] = face;
        const p0 = projected[i0];
        const p1 = projected[i1];
        const p2 = projected[i2];

        const v0x = flatVertices[i0].x, v0y = flatVertices[i0].y;
        const v1x = flatVertices[i1].x, v1y = flatVertices[i1].y;
        const v2x = flatVertices[i2].x, v2y = flatVertices[i2].y;

        const col0 = Math.round((v0x - surface.xMin) / (surface.xMax - surface.xMin) * (surface.resolution - 1));
        const row0 = Math.round((v0y - surface.yMin) / (surface.yMax - surface.yMin) * (surface.resolution - 1));
        const color = colors[Math.max(0, Math.min(surface.resolution - 1, col0))][Math.max(0, Math.min(surface.resolution - 1, row0))];

        ctx.fillStyle = color;
        ctx.globalAlpha = 0.8;
        ctx.beginPath();
        ctx.moveTo(p0.x, p0.y);
        ctx.lineTo(p1.x, p1.y);
        ctx.lineTo(p2.x, p2.y);
        ctx.closePath();
        ctx.fill();
        ctx.globalAlpha = 1;
      }
    }

    if (surface.showWireframe) {
      ctx.strokeStyle = 'rgba(0, 0, 0, 0.3)';
      ctx.lineWidth = 0.5;

      for (let i = 0; i < surface.resolution; i++) {
        for (let j = 0; j < surface.resolution; j++) {
          const idx = i * surface.resolution + j;
          const p = projected[idx];

          if (j < surface.resolution - 1) {
            const pRight = projected[idx + 1];
            ctx.beginPath();
            ctx.moveTo(p.x, p.y);
            ctx.lineTo(pRight.x, pRight.y);
            ctx.stroke();
          }

          if (i < surface.resolution - 1) {
            const pDown = projected[idx + surface.resolution];
            ctx.beginPath();
            ctx.moveTo(p.x, p.y);
            ctx.lineTo(pDown.x, pDown.y);
            ctx.stroke();
          }
        }
      }
    }
  }, []);

  const render = useCallback((time: number) => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const deltaTime = lastTimeRef.current ? (time - lastTimeRef.current) / 1000 : 0;
    lastTimeRef.current = time;

    if (autoRotate) {
      setView3D(prev => ({
        ...prev,
        rotation: {
          ...prev.rotation,
          y: prev.rotation.y + deltaTime * 0.5
        }
      }));
    }

    ctx.fillStyle = '#0f172a';
    ctx.fillRect(0, 0, canvasWidth, canvasHeight);

    draw3DGrid(ctx, currentView, unifiedBounds, canvasWidth, canvasHeight);
    draw3DAxes(ctx, currentView, unifiedBounds, canvasWidth, canvasHeight);

    for (const surface of compiledSurfaces) {
      drawSurface(ctx, surface, currentView, canvasWidth, canvasHeight);
    }

    animationRef.current = requestAnimationFrame(render);
  }, [canvasWidth, canvasHeight, currentView, unifiedBounds, compiledSurfaces, autoRotate, drawSurface]);

  useEffect(() => {
    animationRef.current = requestAnimationFrame(render);
    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [render]);

  return {
    canvasRef,
    view3D,
    setView3D,
    isDragging,
    handleMouseDown,
    handleMouseMove,
    handleMouseUp,
    handleWheel,
    autoRotate,
    setAutoRotate
  };
}

export function animateToView(
  from: View3D,
  to: View3D,
  duration: number,
  onUpdate: (view: View3D) => void,
  onComplete?: () => void
): () => void {
  const startTime = performance.now();
  let cancelled = false;

  function animate(currentTime: number) {
    if (cancelled) return;

    const elapsed = (currentTime - startTime) / 1000;
    const t = Math.min(1, elapsed / duration);
    const easedT = easeInOut(t);

    const interpolated: View3D = {
      rotation: {
        x: lerp(from.rotation.x, to.rotation.x, easedT),
        y: lerp(from.rotation.y, to.rotation.y, easedT),
        z: lerp(from.rotation.z, to.rotation.z, easedT)
      },
      scale: lerp(from.scale, to.scale, easedT),
      distance: lerp(from.distance, to.distance, easedT),
      centerX: lerp(from.centerX, to.centerX, easedT),
      centerY: lerp(from.centerY, to.centerY, easedT),
      centerZ: lerp(from.centerZ, to.centerZ, easedT)
    };

    onUpdate(interpolated);

    if (t < 1) {
      requestAnimationFrame(animate);
    } else if (onComplete) {
      onComplete();
    }
  }

  requestAnimationFrame(animate);

  return () => {
    cancelled = true;
  };
}
