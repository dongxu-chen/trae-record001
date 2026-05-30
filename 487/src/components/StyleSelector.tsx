import React from 'react';
import { IconStyle } from '../engine/types';
import { Palette, Square, Layers, Box } from 'lucide-react';

interface StyleSelectorProps {
  currentStyle: IconStyle;
  onStyleChange: (style: IconStyle) => void;
}

const styles: { id: IconStyle; label: string; icon: React.ReactNode; description: string }[] = [
  {
    id: 'outline',
    label: '线框风格',
    icon: <Palette className="w-5 h-5" />,
    description: '简约线框设计',
  },
  {
    id: 'filled',
    label: '填充风格',
    icon: <Square className="w-5 h-5" />,
    description: '纯色填充设计',
  },
  {
    id: 'gradient',
    label: '渐变风格',
    icon: <Layers className="w-5 h-5" />,
    description: '绚丽渐变效果',
  },
  {
    id: '3d',
    label: '3D风格',
    icon: <Box className="w-5 h-5" />,
    description: '立体3D效果',
  },
];

export function StyleSelector({ currentStyle, onStyleChange }: StyleSelectorProps) {
  return (
    <div className="space-y-3">
      <label className="block text-sm font-medium text-gray-700">
        图标风格
      </label>
      <div className="grid grid-cols-2 gap-2">
        {styles.map((style) => (
          <button
            key={style.id}
            onClick={() => onStyleChange(style.id)}
            className={`p-3 rounded-xl border-2 transition-all duration-200 text-left ${
              currentStyle === style.id
                ? 'border-blue-500 bg-blue-50 shadow-md'
                : 'border-gray-200 hover:border-blue-300 hover:bg-gray-50'
            }`}
          >
            <div className="flex items-center gap-2 mb-1">
              <span className={currentStyle === style.id ? 'text-blue-500' : 'text-gray-500'}>
                {style.icon}
              </span>
              <span className={`font-medium text-sm ${
                currentStyle === style.id ? 'text-blue-700' : 'text-gray-700'
              }`}>
                {style.label}
              </span>
            </div>
            <p className="text-xs text-gray-500 ml-7">
              {style.description}
            </p>
          </button>
        ))}
      </div>
    </div>
  );
}
