import React, { useState, useCallback } from 'react';
import { useCanvas3D } from '../hooks/useCanvas3D';
import type { Surface3D as Surface3DType } from '../types';

interface Surface3DProps {
  width: number;
  height: number;
  surfaces: Surface3DType[];
  onSurfacesChange?: (surfaces: Surface3DType[]) => void;
}

const EXAMPLE_3D = [
  { label: 'sin(r)/r', expr: 'sin(sqrt(x^2 + y^2)) / sqrt(x^2 + y^2)' },
  { label: '旋转抛物面', expr: 'x^2 + y^2' },
  { label: '双曲抛物面', expr: 'x^2 - y^2' },
  { label: '波浪面', expr: 'sin(x) * cos(y)' },
  { label: '钟形曲线', expr: 'exp(-(x^2 + y^2) / 2)' },
  { label: '马鞍面', expr: 'x * y' },
];

const COLORS = ['#ef4444', '#22c55e', '#3b82f6', '#f59e0b', '#8b5cf6', '#ec4899'];

export const Surface3D: React.FC<Surface3DProps> = ({
  width,
  height,
  surfaces,
  onSurfacesChange
}) => {
  const [newExpression, setNewExpression] = useState('sin(sqrt(x^2 + y^2)) / sqrt(x^2 + y^2)');
  const [xRange, setXRange] = useState({ min: -5, max: 5 });
  const [yRange, setYRange] = useState({ min: -5, max: 5 });
  const [resolution, setResolution] = useState(40);
  const [showWireframe, setShowWireframe] = useState(false);
  const [showSurface, setShowSurface] = useState(true);

  const {
    canvasRef,
    view3D,
    setView3D,
    handleMouseDown,
    handleMouseMove,
    handleMouseUp,
    handleWheel,
    autoRotate,
    setAutoRotate
  } = useCanvas3D({
    canvasWidth: width,
    canvasHeight: height,
    surfaces
  });

  const addSurface = useCallback(() => {
    if (!newExpression.trim()) return;

    const newSurface: Surface3DType = {
      id: `surface-${Date.now()}`,
      expression: newExpression,
      color: COLORS[surfaces.length % COLORS.length],
      visible: true,
      xMin: xRange.min,
      xMax: xRange.max,
      yMin: yRange.min,
      yMax: yRange.max,
      resolution,
      showWireframe,
      showSurface
    };

    onSurfacesChange?.([...surfaces, newSurface]);
  }, [newExpression, xRange, yRange, resolution, showWireframe, showSurface, surfaces, onSurfacesChange]);

  const removeSurface = useCallback((id: string) => {
    onSurfacesChange?.(surfaces.filter(s => s.id !== id));
  }, [surfaces, onSurfacesChange]);

  const toggleSurfaceVisibility = useCallback((id: string) => {
    onSurfacesChange?.(surfaces.map(s =>
      s.id === id ? { ...s, visible: !s.visible } : s
    ));
  }, [surfaces, onSurfacesChange]);

  const resetView = useCallback(() => {
    setView3D({
      rotation: { x: -0.5, y: 0.6, z: 0 },
      scale: 50,
      distance: 400,
      centerX: 0,
      centerY: 0,
      centerZ: 0
    });
  }, [setView3D]);

  return (
    <div className="flex gap-4">
      <div className="flex-1">
        <div className="relative">
          <canvas
            ref={canvasRef}
            width={width}
            height={height}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
            onWheel={handleWheel}
            className="rounded-lg shadow-lg cursor-grab active:cursor-grabbing"
            style={{ background: '#0f172a' }}
          />
          <div className="absolute top-2 right-2 flex gap-2">
            <button
              onClick={() => setAutoRotate(!autoRotate)}
              className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                autoRotate
                  ? 'bg-blue-500 text-white'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              {autoRotate ? '停止旋转' : '自动旋转'}
            </button>
            <button
              onClick={resetView}
              className="px-3 py-1 rounded text-sm font-medium bg-gray-700 text-gray-300 hover:bg-gray-600 transition-colors"
            >
              重置视图
            </button>
          </div>
        </div>

        <div className="mt-2 text-xs text-gray-500 text-center">
          拖拽旋转视角 · 滚轮缩放
        </div>
      </div>

      <div className="w-72 bg-gray-800 rounded-lg p-4">
        <h3 className="text-white font-semibold mb-3">3D 曲面设置</h3>

        <div className="mb-4">
          <label className="block text-gray-400 text-sm mb-1">表达式 z = f(x, y)</label>
          <input
            type="text"
            value={newExpression}
            onChange={(e) => setNewExpression(e.target.value)}
            className="w-full px-3 py-2 bg-gray-700 text-white rounded border border-gray-600 focus:border-blue-500 focus:outline-none text-sm"
            placeholder="例如: sin(x) * cos(y)"
          />
        </div>

        <div className="grid grid-cols-2 gap-2 mb-4">
          <div>
            <label className="block text-gray-400 text-xs mb-1">X 最小值</label>
            <input
              type="number"
              value={xRange.min}
              onChange={(e) => setXRange(prev => ({ ...prev, min: parseFloat(e.target.value) || -5 }))}
              className="w-full px-2 py-1 bg-gray-700 text-white rounded border border-gray-600 focus:border-blue-500 focus:outline-none text-sm"
            />
          </div>
          <div>
            <label className="block text-gray-400 text-xs mb-1">X 最大值</label>
            <input
              type="number"
              value={xRange.max}
              onChange={(e) => setXRange(prev => ({ ...prev, max: parseFloat(e.target.value) || 5 }))}
              className="w-full px-2 py-1 bg-gray-700 text-white rounded border border-gray-600 focus:border-blue-500 focus:outline-none text-sm"
            />
          </div>
          <div>
            <label className="block text-gray-400 text-xs mb-1">Y 最小值</label>
            <input
              type="number"
              value={yRange.min}
              onChange={(e) => setYRange(prev => ({ ...prev, min: parseFloat(e.target.value) || -5 }))}
              className="w-full px-2 py-1 bg-gray-700 text-white rounded border border-gray-600 focus:border-blue-500 focus:outline-none text-sm"
            />
          </div>
          <div>
            <label className="block text-gray-400 text-xs mb-1">Y 最大值</label>
            <input
              type="number"
              value={yRange.max}
              onChange={(e) => setYRange(prev => ({ ...prev, max: parseFloat(e.target.value) || 5 }))}
              className="w-full px-2 py-1 bg-gray-700 text-white rounded border border-gray-600 focus:border-blue-500 focus:outline-none text-sm"
            />
          </div>
        </div>

        <div className="mb-4">
          <label className="block text-gray-400 text-xs mb-1">
            分辨率: {resolution} × {resolution}
          </label>
          <input
            type="range"
            min="10"
            max="80"
            value={resolution}
            onChange={(e) => setResolution(parseInt(e.target.value))}
            className="w-full"
          />
        </div>

        <div className="flex gap-2 mb-4">
          <label className="flex items-center gap-2 text-gray-400 text-sm cursor-pointer">
            <input
              type="checkbox"
              checked={showSurface}
              onChange={(e) => setShowSurface(e.target.checked)}
              className="rounded"
            />
            显示曲面
          </label>
          <label className="flex items-center gap-2 text-gray-400 text-sm cursor-pointer">
            <input
              type="checkbox"
              checked={showWireframe}
              onChange={(e) => setShowWireframe(e.target.checked)}
              className="rounded"
            />
            显示网格
          </label>
        </div>

        <button
          onClick={addSurface}
          className="w-full py-2 bg-blue-500 hover:bg-blue-600 text-white rounded font-medium text-sm transition-colors mb-4"
        >
          + 添加曲面
        </button>

        <div className="mb-4">
          <label className="block text-gray-400 text-sm mb-2">示例</label>
          <div className="flex flex-wrap gap-1">
            {EXAMPLE_3D.map((ex, idx) => (
              <button
                key={idx}
                onClick={() => setNewExpression(ex.expr)}
                className="px-2 py-1 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded text-xs transition-colors"
              >
                {ex.label}
              </button>
            ))}
          </div>
        </div>

        <div className="border-t border-gray-700 pt-4">
          <h4 className="text-gray-400 text-sm mb-2">曲面列表</h4>
          <div className="space-y-2 max-h-40 overflow-y-auto">
            {surfaces.map((surface) => (
              <div
                key={surface.id}
                className="flex items-center gap-2 p-2 bg-gray-700 rounded"
              >
                <div
                  className="w-3 h-3 rounded-full flex-shrink-0"
                  style={{ backgroundColor: surface.color }}
                />
                <button
                  onClick={() => toggleSurfaceVisibility(surface.id)}
                  className={`text-xs flex-1 text-left truncate ${
                    surface.visible ? 'text-white' : 'text-gray-500'
                  }`}
                >
                  {surface.expression}
                </button>
                <button
                  onClick={() => removeSurface(surface.id)}
                  className="text-red-400 hover:text-red-300 text-xs"
                >
                  ✕
                </button>
              </div>
            ))}
            {surfaces.length === 0 && (
              <p className="text-gray-500 text-xs text-center py-2">暂无曲面</p>
            )}
          </div>
        </div>

        <div className="mt-4 text-xs text-gray-500">
          <div className="grid grid-cols-3 gap-1 text-center">
            <div className="text-red-400">X 轴</div>
            <div className="text-green-400">Y 轴</div>
            <div className="text-blue-400">Z 轴</div>
          </div>
        </div>
      </div>
    </div>
  );
};
