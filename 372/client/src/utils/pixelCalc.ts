import type { Annotation, PolygonAnnotation, PointAnnotation, RectangleAnnotation, BrushAnnotation, SAMAnnotation, Point } from '@/types/annotation';
import { getPolygonBounds } from './geometry';

export function calculatePixelArea(
  annotation: Annotation,
  imageWidth: number,
  imageHeight: number
): { area: number; percentage: number } {
  const totalPixels = imageWidth * imageHeight;
  let area = 0;

  switch (annotation.type) {
    case 'polygon':
      area = calculatePolygonArea(annotation as PolygonAnnotation, imageWidth, imageHeight);
      break;
    case 'rectangle':
      area = calculateRectangleArea(annotation as RectangleAnnotation);
      break;
    case 'point':
      area = calculatePointArea(annotation as PointAnnotation);
      break;
    case 'brush':
      area = calculateBrushArea(annotation as BrushAnnotation);
      break;
    case 'sam':
      area = calculateSAMArea(annotation as SAMAnnotation);
      break;
  }

  area = Math.round(area);
  const percentage = totalPixels > 0 ? (area / totalPixels) * 100 : 0;

  return { area, percentage };
}

export function calculatePolygonArea(
  annotation: PolygonAnnotation,
  imageWidth: number,
  imageHeight: number
): number {
  const { points } = annotation;
  if (points.length < 3) return 0;

  return scanlineFillArea(points, imageWidth, imageHeight);
}

function scanlineFillArea(points: Point[], width: number, height: number): number {
  const bounds = getPolygonBounds(points);
  const minY = Math.max(0, Math.floor(bounds.minY));
  const maxY = Math.min(height - 1, Math.ceil(bounds.maxY));
  
  let count = 0;

  for (let y = minY; y <= maxY; y++) {
    const intersections: number[] = [];
    
    for (let i = 0; i < points.length; i++) {
      const p1 = points[i];
      const p2 = points[(i + 1) % points.length];
      
      if ((p1.y <= y && p2.y > y) || (p2.y <= y && p1.y > y)) {
        const x = p1.x + ((y - p1.y) / (p2.y - p1.y)) * (p2.x - p1.x);
        intersections.push(x);
      }
    }
    
    intersections.sort((a, b) => a - b);
    
    for (let i = 0; i < intersections.length - 1; i += 2) {
      const x1 = Math.max(0, Math.ceil(intersections[i]));
      const x2 = Math.min(width - 1, Math.floor(intersections[i + 1]));
      if (x2 > x1) {
        count += x2 - x1 + 1;
      }
    }
  }

  return count;
}

export function calculateRectangleArea(annotation: RectangleAnnotation): number {
  return Math.abs(annotation.width * annotation.height);
}

export function calculatePointArea(annotation: PointAnnotation): number {
  return Math.round(Math.PI * annotation.radius * annotation.radius);
}

export function calculateBrushArea(annotation: BrushAnnotation): number {
  const { points, strokeWidth } = annotation;
  if (points.length < 2) return Math.PI * strokeWidth * strokeWidth;
  
  let area = 0;
  for (let i = 0; i < points.length - 1; i++) {
    const dx = points[i + 1].x - points[i].x;
    const dy = points[i + 1].y - points[i].y;
    const length = Math.sqrt(dx * dx + dy * dy);
    area += length * strokeWidth;
  }
  
  return Math.round(area);
}

export function calculateSAMArea(annotation: SAMAnnotation): number {
  const { mask } = annotation;
  let count = 0;
  for (let i = 0; i < mask.length; i++) {
    if (mask[i] > 127) count++;
  }
  return count;
}

export function formatPixelArea(area: number): string {
  if (area >= 1000000) {
    return `${(area / 1000000).toFixed(2)} Mpx`;
  } else if (area >= 1000) {
    return `${(area / 1000).toFixed(2)} Kpx`;
  }
  return `${area} px`;
}

export function formatPercentage(percentage: number): string {
  return `${percentage.toFixed(2)}%`;
}
