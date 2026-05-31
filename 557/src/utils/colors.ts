export const PRESET_COLORS = [
  '#06b6d4',
  '#8b5cf6',
  '#ec4899',
  '#10b981',
  '#f97316',
  '#eab308',
];

export function getNextColor(index: number): string {
  return PRESET_COLORS[index % PRESET_COLORS.length];
}

export function hexToRgba(hex: string, alpha: number): string {
  const cleanHex = hex.replace('#', '');
  const r = parseInt(cleanHex.substring(0, 2), 16);
  const g = parseInt(cleanHex.substring(2, 4), 16);
  const b = parseInt(cleanHex.substring(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

export function generateRandomColor(): string {
  const hue = Math.floor(Math.random() * 360);
  return `hsl(${hue}, 70%, 60%)`;
}
