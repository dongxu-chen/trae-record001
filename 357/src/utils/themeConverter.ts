import { cloneDeep, isString } from 'lodash';
import type { ChartTheme } from '@/types/theme';

export interface HSL {
  h: number;
  s: number;
  l: number;
}

export function hexToHsl(hex: string): HSL {
  let r = 0;
  let g = 0;
  let b = 0;

  if (hex.startsWith('#')) {
    hex = hex.slice(1);
  }

  if (hex.length === 3) {
    r = parseInt(hex[0] + hex[0], 16);
    g = parseInt(hex[1] + hex[1], 16);
    b = parseInt(hex[2] + hex[2], 16);
  } else if (hex.length === 6) {
    r = parseInt(hex.slice(0, 2), 16);
    g = parseInt(hex.slice(2, 4), 16);
    b = parseInt(hex.slice(4, 6), 16);
  }

  r /= 255;
  g /= 255;
  b /= 255;

  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  let h = 0;
  let s = 0;
  const l = (max + min) / 2;

  if (max !== min) {
    const d = max - min;
    s = l > 0.5 ? d / (2 - max - min) : d / (max + min);

    switch (max) {
      case r:
        h = ((g - b) / d + (g < b ? 6 : 0)) / 6;
        break;
      case g:
        h = ((b - r) / d + 2) / 6;
        break;
      case b:
        h = ((r - g) / d + 4) / 6;
        break;
    }
  }

  return { h: h * 360, s: s * 100, l: l * 100 };
}

export function hslToHex(hsl: HSL): string {
  const { h, s, l } = hsl;
  const hNorm = h / 360;
  const sNorm = s / 100;
  const lNorm = l / 100;

  let r = 0;
  let g = 0;
  let b = 0;

  if (sNorm === 0) {
    r = g = b = lNorm;
  } else {
    const hue2rgb = (p: number, q: number, t: number) => {
      if (t < 0) t += 1;
      if (t > 1) t -= 1;
      if (t < 1 / 6) return p + (q - p) * 6 * t;
      if (t < 1 / 2) return q;
      if (t < 2 / 3) return p + (q - p) * (2 / 3 - t) * 6;
      return p;
    };

    const q = lNorm < 0.5 ? lNorm * (1 + sNorm) : lNorm + sNorm - lNorm * sNorm;
    const p = 2 * lNorm - q;

    r = hue2rgb(p, q, hNorm + 1 / 3);
    g = hue2rgb(p, q, hNorm);
    b = hue2rgb(p, q, hNorm - 1 / 3);
  }

  const toHex = (x: number) => {
    const hex = Math.round(x * 255).toString(16);
    return hex.length === 1 ? '0' + hex : hex;
  };

  return `#${toHex(r)}${toHex(g)}${toHex(b)}`;
}

export function adjustColorLightness(color: string, targetLightness: number): string {
  if (!isString(color) || !color.startsWith('#')) {
    return color;
  }

  try {
    const hsl = hexToHsl(color);
    hsl.l = targetLightness;
    return hslToHex(hsl);
  } catch {
    return color;
  }
}

export function getContrastColor(bgColor: string): string {
  if (!isString(bgColor) || !bgColor.startsWith('#')) {
    return '#333333';
  }

  try {
    const hsl = hexToHsl(bgColor);
    return hsl.l > 50 ? '#333333' : '#e8e8e8';
  } catch {
    return '#333333';
  }
}

export function parseRgba(rgba: string): { r: number; g: number; b: number; a: number } | null {
  const match = rgba.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*([\d.]+))?\)/);
  if (!match) return null;
  return {
    r: parseInt(match[1]),
    g: parseInt(match[2]),
    b: parseInt(match[3]),
    a: match[4] ? parseFloat(match[4]) : 1,
  };
}

export function rgbaToHex(rgba: string): string {
  const parsed = parseRgba(rgba);
  if (!parsed) return rgba;
  const toHex = (x: number) => x.toString(16).padStart(2, '0');
  return `#${toHex(parsed.r)}${toHex(parsed.g)}${toHex(parsed.b)}`;
}

