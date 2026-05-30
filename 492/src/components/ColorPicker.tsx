import React, { useState, useRef, useEffect, useCallback } from 'react';

interface ColorPickerProps {
  color: string;
  onChange: (color: string) => void;
  presets?: string[];
}

const defaultPresets = [
  '#ff0000', '#ff3300', '#ff6600', '#ff9900', '#ffcc00', '#ffff00',
  '#ccff00', '#99ff00', '#66ff00', '#33ff00', '#00ff00', '#00ff33',
  '#00ff66', '#00ff99', '#00ffcc', '#00ffff', '#00ccff', '#0099ff',
  '#0066ff', '#0033ff', '#0000ff', '#3300ff', '#6600ff', '#9900ff',
  '#cc00ff', '#ff00ff', '#ff00cc', '#ff0099', '#ff0066', '#ff0033',
  '#ffffff', '#cccccc', '#999999', '#666666', '#333333', '#000000'
];

function hexToRgb(hex: string): { r: number; g: number; b: number } {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  return result
    ? {
        r: parseInt(result[1], 16),
        g: parseInt(result[2], 16),
        b: parseInt(result[3], 16)
      }
    : { r: 0, g: 0, b: 0 };
}

function rgbToHsv(r: number, g: number, b: number): { h: number; s: number; v: number } {
  r /= 255;
  g /= 255;
  b /= 255;

  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  const d = max - min;
  let h = 0;
  const s = max === 0 ? 0 : d / max;
  const v = max;

  if (max !== min) {
    switch (max) {
      case r:
        h = (g - b) / d + (g < b ? 6 : 0);
        break;
      case g:
        h = (b - r) / d + 2;
        break;
      case b:
        h = (r - g) / d + 4;
        break;
    }
    h /= 6;
  }

  return { h: h * 360, s: s * 100, v: v * 100 };
}

function hsvToRgb(h: number, s: number, v: number): { r: number; g: number; b: number } {
  h /= 360;
  s /= 100;
  v /= 100;

  let r = 0, g = 0, b = 0;

  const i = Math.floor(h * 6);
  const f = h * 6 - i;
  const p = v * (1 - s);
  const q = v * (1 - f * s);
  const t = v * (1 - (1 - f) * s);

  switch (i % 6) {
    case 0: r = v; g = t; b = p; break;
    case 1: r = q; g = v; b = p; break;
    case 2: r = p; g = v; b = t; break;
    case 3: r = p; g = q; b = v; break;
    case 4: r = t; g = p; b = v; break;
    case 5: r = v; g = p; b = q; break;
  }

  return {
    r: Math.round(r * 255),
    g: Math.round(g * 255),
    b: Math.round(b * 255)
  };
}

function rgbToHex(r: number, g: number, b: number): string {
  return '#' + [r, g, b].map((x) => x.toString(16).padStart(2, '0')).join('');
}

