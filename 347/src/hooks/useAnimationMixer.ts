import { useEffect, useRef, useCallback } from 'react';
import * as THREE from 'three';
import { useEditorStore } from '../store/editorStore';
import { calculateBlendWeight } from '../utils/three/AnimationUtils';

interface AnimationActionState {
  walk: THREE.AnimationAction | null;
  run: THREE.AnimationAction | null;
  [key: string]: THREE.AnimationAction | null;
}

export function useAnimationMixer(model: THREE.Group | null) {
  const mixerRef = useRef<THREE.AnimationMixer | null>(null);
  const actionsRef = useRef<AnimationActionState>({
    walk: null,
    run: null,
  });
  const clockRef = useRef<THREE.Clock>(new THREE.Clock());
  const animationFrameRef = useRef<number | null>(null);

  const {
    isPlaying,
    playbackSpeed,
    blendState,
    currentTime,
    setCurrentTime,
    animationClips,
  } = useEditorStore();

  const setupMixer = useCallback(() => {
    if (!model) return;

    mixerRef.current = new THREE.AnimationMixer(model);
    const clips = mixerRef.current._clipLibrary || [];

    actionsRef.current.walk = null;
    actionsRef.current.run = null;

    clips.forEach((clip: THREE.AnimationClip) => {
      const action = mixerRef.current?.clipAction(clip);
      const clipName = clip.name.toLowerCase();

      if (clipName.includes('walk')) {
        actionsRef.current.walk = action || null;
      } else if (clipName.includes('run')) {
        actionsRef.current.run = action || null;
      }

      if (action) {
        action.setLoop(THREE.LoopRepeat);
        action.clampWhenFinished = true;
        action.enabled = true;
      }
    });

    if (animationClips.length > 0) {
      animationClips.forEach((storeClip) => {
        const threeClip = convertToThreeClip(storeClip);
        const existing = mixerRef.current?._clipLibrary?.find(
          (c: THREE.AnimationClip) => c.name === threeClip.name
        );
        if (!existing) {
          mixerRef.current?.clipAction(threeClip);
        }
      });
    }

    Object.values(actionsRef.current).forEach((action) => {
      if (action) {
        action.setEffectiveWeight(0);
        action.play();
      }
    });
  }, [model, animationClips]);

  useEffect(() => {
    setupMixer();

    return () => {
      if (mixerRef.current) {
        mixerRef.current.stopAllAction();
        mixerRef.current.uncacheRoot(model);
      }
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [setupMixer, model]);

  useEffect(() => {
    if (!mixerRef.current) return;

    const animate = () => {
      const delta = clockRef.current.getDelta();

      if (isPlaying && mixerRef.current) {
        mixerRef.current.update(delta * playbackSpeed);
        setCurrentTime(mixerRef.current.time);
      }

      updateBlendWeights();

      animationFrameRef.current = requestAnimationFrame(animate);
    };

    animate();

    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [isPlaying, playbackSpeed, setCurrentTime, updateBlendWeights]);

  useEffect(() => {
    if (mixerRef.current && !isPlaying) {
      mixerRef.current.time = currentTime;
      mixerRef.current.update(0);
    }
  }, [currentTime, isPlaying]);

  const updateBlendWeights = useCallback(() => {
    const { walkWeight, runWeight, transitionSpeed } = blendState;

    const walkAction = actionsRef.current.walk;
    const runAction = actionsRef.current.run;

    if (walkAction) {
      const currentWeight = walkAction.getEffectiveWeight();
      const targetWeight = walkWeight;
      const blendedWeight = calculateBlendWeight(
        1,
        transitionSpeed,
        0,
        true,
        true
      ) * targetWeight;
      walkAction.setEffectiveWeight(
        currentWeight + (blendedWeight - currentWeight) * 0.1
      );
    }

    if (runAction) {
      const currentWeight = runAction.getEffectiveWeight();
      const targetWeight = runWeight;
      const blendedWeight = calculateBlendWeight(
        1,
        transitionSpeed,
        0,
        true,
        true
      ) * targetWeight;
      runAction.setEffectiveWeight(
        currentWeight + (blendedWeight - currentWeight) * 0.1
      );
    }
  }, [blendState]);

  const play = useCallback(() => {
    if (!mixerRef.current) return;
    Object.values(actionsRef.current).forEach((action) => {
      if (action) action.paused = false;
    });
    useEditorStore.getState().togglePlay();
  }, []);

  const pause = useCallback(() => {
    if (!mixerRef.current) return;
    Object.values(actionsRef.current).forEach((action) => {
      if (action) action.paused = true;
    });
    useEditorStore.getState().togglePlay();
  }, []);

  const stop = useCallback(() => {
    if (!mixerRef.current) return;
    mixerRef.current.stopAllAction();
    setCurrentTime(0);
  }, [setCurrentTime]);

  const setTime = useCallback((time: number) => {
    if (!mixerRef.current) return;
    mixerRef.current.time = time;
    mixerRef.current.update(0);
    setCurrentTime(time);
  }, [setCurrentTime]);

  const setAnimationWeight = useCallback((type: 'walk' | 'run', weight: number) => {
    const clampedWeight = Math.max(0, Math.min(1, weight));
    const action = actionsRef.current[type];
    if (action) {
      action.setEffectiveWeight(clampedWeight);
    }
    useEditorStore.getState().setBlendWeight(type, clampedWeight);
  }, []);

  const crossFade = useCallback((from: 'walk' | 'run', to: 'walk' | 'run', duration: number) => {
    const fromAction = actionsRef.current[from];
    const toAction = actionsRef.current[to];

    if (fromAction && toAction) {
      fromAction.crossFadeTo(toAction, duration, true);
    }
  }, []);

  const getAvailableAnimations = useCallback((): string[] => {
    if (!mixerRef.current) return [];
    return mixerRef.current._clipLibrary?.map((clip: THREE.AnimationClip) => clip.name) || [];
  }, []);

  const getDuration = useCallback((): number => {
    if (!mixerRef.current || !mixerRef.current._clipLibrary) return 0;
    const clips = mixerRef.current._clipLibrary as THREE.AnimationClip[];
    return Math.max(...clips.map((c) => c.duration));
  }, []);

  return {
    mixer: mixerRef.current,
    play,
    pause,
    stop,
    setTime,
    setAnimationWeight,
    crossFade,
    getAvailableAnimations,
    getDuration,
  };
}

function convertToThreeClip(storeClip: {
  name: string;
  duration: number;
  tracks: {
    boneUuid: string;
    property: 'position' | 'rotation' | 'scale';
    component: 'x' | 'y' | 'z' | 'w';
    keyframes: { time: number; value: number[] }[];
  }[];
}): THREE.AnimationClip {
  const trackMap = new Map<string, { times: number[]; values: number[] }>();

  storeClip.tracks.forEach((track) => {
    const trackName = `${track.boneUuid}.${track.property}`;
    if (!trackMap.has(trackName)) {
      trackMap.set(trackName, { times: [], values: [] });
    }

    const trackData = trackMap.get(trackName)!;
    const componentIndex = ['x', 'y', 'z', 'w'].indexOf(track.component);

    track.keyframes.forEach((keyframe) => {
      let timeIndex = trackData.times.indexOf(keyframe.time);
      if (timeIndex === -1) {
        timeIndex = trackData.times.length;
        trackData.times.push(keyframe.time);
        const valueSize = track.property === 'rotation' ? 4 : 3;
        trackData.values.push(...new Array(valueSize).fill(0));
      }

      const valueSize = track.property === 'rotation' ? 4 : 3;
      trackData.values[timeIndex * valueSize + componentIndex] = keyframe.value[0];
    });
  });

  const threeTracks: THREE.KeyframeTrack[] = [];
  trackMap.forEach((data, name) => {
    const property = name.split('.')[1];
    const sortedTimes = [...data.times].sort((a, b) => a - b);
    const sortedValues: number[] = [];
    const valueSize = property === 'rotation' ? 4 : 3;

    sortedTimes.forEach((time) => {
      const originalIdx = data.times.indexOf(time);
      sortedValues.push(...data.values.slice(originalIdx * valueSize, (originalIdx + 1) * valueSize));
    });

    if (property === 'position') {
      threeTracks.push(new THREE.VectorKeyframeTrack(name, sortedTimes, sortedValues));
    } else if (property === 'rotation') {
      threeTracks.push(new THREE.QuaternionKeyframeTrack(name, sortedTimes, sortedValues));
    } else if (property === 'scale') {
      threeTracks.push(new THREE.VectorKeyframeTrack(name, sortedTimes, sortedValues));
    }
  });

  return new THREE.AnimationClip(storeClip.name, storeClip.duration, threeTracks);
}
