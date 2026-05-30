import { IconConfig } from './types';

export type AnimationType =
  | 'breathe'
  | 'pulse'
  | 'bounce'
  | 'rotate'
  | 'shake'
  | 'swing'
  | 'fadeIn'
  | 'zoom'
  | 'wave'
  | 'shine';

export interface AnimationConfig {
  type: AnimationType;
  duration: number;
  loop: boolean;
  easing: 'linear' | 'easeIn' | 'easeOut' | 'easeInOut';
  delay: number;
}

export interface AnimationFrame {
  time: number;
  scale: number;
  translateX: number;
  translateY: number;
  rotation: number;
  opacity: number;
  colorShift: number;
}

export const defaultAnimationConfig: AnimationConfig = {
  type: 'breathe',
  duration: 2000,
  loop: true,
  easing: 'easeInOut',
  delay: 0,
};

export const animationPresets: { id: AnimationType; name: string; description: string }[] = [
  { id: 'breathe', name: '呼吸', description: '平缓的缩放呼吸效果' },
  { id: 'pulse', name: '脉冲', description: '有节奏的脉冲效果' },
  { id: 'bounce', name: '弹跳', description: '活泼的弹跳效果' },
  { id: 'rotate', name: '旋转', description: '优雅的旋转效果' },
  { id: 'shake', name: '抖动', description: '快速的抖动效果' },
  { id: 'swing', name: '摇摆', description: '左右摇摆效果' },
  { id: 'fadeIn', name: '淡入', description: '渐隐渐现效果' },
  { id: 'zoom', name: '缩放', description: '缩放弹入效果' },
  { id: 'wave', name: '波动', description: '波浪起伏效果' },
  { id: 'shine', name: '闪光', description: '闪光掠过效果' },
];

function easeLinear(t: number): number {
  return t;
}

function easeInQuad(t: number): number {
  return t * t;
}

function easeOutQuad(t: number): number {
  return t * (2 - t);
}

function easeInOutQuad(t: number): number {
  return t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t;
}

function getEasingFunction(easing: AnimationConfig['easing']): (t: number) => number {
  switch (easing) {
    case 'linear':
      return easeLinear;
    case 'easeIn':
      return easeInQuad;
    case 'easeOut':
      return easeOutQuad;
    case 'easeInOut':
      return easeInOutQuad;
    default:
      return easeInOutQuad;
  }
}

export function calculateAnimationFrame(
  config: AnimationConfig,
  elapsedTime: number
): AnimationFrame {
  const effectiveTime = Math.max(0, elapsedTime - config.delay);
  const duration = config.duration;
  let t = effectiveTime / duration;

  if (config.loop) {
    t = t % 1;
    if (t < 0) t += 1;
  } else if (t >= 1) {
    t = 1;
  }

  const easingFn = getEasingFunction(config.easing);
  const easedT = easingFn(t);

  const frame: AnimationFrame = {
    time: elapsedTime,
    scale: 1,
    translateX: 0,
    translateY: 0,
    rotation: 0,
    opacity: 1,
    colorShift: 0,
  };

  switch (config.type) {
    case 'breathe': {
      const breatheT = Math.sin(t * Math.PI * 2);
      frame.scale = 1 + breatheT * 0.08;
      break;
    }
    case 'pulse': {
      const pulseT = Math.sin(t * Math.PI * 2) * 0.5 + 0.5;
      frame.scale = 1 + pulseT * 0.15;
      frame.opacity = 0.8 + pulseT * 0.2;
      break;
    }
    case 'bounce': {
      const bounceT = Math.abs(Math.sin(t * Math.PI * 2));
      frame.scale = 1 + bounceT * 0.2;
      frame.translateY = -bounceT * 10;
      break;
    }
    case 'rotate': {
      frame.rotation = t * 360;
      break;
    }
    case 'shake': {
      const shakeT = Math.sin(t * Math.PI * 10);
      frame.translateX = shakeT * 3;
      frame.rotation = shakeT * 2;
      break;
    }
    case 'swing': {
      const swingT = Math.sin(t * Math.PI * 2);
      frame.rotation = swingT * 15;
      frame.translateX = swingT * 5;
      break;
    }
    case 'fadeIn': {
      const fadeT = Math.sin(t * Math.PI);
      frame.opacity = fadeT;
      frame.scale = 0.9 + fadeT * 0.1;
      break;
    }
    case 'zoom': {
      const zoomT = Math.sin(t * Math.PI * 2) * 0.5 + 0.5;
      frame.scale = 0.8 + zoomT * 0.4;
      break;
    }
    case 'wave': {
      const waveT = Math.sin(t * Math.PI * 4);
      frame.translateY = waveT * 5;
      frame.scale = 1 + waveT * 0.05;
      break;
    }
    case 'shine': {
      const shineT = t;
      frame.colorShift = shineT;
      frame.scale = 1 + Math.sin(shineT * Math.PI) * 0.05;
      break;
    }
  }

  return {
    ...frame,
    scale: 1 + (frame.scale - 1) * easedT,
    translateX: frame.translateX * easedT,
    translateY: frame.translateY * easedT,
    rotation: frame.rotation * easedT,
    opacity: frame.opacity,
    colorShift: frame.colorShift,
  };
}

export function generateAnimationFrames(
  config: AnimationConfig,
  fps: number = 60
): AnimationFrame[] {
  const totalFrames = Math.ceil((config.duration + config.delay) / 1000 * fps);
  const frames: AnimationFrame[] = [];

  for (let i = 0; i <= totalFrames; i++) {
    const elapsedTime = (i / totalFrames) * (config.duration + config.delay);
    frames.push(calculateAnimationFrame(config, elapsedTime));
  }

  return frames;
}
