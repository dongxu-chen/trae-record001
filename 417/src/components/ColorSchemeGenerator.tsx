import { useState } from 'react';
import { Palette, Download, ChevronDown } from 'lucide-react';
import { useColorStore } from '@/hooks/useColorStore';
import { generateColorScheme, SCHEME_TYPES } from '@/utils/colorScheme';
import type { ColorSchemeType, ColorScheme } from '@/types';

export default function ColorSchemeGenerator() {
  const { currentColor } = useColorStore();
  const [schemeType, setSchemeType] = useState<ColorSchemeType>('monochromatic');
  const [isOpen, setIsOpen] = useState(false);

  const scheme: ColorScheme = generateColorScheme(currentColor, schemeType);

  const handleExport = () => {
    const canvas = document.createElement('canvas');
    const padding = 32;
    const colorWidth = 140;
    const colorHeight = 120;
    const totalWidth = padding * 2 + scheme.colors.length * colorWidth;
    const totalHeight = padding * 3 + colorHeight + 80;
    canvas.width = totalWidth;
    canvas.height = totalHeight;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.fillStyle = '#1e1e2e';
    ctx.fillRect(0, 0, totalWidth, totalHeight);

    ctx.fillStyle = '#e5e7eb';
    ctx.font = 'bold 18px Inter, sans-serif';
    ctx.textAlign = 'left';
    ctx.fillText(scheme.name, padding, padding + 20);

    ctx.fillStyle = '#9ca3af';
    ctx.font = '13px Inter, sans-serif';
    ctx.fillText(`基于 ${currentColor.toUpperCase()}`, padding, padding + 44);

    scheme.colors.forEach((color, i) => {
      const x = padding + i * colorWidth;
      const y = padding + 60;
      ctx.fillStyle = color;
      ctx.fillRect(x, y, colorWidth - 8, colorHeight);
      ctx.fillStyle = '#d1d5db';
      ctx.font = '12px JetBrains Mono, monospace';
      ctx.textAlign = 'center';
      ctx.fillText(color.toUpperCase(), x + (colorWidth - 8) / 2, y + colorHeight + 24);
    });

    const link = document.createElement('a');
    link.href = canvas.toDataURL('image/png');
    link.download = `color-scheme-${schemeType}-${currentColor.replace('#', '')}.png`;
    link.click();
  };

  return (
    <div className="bg-[#1e1e2e] rounded-xl p-5 shadow-lg">
      <div className="flex items-center gap-2 mb-4">
        <Palette className="w-5 h-5 text-gray-300" />
        <h3 className="text-gray-200 font-medium">配色方案</h3>
      </div>

      <div className="relative mb-4">
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="w-full flex items-center justify-between bg-[#2a2a3e] text-gray-200 rounded-lg px-3 py-2 text-sm outline-none border border-transparent focus:border-[#5b5fc7]"
        >
          <span>{SCHEME_TYPES.find((t) => t.value === schemeType)?.label}</span>
          <ChevronDown className={`w-4 h-4 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
        </button>
        {isOpen && (
          <div className="absolute z-10 w-full mt-1 bg-[#2a2a3e] rounded-lg shadow-xl border border-white/5 overflow-hidden">
            {SCHEME_TYPES.map((type) => (
              <button
                key={type.value}
                onClick={() => {
                  setSchemeType(type.value);
                  setIsOpen(false);
                }}
                className={`w-full px-3 py-2 text-left text-sm hover:bg-[#3a3a4e] transition-colors ${
                  schemeType === type.value ? 'text-[#8b8cf7] bg-[#2a2a4e]' : 'text-gray-200'
                }`}
              >
                <div className="font-medium">{type.label}</div>
                <div className="text-xs text-gray-500">{type.description}</div>
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="flex gap-2 mb-4 overflow-x-auto pb-1">
        {scheme.colors.map((color, i) => (
          <div
            key={i}
            className="flex-shrink-0 w-full"
            style={{ maxWidth: `calc(${100 / scheme.colors.length}% - 6px)` }}
          >
            <div
              className="w-full h-20 rounded-lg shadow-inner border border-white/5"
              style={{ backgroundColor: color }}
            />
            <p className="text-center text-xs font-mono text-gray-400 mt-1.5">{color.toUpperCase()}</p>
          </div>
        ))}
      </div>

      <button
        onClick={handleExport}
        className="w-full flex items-center justify-center gap-2 bg-[#5b5fc7] hover:bg-[#6b6fd7] text-white rounded-lg py-2 text-sm font-medium transition-colors"
      >
        <Download className="w-4 h-4" />
        导出配色 PNG
      </button>
    </div>
  );
}
