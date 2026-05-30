import { create } from 'zustand';
import type {
  SceneObject,
  LightConfig,
  SceneData,
  ViewMode,
  TransformMode,
  ObjectType,
  MaterialConfig,
  PhysicsConfig,
  AnimationConfig,
  AnimationClipConfig,
} from '../types/scene';
import { DEFAULT_PHYSICS, DEFAULT_ANIMATION } from '../types/scene';

interface SceneState {
  objects: SceneObject[];
  lights: LightConfig[];
  selectedObjectId: string | null;
  backgroundColor: string;
  fog: {
    enabled: boolean;
    color: string;
    near: number;
    far: number;
  };
  viewMode: ViewMode;
  transformMode: TransformMode;
  isPreviewMode: boolean;
  showNormalMaps: boolean;
  physicsEnabled: boolean;
  gravity: [number, number, number];

  addObject: (type: ObjectType, position?: [number, number, number]) => void;
  removeObject: (id: string) => void;
  updateObject: (id: string, updates: Partial<SceneObject>) => void;
  selectObject: (id: string | null) => void;
  updateObjectMaterial: (id: string, material: Partial<MaterialConfig>) => void;
  updateObjectPhysics: (id: string, physics: Partial<PhysicsConfig>) => void;
  updateObjectAnimation: (id: string, animation: Partial<AnimationConfig>) => void;
  addAnimationClip: (id: string, clip: AnimationClipConfig) => void;
  removeAnimationClip: (id: string, clipName: string) => void;

  addLight: (type: LightConfig['type']) => void;
  updateLight: (id: string, updates: Partial<LightConfig>) => void;
  removeLight: (id: string) => void;

  setViewMode: (mode: ViewMode) => void;
  setTransformMode: (mode: TransformMode) => void;
  setBackgroundColor: (color: string) => void;
  setFog: (fog: Partial<SceneState['fog']>) => void;
  togglePreviewMode: () => void;
  setShowNormalMaps: (show: boolean) => void;
  setPhysicsEnabled: (enabled: boolean) => void;
  setGravity: (gravity: [number, number, number]) => void;

  exportScene: () => SceneData;
  importScene: (data: SceneData) => void;
  clearScene: () => void;
  applyTemplate: (data: SceneData) => void;
}

const generateId = () => Math.random().toString(36).substr(2, 9);

const defaultLights: LightConfig[] = [
  { id: 'default-ambient', type: 'ambient', color: '#ffffff', intensity: 0.4 },
  {
    id: 'default-directional-1',
    type: 'directional',
    color: '#ffffff',
    intensity: 1,
    position: [5, 5, 5],
  },
  {
    id: 'default-directional-2',
    type: 'directional',
    color: '#ffffff',
    intensity: 0.5,
    position: [-5, 3, -5],
  },
];

