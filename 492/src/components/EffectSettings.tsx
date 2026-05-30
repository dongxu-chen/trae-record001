import React, { useState } from 'react';
import { Wand2, Sparkles, Code, Sun, Star, CircleOff } from 'lucide-react';
import { useLEDStore } from '../store/ledStore';
import { BackgroundEffect } from '../store/types';
import { ColorPicker } from './ColorPicker';

const effects: { value: BackgroundEffect; label: string; icon: React.ReactNode; desc: string }[] = [
  { value: 'none', label: '无特效', icon: <CircleOff className="w-5 h-5" />, desc: '纯色背景' },
  { value: 'particles', label: '粒子效果', icon: <Sparkles className="w-5 h-5" />, desc: '漂浮粒子' },
  { value: 'matrix', label: '矩阵雨', icon: <Code className="w-5 h-5" />, desc: '代码下落' },
  { value: 'neon-glow', label: '霓虹光晕', icon: <Sun className="w-5 h-5" />, desc: '扩散光晕' },
  { value: 'starfield', label: '星空闪烁', icon: <Star className="w-5 h-5" />, desc: '繁星点点' }
];

export const EffectSettings: React.FC = () => {
  const { background, setBackground } = useLEDStore();
  const [showEffectColorPicker, setShowEffectColorPicker] = useState(false);

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-semibold text-gray-200 flex items-center gap-2">
        <Wand2 className="w-4 h-4" />
        背景特效
      </h3>

      <div className="grid grid-cols-2 gap-2">
        {effects.map((effect) => (
          <button
            key={effect.value}
            onClick={() => setBackground({ effect: effect.value })}
            className={`flex flex-col items-center gap-2 p-3 rounded-lg border transition-all ${
              background.effect === effect.value
                ? 'bg-cyan-500/20 border-cyan-500 text-cyan-400'
                : 'bg-gray-800/50 border-gray-700 text-gray-400 hover:border-gray-600'
            }`}
          >
            {effect.icon}
            <div className="text-center">
              <div className="text-sm font-medium">{effect.label}</div>
              <div className="text-xs opacity-70">{effect.desc}</div>
            </div>
          </button>
        ))}
      </div>

      {background.effect !== 'none' && (
        <>
          <div>
            <label className="text-xs text-gray-400 mb-1.5 block">
              特效强度: {background.effectIntensity}%
            </label>
            <input
              type="range"
              min="10"
              max="100"
              value={background.effectIntensity}
              onChange={(e) => setBackground({ effectIntensity: Number(e.target.value) })}
              className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-cyan-500"
            />
          </div>

          <div className="relative">
            <label className="text-xs text-gray-400 mb-1.5 block">特效颜色</label>
            <button
              onClick={() => setShowEffectColorPicker(!showEffectColorPicker)}
              className="w-full flex items-center gap-3 p-3 bg-gray-800/50 border border-gray-700 rounded-lg hover:border-gray-600 transition-colors"
            >
              <div
                className="w-8 h-8 rounded-md border-2 border-gray-600"
                style={{ backgroundColor: background.effectColor }}
              />
              <span className="text-sm text-gray-300 font-mono">{background.effectColor.toUpperCase()}</span>
            </button>

            {showEffectColorPicker && (
              <div className="absolute z-20 top-full left-0 mt-2 p-3 bg-gray-900 rounded-xl border border-gray-700 shadow-2xl">
                <ColorPicker
                  color={background.effectColor}
                  onChange={(color) => setBackground({ effectColor: color })}
                />
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
};
