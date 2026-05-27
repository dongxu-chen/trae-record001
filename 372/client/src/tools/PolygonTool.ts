import type { Point, PolygonAnnotation } from '@/types/annotation';
import { BaseTool, ToolCallbacks } from './BaseTool';
import { imageToScreen, hexToRgba } from '@/utils/canvas';

export class PolygonTool extends BaseTool {
  private points: Point[] = [];
  private currentMousePos: Point | null = null;

  constructor(callbacks: ToolCallbacks) {
    super(callbacks);
  }

  onMouseDown(e: React.MouseEvent<HTMLCanvasElement>, point: Point): void {
    const imagePoint = this.getImagePoint(point);
    
    if (e.button === 2) {
      this.finishPolygon();
      return;
    }

    if (this.points.length >= 3) {
      const firstPoint = this.points[0];
      const dist = Math.sqrt(
        (imagePoint.x - firstPoint.x) ** 2 + (imagePoint.y - firstPoint.y) ** 2
      );
      if (dist < 10) {
        this.finishPolygon();
        return;
      }
    }

    this.points.push(imagePoint);
    this.callbacks.onPreviewUpdate({ points: [...this.points] });
  }

  onMouseMove(e: React.MouseEvent<HTMLCanvasElement>, point: Point): void {
    this.currentMousePos = this.getImagePoint(point);
    this.callbacks.onPreviewUpdate({ 
      points: [...this.points],
      currentPos: this.currentMousePos 
    });
  }

  onMouseUp(): void {}

  onMouseLeave(): void {
    this.currentMousePos = null;
  }

  private finishPolygon(): void {
    if (this.points.length >= 3) {
      this.callbacks.onAnnotationComplete({
        type: 'polygon',
        points: [...this.points],
        closed: true,
      } as Partial<PolygonAnnotation>);
    }
    this.reset();
  }

  render(ctx: CanvasRenderingContext2D, canvasState: any): void {
    if (this.points.length === 0 && !this.currentMousePos) return;

    const screenPoints = this.points.map(p => imageToScreen(p, canvasState));
    const currentScreenPos = this.currentMousePos 
      ? imageToScreen(this.currentMousePos, canvasState) 
      : null;

    ctx.save();
    
    if (this.points.length > 0) {
      ctx.strokeStyle = '#06b6d4';
      ctx.lineWidth = 2;
      ctx.fillStyle = hexToRgba('#06b6d4', 0.2);
      
      ctx.beginPath();
      ctx.moveTo(screenPoints[0].x, screenPoints[0].y);
      
      for (let i = 1; i < screenPoints.length; i++) {
        ctx.lineTo(screenPoints[i].x, screenPoints[i].y);
      }
      
      if (currentScreenPos) {
        ctx.lineTo(currentScreenPos.x, currentScreenPos.y);
      }
      
      ctx.stroke();
      if (this.points.length >= 3) {
        ctx.closePath();
        ctx.fill();
      }
    }

    screenPoints.forEach((p, i) => {
      ctx.fillStyle = i === 0 ? '#22c55e' : '#06b6d4';
      ctx.beginPath();
      ctx.arc(p.x, p.y, 5, 0, Math.PI * 2);
      ctx.fill();
      ctx.strokeStyle = '#fff';
      ctx.lineWidth = 1;
      ctx.stroke();
    });

    if (this.points.length > 0 && currentScreenPos) {
      const firstPoint = screenPoints[0];
      const dist = Math.sqrt(
        (currentScreenPos.x - firstPoint.x) ** 2 + 
        (currentScreenPos.y - firstPoint.y) ** 2
      );
      if (dist < 15) {
        ctx.strokeStyle = '#22c55e';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(firstPoint.x, firstPoint.y, 10, 0, Math.PI * 2);
        ctx.stroke();
      }
    }

    ctx.restore();
  }

  reset(): void {
    this.points = [];
    this.currentMousePos = null;
    this.isDrawing = false;
  }
}
