import * as THREE from 'three';

const STOPS = [
  { h: -0.2, color: new THREE.Color('#0b3a5b') },
  { h: 0.05, color: new THREE.Color('#d9c37a') },
  { h: 0.2, color: new THREE.Color('#3fa34d') },
  { h: 0.55, color: new THREE.Color('#6b7a3c') },
  { h: 0.8, color: new THREE.Color('#7a6a4d') },
  { h: 1.0, color: new THREE.Color('#ffffff') },
];

export function heightToColor(h: number, waterLevel: number, amplitude: number): THREE.Color {
  const normalized = THREE.MathUtils.clamp(
    (h - waterLevel) / Math.max(0.0001, amplitude),
    0,
    1,
  );
  for (let i = 0; i < STOPS.length - 1; i++) {
    const a = STOPS[i];
    const b = STOPS[i + 1];
    if (normalized <= b.h) {
      const t = (normalized - a.h) / (b.h - a.h);
      return a.color.clone().lerp(b.color, t);
    }
  }
  return STOPS[STOPS.length - 1].color.clone();
}
