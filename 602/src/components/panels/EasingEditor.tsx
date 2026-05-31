import React, { useState, useRef, useEffect, useCallback } from 'react';
import { EASING_PRESETS } from '@/types';

interface EasingEditorProps {
  value: string;
  onChange: (value: string) => void;
}

interface ControlPoint {
  x: number;
  y: number;
}

export const EasingEditor: React.FC<EasingEditorProps> = ({ value, onChange }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [isCustom, setIsCustom] = useState(false);
  const [controlPoints, setControlPoints] = useState<ControlPoint[]>([
    { x: 0.25, y: 0.1 },
    { x: 0.25, y: 1 }
  ]);
  const [draggingPoint, setDraggingPoint] = useState<number | null>(null);
  const [showPresets, setShowPresets] = useState(false);

  const canvasSize = 200;
  const padding = 20;
  const plotSize = canvasSize - padding * 2;

  useEffect(() => {
    if (value.startsWith('cubic-bezier')) {
      setIsCustom(true);
      const match = value.match(/cubic-bezier\(([^)]+)\)/);
      if (match) {
        const nums = match[1].split(',').map(Number);
        setControlPoints([
          { x: nums[0], y: nums[1] },
          { x: nums[2], y: nums[3] }
        ]);
      }
    } else {
      setIsCustom(false);
    }
  }, [value]);

  const drawCurve = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.clearRect(0, 0, canvasSize, canvasSize);

    ctx.fillStyle = '#16213e';
    ctx.fillRect(0, 0, canvasSize, canvasSize);

    ctx.strokeStyle = 'rgba(255, 255, 255, 0.05)';
    ctx.lineWidth = 1;
    for (let i = 0; i <= 4; i++) {
      const pos = padding + (plotSize / 4) * i;
      ctx.beginPath();
      ctx.moveTo(pos, padding);
      ctx.lineTo(pos, canvasSize - padding);
      ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(padding, pos);
      ctx.lineTo(canvasSize - padding, pos);
      ctx.stroke();
    }

    ctx.strokeStyle = 'rgba(255, 255, 255, 0.1)';
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ctx.moveTo(padding, canvasSize - padding);
    ctx.lineTo(canvasSize - padding, padding);
    ctx.stroke();
    ctx.setLineDash([]);

    const p1 = {
      x: padding + controlPoints[0].x * plotSize,
      y: canvasSize - padding - controlPoints[0].y * plotSize
    };
    const p2 = {
      x: padding + controlPoints[1].x * plotSize,
      y: canvasSize - padding - controlPoints[1].y * plotSize
    };
    const start = { x: padding, y: canvasSize - padding };
    const end = { x: canvasSize - padding, y: padding };

    ctx.strokeStyle = 'rgba(0, 217, 255, 0.3)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(start.x, start.y);
    ctx.lineTo(p1.x, p1.y);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(end.x, end.y);
    ctx.lineTo(p2.x, p2.y);
    ctx.stroke();

    ctx.strokeStyle = '#e94560';
    ctx.lineWidth = 2.5;
    ctx.beginPath();
    ctx.moveTo(start.x, start.y);
    ctx.bezierCurveTo(p1.x, p1.y, p2.x, p2.y, end.x, end.y);
    ctx.stroke();

    [p1, p2].forEach((p, i) => {
      ctx.fillStyle = i === 0 ? '#00d9ff' : '#e94560';
      ctx.beginPath();
      ctx.arc(p.x, p.y, 6, 0, Math.PI * 2);
      ctx.fill();
      ctx.strokeStyle = '#fff';
      ctx.lineWidth = 2;
      ctx.stroke();
    });

    ctx.fillStyle = '#fff';
    ctx.beginPath();
    ctx.arc(start.x, start.y, 4, 0, Math.PI * 2);
    ctx.fill();
    ctx.beginPath();
    ctx.arc(end.x, end.y, 4, 0, Math.PI * 2);
    ctx.fill();
  }, [controlPoints, plotSize, canvasSize, padding]);

  useEffect(() => {
    drawCurve();
  }, [drawCurve]);

  const handleMouseDown = (e: React.MouseEvent, pointIndex: number) => {
    e.stopPropagation();
    setDraggingPoint(pointIndex);
    setIsCustom(true);
  };

  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (draggingPoint === null) return;

    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    let x = (e.clientX - rect.left - padding) / plotSize;
    let y = 1 - (e.clientY - rect.top - padding) / plotSize;

    x = Math.max(0, Math.min(1, x));
    y = Math.max(0, Math.min(1, y));

    setControlPoints(prev => {
      const newPoints = [...prev];
      newPoints[draggingPoint] = { x, y };
      return newPoints;
    });
  }, [draggingPoint, padding, plotSize]);

  const handleMouseUp = useCallback(() => {
    if (draggingPoint !== null && isCustom) {
      const bezier = `cubic-bezier(${controlPoints[0].x.toFixed(3)}, ${controlPoints[0].y.toFixed(3)}, ${controlPoints[1].x.toFixed(3)}, ${controlPoints[1].y.toFixed(3)})`;
      onChange(bezier);
    }
    setDraggingPoint(null);
  }, [draggingPoint, isCustom, controlPoints, onChange]);

  useEffect(() => {
    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [handleMouseMove, handleMouseUp]);

  const selectPreset = (presetValue: string) => {
    setIsCustom(false);
    onChange(presetValue);
    setShowPresets(false);
  };

  const presetCategories = [
    { name: 'Basic', presets: EASING_PRESETS.slice(0, 4) },
    { name: 'Power', presets: EASING_PRESETS.slice(4, 16) },
    { name: 'Back', presets: EASING_PRESETS.slice(16, 19) },
    { name: 'Elastic', presets: EASING_PRESETS.slice(19, 22) },
    { name: 'Bounce', presets: EASING_PRESETS.slice(22, 25) },
    { name: 'Circ', presets: EASING_PRESETS.slice(25, 28) },
    { name: 'Expo', presets: EASING_PRESETS.slice(28, 31) },
    { name: 'Sine', presets: EASING_PRESETS.slice(31, 34) },
  ];

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <label className="text-[10px] text-text-muted uppercase tracking-wider">Easing Curve</label>
        <button
          onClick={() => setShowPresets(!showPresets)}
          className="text-xs text-accent-secondary hover:text-accent-secondary/80"
        >
          Presets
        </button>
      </div>

      {showPresets && (
        <div className="max-h-48 overflow-y-auto space-y-2 bg-bg-tertiary rounded p-2">
          {presetCategories.map(category => (
            <div key={category.name}>
              <div className="text-[10px] text-text-muted px-1 mb-1">{category.name}</div>
              <div className="grid grid-cols-3 gap-1">
                {category.presets.map(preset => (
                  <button
                    key={preset.value}
                    onClick={() => selectPreset(preset.value)}
                    className={`text-xs px-2 py-1 rounded text-left transition-colors ${
                      value === preset.value
                        ? 'bg-accent-primary text-white'
                        : 'bg-bg-primary text-text-secondary hover:bg-bg-secondary'
                    }`}
                  >
                    {preset.label.split(' ').slice(-1)[0]}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="relative">
        <canvas
          ref={canvasRef}
          width={canvasSize}
          height={canvasSize}
          className="w-full rounded border border-border-primary cursor-crosshair"
          style={{ maxWidth: canvasSize }}
        />
        
        {controlPoints.map((point, i) => (
          <div
            key={i}
            className="absolute w-4 h-4 rounded-full cursor-grab active:cursor-grabbing"
            style={{
              left: `calc(${(padding + point.x * plotSize) / canvasSize * 100}% - 8px)`,
              top: `calc(${(canvasSize - padding - point.y * plotSize) / canvasSize * 100}% - 8px)`,
              backgroundColor: i === 0 ? '#00d9ff' : '#e94560',
              border: '2px solid white',
              boxShadow: '0 2px 8px rgba(0,0,0,0.3)'
            }}
            onMouseDown={(e) => handleMouseDown(e, i)}
          />
        ))}
      </div>

      <div className="grid grid-cols-4 gap-1">
        {['x1', 'y1', 'x2', 'y2'].map((label, i) => (
          <div key={label}>
            <label className="block text-[10px] text-text-muted mb-1">{label}</label>
            <input
              type="number"
              step="0.01"
              min="0"
              max="1"
              value={controlPoints[Math.floor(i / 2)][i % 2 === 0 ? 'x' : 'y'].toFixed(2)}
              onChange={(e) => {
                const val = Number(e.target.value);
                setControlPoints(prev => {
                  const newPoints = [...prev];
                  const pointIndex = Math.floor(i / 2);
                  const coord = i % 2 === 0 ? 'x' : 'y';
                  newPoints[pointIndex] = { ...newPoints[pointIndex], [coord]: val };
                  return newPoints;
                });
                setIsCustom(true);
              }}
              onBlur={() => {
                if (isCustom) {
                  const bezier = `cubic-bezier(${controlPoints[0].x.toFixed(3)}, ${controlPoints[0].y.toFixed(3)}, ${controlPoints[1].x.toFixed(3)}, ${controlPoints[1].y.toFixed(3)})`;
                  onChange(bezier);
                }
              }}
              className="w-full font-mono text-xs"
            />
          </div>
        ))}
      </div>

      {!isCustom && (
        <div className="text-xs text-text-muted text-center py-2">
          Drag control points to create custom easing
        </div>
      )}
    </div>
  );
};
