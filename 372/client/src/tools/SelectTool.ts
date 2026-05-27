import type { Point, Annotation, PolygonAnnotation, RectangleAnnotation, PointAnnotation, BrushAnnotation, SAMAnnotation } from '@/types/annotation';
import { BaseTool, ToolCallbacks } from './BaseTool';
import { 
  pointInPolygon, 
  pointInRectangle, 
  pointNearPoint, 
  pointNearPolyline,
  distance 
} from '@/utils/geometry';
import { imageToScreen } from '@/utils/canvas';

export class SelectTool extends BaseTool {
  private annotations: Annotation[] = [];
  private selectedId: string | null = null;
  private isDragging: boolean = false;
  private dragStart: Point | null = null;
  private dragAnnotationStart: any = null;
  private hoveredId: string | null = null;

  constructor(callbacks: ToolCallbacks) {
    super(callbacks);
  }

  setAnnotations(annotations: Annotation[]): void {
    this.annotations = annotations;
  }

  setSelectedId(id: string | null): void {
    this.selectedId = id;
  }

  getHoveredId(): string | null {
    return this.hoveredId;
  }

  onMouseDown(e: React.MouseEvent<HTMLCanvasElement>, point: Point): void {
    if (e.button !== 0) return;
    
    const imagePoint = this.getImagePoint(point);
    const clickedAnnotation = this.findAnnotationAtPoint(imagePoint);
    
    if (clickedAnnotation) {
      this.selectedId = clickedAnnotation.id;
      this.isDragging = true;
      this.dragStart = imagePoint;
      this.dragAnnotationStart = this.getAnnotationPosition(clickedAnnotation);
      this.callbacks.onAnnotationStart();
    } else {
      this.selectedId = null;
      this.callbacks.onPreviewUpdate({ selectedId: null });
    }
  }

  onMouseMove(e: React.MouseEvent<HTMLCanvasElement>, point: Point): void {
    const imagePoint = this.getImagePoint(point);
    
    if (this.isDragging && this.selectedId && this.dragStart && this.dragAnnotationStart) {
      const dx = imagePoint.x - this.dragStart.x;
      const dy = imagePoint.y - this.dragStart.y;
      
      const annotation = this.annotations.find(a => a.id === this.selectedId);
      if (annotation) {
        const updated = this.moveAnnotation(annotation, dx, dy);
        this.callbacks.onPreviewUpdate({ 
          selectedId: this.selectedId,
          movingAnnotation: updated
        });
      }
    } else {
      const hovered = this.findAnnotationAtPoint(imagePoint);
      this.hoveredId = hovered ? hovered.id : null;
      this.callbacks.onPreviewUpdate({ hoveredId: this.hoveredId });
    }
  }

  onMouseUp(e: React.MouseEvent<HTMLCanvasElement>, point: Point): void {
    if (this.isDragging && this.selectedId && this.dragStart && this.dragAnnotationStart) {
      const imagePoint = this.getImagePoint(point);
      const dx = imagePoint.x - this.dragStart.x;
      const dy = imagePoint.y - this.dragStart.y;
      
      const annotation = this.annotations.find(a => a.id === this.selectedId);
      if (annotation) {
        const updated = this.moveAnnotation(annotation, dx, dy);
        this.callbacks.onAnnotationComplete({
          id: this.selectedId,
          ...updated,
        });
      }
    }
    
    this.isDragging = false;
    this.dragStart = null;
    this.dragAnnotationStart = null;
    
    if (this.selectedId) {
      this.callbacks.onPreviewUpdate({ selectedId: this.selectedId });
    }
  }

  onMouseLeave(): void {
    this.hoveredId = null;
    if (this.isDragging) {
      this.isDragging = false;
      this.dragStart = null;
      this.dragAnnotationStart = null;
    }
  }

  private findAnnotationAtPoint(point: Point): Annotation | null {
    for (let i = this.annotations.length - 1; i >= 0; i--) {
      const ann = this.annotations[i];
      if (!ann.visible) continue;
      
      if (this.isPointInAnnotation(point, ann)) {
        return ann;
      }
    }
    return null;
  }

  private isPointInAnnotation(point: Point, annotation: Annotation): boolean {
    switch (annotation.type) {
      case 'polygon':
        return pointInPolygon(point, (annotation as PolygonAnnotation).points);
      case 'rectangle':
        const rect = annotation as RectangleAnnotation;
        return pointInRectangle(point, rect.x, rect.y, rect.width, rect.height);
      case 'point':
        return pointNearPoint(point, (annotation as PointAnnotation).position, 10);
      case 'brush':
        return pointNearPolyline(point, (annotation as BrushAnnotation).points, (annotation as BrushAnnotation).strokeWidth);
      case 'sam':
        const sam = annotation as SAMAnnotation;
        const px = Math.floor(point.x);
        const py = Math.floor(point.y);
        if (px >= 0 && px < sam.width && py >= 0 && py < sam.height) {
          const idx = py * sam.width + px;
          return sam.mask[idx] > 127;
        }
        return false;
      default:
        return false;
    }
  }

