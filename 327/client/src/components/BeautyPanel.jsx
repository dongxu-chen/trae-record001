import React, { useState, useEffect } from 'react';
import { CloseIcon, SparklesIcon, MagicIcon } from './icons';

const presets = [
  {
    id: 'natural',
    name: '自然',
    smoothLevel: 0.3,
    whitenLevel: 0.2,
    slimLevel: 0.1,
    icon: '🌿'
  },
  {
    id: 'soft',
    name: '柔光',
    smoothLevel: 0.5,
    whitenLevel: 0.4,
    slimLevel: 0.2,
    icon: '✨'
  },
  {
    id: 'glam',
    name: '精致',
    smoothLevel: 0.7,
    whitenLevel: 0.6,
    slimLevel: 0.3,
    icon: '💎'
  },
  {
    id: 'max',
    name: '完美',
    smoothLevel: 0.9,
    whitenLevel: 0.8,
    slimLevel: 0.4,
    icon: '🌟'
  }
];

const BeautyPanel = ({ onClose, onBeautyChange, initialConfig }) => {
  const [enabled, setEnabled] = useState(initialConfig?.enabled || false);
  const [smoothLevel, setSmoothLevel] = useState(initialConfig?.smoothLevel ?? 0.5);
  const [whitenLevel, setWhitenLevel] = useState(initialConfig?.whitenLevel ?? 0.3);
  const [slimLevel, setSlimLevel] = useState(initialConfig?.slimLevel ?? 0.2);
  const [activePreset, setActivePreset] = useState(null);

  useEffect(() => {
    const preset = presets.find(p => 
      p.smoothLevel === smoothLevel &&
      p.whitenLevel === whitenLevel &&
      p.slimLevel === slimLevel
    );
    setActivePreset(preset?.id || null);
  }, [smoothLevel, whitenLevel, slimLevel]);

  const handlePresetClick = (preset) => {
    setSmoothLevel(preset.smoothLevel);
    setWhitenLevel(preset.whitenLevel);
    setSlimLevel(preset.slimLevel);
    setActivePreset(preset.id);
    setEnabled(true);
  };

  const handleToggle = () => {
    const newEnabled = !enabled;
    setEnabled(newEnabled);
    if (newEnabled) {
      onBeautyChange?.({
        enabled: true,
        smoothLevel,
        whitenLevel,
        slimLevel
      });
    } else {
      onBeautyChange?.({ enabled: false });
    }
  };

  const handleSliderChange = (type, value) => {
    if (type === 'smooth') setSmoothLevel(value);
    if (type === 'whiten') setWhitenLevel(value);
    if (type === 'slim') setSlimLevel(value);
    setActivePreset(null);

    if (enabled) {
      onBeautyChange?.({
        enabled: true,
        smoothLevel: type === 'smooth' ? value : smoothLevel,
        whitenLevel: type === 'whiten' ? value : whitenLevel,
        slimLevel: type === 'slim' ? value : slimLevel
      });
    }
  };

  const handleReset = () => {
    setSmoothLevel(0.5);
    setWhitenLevel(0.3);
    setSlimLevel(0.2);
    setActivePreset(null);
    setEnabled(false);
    onBeautyChange?.({ enabled: false });
  };

  return (
    <div className="h-full flex flex-col bg-slate-800">
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-700">
        <div className="flex items-center gap-2">
          <MagicIcon className="w-5 h-5 text-primary-400" />
          <h2 className="text-lg font-semibold text-white">美颜设置</h2>
        </div>
        <button
          onClick={onClose}
          className="w-8 h-8 rounded-lg hover:bg-slate-700 flex items-center justify-center text-slate-400 hover:text-white transition-colors"
        >
          <CloseIcon className="w-5 h-5" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        <div className="flex items-center justify-between mb-6 p-4 bg-slate-700/30 rounded-xl">
          <div className="flex items-center gap-3">
            <div className={`w-12 h-12 rounded-full flex items-center justify-center ${
              enabled ? 'bg-primary-500/20' : 'bg-slate-600/50'
            }`}>
              <SparklesIcon className={`w-6 h-6 ${enabled ? 'text-primary-400' : 'text-slate-500'}`} />
            </div>
            <div>
              <div className="text-white font-medium">美颜效果</div>
              <div className="text-xs text-slate-400">
                {enabled ? '已开启' : '点击开关启用'}
              </div>
            </div>
          </div>
          <button
            onClick={handleToggle}
            className={`relative w-14 h-8 rounded-full transition-colors ${
              enabled ? 'bg-primary-500' : 'bg-slate-600'
            }`}
          >
            <div className={`absolute top-1 w-6 h-6 rounded-full bg-white shadow-lg transition-transform ${
              enabled ? 'translate-x-7' : 'translate-x-1'
            }`} />
          </button>
        </div>

        <div className="mb-6">
          <h3 className="text-sm font-semibold text-slate-300 mb-3">一键美颜</h3>
          <div className="grid grid-cols-4 gap-2">
            {presets.map((preset) => (
              <button
                key={preset.id}
                onClick={() => handlePresetClick(preset)}
                className={`p-3 rounded-xl transition-all ${
                  activePreset === preset.id
                    ? 'bg-primary-500/20 border-2 border-primary-500'
                    : 'bg-slate-700/30 border-2 border-transparent hover:bg-slate-700/50'
                }`}
              >
                <div className="text-2xl mb-1">{preset.icon}</div>
                <div className={`text-xs font-medium ${
                  activePreset === preset.id ? 'text-primary-400' : 'text-slate-300'
                }`}>
                  {preset.name}
                </div>
              </button>
            ))}
          </div>
        </div>

        <div className="space-y-6">
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm font-medium text-slate-300">磨皮</label>
              <span className="text-xs text-primary-400 font-mono">
                {Math.round(smoothLevel * 100)}%
              </span>
            </div>
            <input
              type="range"
              min="0"
              max="1"
              step="0.01"
              value={smoothLevel}
              onChange={(e) => handleSliderChange('smooth', parseFloat(e.target.value))}
              disabled={!enabled}
              className="w-full h-2 bg-slate-700 rounded-full appearance-none cursor-pointer disabled:opacity-50"
              style={{
                background: `linear-gradient(to right, #6366f1 0%, #6366f1 ${smoothLevel * 100}%, #334155 ${smoothLevel * 100}%, #334155 100%)`
              }}
            />
            <div className="flex justify-between text-xs text-slate-500 mt-1">
              <span>自然</span>
              <span>磨皮</span>
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm font-medium text-slate-300">美白</label>
              <span className="text-xs text-primary-400 font-mono">
                {Math.round(whitenLevel * 100)}%
              </span>
            </div>
            <input
              type="range"
              min="0"
              max="1"
              step="0.01"
              value={whitenLevel}
              onChange={(e) => handleSliderChange('whiten', parseFloat(e.target.value))}
              disabled={!enabled}
              className="w-full h-2 bg-slate-700 rounded-full appearance-none cursor-pointer disabled:opacity-50"
              style={{
                background: `linear-gradient(to right, #6366f1 0%, #6366f1 ${whitenLevel * 100}%, #334155 ${whitenLevel * 100}%, #334155 100%)`
              }}
            />
            <div className="flex justify-between text-xs text-slate-500 mt-1">
              <span>自然</span>
              <span>亮白</span>
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm font-medium text-slate-300">瘦脸</label>
              <span className="text-xs text-primary-400 font-mono">
                {Math.round(slimLevel * 100)}%
              </span>
            </div>
            <input
              type="range"
              min="0"
              max="1"
              step="0.01"
              value={slimLevel}
              onChange={(e) => handleSliderChange('slim', parseFloat(e.target.value))}
              disabled={!enabled}
              className="w-full h-2 bg-slate-700 rounded-full appearance-none cursor-pointer disabled:opacity-50"
              style={{
                background: `linear-gradient(to right, #6366f1 0%, #6366f1 ${slimLevel * 100}%, #334155 ${slimLevel * 100}%, #334155 100%)`
              }}
            />
            <div className="flex justify-between text-xs text-slate-500 mt-1">
              <span>自然</span>
              <span>小脸</span>
            </div>
          </div>
        </div>

        <div className="mt-6 p-4 bg-primary-500/10 border border-primary-500/20 rounded-xl">
          <div className="flex items-start gap-3">
            <SparklesIcon className="w-5 h-5 text-primary-400 flex-shrink-0 mt-0.5" />
            <div>
              <div className="text-sm font-medium text-white">技术说明</div>
              <div className="text-xs text-slate-400 mt-1">
                <p>• 磨皮：双边滤波算法，保留边缘同时平滑皮肤</p>
                <p>• 美白：智能亮度调整，肤色区域识别</p>
                <p>• 瘦脸：GPU网格变形，自然过渡</p>
                <p className="text-primary-400 mt-1">全程WebGL加速，CPU占用 &lt; 5%</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="p-4 border-t border-slate-700">
        <button
          onClick={handleReset}
          className="w-full py-2 px-4 bg-slate-700 hover:bg-slate-600 text-slate-300 rounded-lg transition-colors text-sm"
        >
          重置为默认
        </button>
      </div>
    </div>
  );
};

export default BeautyPanel;
