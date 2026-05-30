import React, { useState } from 'react';
import { Type, Sparkles, Palette } from 'lucide-react';
import { useLEDStore } from '../store/ledStore';
import { ColorPicker } from './ColorPicker';

const fontFamilies = [
  { value: 'Orbitron, sans-serif', label: 'Orbitron (科技)' },
  { value: 'Rajdhani, sans-serif', label: 'Rajdhani (现代)' },
  { value: 'Monaco, monospace', label: 'Monaco (等宽)' },
  { value: 'Consolas, monospace', label: 'Consolas (代码)' },
  { value: 'Arial, sans-serif', label: 'Arial (通用)' },
  { value: 'Georgia, serif', label: 'Georgia (衬线)' },
  { value: '"Courier New", monospace', label: 'Courier New (打字机)' },
  { value: '"Microsoft YaHei", sans-serif', label: '微软雅黑 (中文)' }
];

export const FontSettings: React.FC = () => {
  const { font, setFont } = useLEDStore();
  const [showBgColorPicker, setShowBgColorPicker] = useState(false);
  const { background, setBackground } = useLEDStore();

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-semibold text-gray-200 flex items-center gap-2">
        <Type className="w-4 h-4" />
        字体样式
      </h3>

      <div>
        <label className="text-xs text-gray-400 mb-1.5 block">字体系列</label>
        <select
          value={font.family}
          onChange={(e) => setFont({ family: e.target.value })}
          className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-gray-200 focus:border-cyan-500 focus:outline-none appearance-none cursor-pointer"
        >
          {fontFamilies.map((f) => (
            <option key={f.value} value={f.value}>
              {f.label}
            </option>
          ))}
        </select>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="text-xs text-gray-400 mb-1.5 block">
            字号: {font.size}px
          </label>
          <input
            type="range"
            min="16"
            max="96"
            value={font.size}
            onChange={(e) => setFont({ size: Number(e.target.value) })}
            className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-cyan-500"
          />
        </div>

        <div>
          <label className="text-xs text-gray-400 mb-1.5 block">
            字重: {font.weight}
          </label>
          <input
            type="range"
            min="300"
            max="900"
            step="100"
            value={font.weight}
            onChange={(e) => setFont({ weight: Number(e.target.value) })}
            className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-cyan-500"
          />
        </div>
      </div>

      <div className="flex items-center justify-between p-3 bg-gray-800/50 rounded-lg border border-gray-700">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-cyan-400" />
          <span className="text-sm text-gray-200">发光效果</span>
        </div>
        <button
          onClick={() => setFont({ glow: !font.glow })}
          className={`relative w-12 h-6 rounded-full transition-colors ${
            font.glow ? 'bg-cyan-500' : 'bg-gray-600'
          }`}
        >
          <div
            className={`absolute top-1 w-4 h-4 bg-white rounded-full transition-transform ${
              font.glow ? 'translate-x-7' : 'translate-x-1'
            }`}
          />
        </button>
      </div>

      {font.glow && (
        <div>
          <label className="text-xs text-gray-400 mb-1.5 block">
            发光强度: {font.glowIntensity}px
          </label>
          <input
            type="range"
            min="2"
            max="30"
            value={font.glowIntensity}
            onChange={(e) => setFont({ glowIntensity: Number(e.target.value) })}
            className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-cyan-500"
          />
        </div>
      )}

      <div className="border-t border-gray-700 pt-4">
        <h3 className="text-sm font-semibold text-gray-200 flex items-center gap-2 mb-3">
          <Palette className="w-4 h-4" />
          背景颜色
        </h3>
        <div className="relative">
          <button
            onClick={() => setShowBgColorPicker(!showBgColorPicker)}
            className="w-full flex items-center gap-3 p-3 bg-gray-800/50 border border-gray-700 rounded-lg hover:border-gray-600 transition-colors"
          >
            <div
              className="w-8 h-8 rounded-md border-2 border-gray-600"
              style={{ backgroundColor: background.color }}
            />
            <span className="text-sm text-gray-300 font-mono">{background.color.toUpperCase()}</span>
          </button>

          {showBgColorPicker && (
            <div className="absolute z-20 top-full left-0 mt-2 p-3 bg-gray-900 rounded-xl border border-gray-700 shadow-2xl">
              <ColorPicker
                color={background.color}
                onChange={(color) => setBackground({ color })}
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
