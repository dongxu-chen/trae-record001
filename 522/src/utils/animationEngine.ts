export type EasingFunction = 'linear' | 'easeIn' | 'easeOut' | 'easeInOut' | 'bounce' | 'elastic';
export type AnimationLoopMode = 'once' | 'loop' | 'pingpong';
export type AnimationPreset = 'fadeIn' | 'pulse' | 'wave' | 'flash' | 'breathe' | 'custom';

export interface Keyframe {
  time: number;
  value: number;
  easing?: EasingFunction;
}

export interface ParameterAnimation {
  parameterName: string;
  keyframes: Keyframe[];
  loopMode: AnimationLoopMode;
  duration: number;
}

export interface AnimationState {
  isPlaying: boolean;
  currentTime: number;
  totalDuration: number;
  progress: number;
  loopMode: AnimationLoopMode;
}

export const EASING_FUNCTIONS: Record<EasingFunction, (t: number) => number> = {
  linear: (t) => t,
  easeIn: (t) => t * t,
  easeOut: (t) => 1 - (1 - t) * (1 - t),
  easeInOut: (t) => (t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2),
  bounce: (t) => {
    const n1 = 7.5625;
    const d1 = 2.75;
    if (t < 1 / d1) return n1 * t * t;
    if (t < 2 / d1) return n1 * (t -= 1.5 / d1) * t + 0.75;
    if (t < 2.5 / d1) return n1 * (t -= 2.25 / d1) * t + 0.9375;
    return n1 * (t -= 2.625 / d1) * t + 0.984375;
  },
  elastic: (t) => {
    const c4 = (2 * Math.PI) / 3;
    return t === 0
      ? 0
      : t === 1
      ? 1
      : Math.pow(2, -10 * t) * Math.sin((t * 10 - 0.75) * c4) + 1;
  },
};

export const ANIMATION_PRESETS: Record<AnimationPreset, ParameterAnimation[]> = {
  fadeIn: [
    {
      parameterName: 'intensity',
      keyframes: [
        { time: 0, value: 0 },
        { time: 1, value: 1, easing: 'easeOut' },
      ],
      loopMode: 'once',
      duration: 2000,
    },
  ],
  pulse: [
    {
      parameterName: 'intensity',
      keyframes: [
        { time: 0, value: 0.3, easing: 'easeInOut' },
        { time: 0.5, value: 1.0, easing: 'easeInOut' },
        { time: 1, value: 0.3, easing: 'easeInOut' },
      ],
      loopMode: 'loop',
      duration: 2000,
    },
  ],
  wave: [
    {
      parameterName: 'intensity',
      keyframes: [
        { time: 0, value: 0, easing: 'easeInOut' },
        { time: 0.25, value: 0.8, easing: 'easeInOut' },
        { time: 0.5, value: 0.2, easing: 'easeInOut' },
        { time: 0.75, value: 0.9, easing: 'easeInOut' },
        { time: 1, value: 0, easing: 'easeInOut' },
      ],
      loopMode: 'loop',
      duration: 3000,
    },
  ],
  flash: [
    {
      parameterName: 'intensity',
      keyframes: [
        { time: 0, value: 0, easing: 'easeOut' },
        { time: 0.1, value: 1, easing: 'easeIn' },
        { time: 0.2, value: 0.3, easing: 'easeOut' },
        { time: 0.3, value: 0.8, easing: 'easeIn' },
        { time: 0.4, value: 0, easing: 'easeOut' },
        { time: 1, value: 0 },
      ],
      loopMode: 'once',
      duration: 2000,
    },
  ],
  breathe: [
    {
      parameterName: 'intensity',
      keyframes: [
        { time: 0, value: 0.4, easing: 'easeInOut' },
        { time: 0.4, value: 0.9, easing: 'easeInOut' },
        { time: 0.6, value: 0.9, easing: 'easeInOut' },
        { time: 1, value: 0.4, easing: 'easeInOut' },
      ],
      loopMode: 'loop',
      duration: 4000,
    },
  ],
  custom: [],
};

export class AnimationEngine {
  private animations: Map<string, ParameterAnimation> = new Map();
  private currentValues: Map<string, number> = new Map();
  private state: AnimationState = {
    isPlaying: false,
    currentTime: 0,
    totalDuration: 0,
    progress: 0,
    loopMode: 'loop',
  };
  private animationFrameId: number | null = null;
  private startTime: number = 0;
  private pauseTime: number = 0;
  private onUpdate: ((values: Map<string, number>, state: AnimationState) => void) | null = null;
  private direction: 1 | -1 = 1;

