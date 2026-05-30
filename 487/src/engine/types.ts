export type IconStyle = 'outline' | 'filled' | 'gradient' | '3d';

export interface IconConfig {
  text: string;
  size: number;
  primaryColor: string;
  secondaryColor: string;
  style: IconStyle;
  padding: number;
  borderRadius: number;
  backgroundColor: string;
  showBackground: boolean;
}

export interface RenderContext {
  ctx: CanvasRenderingContext2D | null;
  config: IconConfig;
  width: number;
  height: number;
}

export const defaultConfig: IconConfig = {
  text: 'A',
  size: 256,
  primaryColor: '#3b82f6',
  secondaryColor: '#8b5cf6',
  style: 'filled',
  padding: 32,
  borderRadius: 24,
  backgroundColor: '#ffffff',
  showBackground: true,
};

export function normalizeConfig(config: IconConfig): IconConfig {
  return {
    ...config,
    size: Math.max(64, Math.min(512, Math.round(config.size / 16) * 16)),
    padding: Math.max(0, Math.min(64, Math.round(config.padding / 4) * 4)),
    borderRadius: Math.max(0, Math.min(48, Math.round(config.borderRadius / 4) * 4)),
    text: (config.text || 'A').substring(0, 2),
    primaryColor: config.primaryColor || '#3b82f6',
    secondaryColor: config.secondaryColor || '#8b5cf6',
    backgroundColor: config.backgroundColor || '#ffffff',
  };
}

export function createBatchConfig(
  base: IconConfig,
  overrides: Partial<IconConfig>
): IconConfig {
  return normalizeConfig({ ...base, ...overrides });
}
