import { cloneDeep, isEqual, isObject, isUndefined, isNull, mergeWith, omitBy } from 'lodash';
import type { ChartTheme } from '@/types/theme';
import { defaultTheme } from './defaultTheme';

export function getMappedColor(colors: string[], index: number): string {
  if (!colors || colors.length === 0) return '#5470c6';
  return colors[index % colors.length];
}

export function generateSeriesColors(colors: string[], count: number): string[] {
  const result: string[] = [];
  for (let i = 0; i < count; i++) {
    result.push(getMappedColor(colors, i));
  }
  return result;
}

export function updateThemeWithColorPalette(theme: ChartTheme, newColors: string[]): ChartTheme {
  const updated = cloneDeep(theme);
  updated.color = newColors;
  return updated;
}

function removeEmptyValues(obj: unknown): unknown {
  if (Array.isArray(obj)) {
    return obj.map(removeEmptyValues);
  }
  if (isObject(obj)) {
    const result: Record<string, unknown> = {};
    for (const [key, value] of Object.entries(obj as Record<string, unknown>)) {
      if (isUndefined(value) || isNull(value)) continue;
      const processed = removeEmptyValues(value);
      if (!isUndefined(processed) && !isNull(processed)) {
        result[key] = processed;
      }
    }
    return Object.keys(result).length > 0 ? result : undefined;
  }
  return obj;
}

function findDifferences(
  obj: Record<string, unknown>,
  defaultObj: Record<string, unknown>,
): Record<string, unknown> {
  const result: Record<string, unknown> = {};

  for (const key of Object.keys(obj)) {
    const objValue = obj[key];
    const defaultVal = defaultObj?.[key];

    if (isObject(objValue) && isObject(defaultVal) && !Array.isArray(objValue) && !Array.isArray(defaultVal)) {
      const diff = findDifferences(
        objValue as Record<string, unknown>,
        defaultVal as Record<string, unknown>,
      );
      if (Object.keys(diff).length > 0) {
        result[key] = diff;
      }
    } else if (!isEqual(objValue, defaultVal)) {
      result[key] = objValue;
    }
  }

  return result;
}

function mergeCommonStyles(theme: ChartTheme): ChartTheme {
  const result = cloneDeep(theme);

  const axisConfig = result.categoryAxis;
  if (axisConfig && result.valueAxis) {
    if (isEqual(axisConfig.axisLine, result.valueAxis.axisLine)) {
      delete result.valueAxis.axisLine;
    }
    if (isEqual(axisConfig.axisTick, result.valueAxis.axisTick)) {
      delete result.valueAxis.axisTick;
    }
    if (isEqual(axisConfig.axisLabel, result.valueAxis.axisLabel)) {
      delete result.valueAxis.axisLabel;
    }
  }

  const textStyle = result.textStyle;
  if (textStyle) {
    if (result.title?.textStyle?.color === textStyle.color && result.title.textStyle) {
      delete result.title.textStyle.color;
    }
    if (result.legend?.textStyle?.color === textStyle.color && result.legend.textStyle) {
      delete result.legend.textStyle.color;
    }
    if (result.legend?.textStyle?.fontSize === textStyle.fontSize && result.legend.textStyle) {
      delete result.legend.textStyle.fontSize;
    }
    if (result.tooltip?.textStyle?.fontSize === textStyle.fontSize && result.tooltip.textStyle) {
      delete result.tooltip.textStyle.fontSize;
    }
  }

  return result;
}

export function compressTheme(theme: ChartTheme, format: 'pretty' | 'minified' = 'pretty'): string {
  const cleaned = removeEmptyValues(theme) as ChartTheme;
  const merged = mergeCommonStyles(cleaned);
  const diff = findDifferences(merged as Record<string, unknown>, defaultTheme as Record<string, unknown>) as ChartTheme;
  
  diff.color = merged.color;
  
  if (format === 'minified') {
    return JSON.stringify(diff);
  }
  return JSON.stringify(diff, null, 2);
}

export function mergeThemeWithDefaults(partialTheme: Partial<ChartTheme>): ChartTheme {
  return mergeWith({}, defaultTheme, partialTheme, (objValue, srcValue) => {
    if (Array.isArray(srcValue)) {
      return srcValue;
    }
    return undefined;
  }) as ChartTheme;
}

export function validateTheme(theme: unknown): theme is ChartTheme {
  if (!isObject(theme)) return false;
  const t = theme as Record<string, unknown>;
  if (!Array.isArray(t.color)) return false;
  return true;
}

export function hexToRgba(hex: string, alpha: number = 1): string {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  if (!result) return hex;
  const r = parseInt(result[1], 16);
  const g = parseInt(result[2], 16);
  const b = parseInt(result[3], 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

export function getColorByPath(theme: ChartTheme, path: string): string | undefined {
  const parts = path.split('.');
  let current: unknown = theme;
  for (const part of parts) {
    if (isObject(current) && part in (current as Record<string, unknown>)) {
      current = (current as Record<string, unknown>)[part];
    } else {
      return undefined;
    }
  }
  return typeof current === 'string' ? current : undefined;
}

export function setNestedValue<T extends Record<string, unknown>>(
  obj: T,
  path: string,
  value: unknown,
): T {
  const parts = path.split('.');
  const result = cloneDeep(obj);
  let current: Record<string, unknown> = result;

  for (let i = 0; i < parts.length - 1; i++) {
    const part = parts[i];
    if (!(part in current) || !isObject(current[part])) {
      current[part] = {};
    }
    current = current[part] as Record<string, unknown>;
  }

  current[parts[parts.length - 1]] = value;
  return result;
}

export function omitDefaults(theme: ChartTheme): Partial<ChartTheme> {
  return omitBy(theme, (value, key) => {
    return isEqual(value, (defaultTheme as unknown as Record<string, unknown>)[key]);
  }) as Partial<ChartTheme>;
}
