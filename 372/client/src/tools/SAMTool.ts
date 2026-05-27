import type { Point, SAMAnnotation } from '@/types/annotation';
import { BaseTool, ToolCallbacks } from './BaseTool';
import { imageToScreen, createMaskCanvas } from '@/utils/canvas';
import { wsClient } from '@/services/wsClient';
import { useAnnotationStore } from '@/store/useAnnotationStore';

export class SAMTool extends BaseTool {
  private previewPoint: Point | null = null;
  private previewMask: number[] | null = null;
  private maskWidth: number = 0;
  private maskHeight: number = 0;
  private currentImageId: string | null = null;

  constructor(callbacks: ToolCallbacks) {
    super(callbacks);
    this.setupWebSocketHandlers();
  }

  private setupWebSocketHandlers(): void {
    wsClient.onSAMResult((response) => {
      this.previewMask = response.mask;
      this.maskWidth = response.width;
      this.maskHeight = response.height;
      useAnnotationStore.getState().setSamLoading(false);
      useAnnotationStore.getState().setSamPreviewMask(response.mask);
      this.callbacks.onPreviewUpdate({
        mask: response.mask,
        width: response.width,
        height: response.height,
      });
    });

    wsClient.onSAMError((error) => {
      console.error('SAM error:', error);
      useAnnotationStore.getState().setSamLoading(false);
    });
  }

  setImageId(imageId: string | null): void {
    this.currentImageId = imageId;
  }

  onMouseDown(e: React.MouseEvent<HTMLCanvasElement>, point: Point): void {
    if (e.button !== 0 || !this.currentImageId) return;
    
    const imagePoint = this.getImagePoint(point);
    this.previewPoint = imagePoint;
    
    useAnnotationStore.getState().setSamLoading(true);
    wsClient.sendSAMPredict({
      imageId: this.currentImageId,
      point: imagePoint,
      mode: 'click',
    });
  }

  onMouseMove(e: React.MouseEvent<HTMLCanvasElement>, point: Point): void {
    this.previewPoint = this.getImagePoint(point);
    this.callbacks.onPreviewUpdate({ position: this.previewPoint });
  }

  onMouseUp(e: React.MouseEvent<HTMLCanvasElement>, point: Point): void {
    if (this.previewMask && this.previewMask.length > 0) {
      this.callbacks.onAnnotationComplete({
        type: 'sam',
        mask: [...this.previewMask],
        width: this.maskWidth,
        height: this.maskHeight,
      } as Partial<SAMAnnotation>);
      
      this.previewMask = null;
      useAnnotationStore.getState().setSamPreviewMask(null);
    }
  }

  onMouseLeave(): void {
    this.previewPoint = null;
  }

  onDoubleClick(e: React.MouseEvent<HTMLCanvasElement>, point: Point): void {
    if (this.previewMask && this.previewMask.length > 0) {
      this.callbacks.onAnnotationComplete({
        type: 'sam',
        mask: [...this.previewMask],
        width: this.maskWidth,
        height: this.maskHeight,
      } as Partial<SAMAnnotation>);
      
      this.previewMask = null;
      useAnnotationStore.getState().setSamPreviewMask(null);
    }
  }

  render(ctx: CanvasRenderingContext2D, canvasState: any): void {
    if (this.previewMask && this.previewMask.length > 0) {
      const color = useAnnotationStore.getState().currentColor;
      const maskCanvas = createMaskCanvas(
        this.previewMask,
        this.maskWidth,
        this.maskHeight,
        color
      );
      
      ctx.save();
      ctx.globalAlpha = 0.6;
      ctx.drawImage(
        maskCanvas,
        canvasState.offsetX,
        canvasState.offsetY,
        this.maskWidth * canvasState.scale,
        this.maskHeight * canvasState.scale
      );
      ctx.restore();

      ctx.save();
      ctx.strokeStyle = color;
      ctx.lineWidth = 2;
      ctx.setLineDash([5, 5]);
      ctx.strokeRect(
        canvasState.offsetX,
        canvasState.offsetY,
        this.maskWidth * canvasState.scale,
        this.maskHeight * canvasState.scale
      );
      ctx.restore();
    }

    if (this.previewPoint) {
      const screenPoint = imageToScreen(this.previewPoint, canvasState);
      
      ctx.save();
      ctx.strokeStyle = '#06b6d4';
      ctx.lineWidth = 2;
      ctx.fillStyle = 'rgba(6, 182, 212, 0.3)';
      
      ctx.beginPath();
      ctx.arc(screenPoint.x, screenPoint.y, 10, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();

      ctx.beginPath();
      ctx.moveTo(screenPoint.x - 15, screenPoint.y);
      ctx.lineTo(screenPoint.x + 15, screenPoint.y);
      ctx.moveTo(screenPoint.x, screenPoint.y - 15);
      ctx.lineTo(screenPoint.x, screenPoint.y + 15);
      ctx.stroke();
      ctx.restore();
    }
  }

  reset(): void {
    this.previewPoint = null;
    this.previewMask = null;
    useAnnotationStore.getState().setSamPreviewMask(null);
    useAnnotationStore.getState().setSamLoading(false);
  }
}
