import * as THREE from 'three';
import { catmullRom, catmullRomVector3 } from '../math/CurveMath';

export const InterpolateSpline = 3;

export type InterpolationMode =
  | typeof THREE.InterpolateDiscrete
  | typeof THREE.InterpolateLinear
  | typeof THREE.InterpolateSmooth
  | typeof InterpolateSpline;

export interface KeyframeData {
  times: number[];
  values: number[];
  interpolation: InterpolationMode;
}

export interface AnimationBlendConfig {
  weight: number;
  loop: THREE.AnimationActionLoopStyles;
  clampWhenFinished: boolean;
  timeScale: number;
}

export function interpolateNumber(
  t: number,
  t0: number,
  t1: number,
  v0: number,
  v1: number,
  interpolation: InterpolationMode = THREE.InterpolateLinear
): number {
  if (t <= t0) return v0;
  if (t >= t1) return v1;

  const s = (t - t0) / (t1 - t0);

  switch (interpolation) {
    case THREE.InterpolateDiscrete:
      return v0;
    case THREE.InterpolateLinear:
      return v0 + s * (v1 - v0);
    case THREE.InterpolateSmooth: {
      const s2 = s * s;
      const s3 = s2 * s;
      return v0 + (3 * s2 - 2 * s3) * (v1 - v0);
    }
    case InterpolateSpline: {
      const s2 = s * s;
      const s3 = s2 * s;
      return v0 + (3 * s2 - 2 * s3) * (v1 - v0);
    }
    default:
      return v0 + s * (v1 - v0);
  }
}

export function interpolateNumberSpline(
  t: number,
  times: number[],
  values: number[],
  alpha: number = 0.5
): number {
  const n = times.length;
  if (n === 0) return 0;
  if (n === 1) return values[0];
  if (t <= times[0]) return values[0];
  if (t >= times[n - 1]) return values[n - 1];

  let i = 0;
  while (i < n - 1 && t > times[i + 1]) {
    i++;
  }

  if (n === 2) {
    const s = (t - times[0]) / (times[1] - times[0]);
    return values[0] + s * (values[1] - values[0]);
  }

  const p0 = i === 0 ? values[0] - (values[1] - values[0]) : values[i - 1];
  const p1 = values[i];
  const p2 = values[i + 1];
  const p3 = i >= n - 2 ? values[n - 1] + (values[n - 1] - values[n - 2]) : values[i + 2];

  const s = (t - times[i]) / (times[i + 1] - times[i]);
  return catmullRom(p0, p1, p2, p3, s, alpha);
}

export function interpolateVector3(
  t: number,
  t0: number,
  t1: number,
  v0: THREE.Vector3,
  v1: THREE.Vector3,
  interpolation: InterpolationMode = THREE.InterpolateLinear
): THREE.Vector3 {
  const result = new THREE.Vector3();

  result.x = interpolateNumber(t, t0, t1, v0.x, v1.x, interpolation);
  result.y = interpolateNumber(t, t0, t1, v0.y, v1.y, interpolation);
  result.z = interpolateNumber(t, t0, t1, v0.z, v1.z, interpolation);

  return result;
}

export function interpolateVector3Spline(
  t: number,
  times: number[],
  values: THREE.Vector3[],
  alpha: number = 0.5
): THREE.Vector3 {
  const n = times.length;
  if (n === 0) return new THREE.Vector3();
  if (n === 1) return values[0].clone();
  if (t <= times[0]) return values[0].clone();
  if (t >= times[n - 1]) return values[n - 1].clone();

  let i = 0;
  while (i < n - 1 && t > times[i + 1]) {
    i++;
  }

  if (n === 2) {
    const s = (t - times[0]) / (times[1] - times[0]);
    return new THREE.Vector3().lerpVectors(values[0], values[1], s);
  }

  const p0 = i === 0
    ? values[0].clone().sub(values[1].clone().sub(values[0]))
    : values[i - 1];
  const p1 = values[i];
  const p2 = values[i + 1];
  const p3 = i >= n - 2
    ? values[n - 1].clone().add(values[n - 1].clone().sub(values[n - 2]))
    : values[i + 2];

  const s = (t - times[i]) / (times[i + 1] - times[i]);
  return catmullRomVector3(p0, p1, p2, p3, s, alpha);
}

