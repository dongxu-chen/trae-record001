import React from 'react';
import { IconConfig, IconStyle } from '../engine/types';
import { StyleSelector } from './StyleSelector';
import { Type, Maximize2, Palette, Settings, Radius } from 'lucide-react';

interface ControlPanelProps {
  config: IconConfig;
  onTextChange: (text: string) => void;
  onSizeChange: (size: number) => void;
  onStyleChange: (style: IconStyle) => void;
  onPrimaryColorChange: (color: string) => void;
  onSecondaryColorChange: (color: string) => void;
  onPaddingChange: (padding: number) => void;
  onBorderRadiusChange: (radius: number) => void;
  onShowBackgroundChange: (show: boolean) => void;
}

export function ControlPanel({
  config,
  onTextChange,
  onSizeChange,
  onStyleChange,
  onPrimaryColorChange,
  onSecondaryColorChange,
  onPaddingChange,
  onBorderRadiusChange,
  onShowBackgroundChange,
}: ControlPanelProps) {
  return (
    <div className="bg-white rounded-2xl shadow-xl p-6 space-y-6">
      <div className="flex items-center gap-3 pb-4 border-b border-gray-100">
        <div className="p-2 bg-gradient-to-br from-blue-500 to-purple-500 rounded-xl">
          <Settings className="w-5 h-5 text-white" />
        </div>
        <div>
          <h3 className="text-lg font-semibold text-gray-800">控制面板</h3>
          <p className="text-sm text-gray-500">调整图标参数</p>
        </div>
      </div>

      <div className="space-y-4">
        <div className="space-y-2">
          <label className="flex items-center gap-2 text-sm font-medium text-gray-700">
            <Type className="w-4 h-4" />
            图标文字
          </label>
          <input
            type="text"
            value={config.text}
            onChange={(e) => onTextChange(e.target.value)}
            maxLength={2}
            placeholder="输入1-2个字符"
            className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-blue-500 focus:ring-4 focus:ring-blue-100 transition-all duration-200 text-lg font-semibold text-center uppercase"
          />
          <p className="text-xs text-gray-500">最多支持2个字符，将自动转换为大写</p>
        </div>
      </div>

      <StyleSelector
        currentStyle={config.style}
        onStyleChange={onStyleChange}
      />

      <div className="space-y-4">
        <div className="space-y-2">
          <label className="flex items-center justify-between text-sm font-medium text-gray-700">
            <span className="flex items-center gap-2">
              <Maximize2 className="w-4 h-4" />
              图标尺寸
            </span>
            <span className="text-blue-600 font-mono">{config.size}px</span>
          </label>
          <input
            type="range"
            min={64}
            max={512}
            step={16}
            value={config.size}
            onChange={(e) => onSizeChange(Number(e.target.value))}
            className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-500"
          />
          <div className="flex justify-between text-xs text-gray-400">
            <span>64px</span>
            <span>512px</span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <label className="flex items-center gap-2 text-sm font-medium text-gray-700">
            <Palette className="w-4 h-4" />
            主色调
          </label>
          <div className="relative">
            <input
              type="color"
              value={config.primaryColor}
              onChange={(e) => onPrimaryColorChange(e.target.value)}
              className="w-full h-12 rounded-xl cursor-pointer border-2 border-gray-200"
            />
          </div>
        </div>
        <div className="space-y-2">
          <label className="flex items-center gap-2 text-sm font-medium text-gray-700">
            <Palette className="w-4 h-4" />
            辅助色
          </label>
          <div className="relative">
            <input
              type="color"
              value={config.secondaryColor}
              onChange={(e) => onSecondaryColorChange(e.target.value)}
              className="w-full h-12 rounded-xl cursor-pointer border-2 border-gray-200"
            />
          </div>
        </div>
      </div>

      <div className="space-y-4">
        <div className="space-y-2">
          <label className="flex items-center justify-between text-sm font-medium text-gray-700">
            <span className="flex items-center gap-2">
              <Maximize2 className="w-4 h-4" />
              内边距
            </span>
            <span className="text-blue-600 font-mono">{config.padding}px</span>
          </label>
          <input
            type="range"
            min={0}
            max={64}
            step={4}
            value={config.padding}
            onChange={(e) => onPaddingChange(Number(e.target.value))}
            className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-500"
          />
        </div>
      </div>

      <div className="space-y-4">
        <div className="space-y-2">
          <label className="flex items-center justify-between text-sm font-medium text-gray-700">
            <span className="flex items-center gap-2">
              <Radius className="w-4 h-4" />
              圆角
            </span>
            <span className="text-blue-600 font-mono">{config.borderRadius}px</span>
          </label>
          <input
            type="range"
            min={0}
            max={48}
            step={4}
            value={config.borderRadius}
            onChange={(e) => onBorderRadiusChange(Number(e.target.value))}
            className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-500"
          />
        </div>
      </div>

      <div className="flex items-center justify-between p-4 bg-gray-50 rounded-xl">
        <span className="text-sm font-medium text-gray-700">显示背景</span>
        <button
          onClick={() => onShowBackgroundChange(!config.showBackground)}
          className={`relative w-12 h-6 rounded-full transition-colors duration-200 ${
            config.showBackground ? 'bg-blue-500' : 'bg-gray-300'
          }`}
        >
          <span
            className={`absolute top-1 w-4 h-4 bg-white rounded-full transition-transform duration-200 ${
              config.showBackground ? 'translate-x-7' : 'translate-x-1'
            }`}
          />
        </button>
      </div>
    </div>
  );
}
