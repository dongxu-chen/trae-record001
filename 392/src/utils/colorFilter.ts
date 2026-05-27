export const hexToRgb = (hex: string): { r: number; g: number; b: number } | null => {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  return result
    ? {
        r: parseInt(result[1], 16),
        g: parseInt(result[2], 16),
        b: parseInt(result[3], 16),
      }
    : null;
};

export const getColorFilter = (targetColor: string): string => {
  const rgb = hexToRgb(targetColor);
  if (!rgb) return 'none';

  const r = rgb.r / 255;
  const g = rgb.g / 255;
  const b = rgb.b / 255;

  return `brightness(0) saturate(100%) invert(${r * 100}%) sepia(${(g * 100)}%) saturate(${(b * 10000)}%) hue-rotate(${(b * 360)}deg) brightness(${(r * 100)}%) contrast(${(g * 100 + 50)}%)`;
};

export const generateColorMatrixFilter = (targetColor: string): string => {
  const rgb = hexToRgb(targetColor);
  if (!rgb) return 'none';

  const r = rgb.r / 255;
  const g = rgb.g / 255;
  const b = rgb.b / 255;

  return `
    <filter id="colorize-${targetColor.replace('#', '')}">
      <feColorMatrix
        type="matrix"
        values="
          0 0 0 0 ${r}
          0 0 0 0 ${g}
          0 0 0 0 ${b}
          0 0 0 1 0
        "
      />
    </filter>
  `;
};

export const getFilterStyle = (color: string): React.CSSProperties => {
  const rgb = hexToRgb(color);
  if (!rgb) return {};

  return {
    filter: `
      brightness(0)
      saturate(100%)
      invert(${(rgb.r / 255) * 100}%)
      sepia(${(rgb.g / 255) * 100}%)
      saturate(${Math.max((rgb.b / 255) * 1000, 100)}%)
      hue-rotate(${(rgb.b / 255) * 360}deg)
      brightness(${(rgb.r / 255) * 100 + 50}%)
      contrast(100%)
    `,
  };
};

export const getMixBlendStyle = (color: string): React.CSSProperties => {
  return {
    mixBlendMode: 'multiply' as const,
    backgroundColor: color,
    WebkitMaskImage: 'var(--icon-mask)',
    maskImage: 'var(--icon-mask)',
  };
};
