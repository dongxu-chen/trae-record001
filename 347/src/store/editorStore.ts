import { create } from 'zustand';
import { produce } from 'immer';
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { FBXLoader } from 'three/addons/loaders/FBXLoader.js';
import type { BoneNode } from '../types/skeleton';
import type { AnimationClip, Keyframe, BlendState, IKTarget, IKState, RetargetState, BVHImportState } from '../types/animation';
import { createSampleModel } from '../utils/three/SampleModelGenerator';
import { BVHParser, BVHConverter } from '../utils/three/BVHLoader';
import { AnimationRetargetter, BoneMapper, SkeletonUtils } from '../utils/three/Retargetter';

type TransformMode = 'translate' | 'rotate' | 'scale';
type MeshDisplayMode = 'solid' | 'wireframe' | 'transparent';
type LoopMode = 'once' | 'loop' | 'pingpong';

interface EditorStore {
  model: THREE.Group | null;
  skeleton: BoneNode[];
  animationClips: AnimationClip[];
  selectedBoneUuid: string | null;
  currentTime: number;
  isPlaying: boolean;
  playbackSpeed: number;
  loopMode: LoopMode;
  frameRate: number;
  transformMode: TransformMode;
  blendState: BlendState;
  showSkeleton: boolean;
  showMesh: boolean;
  meshDisplayMode: MeshDisplayMode;
  ikState: IKState;
  retargetState: RetargetState;
  bvhImportState: BVHImportState | null;
  importedAnimations: Array<{ uuid: string; name: string; source: 'FBX' | 'GLB' | 'BVH'; duration: number; boneCount: number }>;
  setSelectedBone: (uuid: string | null) => void;
  setCurrentTime: (time: number) => void;
  togglePlay: () => void;
  setPlaybackSpeed: (speed: number) => void;
  setLoopMode: (mode: LoopMode) => void;
  nextFrame: () => void;
  prevFrame: () => void;
  stop: () => void;
  setTransformMode: (mode: TransformMode) => void;
  getDuration: () => number;
  updateBoneTransform: (uuid: string, property: 'position' | 'rotation' | 'scale', value: number[]) => void;
  addKeyframe: (boneUuid: string, property: 'position' | 'rotation' | 'scale', component: 'x' | 'y' | 'z' | 'w', time: number, value: number[]) => void;
  updateKeyframe: (clipUuid: string, trackIndex: number, keyframeIndex: number, keyframe: Keyframe) => void;
  deleteKeyframe: (clipUuid: string, trackIndex: number, keyframeIndex: number) => void;
  setBlendWeight: (type: 'walk' | 'run', weight: number) => void;
  normalizeBlendWeights: () => void;
  setBlendWeights: (weights: { walk?: number; run?: number }) => void;
  toggleSkeleton: () => void;
  toggleMesh: () => void;
  setMeshDisplayMode: (mode: MeshDisplayMode) => void;
  loadModel: (file: File) => Promise<void>;
  loadSampleModel: () => void;
  clearModel: () => void;
  addIKTarget: (target: IKTarget) => void;
  removeIKTarget: (id: string) => void;
  updateIKTarget: (id: string, updates: Partial<IKTarget>) => void;
  setIKTargetEnabled: (id: string, enabled: boolean) => void;
  setActiveIKTarget: (id: string | null) => void;
  setIKSolverType: (type: 'FABRIK' | 'CCD') => void;
  toggleShowIKTargets: () => void;
  importBVH: (file: File) => Promise<void>;
  setBVHImportScale: (scale: number) => void;
  setRetargetScale: (scale: number) => void;
  setRetargetMirror: (mirror: boolean) => void;
  setRetargetPreservePosition: (preserve: boolean) => void;
  setAutoBoneMapping: (auto: boolean) => void;
  performRetarget: (sourceClipUuid: string) => void;
}

