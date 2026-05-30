export interface LineConfig {
  id: string;
  text: string;
  color: string;
}

export interface FontConfig {
  family: string;
  size: number;
  weight: number;
  glow: boolean;
  glowIntensity: number;
}

export type ScrollDirection = 'left' | 'right' | 'up' | 'down';
export type ScrollMode = 'continuous' | 'once';

export interface ScrollConfig {
  direction: ScrollDirection;
  speed: number;
  mode: ScrollMode;
}

export type BackgroundEffect = 'none' | 'particles' | 'matrix' | 'neon-glow' | 'starfield';

export interface BackgroundConfig {
  color: string;
  effect: BackgroundEffect;
  effectIntensity: number;
  effectColor: string;
}

export interface LEDState {
  lines: LineConfig[];
  font: FontConfig;
  scroll: ScrollConfig;
  background: BackgroundConfig;
  activeLineIndex: number;
  isPlaying: boolean;
}

export interface LEDActions {
  addLine: () => void;
  removeLine: (index: number) => void;
  updateLine: (index: number, updates: Partial<LineConfig>) => void;
  setFont: (font: Partial<FontConfig>) => void;
  setScroll: (scroll: Partial<ScrollConfig>) => void;
  setBackground: (bg: Partial<BackgroundConfig>) => void;
  setActiveLineIndex: (index: number) => void;
  togglePlaying: () => void;
  applyPreset: (preset: PresetConfig) => void;
  reset: () => void;
}

export interface PresetConfig {
  name: string;
  lines: { text: string; color: string }[];
  font: Partial<FontConfig>;
  background: Partial<BackgroundConfig>;
  scroll: Partial<ScrollConfig>;
}

export type LEDStore = LEDState & LEDActions;
