import type { Point, CanvasState } from '@/types/annotation';

export function screenToImage(screenPoint: Point, canvasState: CanvasState): Point {
  return {
    x: (screenPoint.x - canvasState.offsetX) / canvasState.scale,
    y: (screenPoint.y - canvasState.offsetY) / canvasState.scale,
  };
}

export function imageToScreen(imagePoint: Point, canvasState: CanvasState): Point {
  return {
    x: imagePoint.x * canvasState.scale + canvasState.offsetX,
    y: imagePoint.y * canvasState.scale + canvasState.offsetY,
  };
}

export function getMousePos(e: React.MouseEvent<HTMLCanvasElement>): Point {
  const rect = e.currentTarget.getBoundingClientRect();
  return {
    x: e.clientX - rect.left,
    y: e.clientY - rect.top,
  };
}

export function drawGrid(
  ctx: CanvasRenderingContext2D,
  width: number,
  height: number,
  gridSize: number = 20
): void {
  ctx.save();
  ctx.strokeStyle = '#1e293b';
  ctx.lineWidth = 0.5;
  
  for (let x = 0; x <= width; x += gridSize) {
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, height);
    ctx.stroke();
  }
  
  for (let y = 0; y <= height; y += gridSize) {
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(width, y);
    ctx.stroke();
  }
  
  ctx.restore();
}

export function drawCrosshair(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  size: number = 10
): void {
  ctx.save();
  ctx.strokeStyle = '#06b6d4';
  ctx.lineWidth = 1;
  ctx.setLineDash([4, 4]);
  
  ctx.beginPath();
  ctx.moveTo(x - size, y);
  ctx.lineTo(x + size, y);
  ctx.moveTo(x, y - size);
  ctx.lineTo(x, y + size);
  ctx.stroke();
  
  ctx.restore();
}

export function hexToRgba(hex: string, alpha: number = 0.4): string {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

export function createMaskCanvas(
  mask: number[],
  width: number,
  height: number,
  color: string
): HTMLCanvasElement {
  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext('2d')!;
  
  const imageData = ctx.createImageData(width, height);
  const rgb = hexToRgb(color);
  
  for (let i = 0; i < mask.length; i++) {
    if (mask[i] > 127) {
      const idx = i * 4;
      imageData.data[idx] = rgb.r;
      imageData.data[idx + 1] = rgb.g;
      imageData.data[idx + 2] = rgb.b;
      imageData.data[idx + 3] = 102;
    }
  }
  
  ctx.putImageData(imageData, 0, 0);
  return canvas;
}

function hexToRgb(hex: string): { r: number; g: number; b: number } {
  return {
    r: parseInt(hex.slice(1, 3), 16),
    g: parseInt(hex.slice(3, 5), 16),
    b: parseInt(hex.slice(5, 7), 16),
  };
}
