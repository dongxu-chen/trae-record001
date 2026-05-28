import { RelativePosition } from '../types';

export const toRelativePosition = (
  absoluteX: number,
  absoluteY: number,
  pageWidth: number,
  pageHeight: number,
  absoluteWidth?: number,
  absoluteHeight?: number
): RelativePosition => ({
  x: Math.max(0, Math.min(1, absoluteX / pageWidth)),
  y: Math.max(0, Math.min(1, absoluteY / pageHeight)),
  width: absoluteWidth !== undefined ? Math.max(0, Math.min(1, absoluteWidth / pageWidth)) : undefined,
  height: absoluteHeight !== undefined ? Math.max(0, Math.min(1, absoluteHeight / pageHeight)) : undefined,
});

export const toAbsolutePosition = (
  relative: RelativePosition,
  pageWidth: number,
  pageHeight: number
): { x: number; y: number; width?: number; height?: number } => ({
  x: relative.x * pageWidth,
  y: relative.y * pageHeight,
  width: relative.width !== undefined ? relative.width * pageWidth : undefined,
  height: relative.height !== undefined ? relative.height * pageHeight : undefined,
});

export const scalePosition = (
  relative: RelativePosition,
  oldWidth: number,
  oldHeight: number,
  newWidth: number,
  newHeight: number
): RelativePosition => {
  const absolute = toAbsolutePosition(relative, oldWidth, oldHeight);
  return toRelativePosition(
    absolute.x,
    absolute.y,
    newWidth,
    newHeight,
    absolute.width,
    absolute.height
  );
};

export const generateId = (): string => {
  return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
};