const extractSkeleton = (group: THREE.Group): BoneNode[] => {
  const bones: BoneNode[] = [];
  const boneMap = new Map<string, THREE.Bone>();

  group.traverse((obj) => {
    if (obj instanceof THREE.Bone) {
      boneMap.set(obj.uuid, obj);
    }
  });

  let boneIndex = 0;
  boneMap.forEach((bone) => {
    const parentUuid = bone.parent instanceof THREE.Bone ? bone.parent.uuid : null;
    const childrenUuids: string[] = [];
    bone.children.forEach((child) => {
      if (child instanceof THREE.Bone) {
        childrenUuids.push(child.uuid);
      }
    });

    bones.push({
      uuid: bone.uuid,
      name: bone.name,
      parentUuid,
      children: childrenUuids,
      position: [bone.position.x, bone.position.y, bone.position.z],
      rotation: [bone.quaternion.x, bone.quaternion.y, bone.quaternion.z, bone.quaternion.w],
      scale: [bone.scale.x, bone.scale.y, bone.scale.z],
      boneIndex: boneIndex++,
    });
  });

  return bones;
};

const convertAnimationClips = (clips: THREE.AnimationClip[]): AnimationClip[] => {
  return clips.map((clip) => ({
    uuid: THREE.MathUtils.generateUUID(),
    name: clip.name,
    duration: clip.duration,
    tracks: clip.tracks.flatMap((track) => {
      const property = track.name.split('.')[1] as 'position' | 'rotation' | 'scale';
      const components: ('x' | 'y' | 'z' | 'w')[] = track.values.length / track.times.length === 4
        ? ['x', 'y', 'z', 'w']
        : ['x', 'y', 'z'];

      return components.map((component, compIndex) => {
        const keyframes: Keyframe[] = [];
        const valueStride = track.values.length / track.times.length;

        for (let i = 0; i < track.times.length; i++) {
          const valueIndex = i * valueStride + compIndex;
          keyframes.push({
            time: track.times[i],
            value: [track.values[valueIndex]],
            interpolation: 'linear',
          });
        }

        return {
          boneUuid: track.name.split('.')[0],
          property,
          component,
          keyframes,
        };
      });
    }),
  }));
};

