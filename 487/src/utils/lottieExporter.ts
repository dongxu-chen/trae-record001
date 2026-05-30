import { IconConfig } from '../engine/types';
import {
  AnimationConfig,
  generateAnimationFrames,
  AnimationFrame,
} from '../engine/animationEngine';

interface LottieKeyframe {
  t: number;
  s: number[];
  e: number[];
  o: { a: number; k: number; }[];
  k: number[];
}

interface LottieTransform {
  a: {
    a: number;
    k: { t: number; s: number[]; e: number[]; }[];
    k: number[];
  };
  p: {
    a: number;
    k: { t: number; s: number[]; e: number[]; }[];
    k: number[];
  };
  s: {
    a: number;
    k: { t: number; s: number[]; e: number[]; }[];
    k: number[];
  };
  r: {
    a: number;
    k: { t: number; s: number[]; e: number[]; }[];
    k: number[];
  };
  o: {
    a: number;
    k: { t: number; s: number[]; e: number[]; }[];
    k: number[];
  };
}

interface LottieLayer {
  ddd: number;
  ind: number;
  ty: number;
  nm: string;
  sr: number;
  ks: LottieTransform;
  ao: number;
  ip: number;
  op: number;
  st: number;
  shapes?: LottieShape[];
}

interface LottieShape {
  ty: string;
  nm: string;
  it: LottieShapeItem[];
}

interface LottieShapeItem {
  ty: string;
  nm: string;
  d?: number;
  c?: { a: number; k: number[] };
  k?: number[];
  r?: { a: number; k: number };
  p?: { a: number; k: number[] };
  s?: { a: number; k: number[] };
  bm?: number;
  it?: LottieShapeItem[];
}

export interface LottieAnimation {
  v: string;
  fr: number;
  ip: number;
  op: number;
  w: number;
  h: number;
  nm: string;
  ddd: number;
  assets: any[];
  layers: LottieLayer[];
  fonts: any;
  chars: any[];
}

function framesToKeyframes(
  frames: AnimationFrame[],
  getValue: (f: AnimationFrame) => number[]
): { a: number; k: { t: number; s: number[]; e: number[]; }[]; k: number[]; } {
  if (frames.length <= 1) {
    return {
      a: 0,
      k: getValue(frames[0] || { time: 0, scale: 1, translateX: 0, translateY: 0, rotation: 0, opacity: 1, colorShift: 0 }),
    };
  }

  const keyframes: { t: number; s: number[]; e: number[]; }[] = [];

  for (let i = 0; i < frames.length - 1; i++) {
    const current = frames[i];
    const next = frames[i + 1];
    keyframes.push({
      t: i,
      s: getValue(current),
      e: getValue(next),
    });
  }

  return {
    a: 1,
    k: keyframes,
  };
}

export function generateLottieAnimation(
  iconConfig: IconConfig,
  animationConfig: AnimationConfig,
  fps: number = 60
): LottieAnimation {
  const frames = generateAnimationFrames(animationConfig, fps);
  const totalFrames = frames.length;
  const duration = (animationConfig.duration + animationConfig.delay) / 1000;
  const calculatedFps = totalFrames / duration;

  const scaleK = framesToKeyframes(frames, (f) => [f.scale * 100, f.scale * 100, 100]);
  const positionK = framesToKeyframes(frames, (f) => [
    iconConfig.size / 2 + f.translateX,
    iconConfig.size / 2 + f.translateY,
    0,
  ]);
  const rotationK = framesToKeyframes(frames, (f) => [f.rotation]);
  const opacityK = framesToKeyframes(frames, (f) => [f.opacity * 100]);

  const shapeGroup: LottieShape = {
    ty: 'gr',
    nm: 'Icon Group',
    it: [
      {
        ty: 'rc',
        nm: 'Background',
        d: 1,
        s: {
          a: 0,
          k: [
            iconConfig.size - iconConfig.padding,
            iconConfig.size - iconConfig.padding,
          ],
        },
        p: {
          a: 0,
          k: [0, 0],
        },
        r: {
          a: 0,
          k: iconConfig.borderRadius,
        },
      },
      {
        ty: 'fl',
        nm: 'Fill',
        c: {
          a: 0,
          k: [
            parseInt(iconConfig.primaryColor.slice(1, 3), 16) / 255,
            parseInt(iconConfig.primaryColor.slice(3, 5), 16) / 255,
            parseInt(iconConfig.primaryColor.slice(5, 7), 16) / 255,
            1,
          ],
        },
        o: {
          a: 0,
          k: iconConfig.showBackground ? 100 : 0,
        },
        bm: 0,
      },
      {
        ty: 'tr',
        nm: 'Transform',
        a: {
          a: 0,
          k: [0, 0],
        },
        p: {
          a: 0,
          k: [0, 0, 0],
        },
        s: {
          a: 0,
          k: [100, 100, 100],
        },
        r: {
          a: 0,
          k: 0,
        },
        o: {
          a: 0,
          k: 100,
        },
      },
    ],
  };

  const textGroup: LottieShape = {
    ty: 'gr',
    nm: 'Text Group',
    it: [
      {
        ty: 't',
        nm: 'Text',
        d: 1,
        p: {
          a: 0,
          k: [0, 0],
        },
        s: {
          a: 0,
          k: [
            {
              t: 0,
              s: {
                f: 'Space Grotesk',
                s: (iconConfig.size - iconConfig.padding * 2) * 0.5,
                t: iconConfig.text.substring(0, 2).toUpperCase(),
                j: 2,
                lh: 0,
                ls: 0,
                fc: [1, 1, 1],
              },
            },
          ],
        },
      },
      {
        ty: 'tr',
        nm: 'Transform',
        a: {
          a: 0,
          k: [0, 0],
        },
        p: {
          a: 0,
          k: [0, 0, 0],
        },
        s: {
          a: 0,
          k: [100, 100, 100],
        },
        r: {
          a: 0,
          k: 0,
        },
        o: {
          a: 0,
          k: 100,
        },
      },
    ],
  };

  const layer: LottieLayer = {
    ddd: 0,
    ind: 1,
    ty: 4,
    nm: 'Icon Layer',
    sr: 1,
    ks: {
      a: { a: 0, k: [0, 0], },
      p: positionK,
      s: scaleK,
      r: rotationK,
      o: opacityK,
    },
    ao: 0,
    ip: 0,
    op: totalFrames,
    st: 0,
    shapes: [shapeGroup, textGroup],
  };

  return {
    v: '5.7.0',
    fr: calculatedFps,
    ip: 0,
    op: totalFrames,
    w: iconConfig.size,
    h: iconConfig.size,
    nm: `${iconConfig.text}-${animationConfig.type}`,
    ddd: 0,
    assets: [],
    layers: [layer],
    fonts: {
      list: [
        {
          fName: 'Space Grotesk',
          fFamily: 'Space Grotesk',
          fStyle: 'Bold',
          fWeight: '700',
          fClass: '',
          ascent: 0,
        },
      ],
    },
    chars: [],
  };
}

export function exportLottieJson(
  iconConfig: IconConfig,
  animationConfig: AnimationConfig
): string {
  const lottie = generateLottieAnimation(iconConfig, animationConfig);
  return JSON.stringify(lottie, null, 2);
}

export function downloadLottie(
  iconConfig: IconConfig,
  animationConfig: AnimationConfig,
  filename?: string
): void {
  const json = exportLottieJson(iconConfig, animationConfig);
  const blob = new Blob([json], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.download = `${filename || `icon-${iconConfig.text}-${animationConfig.type}.json`;
  link.href = url;
  link.click();
  URL.revokeObjectURL(url);
}
