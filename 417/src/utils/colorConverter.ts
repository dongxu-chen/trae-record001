import chroma from 'chroma-js';
import type { ColorSpaces, RGB, HSL, CMYK, LAB } from '@/types';

export function isValidHex(hex: string): boolean {
  try {
    chroma(hex);
    return true;
  } catch {
    return false;
  }
}

export function normalizeHex(hex: string): string {
  try {
    return chroma(hex).hex();
  } catch {
    return '#000000';
  }
}

export function hexToRgb(hex: string): RGB {
  try {
    const [r, g, b] = chroma(hex).rgb();
    return { r, g, b };
  } catch {
    return { r: 0, g: 0, b: 0 };
  }
}

export function hexToHsl(hex: string): HSL {
  try {
    const [h, s, l] = chroma(hex).hsl();
    return {
      h: isNaN(h) ? 0 : Math.round(h),
      s: Math.round(s * 100),
      l: Math.round(l * 100),
    };
  } catch {
    return { h: 0, s: 0, l: 0 };
  }
}

export function hexToCmyk(hex: string): CMYK {
  try {
    const [c, m, y, k] = chroma(hex).cmyk();
    return {
      c: Math.round(c * 100),
      m: Math.round(m * 100),
      y: Math.round(y * 100),
      k: Math.round(k * 100),
    };
  } catch {
    return { c: 0, m: 0, y: 0, k: 100 };
  }
}

export function hexToLab(hex: string): LAB {
  try {
    const [l, a, b] = chroma(hex).lab();
    return {
      l: Math.round(l * 100) / 100,
      a: Math.round(a * 100) / 100,
      b: Math.round(b * 100) / 100,
    };
  } catch {
    return { l: 0, a: 0, b: 0 };
  }
}

export function convertColor(hex: string): ColorSpaces {
  const normalized = normalizeHex(hex);
  return {
    hex: normalized,
    rgb: hexToRgb(hex),
    hsl: hexToHsl(hex),
    cmyk: hexToCmyk(hex),
    lab: hexToLab(hex),
  };
}

export function rgbToHex(r: number, g: number, b: number): string {
  try {
    return chroma.rgb(r, g, b).hex();
  } catch {
    return '#000000';
  }
}

export function hslToHex(h: number, s: number, l: number): string {
  try {
    return chroma.hsl(h, s / 100, l / 100).hex();
  } catch {
    return '#000000';
  }
}

export function cmykToHex(c: number, m: number, y: number, k: number): string {
  try {
    return chroma.cmyk(c / 100, m / 100, y / 100, k / 100).hex();
  } catch {
    return '#000000';
  }
}

export function labToHex(l: number, a: number, b: number): string {
  try {
    return chroma.lab(l, a, b).hex();
  } catch {
    return '#000000';
  }
}