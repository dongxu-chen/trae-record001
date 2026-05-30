import type { RGB, ColorblindType } from '@/types';

const COLORBLIND_MATRICES: Record<ColorblindType, number[]> = {
  protanopia: [
    0.567, 0.433, 0, 0, 0,
    0.558, 0.442, 0, 0, 0,
    0, 0.242, 0.758, 0, 0,
    0, 0, 0, 1, 0,
  ],
  protanomaly: [
    0.817, 0.183, 0, 0, 0,
    0.333, 0.667, 0, 0, 0,
    0, 0.125, 0.875, 0, 0,
    0, 0, 0, 1, 0,
  ],
  deuteranopia: [
    0.625, 0.375, 0, 0, 0,
    0.7, 0.3, 0, 0, 0,
    0, 0.3, 0.7, 0, 0,
    0, 0, 0, 1, 0,
  ],
  deuteranomaly: [
    0.8, 0.2, 0, 0, 0,
    0.258, 0.742, 0, 0, 0,
    0, 0.142, 0.858, 0, 0,
    0, 0, 0, 1, 0,
  ],
  tritanopia: [
    0.95, 0.05, 0, 0, 0,
    0, 0.433, 0.567, 0, 0,
    0, 0.475, 0.525, 0, 0,
    0, 0, 0, 1, 0,
  ],
  tritanomaly: [
    0.967, 0.033, 0, 0, 0,
    0, 0.733, 0.267, 0, 0,
    0, 0.183, 0.817, 0, 0,
    0, 0, 0, 1, 0,
  ],
  achromatopsia: [
    0.299, 0.587, 0.114, 0, 0,
    0.299, 0.587, 0.114, 0, 0,
    0.299, 0.587, 0.114, 0, 0,
    0, 0, 0, 1, 0,
  ],
  achromatomaly: [
    0.618, 0.32, 0.062, 0, 0,
    0.163, 0.775, 0.062, 0, 0,
    0.163, 0.32, 0.516, 0, 0,
    0, 0, 0, 1, 0,
  ],
};

export function simulateColorblind(color: RGB, type: ColorblindType): RGB {
  const matrix = COLORBLIND_MATRICES[type];
  const r = color.r / 255;
  const g = color.g / 255;
  const b = color.b / 255;

  const newR = matrix[0] * r + matrix[1] * g + matrix[2] * b + matrix[3] * 0 + matrix[4];
  const newG = matrix[5] * r + matrix[6] * g + matrix[7] * b + matrix[8] * 0 + matrix[9];
  const newB = matrix[10] * r + matrix[11] * g + matrix[12] * b + matrix[13] * 0 + matrix[14];

  return {
    r: Math.round(Math.min(255, Math.max(0, newR * 255))),
    g: Math.round(Math.min(255, Math.max(0, newG * 255))),
    b: Math.round(Math.min(255, Math.max(0, newB * 255))),
  };
}

export function applyColorblindToImageData(
  imageData: ImageData,
  type: ColorblindType
): ImageData {
  const data = imageData.data;
  const result = new ImageData(
    new Uint8ClampedArray(data),
    imageData.width,
    imageData.height
  );
  const resultData = result.data;

  for (let i = 0; i < data.length; i += 4) {
    const color: RGB = { r: data[i], g: data[i + 1], b: data[i + 2] };
    const simulated = simulateColorblind(color, type);
    resultData[i] = simulated.r;
    resultData[i + 1] = simulated.g;
    resultData[i + 2] = simulated.b;
    resultData[i + 3] = data[i + 3];
  }

  return result;
}

export function getColorblindSvgFilter(type: ColorblindType): string {
  const matrix = COLORBLIND_MATRICES[type];
  return `
    <filter id="colorblind-${type}">
      <feColorMatrix type="matrix" values="
        ${matrix[0]} ${matrix[1]} ${matrix[2]} ${matrix[3]} ${matrix[4]}
        ${matrix[5]} ${matrix[6]} ${matrix[7]} ${matrix[8]} ${matrix[9]}
        ${matrix[10]} ${matrix[11]} ${matrix[12]} ${matrix[13]} ${matrix[14]}
        ${matrix[15]} ${matrix[16]} ${matrix[17]} ${matrix[18]} ${matrix[19]}
      "/>
    </filter>
  `;
}

export function getCategoryForType(type: ColorblindType): string {
  if (['protanopia', 'protanomaly', 'deuteranopia', 'deuteranomaly'].includes(type)) {
    return 'red-green';
  }
  if (['tritanopia', 'tritanomaly'].includes(type)) {
    return 'blue-yellow';
  }
  return 'total';
}
