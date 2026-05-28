export interface RGB {
  r: number;
  g: number;
  b: number;
}

export interface HSL {
  h: number;
  s: number;
  l: number;
}

export interface CMYK {
  c: number;
  m: number;
  y: number;
  k: number;
}

export interface LAB {
  l: number;
  a: number;
  b: number;
}

export interface ColorSpaces {
  hex: string;
  rgb: RGB;
  hsl: HSL;
  cmyk: CMYK;
  lab: LAB;
}

export interface ColorHistory {
  id: string;
  hex: string;
  rgb: RGB;
  timestamp: number;
  name?: string;
  project?: string;
}

export interface ColorCardData {
  name: string;
  hex: string;
  rgb: RGB;
  description?: string;
}

export type ColorSchemeType = 'monochromatic' | 'complementary' | 'triadic' | 'tetradic';

export interface ColorScheme {
  type: ColorSchemeType;
  name: string;
  colors: string[];
}

export interface GamutCheckResult {
  isOutOfGamut: boolean;
  sourceSpace: string;
  targetSpace: string;
  originalValue: string;
  clampedValue: string;
}

export interface WCAGResult {
  ratio: number;
  aaNormal: boolean;
  aaLarge: boolean;
  aaaNormal: boolean;
  aaaLarge: boolean;
  level: 'fail' | 'aa' | 'aaa';
}

export interface ColorNameResult {
  name: string;
  hex: string;
  distance: number;
}