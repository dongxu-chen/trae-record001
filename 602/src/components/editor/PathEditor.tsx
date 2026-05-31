import React, { useState, useRef, useCallback, useEffect } from 'react';
import { useProjectStore } from '@/store/useProjectStore';
import { useEditorStore } from '@/store/useEditorStore';

interface Point {
  x: number;
  y: number;
  type: 'move' | 'line' | 'cubic';
  handleIn?: { x: number; y: number };
  handleOut?: { x: number; y: number };
}

interface PathEditorProps {
  elementId: string;
  onClose: () => void;
}

export const PathEditor: React.FC<PathEditorProps> = ({ elementId, onClose }) => {
  const { project, updateElement } = useProjectStore();
  const { zoom } = useEditorStore();
  const svgRef = useRef<SVGSVGElement>(null);
  const [points, setPoints] = useState<Point[]>([]);
  const [selectedPointIndex, setSelectedPointIndex] = useState<number | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [dragType, setDragType] = useState<'point' | 'handleIn' | 'handleOut' | null>(null);
  const [isDrawing, setIsDrawing] = useState(false);

  const element = project.elements.find(e => e.id === elementId);
  const pathData = element?.attributes.d || '';

  useEffect(() => {
    if (pathData) {
      const parsed = parsePathData(pathData);
      setPoints(parsed);
    }
  }, [pathData]);

  const parsePathData = (d: string): Point[] => {
    const result: Point[] = [];
    const commands = d.match(/[a-zA-Z][^a-zA-Z]*/g) || [];
    
    let currentX = 0;
    let currentY = 0;

    commands.forEach(cmd => {
      const type = cmd[0];
      const nums = cmd.slice(1).trim().split(/[\s,]+/).map(Number).filter(n => !isNaN(n));

      switch (type) {
        case 'M':
        case 'm': {
          const x = type === 'm' ? currentX + nums[0] : nums[0];
          const y = type === 'm' ? currentY + nums[1] : nums[1];
          result.push({ x, y, type: 'move' });
          currentX = x;
          currentY = y;
          break;
        }
        case 'L':
        case 'l': {
          const x = type === 'l' ? currentX + nums[0] : nums[0];
          const y = type === 'l' ? currentY + nums[1] : nums[1];
          result.push({ x, y, type: 'line' });
          currentX = x;
          currentY = y;
          break;
        }
        case 'C':
        case 'c': {
          for (let i = 0; i < nums.length; i += 6) {
            const cp1x = type === 'c' ? currentX + nums[i] : nums[i];
            const cp1y = type === 'c' ? currentY + nums[i + 1] : nums[i + 1];
            const cp2x = type === 'c' ? currentX + nums[i + 2] : nums[i + 2];
            const cp2y = type === 'c' ? currentY + nums[i + 3] : nums[i + 3];
            const x = type === 'c' ? currentX + nums[i + 4] : nums[i + 4];
            const y = type === 'c' ? currentY + nums[i + 5] : nums[i + 5];
            result.push({
              x, y,
              type: 'cubic',
              handleIn: { x: cp1x, y: cp1y },
              handleOut: { x: cp2x, y: cp2y }
            });
            currentX = x;
            currentY = y;
          }
          break;
        }
      }
    });

    return result;
  };

  const generatePathData = (pts: Point[]): string => {
    if (pts.length === 0) return '';
    
    let d = `M ${pts[0].x.toFixed(1)} ${pts[0].y.toFixed(1)}`;
    
    for (let i = 1; i < pts.length; i++) {
      const p = pts[i];
      if (p.type === 'line') {
        d += ` L ${p.x.toFixed(1)} ${p.y.toFixed(1)}`;
      } else if (p.type === 'cubic' && p.handleIn && p.handleOut) {
        d += ` C ${p.handleIn.x.toFixed(1)} ${p.handleIn.y.toFixed(1)}, ${p.handleOut.x.toFixed(1)} ${p.handleOut.y.toFixed(1)}, ${p.x.toFixed(1)} ${p.y.toFixed(1)}`;
      }
    }
    
    return d;
  };

  const getMousePosition = useCallback((e: React.MouseEvent | MouseEvent) => {
    if (!svgRef.current) return { x: 0, y: 0 };
    const rect = svgRef.current.getBoundingClientRect();
    const transform = element?.transform || { x: 0, y: 0 };
    return {
      x: (e.clientX - rect.left) / zoom - transform.x,
      y: (e.clientY - rect.top) / zoom - transform.y,
    };
  }, [zoom, element?.transform]);

  const handleCanvasClick = useCallback((e: React.MouseEvent) => {
    if (!isDrawing) return;
    
    const pos = getMousePosition(e);
    
    setPoints(prev => {
      const newPoints = [...prev];
      
      if (newPoints.length === 0) {
        newPoints.push({ x: pos.x, y: pos.y, type: 'move' });
      } else {
        newPoints.push({ x: pos.x, y: pos.y, type: 'line' });
      }
      
      const newPathData = generatePathData(newPoints);
      updateElement(elementId, { attributes: { ...element?.attributes, d: newPathData } });
      
      return newPoints;
    });
  }, [isDrawing, getMousePosition, elementId, element?.attributes, updateElement]);

  const handlePointMouseDown = useCallback((e: React.MouseEvent, index: number, type: 'point' | 'handleIn' | 'handleOut') => {
    e.stopPropagation();
    setSelectedPointIndex(index);
    setIsDragging(true);
    setDragType(type);
  }, []);

  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (!isDragging || selectedPointIndex === null || !dragType) return;

    const pos = getMousePosition(e as unknown as React.MouseEvent);

    setPoints(prev => {
      const newPoints = [...prev];
      const point = { ...newPoints[selectedPointIndex] };

      if (dragType === 'point') {
        point.x = pos.x;
        point.y = pos.y;
      } else if (dragType === 'handleIn') {
        point.handleIn = { x: pos.x, y: pos.y };
      } else if (dragType === 'handleOut') {
        point.handleOut = { x: pos.x, y: pos.y };
      }

      newPoints[selectedPointIndex] = point;
      
      const newPathData = generatePathData(newPoints);
      updateElement(elementId, { attributes: { ...element?.attributes, d: newPathData } });

      return newPoints;
    });
  }, [isDragging, selectedPointIndex, dragType, getMousePosition, elementId, element?.attributes, updateElement]);

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
    setDragType(null);
  }, []);

  useEffect(() => {
    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [handleMouseMove, handleMouseUp]);

  const convertToCurve = (index: number) => {
    setPoints(prev => {
      const newPoints = [...prev];
      const point = newPoints[index];
      
      if (point.type === 'line') {
        const prevPoint = newPoints[index - 1] || point;
        newPoints[index] = {
          ...point,
          type: 'cubic',
          handleIn: { x: (prevPoint.x + point.x) / 2, y: (prevPoint.y + point.y) / 2 },
          handleOut: { x: point.x, y: point.y }
        };
        
        const newPathData = generatePathData(newPoints);
        updateElement(elementId, { attributes: { ...element?.attributes, d: newPathData } });
      }
      
      return newPoints;
    });
  };

  const deletePoint = (index: number) => {
    if (points.length <= 1) return;
    
    setPoints(prev => {
      const newPoints = prev.filter((_, i) => i !== index);
      const newPathData = generatePathData(newPoints);
      updateElement(elementId, { attributes: { ...element?.attributes, d: newPathData } });
      return newPoints;
    });
    
    setSelectedPointIndex(null);
  };

  return (
    <div className="absolute inset-0 z-30 pointer-events-none">
      <div className="pointer-events-auto">
        <svg
          ref={svgRef}
          className="absolute inset-0"
          style={{ transform: `translate(${element?.transform.x || 0}px, ${element?.transform.y || 0}px) scale(${zoom})`, transformOrigin: 'top left' }}
          onClick={handleCanvasClick}
        >
          {points.map((point, index) => {
            const nextPoint = points[index + 1];
            
            if (nextPoint?.type === 'cubic' && nextPoint.handleIn) {
              return (
                <g key={index}>
                  <line
                    x1={point.x}
                    y1={point.y}
                    x2={nextPoint.handleIn.x}
                    y2={nextPoint.handleIn.y}
                    stroke="#00d9ff"
                    strokeWidth="1"
                    strokeDasharray="3,3"
                    opacity="0.6"
                  />
                  <circle
                    cx={nextPoint.handleIn.x}
                    cy={nextPoint.handleIn.y}
                    r="4"
                    fill="#00d9ff"
                    cursor="pointer"
                    onMouseDown={(e) => handlePointMouseDown(e, index + 1, 'handleIn')}
                  />
                </g>
              );
            }
            return null;
          })}

          {points.map((point, index) => (
            point.type === 'cubic' && point.handleOut && (
              <g key={`out-${index}`}>
                <line
                  x1={point.x}
                  y1={point.y}
                  x2={point.handleOut.x}
                  y2={point.handleOut.y}
                  stroke="#e94560"
                  strokeWidth="1"
                  strokeDasharray="3,3"
                  opacity="0.6"
                />
                <circle
                  cx={point.handleOut.x}
                  cy={point.handleOut.y}
                  r="4"
                  fill="#e94560"
                  cursor="pointer"
                  onMouseDown={(e) => handlePointMouseDown(e, index, 'handleOut')}
                />
              </g>
            )
          ))}

          {points.map((point, index) => (
            <circle
              key={`point-${index}`}
              cx={point.x}
              cy={point.y}
              r={selectedPointIndex === index ? 6 : 4}
              fill={selectedPointIndex === index ? '#e94560' : '#fff'}
              stroke={selectedPointIndex === index ? '#fff' : '#00d9ff'}
              strokeWidth="2"
              cursor="pointer"
              onMouseDown={(e) => handlePointMouseDown(e, index, 'point')}
            />
          ))}
        </svg>
      </div>

      <div className="absolute top-4 right-4 bg-bg-secondary border border-border-primary rounded-lg p-3 pointer-events-auto z-40">
        <div className="flex items-center gap-2 mb-3">
          <span className="text-sm text-text-primary font-medium">Path Editor</span>
          <button
            onClick={onClose}
            className="p-1 hover:bg-bg-tertiary rounded text-text-secondary hover:text-text-primary"
          >
            ✕
          </button>
        </div>
        
        <div className="space-y-2">
          <button
            onClick={() => setIsDrawing(!isDrawing)}
            className={`w-full px-3 py-1.5 rounded text-sm transition-colors ${
              isDrawing 
                ? 'bg-accent-primary text-white' 
                : 'bg-bg-tertiary text-text-secondary hover:text-text-primary'
            }`}
          >
            {isDrawing ? 'Stop Drawing' : 'Add Points'}
          </button>

          {selectedPointIndex !== null && (
            <>
              {points[selectedPointIndex]?.type === 'line' && selectedPointIndex > 0 && (
                <button
                  onClick={() => convertToCurve(selectedPointIndex)}
                  className="w-full px-3 py-1.5 rounded text-sm bg-bg-tertiary text-text-secondary hover:text-text-primary"
                >
                  Convert to Curve
                </button>
              )}
              <button
                onClick={() => deletePoint(selectedPointIndex)}
                className="w-full px-3 py-1.5 rounded text-sm bg-accent-primary/20 text-accent-primary hover:bg-accent-primary/30"
              >
                Delete Point
              </button>
            </>
          )}

          <div className="text-xs text-text-muted mt-2 pt-2 border-t border-border-primary">
            <div>Points: {points.length}</div>
            {selectedPointIndex !== null && (
              <div>Selected: [{points[selectedPointIndex]?.x.toFixed(0)}, {points[selectedPointIndex]?.y.toFixed(0)}]</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
