import type { Point, PointAnnotation } from '@/types/annotation';
import { BaseTool, ToolCallbacks } from './BaseTool';
import { imageToScreen } from '@/utils/canvas';

export class PointTool extends BaseTool {
  private previewPoint: Point | null = null;

  constructor(callbacks: ToolCallbacks) {
    super(callbacks);
  }

  onMouseDown(e: React.MouseEvent<HTMLCanvasElement>, point: Point): void {
    if (e.button !== 0) return;
    
    const imagePoint = this.getImagePoint(point);
    this.callbacks.onAnnotationComplete({
      type: 'point',
      position: imagePoint,
      radius: 5,
    } as Partial<PointAnnotation>);
  }

  onMouseMove(e: React.MouseEvent<HTMLCanvasElement>, point: Point): void {
    this.previewPoint = this.getImagePoint(point);
    this.callbacks.onPreviewUpdate({ position: this.previewPoint });
  }

  onMouseUp(): void {}

  onMouseLeave(): void {
    this.previewPoint = null;
  }

  render(ctx: CanvasRenderingContext2D, canvasState: any): void {
    if (!this.previewPoint) return;

    const screenPoint = imageToScreen(this.previewPoint, canvasState);

    ctx.save();
    
    ctx.strokeStyle = '#06b6d4';
    ctx.lineWidth = 2;
    ctx.fillStyle = 'rgba(6, 182, 212, 0.3)';
    
    ctx.beginPath();
    ctx.arc(screenPoint.x, screenPoint.y, 8, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();

    ctx.beginPath();
    ctx.moveTo(screenPoint.x - 12, screenPoint.y);
    ctx.lineTo(screenPoint.x + 12, screenPoint.y);
    ctx.moveTo(screenPoint.x, screenPoint.y - 12);
    ctx.lineTo(screenPoint.x, screenPoint.y + 12);
    ctx.stroke();

    ctx.restore();
  }

  reset(): void {
    this.previewPoint = null;
  }
}
