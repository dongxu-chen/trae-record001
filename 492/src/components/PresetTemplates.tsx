import React from 'react';
import { LayoutGrid, RotateCcw } from 'lucide-react';
import { useLEDStore, defaultPresets } from '../store/ledStore';

export const PresetTemplates: React.FC = () => {
  const { applyPreset, reset } = useLEDStore();

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-200 flex items-center gap-2">
          <LayoutGrid className="w-4 h-4" />
          预设模板
        </h3>
        <button
          onClick={reset}
          className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-300 transition-colors"
        >
          <RotateCcw className="w-3 h-3" />
          重置
        </button>
      </div>

      <div className="grid grid-cols-2 gap-2">
        {defaultPresets.map((preset, index) => (
          <button
            key={preset.name}
            onClick={() => applyPreset(preset)}
            className="relative p-3 bg-gray-800/50 border border-gray-700 rounded-lg hover:border-cyan-500/50 transition-all group overflow-hidden"
          >
            <div
              className="absolute inset-0 opacity-20 group-hover:opacity-30 transition-opacity"
              style={{
                background: `linear-gradient(135deg, ${preset.lines[0]?.color || '#00ff88'}, ${preset.lines[1]?.color || preset.background?.effectColor || '#ff0088'})`
              }}
            />
            <div className="relative">
              <div className="text-sm font-medium text-gray-200 mb-1">{preset.name}</div>
              <div className="text-xs text-gray-500">
                {preset.lines.length} 行 · {preset.scroll?.direction === 'left' ? '左滚' : preset.scroll?.direction === 'right' ? '右滚' : preset.scroll?.direction === 'up' ? '上滚' : '下滚'}
              </div>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
};
