import React, { useRef, useEffect, useState, useCallback } from 'react';
import { useProjectStore } from '@/store/useProjectStore';
import { useEditorStore } from '@/store/useEditorStore';
import type { SVGElementData } from '@/types';
import { TransformControls } from './TransformControls';

interface SVGCanvasProps {
  width: number;
  height: number;
}

export const SVGCanvas: React.FC<SVGCanvasProps> = ({ width, height }) => {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const { project, updateElement } = useProjectStore();
  const { selectedElementId, setSelectedElementId, zoom, pan, showGrid, gridSize, snapToGrid } = useEditorStore();
  
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [elementStart, setElementStart] = useState({ x: 0, y: 0 });
  const [draggedElementId, setDraggedElementId] = useState<string | null>(null);

  const getMousePosition = useCallback((e: React.MouseEvent | MouseEvent) => {
    if (!svgRef.current) return { x: 0, y: 0 };
    const rect = svgRef.current.getBoundingClientRect();
    return {
      x: (e.clientX - rect.left) / zoom - pan.x,
      y: (e.clientY - rect.top) / zoom - pan.y,
    };
  }, [zoom, pan]);

  const snapToGridValue = useCallback((value: number) => {
    if (!snapToGrid) return value;
    return Math.round(value / gridSize) * gridSize;
  }, [snapToGrid, gridSize]);

  const handleElementMouseDown = useCallback((e: React.MouseEvent, elementId: string) => {
    e.stopPropagation();
    const element = project.elements.find(el => el.id === elementId);
    if (!element || element.locked) return;

    setSelectedElementId(elementId);
    setDraggedElementId(elementId);
    setIsDragging(true);
    const pos = getMousePosition(e);
    setDragStart(pos);
    setElementStart({ x: element.transform.x, y: element.transform.y });
  }, [project.elements, getMousePosition, setSelectedElementId]);

  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (!isDragging || !draggedElementId) return;

    const pos = getMousePosition(e);
    const deltaX = pos.x - dragStart.x;
    const deltaY = pos.y - dragStart.y;

    let newX = elementStart.x + deltaX;
    let newY = elementStart.y + deltaY;

    newX = snapToGridValue(newX);
    newY = snapToGridValue(newY);

    updateElement(draggedElementId, {
      transform: { x: newX, y: newY },
    });
  }, [isDragging, draggedElementId, dragStart, elementStart, getMousePosition, snapToGridValue, updateElement]);

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
    setDraggedElementId(null);
  }, []);

  const handleCanvasClick = useCallback(() => {
    setSelectedElementId(null);
  }, [setSelectedElementId]);

  useEffect(() => {
    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [handleMouseMove, handleMouseUp]);

  const renderElement = (element: SVGElementData) => {
    const { id, type, attributes, transform, visible } = element;
    const isSelected = selectedElementId === id;
    const commonProps = {
      id,
      opacity: visible ? 1 : 0.3,
      style: { cursor: element.locked ? 'not-allowed' : 'move' },
      onMouseDown: (e: React.MouseEvent) => handleElementMouseDown(e, id),
    };

    const transformString = `translate(${transform.x}, ${transform.y}) rotate(${transform.rotation}) scale(${transform.scaleX}, ${transform.scaleY})`;

    switch (type) {
      case 'rect':
        return (
          <rect
            key={id}
            {...commonProps}
            x={0}
            y={0}
            width={attributes.width}
            height={attributes.height}
            fill={attributes.fill}
            rx={attributes.rx}
            ry={attributes.ry}
            stroke={isSelected ? '#00d9ff' : attributes.stroke || 'none'}
            strokeWidth={isSelected ? 2 : attributes.strokeWidth || 0}
            transform={transformString}
          />
        );
      case 'circle':
        return (
          <circle
            key={id}
            {...commonProps}
            cx={0}
            cy={0}
            r={attributes.r}
            fill={attributes.fill}
            stroke={isSelected ? '#00d9ff' : attributes.stroke || 'none'}
            strokeWidth={isSelected ? 2 : attributes.strokeWidth || 0}
            transform={transformString}
          />
        );
      case 'ellipse':
        return (
          <ellipse
            key={id}
            {...commonProps}
            cx={0}
            cy={0}
            rx={attributes.rx}
            ry={attributes.ry}
            fill={attributes.fill}
            stroke={isSelected ? '#00d9ff' : attributes.stroke || 'none'}
            strokeWidth={isSelected ? 2 : attributes.strokeWidth || 0}
            transform={transformString}
          />
        );
      case 'line':
        return (
          <line
            key={id}
            {...commonProps}
            x1={0}
            y1={0}
            x2={attributes.x2}
            y2={attributes.y2}
            stroke={attributes.stroke}
            strokeWidth={attributes.strokeWidth}
            transform={transformString}
          />
        );
      case 'path':
        return (
          <path
            key={id}
            {...commonProps}
            d={attributes.d}
            fill={attributes.fill}
            stroke={attributes.stroke}
            strokeWidth={attributes.strokeWidth}
            transform={transformString}
          />
        );
      case 'polygon':
        return (
          <polygon
            key={id}
            {...commonProps}
            points={attributes.points}
            fill={attributes.fill}
            stroke={isSelected ? '#00d9ff' : attributes.stroke || 'none'}
            strokeWidth={isSelected ? 2 : attributes.strokeWidth || 0}
            transform={transformString}
          />
        );
      case 'text':
        return (
          <text
            key={id}
            {...commonProps}
            x={0}
            y={0}
            fontSize={attributes.fontSize}
            fontFamily={attributes.fontFamily}
            fill={attributes.fill}
            transform={transformString}
          >
            {attributes.text}
          </text>
        );
      default:
        return null;
    }
  };

  const selectedElement = project.elements.find(el => el.id === selectedElementId);

  return (
    <div 
      ref={containerRef} 
      className="w-full h-full overflow-hidden bg-bg-primary relative"
      onClick={handleCanvasClick}
    >
      {showGrid && (
        <div 
          className="absolute inset-0 canvas-grid pointer-events-none"
          style={{
            backgroundSize: `${gridSize * zoom}px ${gridSize * zoom}px`,
            backgroundPosition: `${pan.x * zoom}px ${pan.y * zoom}px`,
          }}
        />
      )}
      
      <svg
        ref={svgRef}
        width={width}
        height={height}
        viewBox={`0 0 ${width} ${height}`}
        className="absolute"
        style={{
          transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
          transformOrigin: 'top left',
          boxShadow: '0 0 50px rgba(0,0,0,0.5)',
        }}
      >
        <defs>
          <pattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse">
            <path d="M 20 0 L 0 0 0 20" fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="0.5"/>
          </pattern>
        </defs>
        
        <rect width="100%" height="100%" fill="#1a1a2e" />
        
        <g>
          {project.elements.map(renderElement)}
        </g>

        {selectedElement && (
          <TransformControls 
            element={selectedElement} 
            onUpdate={(updates) => updateElement(selectedElementId!, updates)}
          />
        )}
      </svg>
    </div>
  );
};