  private getAnnotationPosition(annotation: Annotation): any {
    switch (annotation.type) {
      case 'polygon':
        return { points: [...(annotation as PolygonAnnotation).points] };
      case 'rectangle':
        return { x: (annotation as RectangleAnnotation).x, y: (annotation as RectangleAnnotation).y };
      case 'point':
        return { position: { ...(annotation as PointAnnotation).position } };
      case 'brush':
        return { points: [...(annotation as BrushAnnotation).points] };
      default:
        return {};
    }
  }

  private moveAnnotation(annotation: Annotation, dx: number, dy: number): Partial<Annotation> {
    switch (annotation.type) {
      case 'polygon':
        const poly = annotation as PolygonAnnotation;
        return {
          points: poly.points.map(p => ({ x: p.x + dx, y: p.y + dy })),
        };
      case 'rectangle':
        const rect = annotation as RectangleAnnotation;
        return {
          x: rect.x + dx,
          y: rect.y + dy,
        };
      case 'point':
        const pt = annotation as PointAnnotation;
        return {
          position: { x: pt.position.x + dx, y: pt.position.y + dy },
        };
      case 'brush':
        const brush = annotation as BrushAnnotation;
        return {
          points: brush.points.map(p => ({ x: p.x + dx, y: p.y + dy })),
        };
      default:
        return {};
    }
  }

  render(ctx: CanvasRenderingContext2D, canvasState: any): void {
    if (this.selectedId) {
      const selected = this.annotations.find(a => a.id === this.selectedId);
      if (selected) {
        this.drawSelectionBox(ctx, selected, canvasState, '#06b6d4');
      }
    }
    
    if (this.hoveredId && this.hoveredId !== this.selectedId) {
      const hovered = this.annotations.find(a => a.id === this.hoveredId);
      if (hovered) {
        this.drawSelectionBox(ctx, hovered, canvasState, '#f59e0b');
      }
    }
  }

  private drawSelectionBox(
    ctx: CanvasRenderingContext2D,
    annotation: Annotation,
    canvasState: any,
    color: string
  ): void {
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;

    switch (annotation.type) {
      case 'polygon':
        const poly = annotation as PolygonAnnotation;
        poly.points.forEach(p => {
          minX = Math.min(minX, p.x);
          minY = Math.min(minY, p.y);
          maxX = Math.max(maxX, p.x);
          maxY = Math.max(maxY, p.y);
        });
        break;
      case 'rectangle':
        const rect = annotation as RectangleAnnotation;
        minX = rect.x;
        minY = rect.y;
        maxX = rect.x + rect.width;
        maxY = rect.y + rect.height;
        break;
      case 'point':
        const pt = annotation as PointAnnotation;
        minX = pt.position.x - pt.radius;
        minY = pt.position.y - pt.radius;
        maxX = pt.position.x + pt.radius;
        maxY = pt.position.y + pt.radius;
        break;
      case 'brush':
        const brush = annotation as BrushAnnotation;
        brush.points.forEach(p => {
          minX = Math.min(minX, p.x);
          minY = Math.min(minY, p.y);
          maxX = Math.max(maxX, p.x);
          maxY = Math.max(maxY, p.y);
        });
        minX -= brush.strokeWidth;
        minY -= brush.strokeWidth;
        maxX += brush.strokeWidth;
        maxY += brush.strokeWidth;
        break;
      case 'sam':
        const sam = annotation as SAMAnnotation;
        minX = 0;
        minY = 0;
        maxX = sam.width;
        maxY = sam.height;
        break;
    }

    const p1 = imageToScreen({ x: minX, y: minY }, canvasState);
    const p2 = imageToScreen({ x: maxX, y: maxY }, canvasState);

    ctx.save();
    ctx.strokeStyle = color;
    ctx.lineWidth = 1.5;
    ctx.setLineDash([4, 4]);
    ctx.strokeRect(p1.x, p1.y, p2.x - p1.x, p2.y - p1.y);
    
    ctx.setLineDash([]);
    ctx.fillStyle = color;
    const handleSize = 6;
    const handles = [
      { x: p1.x, y: p1.y },
      { x: p2.x, y: p1.y },
      { x: p1.x, y: p2.y },
      { x: p2.x, y: p2.y },
      { x: (p1.x + p2.x) / 2, y: p1.y },
      { x: (p1.x + p2.x) / 2, y: p2.y },
      { x: p1.x, y: (p1.y + p2.y) / 2 },
      { x: p2.x, y: (p1.y + p2.y) / 2 },
    ];
    handles.forEach(h => {
      ctx.fillRect(h.x - handleSize / 2, h.y - handleSize / 2, handleSize, handleSize);
    });
    
    ctx.restore();
  }

  reset(): void {
    this.selectedId = null;
    this.hoveredId = null;
    this.isDragging = false;
    this.dragStart = null;
    this.dragAnnotationStart = null;
  }

  getCursor(): string {
    if (this.hoveredId || this.isDragging) {
      return this.isDragging ? 'grabbing' : 'grab';
    }
    return 'default';
  }
}
