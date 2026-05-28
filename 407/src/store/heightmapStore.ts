import { create } from 'zustand';
import * as THREE from 'three';
import { createSampler, type NoiseOptions } from '@/utils/noise';

export interface HeightmapStore {
  size: number;
  resolution: number;
  heights: Float32Array;
  modified: boolean;
  brushSize: number;
  brushStrength: number;
  brushMode: 'raise' | 'lower' | 'smooth' | 'flatten';
  erosion: {
    iterations: number;
    sedimentCapacity: number;
    erosionRate: number;
    depositionRate: number;
    evaporationRate: number;
    minSlope: number;
    inertia: number;
  };
  vegetation: {
    enabled: boolean;
    density: number;
    treeCount: number;
    grassCount: number;
    maxAltitude: number;
    maxSlope: number;
  };
  tools: {
    sculpting: boolean;
    showBrush: boolean;
  };
  setHeight: (x: number, z: number, value: number) => void;
  getHeight: (x: number, z: number) => number;
  getInterpolatedHeight: (wx: number, wz: number, worldSize: number) => number;
  applyBrush: (worldX: number, worldZ: number, worldSize: number) => void;
  generateFromNoise: (opts: NoiseOptions, waterLevel: number) => void;
  applyErosion: (worldSize: number) => Promise<void>;
  reset: () => void;
  set: <K extends keyof HeightmapStore>(k: K, v: HeightmapStore[K]) => void;
}

const DEFAULT_SIZE = 1024;
const DEFAULT_RESOLUTION = 512;

function createEmptyHeights() {
  return new Float32Array(DEFAULT_RESOLUTION * DEFAULT_RESOLUTION);
}

