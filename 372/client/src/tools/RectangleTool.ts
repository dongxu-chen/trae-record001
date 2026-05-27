import type { Point, RectangleAnnotation } from '@/types/annotation';
import { BaseTool, ToolCallbacks } from './BaseTool';
import { imageToScreen, hexToRgba } from '@/utils/canvas';

export class RectangleTool extends BaseTool {
  private startPoint: Point | null = null;
  private endPoint: Point | null = null;

  constructor(callbacks: ToolCallbacks) {
    super(callbacks);
  }

  onMouseDown(e: React.MouseEvent<HTMLCanvasElement>, point: Point): void {
    if (e.button !== 0) return;
    
    this.startPoint = this.getImagePoint(point);
    this.endPoint = { ...this.startPoint };
    this.isDrawing = true;
    this.callbacks.onAnnotationStart();
  }

  onMouseMove(e: React.MouseEvent<HTMLCanvasElement>, point: Point): void {
    if (!this.isDrawing || !this.startPoint) return;
    
    this.endPoint = this.getImagePoint(point);
    this.callbacks.onPreviewUpdate({
      startPoint: this.startPoint,
      endPoint: this.endPoint,
    });
  }

  onMouseUp(e: React.MouseEvent<HTMLCanvasElement>, point: Point): void {
    if (!this.isDrawing || !this.startPoint || !this.endPoint) {
      this.reset();
      return;
    }

    const x = Math.min(this.startPoint.x, this.endPoint.x);
    const y = Math.min(this.startPoint.y, this.endPoint.y);
    const width = Math.abs(this.endPoint.x - this.startPoint.x);
    const height = Math.abs(this.endPoint.y - this.startPoint.y);

    if (width > 3 && height > 3) {
      this.callbacks.onAnnotationComplete({
        type: 'rectangle',
        x,
        y,
        width,
        height,
      } as Partial<RectangleAnnotation>);
    }

    this.reset();
  }

  onMouseLeave(): void {
    if (this.isDrawing && this.startPoint && this.endPoint) {
      const x = Math.min(this.startPoint.x, this.endPoint.x);
      const y = Math.min(this.startPoint.y, this.endPoint.y);
      const width = Math.abs(this.endPoint.x - this.startPoint.x);
      const height = Math.abs(this.endPoint.y - this.startPoint.y);

      if (width > 3 && height > 3) {
        this.callbacks.onAnnotationComplete({
          type: 'rectangle',
          x,
          y,
          width,
          height,
        } as Partial<RectangleAnnotation>);
      }
    }
    this.reset();
  }

  render(ctx: CanvasRenderingContext2D, canvasState: any): void {
    if (!this.startPoint || !this.endPoint) return;

    const start = imageToScreen(this.startPoint, canvasState);
    const end = imageToScreen(this.endPoint, canvasState);

    const x = Math.min(start.x, end.x);
    const y = Math.min(start.y, end.y);
    const width = Math.abs(end.x - start.x);
    const height = Math.abs(end.y - start.y);

    ctx.save();
    
    ctx.strokeStyle = '#06b6d4';
    ctx.lineWidth = 2;
    ctx.setLineDash([5, 5]);
    ctx.fillStyle = hexToRgba('#06b6d4', 0.2);
    
    ctx.fillRect(x, y, width, height);
    ctx.strokeRect(x, y, width, height);

    ctx.setLineDash([]);
    ctx.fillStyle = '#06b6d4';
    const corners = [
      { x, y },
      { x: x + width, y },
      { x, y: y + height },
      { x: x + width, y: y + height },
    ];
    corners.forEach(c => {
      ctx.beginPath();
      ctx.arc(c.x, c.y, 4, 0, Math.PI * 2);
      ctx.fill();
    });

    ctx.restore();
  }

  reset(): void {
    this.startPoint = null;
    this.endPoint = null;
    this.isDrawing = false;
  }
}