export function hexToRgba(hex: string, alpha: number = 1): string {
  let r = 0;
  let g = 0;
  let b = 0;

  if (hex.startsWith('#')) {
    hex = hex.slice(1);
  }

  if (hex.length === 3) {
    r = parseInt(hex[0] + hex[0], 16);
    g = parseInt(hex[1] + hex[1], 16);
    b = parseInt(hex[2] + hex[2], 16);
  } else if (hex.length === 6) {
    r = parseInt(hex.slice(0, 2), 16);
    g = parseInt(hex.slice(2, 4), 16);
    b = parseInt(hex.slice(4, 6), 16);
  }

  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

function invertColorForDarkMode(color: string): string {
  if (color.startsWith('rgba')) {
    const parsed = parseRgba(color);
    if (!parsed) return color;
    const hex = `#${parsed.r.toString(16).padStart(2, '0')}${parsed.g.toString(16).padStart(2, '0')}${parsed.b.toString(16).padStart(2, '0')}`;
    const hsl = hexToHsl(hex);
    hsl.l = 100 - hsl.l;
    const inverted = hslToHex(hsl);
    const r = parseInt(inverted.slice(1, 3), 16);
    const g = parseInt(inverted.slice(3, 5), 16);
    const b = parseInt(inverted.slice(5, 7), 16);
    return `rgba(${r}, ${g}, ${b}, ${parsed.a})`;
  }

  if (!color.startsWith('#')) return color;

  const hsl = hexToHsl(color);
  hsl.l = Math.min(85, hsl.l);
  return hslToHex(hsl);
}

function invertColorForLightMode(color: string): string {
  if (color.startsWith('rgba')) {
    const parsed = parseRgba(color);
    if (!parsed) return color;
    const hex = `#${parsed.r.toString(16).padStart(2, '0')}${parsed.g.toString(16).padStart(2, '0')}${parsed.b.toString(16).padStart(2, '0')}`;
    const hsl = hexToHsl(hex);
    hsl.l = 100 - hsl.l;
    const inverted = hslToHex(hsl);
    const r = parseInt(inverted.slice(1, 3), 16);
    const g = parseInt(inverted.slice(3, 5), 16);
    const b = parseInt(inverted.slice(5, 7), 16);
    return `rgba(${r}, ${g}, ${b}, ${parsed.a})`;
  }

  if (!color.startsWith('#')) return color;

  const hsl = hexToHsl(color);
  hsl.l = Math.max(30, Math.min(60, hsl.l));
  return hslToHex(hsl);
}

function adjustPaletteColors(colors: string[], toDark: boolean): string[] {
  return colors.map(color => {
    if (!color.startsWith('#')) return color;
    const hsl = hexToHsl(color);
    if (toDark) {
      hsl.l = Math.min(80, Math.max(55, hsl.l + 10));
    } else {
      hsl.l = Math.max(35, Math.min(65, hsl.l - 5));
    }
    return hslToHex(hsl);
  });
}

export function convertThemeMode(theme: ChartTheme, toDark: boolean): ChartTheme {
  const converted = cloneDeep(theme);

  if (toDark) {
    converted.backgroundColor = '#141414';
    converted.textStyle = {
      ...converted.textStyle,
      color: '#e8e8e8',
    };
    if (converted.title) {
      converted.title.textStyle = {
        ...converted.title.textStyle,
        color: '#e8e8e8',
      };
      converted.title.subtextStyle = {
        ...converted.title.subtextStyle,
        color: '#bfbfbf',
      };
    }
    if (converted.legend) {
      converted.legend.textStyle = {
        ...converted.legend.textStyle,
        color: '#e8e8e8',
      };
    }
    if (converted.categoryAxis) {
      if (converted.categoryAxis.axisLine?.lineStyle) {
        converted.categoryAxis.axisLine.lineStyle.color = '#8c8c8c';
      }
      if (converted.categoryAxis.axisTick?.lineStyle) {
        converted.categoryAxis.axisTick.lineStyle.color = '#8c8c8c';
      }
      if (converted.categoryAxis.axisLabel) {
        converted.categoryAxis.axisLabel.color = '#bfbfbf';
      }
      if (converted.categoryAxis.splitLine?.lineStyle) {
        converted.categoryAxis.splitLine.lineStyle.color = '#434343';
      }
    }
    if (converted.valueAxis) {
      if (converted.valueAxis.axisLine?.lineStyle) {
        converted.valueAxis.axisLine.lineStyle.color = '#8c8c8c';
      }
      if (converted.valueAxis.axisTick?.lineStyle) {
        converted.valueAxis.axisTick.lineStyle.color = '#8c8c8c';
      }
      if (converted.valueAxis.axisLabel) {
        converted.valueAxis.axisLabel.color = '#bfbfbf';
      }
      if (converted.valueAxis.splitLine?.lineStyle) {
        converted.valueAxis.splitLine.lineStyle.color = '#434343';
      }
    }
    if (converted.grid) {
      converted.grid.borderColor = '#434343';
    }
    if (converted.tooltip) {
      converted.tooltip.backgroundColor = 'rgba(255, 255, 255, 0.95)';
      converted.tooltip.borderColor = '#e8e8e8';
      converted.tooltip.textStyle = {
        ...converted.tooltip.textStyle,
        color: '#333333',
      };
    }
    if (converted.pie?.label) {
      converted.pie.label.color = '#e8e8e8';
    }
    converted.color = adjustPaletteColors(theme.color, true);
  } else {
    converted.backgroundColor = '#ffffff';
    converted.textStyle = {
      ...converted.textStyle,
      color: '#333333',
    };
    if (converted.title) {
      converted.title.textStyle = {
        ...converted.title.textStyle,
        color: '#333333',
      };
      converted.title.subtextStyle = {
        ...converted.title.subtextStyle,
        color: '#666666',
      };
    }
    if (converted.legend) {
      converted.legend.textStyle = {
        ...converted.legend.textStyle,
        color: '#333333',
      };
    }
    if (converted.categoryAxis) {
      if (converted.categoryAxis.axisLine?.lineStyle) {
        converted.categoryAxis.axisLine.lineStyle.color = '#666666';
      }
      if (converted.categoryAxis.axisTick?.lineStyle) {
        converted.categoryAxis.axisTick.lineStyle.color = '#666666';
      }
      if (converted.categoryAxis.axisLabel) {
        converted.categoryAxis.axisLabel.color = '#666666';
      }
      if (converted.categoryAxis.splitLine?.lineStyle) {
        converted.categoryAxis.splitLine.lineStyle.color = '#e0e0e0';
      }
    }
    if (converted.valueAxis) {
      if (converted.valueAxis.axisLine?.lineStyle) {
        converted.valueAxis.axisLine.lineStyle.color = '#666666';
      }
      if (converted.valueAxis.axisTick?.lineStyle) {
        converted.valueAxis.axisTick.lineStyle.color = '#666666';
      }
      if (converted.valueAxis.axisLabel) {
        converted.valueAxis.axisLabel.color = '#666666';
      }
      if (converted.valueAxis.splitLine?.lineStyle) {
        converted.valueAxis.splitLine.lineStyle.color = '#e0e0e0';
      }
    }
    if (converted.grid) {
      converted.grid.borderColor = '#e0e0e0';
    }
    if (converted.tooltip) {
      converted.tooltip.backgroundColor = 'rgba(50, 50, 50, 0.9)';
      converted.tooltip.borderColor = '#333333';
      converted.tooltip.textStyle = {
        ...converted.tooltip.textStyle,
        color: '#ffffff',
      };
    }
    if (converted.pie?.label) {
      converted.pie.label.color = '#333333';
    }
    converted.color = adjustPaletteColors(theme.color, false);
  }

  return converted;
}

export function isDarkTheme(theme: ChartTheme): boolean {
  const bg = theme.backgroundColor || '#ffffff';
  if (!bg.startsWith('#')) return false;
  const hsl = hexToHsl(bg);
  return hsl.l < 50;
}
