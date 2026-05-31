import React, { useState, useRef, useCallback, useEffect } from 'react';
import type { SVGElementData } from '@/types';

interface TransformControlsProps {
  element: SVGElementData;
  onUpdate: (updates: Partial<SVGElementData>) => void;
}

export const TransformControls: React.FC<TransformControlsProps> = ({ element, onUpdate }) => {
  const [isDragging, setIsDragging] = useState<string | null>(null);
  const [startPos, setStartPos] = useState({ x: 0, y: 0 });
  const [startTransform, setStartTransform] = useState(element.transform);
  const [startSize, setStartSize] = useState({ width: 0, height: 0 });
  const svgRef = useRef<SVGGElement>(null);

  const getElementBounds = useCallback(() => {
    const { type, attributes } = element;
    switch (type) {
      case 'rect':
        return { x: 0, y: 0, width: attributes.width, height: attributes.height };
      case 'circle':
        const r = attributes.r || 50;
        return { x: -r, y: -r, width: r * 2, height: r * 2 };
      case 'ellipse':
        const rx = attributes.rx || 50;
        const ry = attributes.ry || 30;
        return { x: -rx, y: -ry, width: rx * 2, height: ry * 2 };
      case 'polygon':
        return { x: 0, y: 0, width: 100, height: 80 };
      case 'path':
        return { x: 0, y: 0, width: 150, height: 50 };
      case 'line':
        return { x: 0, y: 0, width: attributes.x2 || 100, height: attributes.y2 || 50 };
      case 'text':
        const fontSize = attributes.fontSize || 24;
        return { x: 0, y: -fontSize, width: (attributes.text?.length || 4) * fontSize * 0.6, height: fontSize };
      default:
        return { x: 0, y: 0, width: 100, height: 100 };
    }
  }, [element]);

  const bounds = getElementBounds();
  const { x, y, rotation, scaleX, scaleY } = element.transform;

  const handleMouseDown = useCallback((handle: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setIsDragging(handle);
    setStartPos({ x: e.clientX, y: e.clientY });
    setStartTransform({ ...element.transform });
    const b = getElementBounds();
    setStartSize({ width: b.width, height: b.height });
  }, [element.transform, getElementBounds]);

  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (!isDragging) return;

    const deltaX = (e.clientX - startPos.x) / 1;
    const deltaY = (e.clientY - startPos.y) / 1;

    switch (isDragging) {
      case 'tl':
        onUpdate({
          transform: {
            ...startTransform,
            scaleX: Math.max(0.1, startTransform.scaleX - deltaX / startSize.width),
            scaleY: Math.max(0.1, startTransform.scaleY - deltaY / startSize.height),
          },
        });
        break;
      case 'tr':
        onUpdate({
          transform: {
            ...startTransform,
            scaleX: Math.max(0.1, startTransform.scaleX + deltaX / startSize.width),
            scaleY: Math.max(0.1, startTransform.scaleY - deltaY / startSize.height),
          },
        });
        break;
      case 'bl':
        onUpdate({
          transform: {
            ...startTransform,
            scaleX: Math.max(0.1, startTransform.scaleX - deltaX / startSize.width),
            scaleY: Math.max(0.1, startTransform.scaleY + deltaY / startSize.height),
          },
        });
        break;
      case 'br':
        onUpdate({
          transform: {
            ...startTransform,
            scaleX: Math.max(0.1, startTransform.scaleX + deltaX / startSize.width),
            scaleY: Math.max(0.1, startTransform.scaleY + deltaY / startSize.height),
          },
        });
        break;
      case 'rotate':
        const centerX = x + bounds.width / 2;
        const centerY = y + bounds.height / 2;
        const angle = Math.atan2(e.clientY - centerY, e.clientX - centerX) * 180 / Math.PI;
        onUpdate({
          transform: {
            ...startTransform,
            rotation: angle,
          },
        });
        break;
    }
  }, [isDragging, startPos, startTransform, startSize, onUpdate, x, y, bounds]);

  const handleMouseUp = useCallback(() => {
    setIsDragging(null);
  }, []);

  useEffect(() => {
    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [handleMouseMove, handleMouseUp]);

  const transformString = `translate(${x}, ${y}) rotate(${rotation}) scale(${scaleX}, ${scaleY})`;

  const handleSize = 8;
  const handleOffset = handleSize / 2;

  return (
    <g transform={transformString} ref={svgRef}>
      <rect
        x={bounds.x - 5}
        y={bounds.y - 5}
        width={bounds.width + 10}
        height={bounds.height + 10}
        fill="none"
        stroke="#00d9ff"
        strokeWidth="1"
        strokeDasharray="4,4"
      />

      <circle
        cx={bounds.x + bounds.width / 2}
        cy={bounds.y - 25}
        r={4}
        fill="#00d9ff"
        cursor="grab"
        onMouseDown={(e) => handleMouseDown('rotate', e)}
      />
      <line
        x1={bounds.x + bounds.width / 2}
        y1={bounds.y - 5}
        x2={bounds.x + bounds.width / 2}
        y2={bounds.y - 20}
        stroke="#00d9ff"
        strokeWidth="1"
      />

      {['tl', 'tr', 'bl', 'br'].map((handle) => {
        let hx, hy;
        switch (handle) {
          case 'tl':
            hx = bounds.x - handleOffset;
            hy = bounds.y - handleOffset;
            break;
          case 'tr':
            hx = bounds.x + bounds.width - handleOffset;
            hy = bounds.y - handleOffset;
            break;
          case 'bl':
            hx = bounds.x - handleOffset;
            hy = bounds.y + bounds.height - handleOffset;
            break;
          case 'br':
            hx = bounds.x + bounds.width - handleOffset;
            hy = bounds.y + bounds.height - handleOffset;
            break;
        }
        return (
          <rect
            key={handle}
            x={hx}
            y={hy}
            width={handleSize}
            height={handleSize}
            fill="#00d9ff"
            stroke="#fff"
            strokeWidth="1"
            cursor={`${handle === 'tl' || handle === 'br' ? 'nwse' : 'nesw'}-resize`}
            onMouseDown={(e) => handleMouseDown(handle, e)}
          />
        );
      })}
    </g>
  );
};