export function interpolateQuaternion(
  t: number,
  t0: number,
  t1: number,
  q0: THREE.Quaternion,
  q1: THREE.Quaternion,
  interpolation: InterpolationMode = THREE.InterpolateLinear
): THREE.Quaternion {
  if (t <= t0) return q0.clone();
  if (t >= t1) return q1.clone();

  const s = (t - t0) / (t1 - t0);
  const result = new THREE.Quaternion();

  switch (interpolation) {
    case THREE.InterpolateDiscrete:
      return q0.clone();
    case THREE.InterpolateLinear:
    case THREE.InterpolateSmooth:
    case InterpolateSpline:
      result.copy(q0).slerp(q1, s);
      return result;
    default:
      result.copy(q0).slerp(q1, s);
      return result;
  }
}

export function interpolateQuaternionSpline(
  t: number,
  times: number[],
  values: THREE.Quaternion[],
  alpha: number = 0.5
): THREE.Quaternion {
  const n = times.length;
  if (n === 0) return new THREE.Quaternion();
  if (n === 1) return values[0].clone();
  if (t <= times[0]) return values[0].clone();
  if (t >= times[n - 1]) return values[n - 1].clone();

  let i = 0;
  while (i < n - 1 && t > times[i + 1]) {
    i++;
  }

  const s = (t - times[i]) / (times[i + 1] - times[i]);
  const q0 = values[i];
  const q1 = values[i + 1];

  return q0.clone().slerp(q1, s);
}

export function sampleAnimationCurve(
  track: THREE.KeyframeTrack,
  time: number
): number[] {
  const times = track.times;
  const values = track.values;
  const valueSize = track.getValueSize();

  if (times.length === 0) return [];
  if (time <= times[0]) {
    return Array.from(values.slice(0, valueSize));
  }
  if (time >= times[times.length - 1]) {
    return Array.from(values.slice(-valueSize));
  }

  let leftIndex = 0;
  let rightIndex = times.length - 1;

  while (leftIndex <= rightIndex) {
    const mid = Math.floor((leftIndex + rightIndex) / 2);
    if (times[mid] < time) {
      leftIndex = mid + 1;
    } else if (times[mid] > time) {
      rightIndex = mid - 1;
    } else {
      return Array.from(values.slice(mid * valueSize, (mid + 1) * valueSize));
    }
  }

  leftIndex = Math.max(0, Math.min(leftIndex - 1, times.length - 2));
  rightIndex = leftIndex + 1;

  const t0 = times[leftIndex];
  const t1 = times[rightIndex];
  const result: number[] = [];

  for (let i = 0; i < valueSize; i++) {
    const v0 = values[leftIndex * valueSize + i];
    const v1 = values[rightIndex * valueSize + i];
    result.push(interpolateNumber(time, t0, t1, v0, v1, track.getInterpolation()));
  }

  return result;
}

export function sampleAnimationClip(
  clip: THREE.AnimationClip,
  time: number,
  trackName?: string
): Map<string, number[]> {
  const results = new Map<string, number[]>();
  const normalizedTime = ((time % clip.duration) + clip.duration) % clip.duration;

  clip.tracks.forEach((track) => {
    if (trackName && track.name !== trackName) return;
    results.set(track.name, sampleAnimationCurve(track, normalizedTime));
  });

  return results;
}

export function calculateBlendWeight(
  currentTime: number,
  blendDuration: number,
  blendStart: number = 0,
  easeIn: boolean = true,
  easeOut: boolean = true
): number {
  const progress = Math.max(0, Math.min(1, (currentTime - blendStart) / blendDuration));

  if (easeIn && easeOut) {
    return progress < 0.5
      ? 2 * progress * progress
      : 1 - Math.pow(-2 * progress + 2, 2) / 2;
  } else if (easeIn) {
    return progress * progress;
  } else if (easeOut) {
    return 1 - Math.pow(1 - progress, 2);
  }

  return progress;
}

