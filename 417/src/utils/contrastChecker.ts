import chroma from 'chroma-js';
import type { WCAGResult } from '@/types';

function luminance(r: number, g: number, b: number): number {
  const [rs, gs, bs] = [r, g, b].map((c) => {
    const s = c / 255;
    return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
  });
  return 0.2126 * rs + 0.7152 * gs + 0.0722 * bs;
}

export function contrastRatio(hex1: string, hex2: string): number {
  try {
    const c1 = chroma(hex1);
    const c2 = chroma(hex2);
    const [r1, g1, b1] = c1.rgb();
    const [r2, g2, b2] = c2.rgb();
    const l1 = luminance(r1, g1, b1);
    const l2 = luminance(r2, g2, b2);
    const lighter = Math.max(l1, l2);
    const darker = Math.min(l1, l2);
    return (lighter + 0.05) / (darker + 0.05);
  } catch {
    return 1;
  }
}

export function evaluateWCAG(ratio: number): WCAGResult {
  const aaNormal = ratio >= 4.5;
  const aaLarge = ratio >= 3;
  const aaaNormal = ratio >= 7;
  const aaaLarge = ratio >= 4.5;

  let level: 'fail' | 'aa' | 'aaa' = 'fail';
  if (aaaNormal) level = 'aaa';
  else if (aaNormal) level = 'aa';

  return {
    ratio: Math.round(ratio * 100) / 100,
    aaNormal,
    aaLarge,
    aaaNormal,
    aaaLarge,
    level,
  };
}

export function checkContrast(foreground: string, background: string): WCAGResult {
  const ratio = contrastRatio(foreground, background);
  return evaluateWCAG(ratio);
}
