import { useState } from 'react';
import { Hash, Ruler, Droplets, Printer, Pipette, AlertTriangle } from 'lucide-react';
import { useColorStore } from '@/hooks/useColorStore';
import { convertColor, isValidHex, rgbToHex, hslToHex, cmykToHex, labToHex } from '@/utils/colorConverter';
import { checkRGBGamut, checkHSLGamut, checkCMYKGamut, checkLABGamut } from '@/utils/gamutChecker';
import type { GamutCheckResult } from '@/types';

export default function ColorConverter() {
  const colorSpaces = useColorStore((s) => s.colorSpaces);
  const setCurrentColor = useColorStore((s) => s.setCurrentColor);
  const { hex, rgb, hsl, cmyk, lab } = colorSpaces;

  const [hexInput, setHexInput] = useState<string>(hex);
  const [gamutWarning, setGamutWarning] = useState<GamutCheckResult | null>(null);

  const handleHexChange = (value: string) => {
    setHexInput(value);
    setGamutWarning(null);
    if (isValidHex(value)) {
      setCurrentColor(value);
    }
  };

  const handleRgbChange = (key: 'r' | 'g' | 'b', value: string) => {
    const n = parseInt(value, 10);
    if (isNaN(n)) return;
    const gamutCheck = checkRGBGamut(
      key === 'r' ? n : rgb.r,
      key === 'g' ? n : rgb.g,
      key === 'b' ? n : rgb.b,
    );
    if (gamutCheck.isOutOfGamut) {
      setGamutWarning(gamutCheck);
    } else {
      setGamutWarning(null);
    }
    const clamped = Math.max(0, Math.min(255, n));
    const next = { ...rgb, [key]: clamped };
    const nextHex = rgbToHex(next.r, next.g, next.b);
    setCurrentColor(nextHex);
    setHexInput(nextHex);
  };

  const handleHslChange = (key: 'h' | 's' | 'l', value: string) => {
    const n = parseInt(value, 10);
    if (isNaN(n)) return;
    const max = key === 'h' ? 360 : 100;
    const gamutCheck = checkHSLGamut(
      key === 'h' ? n : hsl.h,
      key === 's' ? n : hsl.s,
      key === 'l' ? n : hsl.l,
    );
    if (gamutCheck.isOutOfGamut) {
      setGamutWarning(gamutCheck);
    } else {
      setGamutWarning(null);
    }
    const clamped = Math.max(0, Math.min(max, n));
    const next = { ...hsl, [key]: clamped };
    const nextHex = hslToHex(next.h, next.s, next.l);
    setCurrentColor(nextHex);
    setHexInput(nextHex);
  };

  const handleCmykChange = (key: 'c' | 'm' | 'y' | 'k', value: string) => {
    const n = parseInt(value, 10);
    if (isNaN(n)) return;
    const gamutCheck = checkCMYKGamut(
      key === 'c' ? n : cmyk.c,
      key === 'm' ? n : cmyk.m,
      key === 'y' ? n : cmyk.y,
      key === 'k' ? n : cmyk.k,
    );
    if (gamutCheck.isOutOfGamut) {
      setGamutWarning(gamutCheck);
    } else {
      setGamutWarning(null);
    }
    const clamped = Math.max(0, Math.min(100, n));
    const next = { ...cmyk, [key]: clamped };
    const nextHex = cmykToHex(next.c, next.m, next.y, next.k);
    setCurrentColor(nextHex);
    setHexInput(nextHex);
  };

  const handleLabChange = (key: 'l' | 'a' | 'b', value: string) => {
    const n = parseFloat(value);
    if (isNaN(n)) return;
    const result = checkLABGamut(
      key === 'l' ? n : lab.l,
      key === 'a' ? n : lab.a,
      key === 'b' ? n : lab.b,
    );
    if (result.check.isOutOfGamut) {
      setGamutWarning(result.check);
    } else {
      setGamutWarning(null);
    }
    const clamped = Math.max(-128, Math.min(128, n));
    const next = { ...lab, [key]: clamped };
    const nextHex = labToHex(next.l, next.a, next.b);
    setCurrentColor(nextHex);
    setHexInput(nextHex);
  };

  return (
    <div className="bg-[#1e1e2e] rounded-xl p-5 shadow-lg">
      <h2 className="mb-4 text-lg font-semibold text-gray-200 flex items-center gap-2">
        颜色转换器
      </h2>

      {gamutWarning && gamutWarning.isOutOfGamut && (
        <div className="mb-4 bg-amber-500/10 border border-amber-500/30 rounded-lg px-3 py-2.5 flex items-start gap-2">
          <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-amber-300 text-xs font-medium">色域警告</p>
            <p className="text-amber-200/70 text-xs mt-0.5">
              {gamutWarning.originalValue} 超出 {gamutWarning.targetSpace} 色域，已自动裁剪为 {gamutWarning.clampedValue}
            </p>
          </div>
        </div>
      )}

      <div className="space-y-3">
        <div className="flex items-center gap-3">
          <div className="flex w-24 items-center gap-2 text-gray-400">
            <Hash size={16} />
            <span className="text-sm">HEX</span>
          </div>
          <input
            type="text"
            value={hexInput}
            onChange={(e) => handleHexChange(e.target.value)}
            className="flex-1 rounded-lg bg-[#2a2a3e] px-3 py-2 font-mono text-sm text-gray-200 outline-none ring-1 ring-white/5 focus:ring-[#5b5fc7]"
          />
        </div>
        <div className="flex items-center gap-3">
          <div className="flex w-24 items-center gap-2 text-gray-400">
            <Ruler size={16} />
            <span className="text-sm">RGB</span>
          </div>
          <div className="flex flex-1 gap-2">
            {(['r', 'g', 'b'] as const).map((k) => (
              <input
                key={k}
                type="number"
                min={0}
                max={255}
                value={rgb[k]}
                onChange={(e) => handleRgbChange(k, e.target.value)}
                className="w-full rounded-lg bg-[#2a2a3e] px-3 py-2 font-mono text-sm text-gray-200 outline-none ring-1 ring-white/5 focus:ring-[#5b5fc7]"
              />
            ))}
          </div>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex w-24 items-center gap-2 text-gray-400">
            <Droplets size={16} />
            <span className="text-sm">HSL</span>
          </div>
          <div className="flex flex-1 gap-2">
            {(['h', 's', 'l'] as const).map((k) => (
              <input
                key={k}
                type="number"
                min={0}
                max={k === 'h' ? 360 : 100}
                value={hsl[k]}
                onChange={(e) => handleHslChange(k, e.target.value)}
                className="w-full rounded-lg bg-[#2a2a3e] px-3 py-2 font-mono text-sm text-gray-200 outline-none ring-1 ring-white/5 focus:ring-[#5b5fc7]"
              />
            ))}
          </div>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex w-24 items-center gap-2 text-gray-400">
            <Printer size={16} />
            <span className="text-sm">CMYK</span>
          </div>
          <div className="flex flex-1 gap-2">
            {(['c', 'm', 'y', 'k'] as const).map((k) => (
              <input
                key={k}
                type="number"
                min={0}
                max={100}
                value={cmyk[k]}
                onChange={(e) => handleCmykChange(k, e.target.value)}
                className="w-full rounded-lg bg-[#2a2a3e] px-3 py-2 font-mono text-sm text-gray-200 outline-none ring-1 ring-white/5 focus:ring-[#5b5fc7]"
              />
            ))}
          </div>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex w-24 items-center gap-2 text-gray-400">
            <Pipette size={16} />
            <span className="text-sm">LAB</span>
          </div>
          <div className="flex flex-1 gap-2">
            {(['l', 'a', 'b'] as const).map((k) => (
              <input
                key={k}
                type="number"
                step="0.01"
                min={-128}
                max={128}
                value={lab[k]}
                onChange={(e) => handleLabChange(k, e.target.value)}
                className="w-full rounded-lg bg-[#2a2a3e] px-3 py-2 font-mono text-sm text-gray-200 outline-none ring-1 ring-white/5 focus:ring-[#5b5fc7]"
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