export const useEditorStore = create<EditorStore>((set, get) => ({
  model: null,
  skeleton: [],
  animationClips: [],
  selectedBoneUuid: null,
  currentTime: 0,
  isPlaying: false,
  playbackSpeed: 1,
  loopMode: 'loop',
  frameRate: 30,
  transformMode: 'translate',
  blendState: {
    walkWeight: 0,
    runWeight: 0,
    transitionSpeed: 0.1,
  },
  showSkeleton: true,
  showMesh: true,
  meshDisplayMode: 'solid',
  ikState: {
    targets: [],
    activeTargetId: null,
    showTargets: true,
    solverType: 'FABRIK',
  },
  retargetState: {
    sourceSkeleton: null,
    targetSkeleton: null,
    boneMapping: [],
    scaleFactor: 1,
    mirror: false,
    preservePosition: true,
    autoMapping: true,
  },
  bvhImportState: null,
  importedAnimations: [],

  setSelectedBone: (uuid) => set({ selectedBoneUuid: uuid }),

  setCurrentTime: (time) => {
    const duration = get().getDuration();
    const clampedTime = Math.max(0, Math.min(time, duration));
    set({ currentTime: clampedTime });
  },

  togglePlay: () => set((state) => ({ isPlaying: !state.isPlaying })),

  setPlaybackSpeed: (speed) => set({ playbackSpeed: Math.max(0.25, Math.min(4, speed)) }),

  setLoopMode: (mode) => set({ loopMode: mode }),

  nextFrame: () => {
    const { currentTime, frameRate, setCurrentTime } = get();
    setCurrentTime(currentTime + 1 / frameRate);
  },

  prevFrame: () => {
    const { currentTime, frameRate, setCurrentTime } = get();
    setCurrentTime(currentTime - 1 / frameRate);
  },

  stop: () => set({ currentTime: 0, isPlaying: false }),

  getDuration: () => {
    const { animationClips } = get();
    if (animationClips.length === 0) return 10;
    return Math.max(...animationClips.map((clip) => clip.duration), 10);
  },

  setTransformMode: (mode) => set({ transformMode: mode }),

  updateBoneTransform: (uuid, property, value) =>
    set(
      produce((state: EditorStore) => {
        const bone = state.skeleton.find((b) => b.uuid === uuid);
        if (bone) {
          (bone[property] as number[]) = [...value];
        }

        if (state.model) {
          const threeBone = state.model.getObjectByProperty('uuid', uuid);
          if (threeBone instanceof THREE.Bone) {
            if (property === 'position') {
              threeBone.position.set(value[0], value[1], value[2]);
            } else if (property === 'rotation') {
              threeBone.quaternion.set(value[0], value[1], value[2], value[3]);
            } else if (property === 'scale') {
              threeBone.scale.set(value[0], value[1], value[2]);
            }
          }
        }
      })
    ),

  addKeyframe: (boneUuid, property, component, time, value) =>
    set(
      produce((state: EditorStore) => {
        if (state.animationClips.length === 0) {
          state.animationClips.push({
            uuid: THREE.MathUtils.generateUUID(),
            name: 'New Clip',
            duration: time,
            tracks: [],
          });
        }

        const clip = state.animationClips[0];
        let track = clip.tracks.find(
          (t) => t.boneUuid === boneUuid && t.property === property && t.component === component
        );

        if (!track) {
          track = {
            boneUuid,
            property,
            component,
            keyframes: [],
          };
          clip.tracks.push(track);
        }

        const keyframe: Keyframe = {
          time,
          value,
          interpolation: 'linear',
        };

        const insertIndex = track.keyframes.findIndex((k) => k.time > time);
        if (insertIndex === -1) {
          track.keyframes.push(keyframe);
        } else {
          track.keyframes.splice(insertIndex, 0, keyframe);
        }

        clip.duration = Math.max(clip.duration, time);
      })
    ),

  updateKeyframe: (clipUuid, trackIndex, keyframeIndex, keyframe) =>
    set(
      produce((state: EditorStore) => {
        const clip = state.animationClips.find((c) => c.uuid === clipUuid);
        if (clip && clip.tracks[trackIndex] && clip.tracks[trackIndex].keyframes[keyframeIndex]) {
          clip.tracks[trackIndex].keyframes[keyframeIndex] = keyframe;
        }
      })
    ),

  deleteKeyframe: (clipUuid, trackIndex, keyframeIndex) =>
    set(
      produce((state: EditorStore) => {
        const clip = state.animationClips.find((c) => c.uuid === clipUuid);
        if (clip && clip.tracks[trackIndex]) {
          clip.tracks[trackIndex].keyframes.splice(keyframeIndex, 1);
        }
      })
    ),

  setBlendWeight: (type, weight) =>
    set(
      produce((state: EditorStore) => {
        const clampedWeight = Math.max(0, Math.min(1, weight));
        
        if (type === 'walk') {
          state.blendState.walkWeight = clampedWeight;
          state.blendState.runWeight = 1 - clampedWeight;
        } else if (type === 'run') {
          state.blendState.runWeight = clampedWeight;
          state.blendState.walkWeight = 1 - clampedWeight;
        }
      })
    ),

  normalizeBlendWeights: () =>
    set(
      produce((state: EditorStore) => {
        const total = state.blendState.walkWeight + state.blendState.runWeight;
        if (total > 0 && total !== 1) {
          state.blendState.walkWeight = state.blendState.walkWeight / total;
          state.blendState.runWeight = state.blendState.runWeight / total;
        } else if (total === 0) {
          state.blendState.walkWeight = 0.5;
          state.blendState.runWeight = 0.5;
        }
      })
    ),

  setBlendWeights: (weights: { walk?: number; run?: number }) =>
    set(
      produce((state: EditorStore) => {
        if (weights.walk !== undefined) {
          state.blendState.walkWeight = Math.max(0, Math.min(1, weights.walk));
        }
        if (weights.run !== undefined) {
          state.blendState.runWeight = Math.max(0, Math.min(1, weights.run));
        }

        const total = state.blendState.walkWeight + state.blendState.runWeight;
        if (total > 0 && total !== 1) {
          state.blendState.walkWeight = state.blendState.walkWeight / total;
          state.blendState.runWeight = state.blendState.runWeight / total;
        }
      })
    ),

  toggleSkeleton: () => set((state) => ({ showSkeleton: !state.showSkeleton })),

  toggleMesh: () => set((state) => ({ showMesh: !state.showMesh })),

  setMeshDisplayMode: (mode) => set({ meshDisplayMode: mode }),

  loadModel: async (file: File) => {
    const arrayBuffer = await file.arrayBuffer();
    const extension = file.name.split('.').pop()?.toLowerCase();

    let model: THREE.Group | null = null;
    let clips: THREE.AnimationClip[] = [];

    if (extension === 'glb' || extension === 'gltf') {
      const loader = new GLTFLoader();
      const gltf = await loader.parseAsync(arrayBuffer, '');
      model = gltf.scene;
      clips = gltf.animations || [];
    } else if (extension === 'fbx') {
      const loader = new FBXLoader();
      model = loader.parse(arrayBuffer, '');
      clips = model.animations || [];
    }

    if (!model) {
      throw new Error(`Unsupported file format: ${extension}`);
    }

    const skeleton = extractSkeleton(model);
    const animationClips = convertAnimationClips(clips);

    set({
      model,
      skeleton,
      animationClips,
      selectedBoneUuid: null,
      currentTime: 0,
      isPlaying: false,
    });
  },

  loadSampleModel: () => {
    const { clearModel } = get();
    clearModel();

    const { model, animations } = createSampleModel();
    const skeleton = extractSkeleton(model);
    const animationClips = convertAnimationClips(animations);

    set({
      model,
      skeleton,
      animationClips,
      selectedBoneUuid: null,
      currentTime: 0,
      isPlaying: false,
    });
  },

  clearModel: () => {
    const { model } = get();
    if (model) {
      model.traverse((obj) => {
        if (obj instanceof THREE.Mesh) {
          obj.geometry.dispose();
          if (Array.isArray(obj.material)) {
            obj.material.forEach((m) => m.dispose());
          } else {
            obj.material.dispose();
          }
        }
      });
    }

    set({
      model: null,
      skeleton: [],
      animationClips: [],
      selectedBoneUuid: null,
      currentTime: 0,
      isPlaying: false,
      ikState: {
        targets: [],
        activeTargetId: null,
        showTargets: true,
        solverType: 'FABRIK',
      },
      bvhImportState: null,
    });
  },

  addIKTarget: (target) =>
    set(
      produce((state: EditorStore) => {
        state.ikState.targets.push(target);
      })
    ),

  removeIKTarget: (id) =>
    set(
      produce((state: EditorStore) => {
        state.ikState.targets = state.ikState.targets.filter((t) => t.id !== id);
        if (state.ikState.activeTargetId === id) {
          state.ikState.activeTargetId = null;
        }
      })
    ),

  updateIKTarget: (id, updates) =>
    set(
      produce((state: EditorStore) => {
        const target = state.ikState.targets.find((t) => t.id === id);
        if (target) {
          Object.assign(target, updates);
        }
      })
    ),

  setIKTargetEnabled: (id, enabled) =>
    set(
      produce((state: EditorStore) => {
        const target = state.ikState.targets.find((t) => t.id === id);
        if (target) {
          target.enabled = enabled;
        }
      })
    ),

  setActiveIKTarget: (id) => set({ ikState: { ...get().ikState, activeTargetId: id } }),

  setIKSolverType: (type) => set({ ikState: { ...get().ikState, solverType: type } }),

  toggleShowIKTargets: () =>
    set((state) => ({ ikState: { ...state.ikState, showTargets: !state.ikState.showTargets } })),

  importBVH: async (file) => {
    const content = await file.text();
    const parser = new BVHParser();
    const bvhData = parser.parse(content);

    const { scale } = get().retargetState;
    const { skeleton } = BVHConverter.toSkeleton(bvhData, scale);
    const clip = BVHConverter.toAnimationClip(bvhData, scale);

    const jointNames = BVHConverter.getJointNames(bvhData);

    set({
      bvhImportState: {
        fileName: file.name,
        jointCount: jointNames.length,
        frameCount: bvhData.motion.frames,
        duration: bvhData.motion.frames * bvhData.motion.frameTime,
        scale,
        offset: [0, 0, 0],
      },
    });

    const clipUuid = THREE.MathUtils.generateUUID();
    const animationClip: AnimationClip = {
      uuid: clipUuid,
      name: file.name.replace('.bvh', ''),
      duration: clip.duration,
      tracks: clip.tracks.flatMap((track) => {
        const property = track.name.split('.')[1] as 'position' | 'rotation' | 'scale';
        const components: ('x' | 'y' | 'z' | 'w')[] = track.values.length / track.times.length === 4
          ? ['x', 'y', 'z', 'w']
          : ['x', 'y', 'z'];

        return components.map((component, compIndex) => {
          const keyframes: Keyframe[] = [];
          const valueStride = track.values.length / track.times.length;

          for (let i = 0; i < track.times.length; i++) {
            const valueIndex = i * valueStride + compIndex;
            keyframes.push({
              time: track.times[i],
              value: [track.values[valueIndex]],
              interpolation: 'spline',
            });
          }

          return {
            boneUuid: track.name.split('.')[0],
            property,
            component,
            keyframes,
          };
        });
      }),
    };

    set(
      produce((state: EditorStore) => {
        state.animationClips.push(animationClip);
        state.importedAnimations.push({
          uuid: clipUuid,
          name: animationClip.name,
          source: 'BVH',
          duration: clip.duration,
          boneCount: jointNames.length,
        });
      })
    );
  },

  setBVHImportScale: (scale) =>
    set(
      produce((state: EditorStore) => {
        if (state.bvhImportState) {
          state.bvhImportState.scale = scale;
        }
      })
    ),

  setRetargetScale: (scale) => set({ retargetState: { ...get().retargetState, scaleFactor: scale } }),

  setRetargetMirror: (mirror) => set({ retargetState: { ...get().retargetState, mirror } }),

  setRetargetPreservePosition: (preserve) =>
    set({ retargetState: { ...get().retargetState, preservePosition: preserve } }),

  setAutoBoneMapping: (auto) => set({ retargetState: { ...get().retargetState, autoMapping: auto } }),

  performRetarget: (sourceClipUuid) => {
    const { model, animationClips, retargetState } = get();
    if (!model) return;

    const sourceClip = animationClips.find((c) => c.uuid === sourceClipUuid);
    if (!sourceClip) return;

    let targetSkeleton: THREE.Skeleton | null = null;
    let sourceSkeleton: THREE.Skeleton | null = null;

    model.traverse((obj) => {
      if (obj instanceof THREE.SkinnedMesh && obj.skeleton) {
        targetSkeleton = obj.skeleton;
      }
    });

    if (!targetSkeleton) return;

    const sourceThreeClip = new THREE.AnimationClip(
      sourceClip.name,
      sourceClip.duration,
      sourceClip.tracks.map((track) => {
        const times = new Float32Array(track.keyframes.map((k) => k.time));
        const values = new Float32Array(
          track.keyframes.flatMap((k) => k.value)
        );

        if (track.property === 'rotation') {
          return new THREE.QuaternionKeyframeTrack(
            `${track.boneUuid}.quaternion`,
            times,
            values
          );
        } else {
          return new THREE.VectorKeyframeTrack(
            `${track.boneUuid}.${track.property}`,
            times,
            values
          );
        }
      })
    );

    const retargetOptions = {
      scale: retargetState.scaleFactor,
      offset: new THREE.Vector3(0, 0, 0),
      preservePosition: retargetState.preservePosition,
      preserveRotation: true,
      mirror: retargetState.mirror,
    };

    const retargetedClip = AnimationRetargetter.retargetClip(
      sourceThreeClip,
      targetSkeleton,
      targetSkeleton,
      retargetOptions
    );

    const retargetedClipData: AnimationClip = {
      uuid: THREE.MathUtils.generateUUID(),
      name: `${sourceClip.name}_retargeted`,
      duration: retargetedClip.duration,
      tracks: retargetedClip.tracks.flatMap((track) => {
        const property = track.name.split('.')[1] as 'position' | 'rotation' | 'scale';
        const components: ('x' | 'y' | 'z' | 'w')[] = track.values.length / track.times.length === 4
          ? ['x', 'y', 'z', 'w']
          : ['x', 'y', 'z'];

        return components.map((component, compIndex) => {
          const keyframes: Keyframe[] = [];
          const valueStride = track.values.length / track.times.length;

          for (let i = 0; i < track.times.length; i++) {
            const valueIndex = i * valueStride + compIndex;
            keyframes.push({
              time: track.times[i],
              value: [track.values[valueIndex]],
              interpolation: 'spline',
            });
          }

          return {
            boneUuid: track.name.split('.')[0],
            property,
            component,
            keyframes,
          };
        });
      }),
    };

    set(
      produce((state: EditorStore) => {
        state.animationClips.push(retargetedClipData);
        state.importedAnimations.push({
          uuid: retargetedClipData.uuid,
          name: retargetedClipData.name,
          source: 'BVH',
          duration: retargetedClip.duration,
          boneCount: targetSkeleton?.bones.length || 0,
        });
      })
    );
  },
}));
