export const particlePresets = {
  fire: {
    name: '火焰',
    icon: '🔥',
    config: {
      maxParticles: 1000000,
      particleCount: 150000,
      emissionRate: 30000,
      speed: { min: 2, max: 5 },
      life: { min: 0.5, max: 1.5 },
      size: { min: 0.2, max: 0.8 },
      color: { start: '#ffff00', end: '#ff0000' },
      direction: { x: 0, y: 1, z: 0 },
      spread: 0.6,
      gravity: { x: 0, y: -1, z: 0 },
      emitterPosition: { x: 0, y: -2, z: 0 },
      emitterShape: 'circle',
      emitterRadius: 0.5,
      rotationSpeed: { min: 0, max: 3 },
      blending: 'additive'
    }
  },
  smoke: {
    name: '烟雾',
    icon: '💨',
    config: {
      maxParticles: 500000,
      particleCount: 80000,
      emissionRate: 8000,
      speed: { min: 0.5, max: 1.5 },
      life: { min: 2, max: 5 },
      size: { min: 0.5, max: 1.5 },
      color: { start: '#888888', end: '#333333' },
      direction: { x: 0, y: 1, z: 0 },
      spread: 0.8,
      gravity: { x: 0, y: 0.2, z: 0 },
      emitterPosition: { x: 0, y: -2, z: 0 },
      emitterShape: 'circle',
      emitterRadius: 0.3,
      rotationSpeed: { min: 0.5, max: 2 },
      blending: 'normal'
    }
  },
  stars: {
    name: '星空',
    icon: '✨',
    config: {
      maxParticles: 2000000,
      particleCount: 500000,
      emissionRate: 50000,
      speed: { min: 0.05, max: 0.2 },
      life: { min: 3, max: 8 },
      size: { min: 0.05, max: 0.2 },
      color: { start: '#ffffff', end: '#88ccff' },
      direction: { x: 0, y: 0, z: 0 },
      spread: 0,
      gravity: { x: 0, y: 0, z: 0 },
      emitterPosition: { x: 0, y: 0, z: 0 },
      emitterShape: 'sphere',
      emitterRadius: 20,
      rotationSpeed: { min: 0, max: 1 },
      blending: 'additive'
    }
  },
  snow: {
    name: '雪花',
    icon: '❄️',
    config: {
      maxParticles: 1000000,
      particleCount: 200000,
      emissionRate: 15000,
      speed: { min: 0.3, max: 1 },
      life: { min: 5, max: 10 },
      size: { min: 0.1, max: 0.4 },
      color: { start: '#ffffff', end: '#aaddff' },
      direction: { x: 0, y: -1, z: 0 },
      spread: 0.3,
      gravity: { x: 0, y: -0.1, z: 0 },
      emitterPosition: { x: 0, y: 8, z: 0 },
      emitterShape: 'box',
      emitterRadius: 15,
      rotationSpeed: { min: 1, max: 4 },
      blending: 'additive'
    }
  }
}

export function getPresetByName(name) {
  return particlePresets[name] || particlePresets.fire
}

export function getAllPresetNames() {
  return Object.keys(particlePresets)
}