export function normalizeWeights(weights: number[]): number[] {
  const sum = weights.reduce((a, b) => a + b, 0);
  if (sum === 0) return weights.map(() => 0);
  return weights.map((w) => w / sum);
}

export function blendValues(
  valueSets: number[][],
  weights: number[]
): number[] {
  if (valueSets.length === 0) return [];
  if (valueSets.length === 1) return valueSets[0];

  const normalizedWeights = normalizeWeights(weights);
  const result = new Array(valueSets[0].length).fill(0);

  for (let i = 0; i < valueSets.length; i++) {
    const values = valueSets[i];
    const weight = normalizedWeights[i];
    for (let j = 0; j < values.length; j++) {
      result[j] += values[j] * weight;
    }
  }

  return result;
}

export function blendVector3(
  vectors: THREE.Vector3[],
  weights: number[]
): THREE.Vector3 {
  const valueSets = vectors.map((v) => [v.x, v.y, v.z]);
  const result = blendValues(valueSets, weights);
  return new THREE.Vector3(result[0], result[1], result[2]);
}

export function blendQuaternions(
  quaternions: THREE.Quaternion[],
  weights: number[]
): THREE.Quaternion {
  if (quaternions.length === 0) return new THREE.Quaternion();
  if (quaternions.length === 1) return quaternions[0].clone();

  const normalizedWeights = normalizeWeights(weights);
  const result = new THREE.Quaternion().copy(quaternions[0]);

  for (let i = 1; i < quaternions.length; i++) {
    const weight = normalizedWeights[i];
    if (weight > 0) {
      result.slerp(quaternions[i], weight / (normalizedWeights.slice(0, i + 1).reduce((a, b) => a + b, 0)));
    }
  }

  return result.normalize();
}

export function getTrackByName(
  clip: THREE.AnimationClip,
  name: string
): THREE.KeyframeTrack | undefined {
  return clip.tracks.find((track) => track.name === name);
}

export function getTrackTargetName(trackName: string): string {
  const parts = trackName.split('.');
  return parts[0];
}

export function getTrackPropertyName(trackName: string): string {
  const parts = trackName.split('.');
  return parts.length > 1 ? parts.slice(1).join('.') : '';
}

export function extractKeyframeData(track: THREE.KeyframeTrack): KeyframeData {
  return {
    times: Array.from(track.times),
    values: Array.from(track.values),
    interpolation: track.getInterpolation(),
  };
}

export function applyAnimationToBone(
  bone: THREE.Bone,
  positionTrack?: THREE.KeyframeTrack,
  quaternionTrack?: THREE.KeyframeTrack,
  scaleTrack?: THREE.KeyframeTrack,
  time: number = 0,
  weight: number = 1
): void {
  if (weight <= 0) return;

  if (positionTrack) {
    const values = sampleAnimationCurve(positionTrack, time);
    if (values.length >= 3) {
      const targetPos = new THREE.Vector3(values[0], values[1], values[2]);
      bone.position.lerp(targetPos, weight);
    }
  }

  if (quaternionTrack) {
    const values = sampleAnimationCurve(quaternionTrack, time);
    if (values.length >= 4) {
      const targetQuat = new THREE.Quaternion(values[0], values[1], values[2], values[3]);
      bone.quaternion.slerp(targetQuat, weight);
    }
  }

  if (scaleTrack) {
    const values = sampleAnimationCurve(scaleTrack, time);
    if (values.length >= 3) {
      const targetScale = new THREE.Vector3(values[0], values[1], values[2]);
      bone.scale.lerp(targetScale, weight);
    }
  }
}

export function clipTime(
  time: number,
  duration: number,
  loop: THREE.AnimationActionLoopStyles = THREE.LoopRepeat
): number {
  switch (loop) {
    case THREE.LoopOnce:
      return Math.min(Math.max(0, time), duration);
    case THREE.LoopRepeat:
      return ((time % duration) + duration) % duration;
    case THREE.LoopPingPong: {
      const t = ((time % (duration * 2)) + duration * 2) % (duration * 2);
      return t <= duration ? t : duration * 2 - t;
    }
    default:
      return time;
  }
}
