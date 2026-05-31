import { Point, RelativePoint, Annotation } from '../../shared/types';

export interface ChartBounds {
  left: number;
  top: number;
  width: number;
  height: number;
}

export const toRelative = (point: Point, bounds: ChartBounds): RelativePoint => {
  return {
    x: Math.max(0, Math.min(1, (point.x - bounds.left) / bounds.width)),
    y: Math.max(0, Math.min(1, (point.y - bounds.top) / bounds.height)),
  };
};

export const toAbsolute = (point: RelativePoint, bounds: ChartBounds): Point => {
  return {
    x: bounds.left + point.x * bounds.width,
    y: bounds.top + point.y * bounds.height,
  };
};

export const annotationToAbsolute = (
  annotation: Annotation,
  bounds: ChartBounds
): Annotation & { absolutePosition: Point; absoluteEndPosition?: Point } => {
  return {
    ...annotation,
    absolutePosition: toAbsolute(annotation.position, bounds),
    absoluteEndPosition: annotation.endPosition
      ? toAbsolute(annotation.endPosition, bounds)
      : undefined,
  };
};

export const annotationToRelative = (
  annotation: Omit<Annotation, 'id' | 'createdAt' | 'updatedAt' | 'version'>,
  bounds: ChartBounds
): Omit<Annotation, 'id' | 'createdAt' | 'updatedAt' | 'version'> => {
  return {
    ...annotation,
    position: toRelative(annotation.position as Point, bounds),
    endPosition: annotation.endPosition
      ? toRelative(annotation.endPosition as Point, bounds)
      : undefined,
  };
};

export const clampRelativePoint = (point: RelativePoint): RelativePoint => {
  return {
    x: Math.max(0, Math.min(1, point.x)),
    y: Math.max(0, Math.min(1, point.y)),
  };
};

export const isPointInBounds = (point: Point, bounds: ChartBounds): boolean => {
  return (
    point.x >= bounds.left &&
    point.x <= bounds.left + bounds.width &&
    point.y >= bounds.top &&
    point.y <= bounds.top + bounds.height
  );
};

export const getDefaultChartBounds = (containerWidth: number, containerHeight: number): ChartBounds => {
  const padding = { left: 60, right: 40, top: 40, bottom: 60 };
  return {
    left: padding.left,
    top: padding.top,
    width: Math.max(100, containerWidth - padding.left - padding.right),
    height: Math.max(100, containerHeight - padding.top - padding.bottom),
  };
};