  setAnimations(animations: ParameterAnimation[]) {
    this.animations.clear();
    let maxDuration = 0;
    for (const anim of animations) {
      this.animations.set(anim.parameterName, anim);
      if (anim.duration > maxDuration) {
        maxDuration = anim.duration;
      }
    }
    this.state.totalDuration = maxDuration;
    this.state.loopMode = animations.length > 0 ? animations[0].loopMode : 'loop';
  }

  setOnUpdate(callback: (values: Map<string, number>, state: AnimationState) => void) {
    this.onUpdate = callback;
  }

  play() {
    if (this.state.isPlaying) return;
    if (this.animations.size === 0) return;

    this.state.isPlaying = true;
    this.startTime = performance.now() - this.pauseTime;
    this.direction = 1;
    this.animate();
  }

  pause() {
    this.state.isPlaying = false;
    this.pauseTime = performance.now() - this.startTime;
    if (this.animationFrameId) {
      cancelAnimationFrame(this.animationFrameId);
      this.animationFrameId = null;
    }
  }

  stop() {
    this.state.isPlaying = false;
    this.state.currentTime = 0;
    this.state.progress = 0;
    this.pauseTime = 0;
    this.currentValues.clear();
    if (this.animationFrameId) {
      cancelAnimationFrame(this.animationFrameId);
      this.animationFrameId = null;
    }
  }

  seek(progress: number) {
    this.state.progress = Math.max(0, Math.min(1, progress));
    this.state.currentTime = this.state.progress * this.state.totalDuration;
    this.pauseTime = this.state.currentTime;
    this.updateValues();
    this.invokeCallback();
  }

  setLoopMode(mode: AnimationLoopMode) {
    this.state.loopMode = mode;
  }

  getState(): AnimationState {
    return { ...this.state };
  }

  getValues(): Map<string, number> {
    return new Map(this.currentValues);
  }

  private animate = () => {
    if (!this.state.isPlaying) return;

    const now = performance.now();
    let elapsed = now - this.startTime;

    const { totalDuration, loopMode } = this.state;

    if (loopMode === 'loop') {
      elapsed = elapsed % totalDuration;
    } else if (loopMode === 'pingpong') {
      const cycle = totalDuration * 2;
      const cycleElapsed = elapsed % cycle;
      if (cycleElapsed < totalDuration) {
        this.direction = 1;
        elapsed = cycleElapsed;
      } else {
        this.direction = -1;
        elapsed = cycle - cycleElapsed;
      }
    } else {
      if (elapsed >= totalDuration) {
        elapsed = totalDuration;
        this.state.isPlaying = false;
      }
    }

    this.state.currentTime = elapsed;
    this.state.progress = totalDuration > 0 ? elapsed / totalDuration : 0;

    this.updateValues();
    this.invokeCallback();

    if (this.state.isPlaying) {
      this.animationFrameId = requestAnimationFrame(this.animate);
    }
  };

  private updateValues() {
    const { progress } = this.state;

    for (const [paramName, animation] of this.animations) {
      const value = this.interpolateKeyframes(animation.keyframes, progress);
      this.currentValues.set(paramName, value);
    }
  }

  private interpolateKeyframes(keyframes: Keyframe[], progress: number): number {
    if (keyframes.length === 0) return 0;
    if (keyframes.length === 1) return keyframes[0].value;

    let prevFrame = keyframes[0];
    let nextFrame = keyframes[keyframes.length - 1];

    for (let i = 0; i < keyframes.length - 1; i++) {
      if (progress >= keyframes[i].time && progress <= keyframes[i + 1].time) {
        prevFrame = keyframes[i];
        nextFrame = keyframes[i + 1];
        break;
      }
    }

    if (prevFrame.time === nextFrame.time) return prevFrame.value;

    const segmentProgress =
      (progress - prevFrame.time) / (nextFrame.time - prevFrame.time);

    const easing = EASING_FUNCTIONS[prevFrame.easing || 'linear'];
    const easedProgress = easing(segmentProgress);

    return prevFrame.value + (nextFrame.value - prevFrame.value) * easedProgress;
  }

  private invokeCallback() {
    if (this.onUpdate) {
      this.onUpdate(new Map(this.currentValues), { ...this.state });
    }
  }

  destroy() {
    this.stop();
    this.animations.clear();
    this.currentValues.clear();
    this.onUpdate = null;
  }
}
