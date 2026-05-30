export function hexToRgb(hex: string): { r: number; g: number; b: number } | null {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  return result
    ? {
        r: parseInt(result[1], 16),
        g: parseInt(result[2], 16),
        b: parseInt(result[3], 16),
      }
    : null;
}

export function rgbToHex(r: number, g: number, b: number): string {
  return (
    '#' +
    [r, g, b]
      .map((x) => {
        const hex = Math.round(Math.max(0, Math.min(255, x))).toString(16);
        return hex.length === 1 ? '0' + hex : hex;
      })
      .join('')
  );
}

export function lightenColor(hex: string, percent: number): string {
  const rgb = hexToRgb(hex);
  if (!rgb) return hex;
  const amount = Math.round(255 * percent);
  return rgbToHex(rgb.r + amount, rgb.g + amount, rgb.b + amount);
}

export function darkenColor(hex: string, percent: number): string {
  const rgb = hexToRgb(hex);
  if (!rgb) return hex;
  const amount = Math.round(255 * percent);
  return rgbToHex(rgb.r - amount, rgb.g - amount, rgb.b - amount);
}

export function getContrastColor(hex: string): string {
  const rgb = hexToRgb(hex);
  if (!rgb) return '#000000';
  const brightness = (rgb.r * 299 + rgb.g * 587 + rgb.b * 114) / 1000;
  return brightness > 128 ? '#000000' : '#ffffff';
}

export function generateRandomColor(): string {
  const hue = Math.floor(Math.random() * 360);
  return `hsl(${hue}, 70%, 60%)`;
}
