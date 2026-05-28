import { create } from 'zustand';
import type { NoiseType } from '@/utils/noise';

export type MaterialMode = 'heightColor' | 'wireframe' | 'solid';

export interface TerrainState {
  noiseType: NoiseType;
  amplitude: number;
  frequency: number;
  octaves: number;
  persistence: number;
  lacunarity: number;
  seed: number;
  gridSize: number;
  chunkSize: number;
  chunks: number;
  waterLevel: number;
  material: MaterialMode;
  showWater: boolean;
  showShadows: boolean;
  autoRotate: boolean;
  lodBias: number;
  wireframe: boolean;
  reset: () => void;
  randomize: () => void;
  set: <K extends keyof TerrainState>(k: K, v: TerrainState[K]) => void;
}

export const DEFAULTS: Omit<TerrainState, 'reset' | 'randomize' | 'set'> = {
  noiseType: 'simplex',
  amplitude: 60,
  frequency: 0.012,
  octaves: 7,
  persistence: 0.5,
  lacunarity: 2.0,
  seed: 42,
  gridSize: 128,
  chunkSize: 200,
  chunks: 3,
  waterLevel: 2,
  material: 'heightColor',
  showWater: true,
  showShadows: true,
  autoRotate: false,
  lodBias: 1.2,
  wireframe: false,
};

export const useTerrainStore = create<TerrainState>((set) => ({
  ...DEFAULTS,
  reset: () => set(DEFAULTS),
  randomize: () => set({ seed: Math.floor(Math.random() * 999999) }),
  set: (k, v) => set({ [k]: v } as any),
}));
