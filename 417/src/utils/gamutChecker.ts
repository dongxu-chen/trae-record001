import chroma from 'chroma-js';
import type { GamutCheckResult, LAB, CMYK } from '@/types';

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

export function checkRGBGamut(r: number, g: number, b: number): GamutCheckResult {
  const clampedR = clamp(r, 0, 255);
  const clampedG = clamp(g, 0, 255);
  const clampedB = clamp(b, 0, 255);

  const isOutOfGamut = r < 0 || r > 255 || g < 0 || g > 255 || b < 0 || b > 255;

  return {
    isOutOfGamut,
    sourceSpace: 'RGB',
    targetSpace: 'sRGB',
    originalValue: `rgb(${Math.round(r)}, ${Math.round(g)}, ${Math.round(b)})`,
    clampedValue: `rgb(${clampedR}, ${clampedG}, ${clampedB})`,
  };
}

export function checkHSLGamut(h: number, s: number, l: number): GamutCheckResult {
  const clampedH = clamp(h, 0, 360);
  const clampedS = clamp(s, 0, 100);
  const clampedL = clamp(l, 0, 100);

  const isOutOfGamut = h < 0 || h > 360 || s < 0 || s > 100 || l < 0 || l > 100;

  return {
    isOutOfGamut,
    sourceSpace: 'HSL',
    targetSpace: 'sRGB',
    originalValue: `hsl(${Math.round(h)}, ${Math.round(s)}%, ${Math.round(l)}%)`,
    clampedValue: `hsl(${clampedH}, ${clampedS}%, ${clampedL}%)`,
  };
}

export function checkCMYKGamut(c: number, m: number, y: number, k: number): GamutCheckResult {
  const clampedC = clamp(c, 0, 100);
  const clampedM = clamp(m, 0, 100);
  const clampedY = clamp(y, 0, 100);
  const clampedK = clamp(k, 0, 100);

  const isOutOfGamut = c < 0 || c > 100 || m < 0 || m > 100 || y < 0 || y > 100 || k < 0 || k > 100;

  return {
    isOutOfGamut,
    sourceSpace: 'CMYK',
    targetSpace: 'sRGB',
    originalValue: `cmyk(${Math.round(c)}%, ${Math.round(m)}%, ${Math.round(y)}%, ${Math.round(k)}%)`,
    clampedValue: `cmyk(${clampedC}%, ${clampedM}%, ${clampedY}%, ${clampedK}%)`,
  };
}

export function checkLABGamut(l: number, a: number, b: number): { check: GamutCheckResult; clampedHex: string } {
  const clampedL = clamp(l, 0, 100);
  const clampedA = clamp(a, -128, 127);
  const clampedB = clamp(b, -128, 127);

  const isOutOfGamut = l < 0 || l > 100 || a < -128 || a > 127 || b < -128 || b > 127;

  let clampedHex = '#000000';
  try {
    clampedHex = chroma.lab(clampedL, clampedA, clampedB).hex();
  } catch {}

  return {
    check: {
      isOutOfGamut,
      sourceSpace: 'LAB',
      targetSpace: 'sRGB',
      originalValue: `lab(${l.toFixed(1)}, ${a.toFixed(1)}, ${b.toFixed(1)})`,
      clampedValue: `lab(${clampedL.toFixed(1)}, ${clampedA.toFixed(1)}, ${clampedB.toFixed(1)})`,
    },
    clampedHex,
  };
}

export function checkLABInGamut(lab: LAB): { isOutOfGamut: boolean; message: string; displayHex: string } {
  try {
    const color = chroma.lab(lab.l, lab.a, lab.b);
    const [r, g, b] = color.rgb();

    if (r < 0 || r > 255 || g < 0 || g > 255 || b < 0 || b > 255) {
      const clampedR = Math.round(clamp(r, 0, 255));
      const clampedG = Math.round(clamp(g, 0, 255));
      const clampedB = Math.round(clamp(b, 0, 255));
      const clampedHex = chroma.rgb(clampedR, clampedG, clampedB).hex();
      return {
        isOutOfGamut: true,
        message: `LAB 值超出 sRGB 色域，已自动裁剪至可显示范围`,
        displayHex: clampedHex,
      };
    }
    return {
      isOutOfGamut: false,
      message: '',
      displayHex: color.hex(),
    };
  } catch {
    return {
      isOutOfGamut: true,
      message: '无效的 LAB 值，已重置为默认颜色',
      displayHex: '#000000',
    };
  }
}

export function checkCMYKInGamut(cmyk: CMYK): { isOutOfGamut: boolean; message: string } {
  const cmykArr = [cmyk.c / 100, cmyk.m / 100, cmyk.y / 100, cmyk.k / 100];
  try {
    const color = chroma.cmyk(...cmykArr);
    const [r, g, b] = color.rgb();
    if (r < 0 || r > 255 || g < 0 || g > 255 || b < 0 || b > 255) {
      return {
        isOutOfGamut: true,
        message: `CMYK 值超出 sRGB 色域，已自动裁剪至可显示范围`,
      };
    }
    return {
      isOutOfGamut: false,
      message: '',
    };
  } catch {
    return {
      isOutOfGamut: true,
      message: '无效的 CMYK 值',
    };
  }
}