export const ColorPicker: React.FC<ColorPickerProps> = ({
  color,
  onChange,
  presets = defaultPresets
}) => {
  const [hsv, setHsv] = useState(() => {
    const rgb = hexToRgb(color);
    return rgbToHsv(rgb.r, rgb.g, rgb.b);
  });
  const [isDragging, setIsDragging] = useState(false);
  const [dragType, setDragType] = useState<'saturation' | 'hue' | null>(null);

  const saturationRef = useRef<HTMLCanvasElement>(null);
  const hueRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const canvas = saturationRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const { width, height } = canvas;

    const saturationGradient = ctx.createLinearGradient(0, 0, width, 0);
    saturationGradient.addColorStop(0, '#ffffff');
    saturationGradient.addColorStop(1, hsvToRgb(hsv.h, 100, 100) && rgbToHex(
      ...Object.values(hsvToRgb(hsv.h, 100, 100))
    ));
    ctx.fillStyle = saturationGradient;
    ctx.fillRect(0, 0, width, height);

    const valueGradient = ctx.createLinearGradient(0, 0, 0, height);
    valueGradient.addColorStop(0, 'rgba(0, 0, 0, 0)');
    valueGradient.addColorStop(1, 'rgba(0, 0, 0, 1)');
    ctx.fillStyle = valueGradient;
    ctx.fillRect(0, 0, width, height);
  }, [hsv.h]);

  useEffect(() => {
    const canvas = hueRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const { width, height } = canvas;
    const gradient = ctx.createLinearGradient(0, 0, 0, height);

    const hues = [0, 60, 120, 180, 240, 300, 360];
    hues.forEach((h, i) => {
      const { r, g, b } = hsvToRgb(h, 100, 100);
      gradient.addColorStop(i / (hues.length - 1), `rgb(${r}, ${g}, ${b})`);
    });

    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, width, height);
  }, []);

  useEffect(() => {
    const rgb = hexToRgb(color);
    const newHsv = rgbToHsv(rgb.r, rgb.g, rgb.b);
    if (Math.abs(newHsv.h - hsv.h) > 0.1 || Math.abs(newHsv.s - hsv.s) > 0.1 || Math.abs(newHsv.v - hsv.v) > 0.1) {
      setHsv(newHsv);
    }
  }, [color]);

  const updateColorFromHsv = useCallback((newHsv: typeof hsv) => {
    setHsv(newHsv);
    const rgb = hsvToRgb(newHsv.h, newHsv.s, newHsv.v);
    onChange(rgbToHex(rgb.r, rgb.g, rgb.b));
  }, [onChange]);

  const handleSaturationMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    setIsDragging(true);
    setDragType('saturation');
    handleSaturationMove(e);
  };

  const handleHueMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    setIsDragging(true);
    setDragType('hue');
    handleHueMove(e);
  };

  const handleSaturationMove = (e: React.MouseEvent | MouseEvent) => {
    const canvas = saturationRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const clientX = 'clientX' in e ? e.clientX : (e as MouseEvent).clientX;
    const clientY = 'clientY' in e ? e.clientY : (e as MouseEvent).clientY;
    const x = Math.max(0, Math.min(canvas.width, clientX - rect.left));
    const y = Math.max(0, Math.min(canvas.height, clientY - rect.top));

    const s = (x / canvas.width) * 100;
    const v = 100 - (y / canvas.height) * 100;

    updateColorFromHsv({ ...hsv, s, v });
  };

  const handleHueMove = (e: React.MouseEvent | MouseEvent) => {
    const canvas = hueRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const clientY = 'clientY' in e ? e.clientY : (e as MouseEvent).clientY;
    const y = Math.max(0, Math.min(canvas.height, clientY - rect.top));

    const h = (y / canvas.height) * 360;
    updateColorFromHsv({ ...hsv, h });
  };

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isDragging) return;
      if (dragType === 'saturation') {
        handleSaturationMove(e);
      } else if (dragType === 'hue') {
        handleHueMove(e);
      }
    };

    const handleMouseUp = () => {
      setIsDragging(false);
      setDragType(null);
    };

    if (isDragging) {
      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleMouseUp);
    }

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDragging, dragType, hsv]);

  const handleHexInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    let value = e.target.value;
    if (!value.startsWith('#')) {
      value = '#' + value;
    }
    if (/^#[0-9A-Fa-f]{6}$/.test(value)) {
      onChange(value.toLowerCase());
    }
  };

  const saturationX = (hsv.s / 100) * 180;
  const saturationY = (1 - hsv.v / 100) * 180;
  const hueY = (hsv.h / 360) * 180;

  return (
    <div ref={containerRef} className="color-picker">
      <div className="flex gap-3 mb-3">
        <div className="relative">
          <canvas
            ref={saturationRef}
            width={180}
            height={180}
            className="cursor-crosshair rounded-lg"
            onMouseDown={handleSaturationMouseDown}
          />
          <div
            className="absolute w-4 h-4 border-2 border-white rounded-full pointer-events-none transform -translate-x-1/2 -translate-y-1/2 shadow-lg"
            style={{
              left: saturationX,
              top: saturationY,
              backgroundColor: color,
              boxShadow: '0 0 0 1px rgba(0,0,0,0.3), 0 2px 4px rgba(0,0,0,0.2)'
            }}
          />
        </div>

        <div className="relative">
          <canvas
            ref={hueRef}
            width={20}
            height={180}
            className="cursor-row-resize rounded-lg"
            onMouseDown={handleHueMouseDown}
          />
          <div
            className="absolute left-0 w-full h-2 bg-white rounded pointer-events-none transform -translate-y-1/2 shadow-md"
            style={{ top: hueY }}
          />
        </div>
      </div>

      <div className="flex items-center gap-3 mb-3">
        <div
          className="w-10 h-10 rounded-lg border-2 border-white/20 shadow-inner"
          style={{ backgroundColor: color }}
        />
        <div className="flex-1">
          <label className="text-xs text-gray-400 mb-1 block">HEX</label>
          <input
            type="text"
            value={color.replace('#', '').toUpperCase()}
            onChange={handleHexInput}
            className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white text-sm font-mono focus:border-cyan-500 focus:outline-none"
            maxLength={6}
          />
        </div>
      </div>

      <div className="border-t border-gray-700 pt-3">
        <p className="text-xs text-gray-400 mb-2">预设颜色</p>
        <div className="grid grid-cols-6 gap-1.5">
          {presets.map((presetColor, index) => (
            <button
              key={index}
              onClick={() => onChange(presetColor)}
              className="w-8 h-8 rounded-md transition-transform hover:scale-110 focus:outline-none focus:ring-2 focus:ring-cyan-500"
              style={{
                backgroundColor: presetColor,
                boxShadow: color.toLowerCase() === presetColor.toLowerCase() ? '0 0 0 2px #00ff88' : 'none'
              }}
              title={presetColor}
            />
          ))}
        </div>
      </div>
    </div>
  );
};