export const useHeightmapStore = create<HeightmapStore>((set, get) => ({
  size: DEFAULT_SIZE,
  resolution: DEFAULT_RESOLUTION,
  heights: createEmptyHeights(),
  modified: false,
  brushSize: 30,
  brushStrength: 8,
  brushMode: 'raise',
  erosion: {
    iterations: 50,
    sedimentCapacity: 4,
    erosionRate: 0.3,
    depositionRate: 0.3,
    evaporationRate: 0.02,
    minSlope: 0.01,
    inertia: 0.05,
  },
  vegetation: {
    enabled: true,
    density: 0.6,
    treeCount: 2000,
    grassCount: 5000,
    maxAltitude: 0.7,
    maxSlope: 0.5,
  },
  tools: {
    sculpting: false,
    showBrush: true,
  },

  setHeight: (x, z, value) => {
    const { resolution, heights } = get();
    const idx = z * resolution + x;
    if (idx >= 0 && idx < heights.length) {
      heights[idx] = value;
    }
  },

  getHeight: (x, z) => {
    const { resolution, heights } = get();
    const idx = Math.floor(z) * resolution + Math.floor(x);
    if (idx >= 0 && idx < heights.length) {
      return heights[idx];
    }
    return 0;
  },

  getInterpolatedHeight: (wx, wz, worldSize) => {
    const { resolution, heights } = get();
    const scale = resolution / worldSize;
    const x = wx * scale + resolution / 2;
    const z = wz * scale + resolution / 2;

    const x0 = Math.floor(x);
    const z0 = Math.floor(z);
    const x1 = x0 + 1;
    const z1 = z0 + 1;

    if (x0 < 0 || z0 < 0 || x1 >= resolution || z1 >= resolution) {
      return 0;
    }

    const fx = x - x0;
    const fz = z - z0;

    const h00 = heights[z0 * resolution + x0];
    const h10 = heights[z0 * resolution + x1];
    const h01 = heights[z1 * resolution + x0];
    const h11 = heights[z1 * resolution + x1];

    const h0 = h00 * (1 - fx) + h10 * fx;
    const h1 = h01 * (1 - fx) + h11 * fx;
    return h0 * (1 - fz) + h1 * fz;
  },

  applyBrush: (worldX, worldZ, worldSize) => {
    const state = get();
    const { resolution, heights, brushSize, brushStrength, brushMode } = state;
    const scale = resolution / worldSize;
    const cx = worldX * scale + resolution / 2;
    const cz = worldZ * scale + resolution / 2;
    const radius = brushSize * scale;
    const radiusSq = radius * radius;

    const minX = Math.max(0, Math.floor(cx - radius));
    const maxX = Math.min(resolution - 1, Math.ceil(cx + radius));
    const minZ = Math.max(0, Math.floor(cz - radius));
    const maxZ = Math.min(resolution - 1, Math.ceil(cz + radius));

    for (let z = minZ; z <= maxZ; z++) {
      for (let x = minX; x <= maxX; x++) {
        const dx = x - cx;
        const dz = z - cz;
        const distSq = dx * dx + dz * dz;
        if (distSq > radiusSq) continue;

        const falloff = 1 - Math.sqrt(distSq) / radius;
        const idx = z * resolution + x;
        const delta = brushStrength * falloff * 0.1;

        if (brushMode === 'raise') {
          heights[idx] += delta;
        } else if (brushMode === 'lower') {
          heights[idx] -= delta;
        } else if (brushMode === 'smooth') {
          let sum = 0;
          let count = 0;
          for (let oz = -1; oz <= 1; oz++) {
            for (let ox = -1; ox <= 1; ox++) {
              const nx = x + ox;
              const nz = z + oz;
              if (nx >= 0 && nx < resolution && nz >= 0 && nz < resolution) {
                sum += heights[nz * resolution + nx];
                count++;
              }
            }
          }
          heights[idx] = heights[idx] * (1 - falloff * 0.5) + (sum / count) * falloff * 0.5;
        }
      }
    }

    set({ modified: true });
  },

  generateFromNoise: (opts, waterLevel) => {
    const { resolution } = get();
    const heights = new Float32Array(resolution * resolution);
    const sample = createSampler(opts);

    for (let z = 0; z < resolution; z++) {
      for (let x = 0; x < resolution; x++) {
        const wx = (x - resolution / 2) * (100 / resolution);
        const wz = (z - resolution / 2) * (100 / resolution);
        heights[z * resolution + x] = sample(wx, wz);
      }
    }

    set({ heights, modified: false });
  },

  applyErosion: async (worldSize) => {
    const state = get();
    const { resolution, heights, erosion } = state;
    const {
      iterations,
      sedimentCapacity,
      erosionRate,
      depositionRate,
      evaporationRate,
      minSlope,
      inertia,
    } = erosion;

    const scale = resolution / worldSize;
    const newHeights = new Float32Array(heights);

    const particleCount = Math.min(50000, iterations * 100);

    for (let i = 0; i < particleCount; i++) {
      if (i % 10000 === 0) {
        await new Promise((r) => setTimeout(r, 0));
      }

      let px = Math.random() * resolution;
      let pz = Math.random() * resolution;
      let dirX = 0;
      let dirZ = 0;
      let speed = 1;
      let water = 1;
      let sediment = 0;

      for (let step = 0; step < 64; step++) {
        const ix = Math.floor(px);
        const iz = Math.floor(pz);
        if (ix < 1 || iz < 1 || ix >= resolution - 1 || iz >= resolution - 1) break;

        const h = newHeights[iz * resolution + ix];
        const hR = newHeights[iz * resolution + ix + 1];
        const hD = newHeights[(iz + 1) * resolution + ix];

        const gx = hR - h;
        const gz = hD - h;

        dirX = dirX * inertia - gx * (1 - inertia);
        dirZ = dirZ * inertia - gz * (1 - inertia);

        const len = Math.sqrt(dirX * dirX + dirZ * dirZ);
        if (len > 0.0001) {
          dirX /= len;
          dirZ /= len;
        } else {
          const angle = Math.random() * Math.PI * 2;
          dirX = Math.cos(angle);
          dirZ = Math.sin(angle);
        }

        const npx = px + dirX;
        const npz = pz + dirZ;
        const nix = Math.floor(npx);
        const niz = Math.floor(npz);
        if (nix < 1 || niz < 1 || nix >= resolution - 1 || niz >= resolution - 1) break;

        const nh = newHeights[niz * resolution + nix];
        const dh = nh - h;

        const capacity = Math.max(-dh, minSlope) * speed * water * sedimentCapacity;

        if (sediment > capacity || dh < 0) {
          const deposit = dh < 0
            ? Math.min(-dh, sediment)
            : (sediment - capacity) * depositionRate;
          sediment -= deposit;
          newHeights[iz * resolution + ix] += deposit;
        } else {
          const erode = Math.min((capacity - sediment) * erosionRate, -dh);
          sediment += erode;
          newHeights[iz * resolution + ix] -= erode;
        }

        water *= 1 - evaporationRate;
        speed = Math.sqrt(Math.max(0, speed * speed + dh * 4));
        px = npx;
        pz = npz;
      }
    }

    set({ heights: newHeights, modified: true });
  },

  reset: () => {
    set({ heights: createEmptyHeights(), modified: false });
  },

  set: (k, v) => {
    set({ [k]: v } as any);
  },
}));
