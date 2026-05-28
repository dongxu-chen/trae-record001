import chroma from 'chroma-js';
import type { ColorScheme, ColorSchemeType } from '@/types';

export function generateMonochromatic(baseHex: string): string[] {
  const base = chroma(baseHex);
  const [h, s] = base.hsl();
  const colors: string[] = [];
  const lightnesses = [0.15, 0.3, 0.5, 0.7, 0.85];
  lightnesses.forEach((l) => {
    colors.push(chroma.hsl(isNaN(h) ? 0 : h, s, l).hex());
  });
  return colors;
}

export function generateComplementary(baseHex: string): string[] {
  const base = chroma(baseHex);
  const [h, s, l] = base.hsl();
  const complementH = (h + 180) % 360;
  return [
    base.hex(),
    chroma.hsl(isNaN(h) ? 0 : h, s, Math.max(l * 0.7, 0.8)).hex(),
    chroma.hsl(isNaN(complementH) ? 0 : complementH, s, l).hex(),
    chroma.hsl(isNaN(complementH) ? 0 : complementH, s, Math.max(l * 0.7, 0.8)).hex(),
  ];
}

export function generateTriadic(baseHex: string): string[] {
  const base = chroma(baseHex);
  const [h, s, l] = base.hsl();
  const hue1 = (h + 120) % 360;
  const hue2 = (h + 240) % 360;
  return [
    base.hex(),
    chroma.hsl(isNaN(h) ? 0 : h, s, l).hex(),
    chroma.hsl(isNaN(hue1) ? 0 : hue1, s, l).hex(),
    chroma.hsl(isNaN(hue2) ? 0 : hue2, s, l).hex(),
  ];
}

export function generateTetradic(baseHex: string): string[] {
  const base = chroma(baseHex);
  const [h, s, l] = base.hsl();
  const hue1 = (h + 90) % 360;
  const hue2 = (h + 180) % 360;
  const hue3 = (h + 270) % 360;
  return [
    base.hex(),
    chroma.hsl(isNaN(h) ? 0 : h, s, l).hex(),
    chroma.hsl(isNaN(hue1) ? 0 : hue1, s, l).hex(),
    chroma.hsl(isNaN(hue2) ? 0 : hue2, s, l).hex(),
    chroma.hsl(isNaN(hue3) ? 0 : hue3, s, l).hex(),
  ];
}

export function generateColorScheme(baseHex: string, type: ColorSchemeType): ColorScheme {
  let colors: string[];
  let name: string;

  switch (type) {
    case 'monochromatic':
      colors = generateMonochromatic(baseHex);
      name = '单色配色';
      break;
    case 'complementary':
      colors = generateComplementary(baseHex);
      name = '互补配色';
      break;
    case 'triadic':
      colors = generateTriadic(baseHex);
      name = '三角配色';
      break;
    case 'tetradic':
      colors = generateTetradic(baseHex);
      name = '矩形配色';
      break;
    default:
      colors = generateMonochromatic(baseHex);
      name = '单色配色';
  }

  return { type, name, colors };
}

export const SCHEME_TYPES: { value: ColorSchemeType; label: string; description: string }[] = [
  { value: 'monochromatic', label: '单色', description: '同色相不同明度' },
  { value: 'complementary', label: '互补', description: '色环对面颜色' },
  { value: 'triadic', label: '三角', description: '120度等距三色' },
  { value: 'tetradic', label: '矩形', description: '90度等距四色' },
];
