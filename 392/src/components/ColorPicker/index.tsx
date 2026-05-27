import React from 'react';
import { useIconStore } from '../../store/iconStore';
import { Layers, Palette } from 'lucide-react';

const presetColors = [
  '#4F46E5',
  '#06B6D4',
  '#10B981',
  '#F59E0B',
  '#EF4444',
  '#EC4899',
  '#8B5CF6',
  '#3B82F6',
  '#FFFFFF',
  '#000000',
  '#6B7280',
  '#374151',
];

const ColorPicker: React.FC = () => {
  const { currentColor, setCurrentColor, currentSize, setCurrentSize, useFilterMode, setUseFilterMode } = useIconStore();

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <h5 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
          调色板
        </h5>
        <button
          onClick={() => setUseFilterMode(!useFilterMode)}
          className={`flex items-center gap-1.5 px-2 py-1 rounded-md text-xs transition-all ${
            useFilterMode
              ? 'bg-[#4F46E5]/20 text-[#4F46E5]'
              : 'bg-[#1a1a2a] text-gray-500 hover:text-gray-300'
          }`}
          title={useFilterMode ? '使用CSS Filter模式' : '使用直接填充模式'}
        >
          {useFilterMode ? <Layers size={12} /> : <Palette size={12} />}
          {useFilterMode ? 'Filter' : 'Fill'}
        </button>
      </div>
      
      <div className="grid grid-cols-6 gap-2 mb-4">
        {presetColors.map((color) => (
          <button
            key={color}
            onClick={() => setCurrentColor(color)}
            className={`w-full aspect-square rounded-lg border-2 transition-all relative group ${
              currentColor === color
                ? 'border-[#4F46E5] scale-110'
                : 'border-[#2a2a3a] hover:border-[#3a3a4a]'
            }`}
            style={{ backgroundColor: color }}
          >
            {currentColor === color && (
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="w-2 h-2 rounded-full bg-white shadow-lg" />
              </div>
            )}
          </button>
        ))}
      </div>

      <div className="flex items-center gap-3 mb-4">
        <input
          type="color"
          value={currentColor}
          onChange={(e) => setCurrentColor(e.target.value)}
          className="w-10 h-10 rounded-lg border-2 border-[#2a2a3a] cursor-pointer bg-transparent"
        />
        <input
          type="text"
          value={currentColor}
          onChange={(e) => setCurrentColor(e.target.value)}
          className="flex-1 px-3 py-2 rounded-lg bg-[#1a1a2a] border border-[#2a2a3a] text-gray-300 text-sm focus:outline-none focus:border-[#4F46E5]/50"
        />
      </div>

      <div>
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs text-gray-500">图标大小</span>
          <span className="text-xs text-gray-400">{currentSize}px</span>
        </div>
        <input
          type="range"
          min={16}
          max={64}
          value={currentSize}
          onChange={(e) => setCurrentSize(Number(e.target.value))}
          className="w-full h-2 bg-[#1a1a2a] rounded-lg appearance-none cursor-pointer accent-[#4F46E5]"
        />
      </div>

      {useFilterMode && (
        <div className="mt-4 p-3 rounded-lg bg-[#4F46E5]/10 border border-[#4F46E5]/20">
          <p className="text-xs text-[#4F46E5]">
            💡 Filter模式使用CSS滤镜混合模式变色，对彩色图标效果更好
          </p>
        </div>
      )}
    </div>
  );
};

export default ColorPicker;