export const useSceneStore = create<SceneState>((set, get) => ({
  objects: [],
  lights: defaultLights,
  selectedObjectId: null,
  backgroundColor: '#1a1a2e',
  fog: {
    enabled: true,
    color: '#1a1a2e',
    near: 10,
    far: 50,
  },
  viewMode: 'perspective',
  transformMode: 'translate',
  isPreviewMode: false,
  showNormalMaps: true,
  physicsEnabled: false,
  gravity: [0, -9.81, 0],

  addObject: (type, position = [0, 0, 0]) => {
    const newObject: SceneObject = {
      id: generateId(),
      name: `${type}-${Date.now()}`,
      type,
      position,
      rotation: [0, 0, 0],
      scale: [1, 1, 1],
      material: {
        color: '#3b82f6',
        metalness: 0.1,
        roughness: 0.5,
        emissive: '#000000',
        emissiveIntensity: 0,
        normalMapUrl: '',
        normalScale: 1,
      },
      physics: { ...DEFAULT_PHYSICS },
      animation: { ...DEFAULT_ANIMATION },
    };
    set((state) => ({
      objects: [...state.objects, newObject],
      selectedObjectId: newObject.id,
    }));
  },

  removeObject: (id) => {
    set((state) => ({
      objects: state.objects.filter((obj) => obj.id !== id),
      selectedObjectId: state.selectedObjectId === id ? null : state.selectedObjectId,
    }));
  },

  updateObject: (id, updates) => {
    set((state) => ({
      objects: state.objects.map((obj) =>
        obj.id === id ? { ...obj, ...updates } : obj
      ),
    }));
  },

  selectObject: (id) => {
    set({ selectedObjectId: id });
  },

  updateObjectMaterial: (id, material) => {
    set((state) => ({
      objects: state.objects.map((obj) =>
        obj.id === id
          ? { ...obj, material: { ...obj.material, ...material } }
          : obj
      ),
    }));
  },

  updateObjectPhysics: (id, physics) => {
    set((state) => ({
      objects: state.objects.map((obj) =>
        obj.id === id
          ? { ...obj, physics: { ...obj.physics, ...physics } }
          : obj
      ),
    }));
  },

  updateObjectAnimation: (id, animation) => {
    set((state) => ({
      objects: state.objects.map((obj) =>
        obj.id === id
          ? { ...obj, animation: { ...obj.animation, ...animation } }
          : obj
      ),
    }));
  },

  addAnimationClip: (id, clip) => {
    set((state) => ({
      objects: state.objects.map((obj) =>
        obj.id === id
          ? {
              ...obj,
              animation: {
                ...obj.animation,
                clips: [...obj.animation.clips, clip],
              },
            }
          : obj
      ),
    }));
  },

  removeAnimationClip: (id, clipName) => {
    set((state) => ({
      objects: state.objects.map((obj) =>
        obj.id === id
          ? {
              ...obj,
              animation: {
                ...obj.animation,
                clips: obj.animation.clips.filter((c) => c.name !== clipName),
              },
            }
          : obj
      ),
    }));
  },

  addLight: (type) => {
    const newLight: LightConfig = {
      id: generateId(),
      type,
      color: '#ffffff',
      intensity: 0.5,
      position: type === 'ambient' ? undefined : [0, 3, 0],
    };
    set((state) => ({
      lights: [...state.lights, newLight],
    }));
  },

  updateLight: (id, updates) => {
    set((state) => ({
      lights: state.lights.map((light) =>
        light.id === id ? { ...light, ...updates } : light
      ),
    }));
  },

  removeLight: (id) => {
    set((state) => ({
      lights: state.lights.filter((light) => light.id !== id),
    }));
  },

  setViewMode: (mode) => {
    set({ viewMode: mode });
  },

  setTransformMode: (mode) => {
    set({ transformMode: mode });
  },

  setBackgroundColor: (color) => {
    set({ backgroundColor: color });
  },

  setFog: (fog) => {
    set((state) => ({
      fog: { ...state.fog, ...fog },
    }));
  },

  togglePreviewMode: () => {
    set((state) => ({ isPreviewMode: !state.isPreviewMode }));
  },

  setShowNormalMaps: (show) => {
    set({ showNormalMaps: show });
  },

  setPhysicsEnabled: (enabled) => {
    set({ physicsEnabled: enabled });
  },

  setGravity: (gravity) => {
    set({ gravity });
  },

  exportScene: () => {
    const state = get();
    return {
      objects: state.objects,
      lights: state.lights,
      backgroundColor: state.backgroundColor,
      fog: state.fog,
    };
  },

  importScene: (data) => {
    set({
      objects: data.objects.map((obj) => ({
        ...obj,
        material: {
          normalMapUrl: '',
          normalScale: 1,
          ...obj.material,
        },
        physics: { ...DEFAULT_PHYSICS, ...obj.physics },
        animation: { ...DEFAULT_ANIMATION, ...obj.animation },
      })),
      lights: data.lights,
      backgroundColor: data.backgroundColor,
      fog: data.fog,
      selectedObjectId: null,
    });
  },

  clearScene: () => {
    set({
      objects: [],
      selectedObjectId: null,
    });
  },

  applyTemplate: (data) => {
    set({
      objects: data.objects.map((obj) => ({
        ...obj,
        id: generateId(),
        physics: { ...DEFAULT_PHYSICS, ...obj.physics },
        animation: { ...DEFAULT_ANIMATION, ...obj.animation },
      })),
      lights: data.lights.map((l) => ({ ...l, id: generateId() })),
      backgroundColor: data.backgroundColor,
      fog: data.fog,
      selectedObjectId: null,
    });
  },
}));
