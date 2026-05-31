import { useCallback, useRef } from 'react';
import { useGraphStore } from '../store/useGraphStore';
import { screenToMath } from '../utils/coordinate';

interface UseZoomPanOptions {
  canvasWidth: number;
  canvasHeight: number;
}

export const useZoomPan = ({ canvasWidth, canvasHeight }: UseZoomPanOptions) => {
  const { viewState, setViewState, setMouseState } = useGraphStore();
  const dragStartRef = useRef<{ x: number; y: number; viewState: typeof viewState } | null>(null);

  const MIN_ZOOM = 0.01;
  const MAX_ZOOM = 10000;

  const handleWheel = useCallback(
    (e: React.WheelEvent<HTMLCanvasElement>) => {
      e.preventDefault();
      if (canvasWidth === 0 || canvasHeight === 0) return;

      const rect = e.currentTarget.getBoundingClientRect();
      const mouseX = e.clientX - rect.left;
      const mouseY = e.clientY - rect.top;

      const { x: mathX, y: mathY } = screenToMath(
        mouseX,
        mouseY,
        canvasWidth,
        canvasHeight,
        viewState
      );

      const zoomFactor = e.deltaY > 0 ? 1.1 : 0.9;

      const newXRange = (viewState.xMax - viewState.xMin) * zoomFactor;
      const newYRange = (viewState.yMax - viewState.yMin) * zoomFactor;

      const totalRange = newXRange;
      if (totalRange < MIN_ZOOM || totalRange > MAX_ZOOM) {
        return;
      }

      const xRatio = (mouseX - 0) / canvasWidth;
      const yRatio = (mouseY - 0) / canvasHeight;

      const newXMin = mathX - newXRange * xRatio;
      const newXMax = mathX + newXRange * (1 - xRatio);
      const newYMin = mathY - newYRange * (1 - yRatio);
      const newYMax = mathY + newYRange * yRatio;

      setViewState({
        xMin: newXMin,
        xMax: newXMax,
        yMin: newYMin,
        yMax: newYMax,
      });
    },
    [canvasWidth, canvasHeight, viewState, setViewState]
  );

  const handleMouseDown = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      if (e.button !== 0) return;

      setMouseState({ isDragging: true });
      dragStartRef.current = {
        x: e.clientX,
        y: e.clientY,
        viewState: { ...viewState },
      };
    },
    [viewState, setMouseState]
  );

  const handleMouseMove = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      const rect = e.currentTarget.getBoundingClientRect();
      const mouseX = e.clientX - rect.left;
      const mouseY = e.clientY - rect.top;

      const { x: mathX, y: mathY } = screenToMath(
        mouseX,
        mouseY,
        canvasWidth,
        canvasHeight,
        viewState
      );

      setMouseState({
        x: mouseX,
        y: mouseY,
        mathX,
        mathY,
      });

      if (dragStartRef.current) {
        const dx = e.clientX - dragStartRef.current.x;
        const dy = e.clientY - dragStartRef.current.y;

        const mathDx = (dx / canvasWidth) * (viewState.xMax - viewState.xMin);
        const mathDy = -(dy / canvasHeight) * (viewState.yMax - viewState.yMin);

        setViewState({
          xMin: dragStartRef.current.viewState.xMin - mathDx,
          xMax: dragStartRef.current.viewState.xMax - mathDx,
          yMin: dragStartRef.current.viewState.yMin - mathDy,
          yMax: dragStartRef.current.viewState.yMax - mathDy,
        });
      }
    },
    [canvasWidth, canvasHeight, viewState, setViewState, setMouseState]
  );

  const handleMouseUp = useCallback(() => {
    setMouseState({ isDragging: false });
    dragStartRef.current = null;
    useGraphStore.getState().saveToLocalStorage();
  }, [setMouseState]);

  const handleMouseLeave = useCallback(() => {
    if (dragStartRef.current) {
      setMouseState({ isDragging: false });
      dragStartRef.current = null;
    }
  }, [setMouseState]);

  return {
    handleWheel,
    handleMouseDown,
    handleMouseMove,
    handleMouseUp,
    handleMouseLeave,
  };
};
