import type { RGB, ColorSuggestion } from '@/types';

function linearize(c: number): number {
  const srgb = c / 255;
  if (srgb <= 0.03928) {
    return srgb / 12.92;
  }
  return Math.pow((srgb + 0.055) / 1.055, 2.4);
}

export function getRelativeLuminance(color: RGB): number {
  return (
    0.2126 * linearize(color.r) +
    0.7152 * linearize(color.g) +
    0.0722 * linearize(color.b)
  );
}

export function getContrastRatio(color1: RGB, color2: RGB): number {
  const l1 = getRelativeLuminance(color1);
  const l2 = getRelativeLuminance(color2);
  const lighter = Math.max(l1, l2);
  const darker = Math.min(l1, l2);
  return (lighter + 0.05) / (darker + 0.05);
}

export function meetsWcagAA(ratio: number, isLargeText: boolean): boolean {
  return isLargeText ? ratio >= 3 : ratio >= 4.5;
}

export function meetsWcagAAA(ratio: number, isLargeText: boolean): boolean {
  return isLargeText ? ratio >= 4.5 : ratio >= 7;
}

export function getContrastLevel(
  ratio: number,
  isLargeText: boolean
): 'AAA' | 'AA' | 'fail' {
  if (meetsWcagAAA(ratio, isLargeText)) return 'AAA';
  if (meetsWcagAA(ratio, isLargeText)) return 'AA';
  return 'fail';
}

export function generateSuggestions(
  foreground: RGB,
  background: RGB,
  targetRatio: number = 4.5
): ColorSuggestion[] {
  const suggestions: ColorSuggestion[] = [];
  const bgLuminance = getRelativeLuminance(background);

  const isDarkBackground = bgLuminance < 0.5;

  const candidates: RGB[] = [];

  if (isDarkBackground) {
    for (let l = 90; l >= 50; l -= 5) {
      const testColor: RGB = hslToRgb({ h: 0, s: 0, l });
      const ratio = getContrastRatio(testColor, background);
      if (ratio >= targetRatio) {
        candidates.push(testColor);
        break;
      }
    }
  } else {
    for (let l = 10; l <= 50; l += 5) {
      const testColor: RGB = hslToRgb({ h: 0, s: 0, l });
      const ratio = getContrastRatio(testColor, background);
      if (ratio >= targetRatio) {
        candidates.push(testColor);
        break;
      }
    }
  }

  const fgHsl = rgbToHsl(foreground);
  if (isDarkBackground) {
    for (let l = Math.max(fgHsl.l + 10, 50); l <= 100; l += 5) {
      const testColor: RGB = hslToRgb({ h: fgHsl.h, s: fgHsl.s, l });
      const ratio = getContrastRatio(testColor, background);
      if (ratio >= targetRatio) {
        candidates.push(testColor);
        break;
      }
    }
  } else {
    for (let l = Math.min(fgHsl.l - 10, 50); l >= 0; l -= 5) {
      const testColor: RGB = hslToRgb({ h: fgHsl.h, s: fgHsl.s, l });
      const ratio = getContrastRatio(testColor, background);
      if (ratio >= targetRatio) {
        candidates.push(testColor);
        break;
      }
    }
  }

  const uniqueColors = candidates.filter((c, i, arr) => {
    return !arr.slice(0, i).some(
      (prev) => prev.r === c.r && prev.g === c.g && prev.b === c.b
    );
  });

  for (const suggested of uniqueColors.slice(0, 3)) {
    const ratio = getContrastRatio(suggested, background);
    suggestions.push({
      original: foreground,
      suggested,
      contrastRatio: ratio,
      aaPass: meetsWcagAA(ratio, false),
      aaaPass: meetsWcagAAA(ratio, false),
    });
  }

  return suggestions;
}

function rgbToHsl(color: RGB): { h: number; s: number; l: number } {
  const r = color.r / 255;
  const g = color.g / 255;
  const b = color.b / 255;

  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  const l = (max + min) / 2;

  if (max === min) {
    return { h: 0, s: 0, l: l * 100 };
  }

  const d = max - min;
  const s = l > 0.5 ? d / (2 - max - min) : d / (max + min);

  let h: number;
  switch (max) {
    case r:
      h = ((g - b) / d + (g < b ? 6 : 0)) / 6;
      break;
    case g:
      h = ((b - r) / d + 2) / 6;
      break;
    default:
      h = ((r - g) / d + 4) / 6;
      break;
  }

  return { h: h * 360, s: s * 100, l: l * 100 };
}

function hslToRgb(hsl: { h: number; s: number; l: number }): RGB {
  const h = hsl.h / 360;
  const s = hsl.s / 100;
  const l = hsl.l / 100;

  if (s === 0) {
    const val = Math.round(l * 255);
    return { r: val, g: val, b: val };
  }

  const hue2rgb = (p: number, q: number, t: number) => {
    if (t < 0) t += 1;
    if (t > 1) t -= 1;
    if (t < 1 / 6) return p + (q - p) * 6 * t;
    if (t < 1 / 2) return q;
    if (t < 2 / 3) return p + (q - p) * (2 / 3 - t) * 6;
    return p;
  };

  const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
  const p = 2 * l - q;

  return {
    r: Math.round(hue2rgb(p, q, h + 1 / 3) * 255),
    g: Math.round(hue2rgb(p, q, h) * 255),
    b: Math.round(hue2rgb(p, q, h - 1 / 3) * 255),
  };
}
