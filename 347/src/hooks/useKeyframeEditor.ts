import { useState, useCallback, useMemo } from 'react';
import type { AnimationClip, AnimationTrack } from '../types/animation';
import { useEditorStore } from '../store/editorStore';
import { computeCubicSpline, evaluateCubicSpline, evaluateCubicSplineDerivative } from '../utils/math/CurveMath';

type CurveEditMode = 'select' | 'add' | 'delete' | 'move' | 'tangent';

interface SelectedKeyframe {
  clipUuid: string;
  trackIndex: number;
  keyframeIndex: number;
}

interface CurveEditorState {
  mode: CurveEditMode;
  selectedKeyframes: SelectedKeyframe[];
  selectedTrackIndices: number[];
  zoom: number;
  panOffset: { x: number; y: number };
  snapToGrid: boolean;
  gridSize: { x: number; y: number };
}

export function useKeyframeEditor() {
  const {
    animationClips,
    selectedBoneUuid,
    currentTime,
    addKeyframe,
    updateKeyframe,
    deleteKeyframe,
  } = useEditorStore();

  const [editorState, setEditorState] = useState<CurveEditorState>({
    mode: 'select',
    selectedKeyframes: [],
    selectedTrackIndices: [],
    zoom: 1,
    panOffset: { x: 0, y: 0 },
    snapToGrid: true,
    gridSize: { x: 0.1, y: 0.1 },
  });

  const activeClip = useMemo((): AnimationClip | null => {
    return animationClips.length > 0 ? animationClips[0] : null;
  }, [animationClips]);

  const filteredTracks = useMemo((): AnimationTrack[] => {
    if (!activeClip || !selectedBoneUuid) return activeClip?.tracks || [];
    return activeClip.tracks.filter((t) => t.boneUuid === selectedBoneUuid);
  }, [activeClip, selectedBoneUuid]);

  const addKeyframeAtTime = useCallback((
    boneUuid: string,
    property: 'position' | 'rotation' | 'scale',
    component: 'x' | 'y' | 'z' | 'w',
    time: number,
    value: number[]
  ) => {
    const snappedTime = editorState.snapToGrid
      ? Math.round(time / editorState.gridSize.x) * editorState.gridSize.x
      : time;

    addKeyframe(boneUuid, property, component, snappedTime, value);
  }, [addKeyframe, editorState.snapToGrid, editorState.gridSize.x]);

  const addKeyframeAtCurrentTime = useCallback((
    boneUuid: string,
    property: 'position' | 'rotation' | 'scale',
    component: 'x' | 'y' | 'z' | 'w',
    value: number[]
  ) => {
    addKeyframeAtTime(boneUuid, property, component, currentTime, value);
  }, [addKeyframeAtTime, currentTime]);

  const updateKeyframeValue = useCallback((
    clipUuid: string,
    trackIndex: number,
    keyframeIndex: number,
    value: number[]
  ) => {
    const clip = animationClips.find((c) => c.uuid === clipUuid);
    if (!clip || !clip.tracks[trackIndex] || !clip.tracks[trackIndex].keyframes[keyframeIndex]) return;

    const keyframe = clip.tracks[trackIndex].keyframes[keyframeIndex];
    updateKeyframe(clipUuid, trackIndex, keyframeIndex, {
      ...keyframe,
      value,
    });
  }, [animationClips, updateKeyframe]);

  const updateKeyframeTime = useCallback((
    clipUuid: string,
    trackIndex: number,
    keyframeIndex: number,
    time: number
  ) => {
    const clip = animationClips.find((c) => c.uuid === clipUuid);
    if (!clip || !clip.tracks[trackIndex] || !clip.tracks[trackIndex].keyframes[keyframeIndex]) return;

    const snappedTime = editorState.snapToGrid
      ? Math.round(time / editorState.gridSize.x) * editorState.gridSize.x
      : time;

    const keyframe = clip.tracks[trackIndex].keyframes[keyframeIndex];
    const track = clip.tracks[trackIndex];

    const insertIndex = track.keyframes.findIndex((k, i) =>
      i !== keyframeIndex && k.time > snappedTime
    );

    if (insertIndex !== -1 && insertIndex !== keyframeIndex + 1) {
      track.keyframes.splice(keyframeIndex, 1);
      const newIndex = insertIndex > keyframeIndex ? insertIndex - 1 : insertIndex;
      track.keyframes.splice(newIndex, 0, { ...keyframe, time: snappedTime });
    } else {
      updateKeyframe(clipUuid, trackIndex, keyframeIndex, {
        ...keyframe,
        time: snappedTime,
      });
    }
  }, [animationClips, updateKeyframe, editorState.snapToGrid, editorState.gridSize.x]);

  const updateKeyframeInterpolation = useCallback((
    clipUuid: string,
    trackIndex: number,
    keyframeIndex: number,
    interpolation: 'linear' | 'smooth' | 'step' | 'bezier'
  ) => {
    const clip = animationClips.find((c) => c.uuid === clipUuid);
    if (!clip || !clip.tracks[trackIndex] || !clip.tracks[trackIndex].keyframes[keyframeIndex]) return;

    const keyframe = clip.tracks[trackIndex].keyframes[keyframeIndex];
    updateKeyframe(clipUuid, trackIndex, keyframeIndex, {
      ...keyframe,
      interpolation,
    });
  }, [animationClips, updateKeyframe]);

  const updateKeyframeTangents = useCallback((
    clipUuid: string,
    trackIndex: number,
    keyframeIndex: number,
    inTangent?: number[],
    outTangent?: number[]
  ) => {
    const clip = animationClips.find((c) => c.uuid === clipUuid);
    if (!clip || !clip.tracks[trackIndex] || !clip.tracks[trackIndex].keyframes[keyframeIndex]) return;

    const keyframe = clip.tracks[trackIndex].keyframes[keyframeIndex];
    updateKeyframe(clipUuid, trackIndex, keyframeIndex, {
      ...keyframe,
      inTangent: inTangent ?? keyframe.inTangent,
      outTangent: outTangent ?? keyframe.outTangent,
    });
  }, [animationClips, updateKeyframe]);

  const deleteSelectedKeyframes = useCallback(() => {
    const sorted = [...editorState.selectedKeyframes].sort((a, b) =>
      b.keyframeIndex - a.keyframeIndex
    );

    sorted.forEach(({ clipUuid, trackIndex, keyframeIndex }) => {
      deleteKeyframe(clipUuid, trackIndex, keyframeIndex);
    });

    setEditorState((prev) => ({ ...prev, selectedKeyframes: [] }));
  }, [editorState.selectedKeyframes, deleteKeyframe]);

  const selectKeyframe = useCallback((
    clipUuid: string,
    trackIndex: number,
    keyframeIndex: number,
    multiSelect: boolean = false
  ) => {
    setEditorState((prev) => {
      const existing = prev.selectedKeyframes.find(
        (k) =>
          k.clipUuid === clipUuid &&
          k.trackIndex === trackIndex &&
          k.keyframeIndex === keyframeIndex
      );

      if (existing) {
        if (multiSelect) {
          return {
            ...prev,
            selectedKeyframes: prev.selectedKeyframes.filter(
              (k) =>
                !(k.clipUuid === clipUuid && k.trackIndex === trackIndex && k.keyframeIndex === keyframeIndex)
            ),
          };
        }
        return prev;
      }

      return {
        ...prev,
        selectedKeyframes: multiSelect
          ? [...prev.selectedKeyframes, { clipUuid, trackIndex, keyframeIndex }]
          : [{ clipUuid, trackIndex, keyframeIndex }],
      };
    });
  }, []);

  const clearSelection = useCallback(() => {
    setEditorState((prev) => ({ ...prev, selectedKeyframes: [] }));
  }, []);

  const setEditMode = useCallback((mode: CurveEditMode) => {
    setEditorState((prev) => ({ ...prev, mode }));
  }, []);

  const toggleTrackSelection = useCallback((trackIndex: number) => {
    setEditorState((prev) => ({
      ...prev,
      selectedTrackIndices: prev.selectedTrackIndices.includes(trackIndex)
        ? prev.selectedTrackIndices.filter((i) => i !== trackIndex)
        : [...prev.selectedTrackIndices, trackIndex],
    }));
  }, []);

  const setZoom = useCallback((zoom: number) => {
    setEditorState((prev) => ({ ...prev, zoom: Math.max(0.1, Math.min(10, zoom)) }));
  }, []);

  const setPanOffset = useCallback((x: number, y: number) => {
    setEditorState((prev) => ({ ...prev, panOffset: { x, y } }));
  }, []);

  const toggleSnapToGrid = useCallback(() => {
    setEditorState((prev) => ({ ...prev, snapToGrid: !prev.snapToGrid }));
  }, []);

  const setGridSize = useCallback((x: number, y: number) => {
    setEditorState((prev) => ({ ...prev, gridSize: { x, y } }));
  }, []);

  const getTrackSpline = useCallback((track: AnimationTrack) => {
    if (track.keyframes.length < 2) return null;

    const xValues = track.keyframes.map((k) => k.time);
    const yValues = track.keyframes.map((k) => k.value[0]);

    return computeCubicSpline(xValues, yValues);
  }, []);

  const getValueAtTime = useCallback((
    track: AnimationTrack,
    time: number
  ): number => {
    if (track.keyframes.length === 0) return 0;
    if (track.keyframes.length === 1) return track.keyframes[0].value[0];

    const spline = getTrackSpline(track);
    if (!spline) return track.keyframes[0].value[0];

    return evaluateCubicSpline(spline, time);
  }, [getTrackSpline]);

  const getTangentAtTime = useCallback((
    track: AnimationTrack,
    time: number
  ): number => {
    if (track.keyframes.length < 2) return 0;

    const spline = getTrackSpline(track);
    if (!spline) return 0;

    return evaluateCubicSplineDerivative(spline, time);
  }, [getTrackSpline]);

  const duplicateSelectedKeyframes = useCallback(() => {
    if (editorState.selectedKeyframes.length === 0 || !activeClip) return;

    const maxTime = Math.max(
      ...editorState.selectedKeyframes.map(({ clipUuid, trackIndex, keyframeIndex }) => {
        const clip = animationClips.find((c) => c.uuid === clipUuid);
        return clip?.tracks[trackIndex]?.keyframes[keyframeIndex]?.time || 0;
      })
    );

    const minTime = Math.min(
      ...editorState.selectedKeyframes.map(({ clipUuid, trackIndex, keyframeIndex }) => {
        const clip = animationClips.find((c) => c.uuid === clipUuid);
        return clip?.tracks[trackIndex]?.keyframes[keyframeIndex]?.time || 0;
      })
    );

    const offset = maxTime - minTime + 0.1;

    editorState.selectedKeyframes.forEach(({ clipUuid, trackIndex, keyframeIndex }) => {
      const clip = animationClips.find((c) => c.uuid === clipUuid);
      if (!clip || !clip.tracks[trackIndex] || !clip.tracks[trackIndex].keyframes[keyframeIndex]) return;

      const keyframe = clip.tracks[trackIndex].keyframes[keyframeIndex];
      const track = clip.tracks[trackIndex];

      addKeyframeAtTime(
        track.boneUuid,
        track.property,
        track.component,
        keyframe.time + offset,
        [...keyframe.value]
      );
    });
  }, [editorState.selectedKeyframes, activeClip, animationClips, addKeyframeAtTime]);

  const moveSelectedKeyframes = useCallback((deltaTime: number, deltaValue: number) => {
    editorState.selectedKeyframes.forEach(({ clipUuid, trackIndex, keyframeIndex }) => {
      const clip = animationClips.find((c) => c.uuid === clipUuid);
      if (!clip || !clip.tracks[trackIndex] || !clip.tracks[trackIndex].keyframes[keyframeIndex]) return;

      const keyframe = clip.tracks[trackIndex].keyframes[keyframeIndex];

      updateKeyframeTime(clipUuid, trackIndex, keyframeIndex, keyframe.time + deltaTime);

      if (deltaValue !== 0) {
        const newValue = keyframe.value.map((v) => v + deltaValue);
        updateKeyframeValue(clipUuid, trackIndex, keyframeIndex, newValue);
      }
    });
  }, [editorState.selectedKeyframes, animationClips, updateKeyframeTime, updateKeyframeValue]);

  return {
    activeClip,
    filteredTracks,
    editorState,
    addKeyframeAtTime,
    addKeyframeAtCurrentTime,
    updateKeyframeValue,
    updateKeyframeTime,
    updateKeyframeInterpolation,
    updateKeyframeTangents,
    deleteSelectedKeyframes,
    selectKeyframe,
    clearSelection,
    setEditMode,
    toggleTrackSelection,
    setZoom,
    setPanOffset,
    toggleSnapToGrid,
    setGridSize,
    getTrackSpline,
    getValueAtTime,
    getTangentAtTime,
    duplicateSelectedKeyframes,
    moveSelectedKeyframes,
  };
}
