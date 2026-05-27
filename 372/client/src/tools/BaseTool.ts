import type { Point, Annotation, CanvasState } from '@/types/annotation';
import { screenToImage } from '@/utils/canvas';

export interface ToolCallbacks {
  onAnnotationStart: () => void;
  onAnnotationComplete: (annotation: Partial<Annotation>) => void;
  onPreviewUpdate: (preview: any) => void;
  getCanvasState: () => CanvasState;
}

export abstract class BaseTool {
  protected isDrawing: boolean = false;
  protected callbacks: ToolCallbacks;
  protected canvasState: CanvasState | null = null;

  constructor(callbacks: ToolCallbacks) {
    this.callbacks = callbacks;
  }

  protected getImagePoint(screenPoint: Point): Point {
    const state = this.callbacks.getCanvasState();
    return screenToImage(screenPoint, state);
  }

  abstract onMouseDown(e: React.MouseEvent<HTMLCanvasElement>, point: Point): void;
  abstract onMouseMove(e: React.MouseEvent<HTMLCanvasElement>, point: Point): void;
  abstract onMouseUp(e: React.MouseEvent<HTMLCanvasElement>, point: Point): void;
  abstract onMouseLeave(e: React.MouseEvent<HTMLCanvasElement>): void;
  abstract render(ctx: CanvasRenderingContext2D, canvasState: CanvasState): void;
  abstract reset(): void;

  getCursor(): string {
    return 'crosshair';
  }
}
