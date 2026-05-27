import type { Point, BrushAnnotation } from '@/types/annotation';
import { BaseTool, ToolCallbacks } from './BaseTool';
import { imageToScreen, hexToRgba } from '@/utils/canvas';

export class BrushTool extends BaseTool {
  private points: Point[] = [];
  private strokeWidth: number = 5;

  constructor(callbacks: ToolCallbacks, strokeWidth: number = 5) {
    super(callbacks);
    this.strokeWidth = strokeWidth;
  }

  setStrokeWidth(width: number): void {
    this.strokeWidth = width;
  }

  onMouseDown(e: React.MouseEvent<HTMLCanvasElement>, point: Point): void {
    if (e.button !== 0) return;
    
    const imagePoint = this.getImagePoint(point);
    this.points = [imagePoint];
    this.isDrawing = true;
    this.callbacks.onAnnotationStart();
  }

  onMouseMove(e: React.MouseEvent<HTMLCanvasElement>, point: Point): void {
    if (!this.isDrawing) return;
    
    const imagePoint = this.getImagePoint(point);
    this.points.push(imagePoint);
    this.callbacks.onPreviewUpdate({
      points: [...this.points],
      strokeWidth: this.strokeWidth,
    });
  }

  onMouseUp(e: React.MouseEvent<HTMLCanvasElement>, point: Point): void {
    if (!this.isDrawing || this.points.length < 2) {
      this.reset();
      return;
    }

    this.callbacks.onAnnotationComplete({
      type: 'brush',
      points: [...this.points],
      strokeWidth: this.strokeWidth,
    } as Partial<BrushAnnotation>);

    this.reset();
  }

  onMouseLeave(): void {
    if (this.isDrawing && this.points.length >= 2) {
      this.callbacks.onAnnotationComplete({
        type: 'brush',
        points: [...this.points],
        strokeWidth: this.strokeWidth,
      } as Partial<BrushAnnotation>);
    }
    this.reset();
  }

  render(ctx: CanvasRenderingContext2D, canvasState: any): void {
    if (this.points.length < 1) return;

    const screenPoints = this.points.map(p => imageToScreen(p, canvasState));

    ctx.save();
    
    ctx.strokeStyle = hexToRgba('#06b6d4', 0.8);
    ctx.lineWidth = this.strokeWidth * canvasState.scale;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    ctx.fillStyle = hexToRgba('#06b6d4', 0.3);

    if (screenPoints.length === 1) {
      ctx.beginPath();
      ctx.arc(screenPoints[0].x, screenPoints[0].y, this.strokeWidth * canvasState.scale / 2, 0, Math.PI * 2);
      ctx.fill();
    } else {
      ctx.beginPath();
      ctx.moveTo(screenPoints[0].x, screenPoints[0].y);
      for (let i = 1; i < screenPoints.length; i++) {
        ctx.lineTo(screenPoints[i].x, screenPoints[i].y);
      }
      ctx.stroke();
    }

    ctx.restore();
  }

  reset(): void {
    this.points = [];
    this.isDrawing = false;
  }
}
