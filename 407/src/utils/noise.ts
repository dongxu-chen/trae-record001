import { createNoise2D } from 'simplex-noise';

export type NoiseType = 'perlin' | 'simplex';

function mulberry32(seed: number) {
  return function () {
    let t = (seed += 0x6d2b79f5);
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export interface NoiseOptions {
  type: NoiseType;
  amplitude: number;
  frequency: number;
  octaves: number;
  persistence: number;
  lacunarity: number;
  seed: number;
}

export function createSampler(opts: NoiseOptions) {
  const rng = mulberry32(opts.seed);
  const noise2D = createNoise2D(rng);
  return (x: number, y: number) => {
    let value = 0;
    let amp = 1;
    let freq = opts.frequency;
    let maxAmp = 0;
    for (let i = 0; i < opts.octaves; i++) {
      value += noise2D(x * freq, y * freq) * amp;
      maxAmp += amp;
      amp *= opts.persistence;
      freq *= opts.lacunarity;
    }
    const n = value / maxAmp;
    return n * opts.amplitude;
  };
}
