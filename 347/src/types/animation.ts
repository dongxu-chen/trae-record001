export interface Keyframe {
  time: number;
  value: number[];
  interpolation: 'linear' | 'smooth' | 'step' | 'bezier' | 'spline';
  inTangent?: number[];
  outTangent?: number[];
}

export interface AnimationTrack {
  boneUuid: string;
  property: 'position' | 'rotation' | 'scale';
  component: 'x' | 'y' | 'z' | 'w';
  keyframes: Keyframe[];
}

export interface AnimationClip {
  uuid: string;
  name: string;
  duration: number;
  tracks: AnimationTrack[];
}

export interface BlendState {
  walkWeight: number;
  runWeight: number;
  transitionSpeed: number;
}

export interface IKTarget {
  id: string;
  name: string;
  type: 'foot' | 'hand' | 'custom';
  bonePath: string;
  position: [number, number, number];
  enabled: boolean;
  poleVector?: [number, number, number];
  weight: number;
  rotationOffset?: [number, number, number, number];
}

export interface IKState {
  targets: IKTarget[];
  activeTargetId: string | null;
  showTargets: boolean;
  solverType: 'FABRIK' | 'CCD';
}

export interface RetargetState {
  sourceSkeleton: string | null;
  targetSkeleton: string | null;
  boneMapping: { source: string; target: string }[];
  scaleFactor: number;
  mirror: boolean;
  preservePosition: boolean;
  autoMapping: boolean;
}

export interface BVHImportState {
  fileName: string;
  jointCount: number;
  frameCount: number;
  duration: number;
  scale: number;
  offset: [number, number, number];
}

export interface ImportedAnimation {
  uuid: string;
  name: string;
  source: 'FBX' | 'GLB' | 'BVH';
  clip: THREE.AnimationClip;
  boneCount: number;
  duration: number;
}
