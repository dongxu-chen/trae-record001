export type ObjectType = 'box' | 'sphere' | 'gltf';

export type LightType = 'ambient' | 'directional' | 'point';

export interface MaterialConfig {
  color: string;
  metalness: number;
  roughness: number;
  emissive: string;
  emissiveIntensity: number;
  normalMapUrl: string;
  normalScale: number;
}

export interface PhysicsConfig {
  enabled: boolean;
  bodyType: 'dynamic' | 'fixed' | 'kinematic';
  mass: number;
  restitution: number;
  friction: number;
  linearDamping: number;
  angularDamping: number;
}

export interface AnimationClipConfig {
  name: string;
  start: number;
  end: number;
  loop: boolean;
  speed: number;
}

export interface AnimationConfig {
  enabled: boolean;
  currentClip: string;
  clips: AnimationClipConfig[];
  isPlaying: boolean;
  timeScale: number;
}

export interface SceneObject {
  id: string;
  name: string;
  type: ObjectType;
  position: [number, number, number];
  rotation: [number, number, number];
  scale: [number, number, number];
  material: MaterialConfig;
  physics: PhysicsConfig;
  animation: AnimationConfig;
  gltfUrl?: string;
}

export interface LightConfig {
  id: string;
  type: LightType;
  color: string;
  intensity: number;
  position?: [number, number, number];
}

export interface FogConfig {
  enabled: boolean;
  color: string;
  near: number;
  far: number;
}

export interface SceneData {
  objects: SceneObject[];
  lights: LightConfig[];
  backgroundColor: string;
  fog: FogConfig;
}

export type ViewMode = 'perspective' | 'front' | 'top' | 'side';

export type TransformMode = 'translate' | 'rotate' | 'scale';

export interface CameraPreset {
  position: [number, number, number];
  target: [number, number, number];
}

export interface SceneTemplate {
  id: string;
  name: string;
  description: string;
  icon: string;
  category: 'indoor' | 'outdoor';
  data: SceneData;
}

export const DEFAULT_PHYSICS: PhysicsConfig = {
  enabled: false,
  bodyType: 'dynamic',
  mass: 1,
  restitution: 0.3,
  friction: 0.5,
  linearDamping: 0.1,
  angularDamping: 0.1,
};

export const DEFAULT_ANIMATION: AnimationConfig = {
  enabled: false,
  currentClip: '',
  clips: [],
  isPlaying: false,
  timeScale: 1,
};
