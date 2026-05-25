import { useState, useRef, useEffect, useMemo, useCallback } from 'react';
import {
  MousePointer2,
  Plus,
  Trash2,
  Move,
  PenTool,
  Maximize2,
  Grid3X3,
  Magnet,
  Link,
  Unlink,
  Copy,
  Clipboard,
  ChevronRight,
} from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { useEditorStore } from '@/store/editorStore';
import { useKeyframeEditor } from '@/hooks/useKeyframeEditor';
import { cn } from '@/lib/utils';
import type { AnimationTrack, Keyframe } from '@/types/animation';
import { bezierCubic, evaluateCubicSpline, computeCubicSpline, catmullRom } from '@/utils/math/CurveMath';

type CurveEditMode = 'select' | 'add' | 'delete' | 'move' | 'tangent';

interface ContextMenuState {
  visible: boolean;
  x: number;
  y: number;
  clipUuid: string | null;
  trackIndex: number;
  keyframeIndex: number;
}

interface DragState {
  isDragging: boolean;
  type: 'keyframe' | 'tangentIn' | 'tangentOut' | 'pan' | 'playhead' | 'selection';
  startX: number;
  startY: number;
  startValueX: number;
  startValueY: number;
  clipUuid: string | null;
  trackIndex: number;
  keyframeIndex: number;
  tangentBroken: boolean;
}

const TRACK_COLORS: Record<string, string> = {
  x: '#ef4444',
  y: '#22c55e',
  z: '#3b82f6',
  w: '#eab308',
};

const TRACK_HEADER_WIDTH = 180;
const TOOLBAR_HEIGHT = 48;
const AXIS_LABEL_MARGIN = 60;
const KEYFRAME_SIZE = 10;
const TANGENT_HANDLE_SIZE = 6;

const CurveEditor = () => {
  const {
    currentTime,
    setCurrentTime,
    animationClips,
    selectedBoneUuid,
    skeleton,
    updateKeyframe,
  } = useEditorStore();

  const {
    activeClip,
    filteredTracks,
    editorState,
    addKeyframeAtTime,
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
    moveSelectedKeyframes,
    duplicateSelectedKeyframes,
  } = useKeyframeEditor();

  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const contextMenuRef = useRef<HTMLDivElement>(null);

  const [showGrid, setShowGrid] = useState(true);
  const [selectedInterpolation, setSelectedInterpolation] = useState<'linear' | 'smooth' | 'step' | 'bezier' | 'spline'>('linear');
  const [contextMenu, setContextMenu] = useState<ContextMenuState>({
    visible: false,
    x: 0,
    y: 0,
    clipUuid: null,
    trackIndex: -1,
    keyframeIndex: -1,
  });
  const [clipboardKeyframe, setClipboardKeyframe] = useState<Keyframe | null>(null);
  const [dragState, setDragState] = useState<DragState>({
    isDragging: false,
    type: 'keyframe',
    startX: 0,
    startY: 0,
    startValueX: 0,
    startValueY: 0,
    clipUuid: null,
    trackIndex: -1,
    keyframeIndex: -1,
    tangentBroken: false,
  });
  const [selectionBox, setSelectionBox] = useState<{ x: number; y: number; width: number; height: number } | null>(null);

  const visibleTracks = useMemo(() => {
    if (editorState.selectedTrackIndices.length === 0) {
      return filteredTracks;
    }
    return filteredTracks.filter((_, i) => editorState.selectedTrackIndices.includes(i));
  }, [filteredTracks, editorState.selectedTrackIndices]);

  const valueRange = useMemo(() => {
    let min = Infinity;
    let max = -Infinity;

    visibleTracks.forEach((track) => {
      track.keyframes.forEach((k) => {
        const v = k.value[0];
        min = Math.min(min, v);
        max = Math.max(max, v);
      });
    });

    if (min === Infinity || max === -Infinity) {
      min = -1;
      max = 1;
    }

    const padding = (max - min) * 0.1 || 0.5;
    return { min: min - padding, max: max + padding };
  }, [visibleTracks]);

  const timeRange = useMemo(() => {
    const duration = useEditorStore.getState().getDuration();
    return { min: 0, max: duration };
  }, []);

  const canvasSize = useMemo(() => {
    const container = containerRef.current;
    if (!container) return { width: 800, height: 400 };
    return {
      width: container.clientWidth - TRACK_HEADER_WIDTH,
      height: container.clientHeight - TOOLBAR_HEIGHT,
    };
  }, [containerRef.current?.clientWidth, containerRef.current?.clientHeight]);

  const transform = useMemo(() => {
    const { zoom, panOffset } = editorState;
    const { width, height } = canvasSize;

    const timeSpan = timeRange.max - timeRange.min;
    const valueSpan = valueRange.max - valueRange.min;

    const pixelsPerSecond = (width - AXIS_LABEL_MARGIN) / timeSpan * zoom;
    const pixelsPerUnit = (height - AXIS_LABEL_MARGIN) / valueSpan * zoom;

    const originX = AXIS_LABEL_MARGIN + panOffset.x;
    const originY = height - AXIS_LABEL_MARGIN + panOffset.y;

    const timeToX = (time: number) => originX + (time - timeRange.min) * pixelsPerSecond;
    const valueToY = (value: number) => originY - (value - valueRange.min) * pixelsPerUnit;
    const xToTime = (x: number) => (x - originX) / pixelsPerSecond + timeRange.min;
    const yToValue = (y: number) => -(y - originY) / pixelsPerUnit + valueRange.min;

    return {
      pixelsPerSecond,
      pixelsPerUnit,
      originX,
      originY,
      timeToX,
      valueToY,
      xToTime,
      yToValue,
    };
  }, [editorState.zoom, editorState.panOffset, canvasSize, timeRange, valueRange]);

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const { width, height } = canvasSize;
    const { timeToX, valueToY, xToTime, yToValue, originX, originY } = transform;

    ctx.clearRect(0, 0, width, height);

    ctx.fillStyle = '#0f172a';
    ctx.fillRect(0, 0, width, height);

    if (showGrid) {
      drawGrid(ctx, width, height, xToTime, yToValue, timeToX, valueToY);
    }

    drawAxes(ctx, width, height, originX, originY, timeToX, valueToY);

    visibleTracks.forEach((track) => {
      drawCurve(ctx, track, timeToX, valueToY);
    });

    drawPlayhead(ctx, timeToX(currentTime), height);

    visibleTracks.forEach((track, trackIdx) => {
      const globalTrackIndex = filteredTracks.findIndex(
        (t) => t.boneUuid === track.boneUuid && t.property === track.property && t.component === track.component
      );
      drawKeyframes(ctx, track, globalTrackIndex, timeToX, valueToY);
    });

    if (selectionBox) {
      ctx.strokeStyle = '#06b6d4';
      ctx.lineWidth = 1;
      ctx.setLineDash([4, 4]);
      ctx.strokeRect(selectionBox.x, selectionBox.y, selectionBox.width, selectionBox.height);
      ctx.fillStyle = 'rgba(6, 182, 212, 0.1)';
      ctx.fillRect(selectionBox.x, selectionBox.y, selectionBox.width, selectionBox.height);
      ctx.setLineDash([]);
    }
  }, [canvasSize, transform, visibleTracks, filteredTracks, currentTime, showGrid, selectionBox, editorState.selectedKeyframes, activeClip]);

  const drawGrid = (
    ctx: CanvasRenderingContext2D,
    width: number,
    height: number,
    xToTime: (x: number) => number,
    yToValue: (y: number) => number,
    timeToX: (time: number) => number,
    valueToY: (value: number) => number
  ) => {
    const { gridSize } = editorState;

    ctx.strokeStyle = '#1e293b';
    ctx.lineWidth = 1;

    const startTime = Math.floor(xToTime(AXIS_LABEL_MARGIN) / gridSize.x) * gridSize.x;
    const endTime = Math.ceil(xToTime(width) / gridSize.x) * gridSize.x;

    for (let t = startTime; t <= endTime; t += gridSize.x) {
      const x = timeToX(t);
      if (x < AXIS_LABEL_MARGIN || x > width) continue;

      const isMajor = Math.abs(t - Math.round(t)) < 0.001;
      ctx.strokeStyle = isMajor ? '#334155' : '#1e293b';
      ctx.beginPath();
      ctx.moveTo(x, AXIS_LABEL_MARGIN);
      ctx.lineTo(x, height - AXIS_LABEL_MARGIN);
      ctx.stroke();
    }

    const startValue = Math.floor(yToValue(height - AXIS_LABEL_MARGIN) / gridSize.y) * gridSize.y;
    const endValue = Math.ceil(yToValue(0) / gridSize.y) * gridSize.y;

    for (let v = startValue; v <= endValue; v += gridSize.y) {
      const y = valueToY(v);
      if (y < 0 || y > height - AXIS_LABEL_MARGIN) continue;

      const isMajor = Math.abs(v - Math.round(v)) < 0.001;
      ctx.strokeStyle = isMajor ? '#334155' : '#1e293b';
      ctx.beginPath();
      ctx.moveTo(AXIS_LABEL_MARGIN, y);
      ctx.lineTo(width, y);
      ctx.stroke();
    }
  };

  const drawAxes = (
    ctx: CanvasRenderingContext2D,
    width: number,
    height: number,
    originX: number,
    originY: number,
    timeToX: (time: number) => number,
    valueToY: (value: number) => number
  ) => {
    const { gridSize } = editorState;

    ctx.strokeStyle = '#475569';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(AXIS_LABEL_MARGIN, AXIS_LABEL_MARGIN);
    ctx.lineTo(AXIS_LABEL_MARGIN, height - AXIS_LABEL_MARGIN);
    ctx.lineTo(width, height - AXIS_LABEL_MARGIN);
    ctx.stroke();

    ctx.fillStyle = '#94a3b8';
    ctx.font = '11px system-ui';
    ctx.textAlign = 'center';

    const startTime = Math.floor(timeRange.min / gridSize.x) * gridSize.x;
    for (let t = startTime; t <= timeRange.max; t += gridSize.x * 10) {
      const x = timeToX(t);
      if (x < AXIS_LABEL_MARGIN || x > width) continue;

      ctx.fillText(t.toFixed(1), x, height - AXIS_LABEL_MARGIN + 20);
    }

    ctx.textAlign = 'right';
    ctx.textBaseline = 'middle';

    const startValue = Math.floor(valueRange.min / gridSize.y) * gridSize.y;
    for (let v = startValue; v <= valueRange.max; v += gridSize.y * 5) {
      const y = valueToY(v);
      if (y < AXIS_LABEL_MARGIN || y > height - AXIS_LABEL_MARGIN) continue;

      ctx.fillText(v.toFixed(2), AXIS_LABEL_MARGIN - 8, y);
    }

    ctx.fillStyle = '#64748b';
    ctx.font = 'bold 12px system-ui';
    ctx.textAlign = 'center';
    ctx.fillText('时间 (s)', width / 2, height - 8);

    ctx.save();
    ctx.translate(16, height / 2);
    ctx.rotate(-Math.PI / 2);
    ctx.fillText('数值', 0, 0);
    ctx.restore();
  };

  const drawCurve = (
    ctx: CanvasRenderingContext2D,
    track: AnimationTrack,
    timeToX: (time: number) => number,
    valueToY: (value: number) => number
  ) => {
    const color = TRACK_COLORS[track.component] || '#64748b';

    if (track.keyframes.length === 0) return;

    ctx.strokeStyle = color;
    ctx.lineWidth = 2;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';

    if (track.keyframes.length === 1) {
      const k = track.keyframes[0];
      ctx.beginPath();
      ctx.arc(timeToX(k.time), valueToY(k.value[0]), 4, 0, Math.PI * 2);
      ctx.stroke();
      return;
    }

    ctx.beginPath();

    for (let i = 0; i < track.keyframes.length - 1; i++) {
      const k0 = track.keyframes[i];
      const k1 = track.keyframes[i + 1];

      const x0 = timeToX(k0.time);
      const y0 = valueToY(k0.value[0]);
      const x1 = timeToX(k1.time);
      const y1 = valueToY(k1.value[0]);

      if (i === 0) {
        ctx.moveTo(x0, y0);
      }

      if (k0.interpolation === 'step') {
        ctx.lineTo(x1, y0);
        ctx.lineTo(x1, y1);
      } else if (k0.interpolation === 'linear') {
        ctx.lineTo(x1, y1);
      } else if (k0.interpolation === 'bezier' && k0.outTangent && k1.inTangent) {
        const cp1x = x0 + k0.outTangent[0] * transform.pixelsPerSecond;
        const cp1y = y0 - k0.outTangent[1] * transform.pixelsPerUnit;
        const cp2x = x1 + k1.inTangent[0] * transform.pixelsPerSecond;
        const cp2y = y1 - k1.inTangent[1] * transform.pixelsPerUnit;

        ctx.bezierCurveTo(cp1x, cp1y, cp2x, cp2y, x1, y1);
      } else if (k0.interpolation === 'spline') {
        const keyframes = track.keyframes;
        const n = keyframes.length;
        
        const p0 = i === 0
          ? keyframes[0].value[0] - (keyframes[1].value[0] - keyframes[0].value[0])
          : keyframes[i - 1].value[0];
        const p1 = keyframes[i].value[0];
        const p2 = keyframes[i + 1].value[0];
        const p3 = i >= n - 2
          ? keyframes[n - 1].value[0] + (keyframes[n - 1].value[0] - keyframes[n - 2].value[0])
          : keyframes[i + 2].value[0];

        const steps = 30;
        for (let s = 0; s <= steps; s++) {
          const t = s / steps;
          const v = catmullRom(p0, p1, p2, p3, t, 0.5);
          ctx.lineTo(x0 + (x1 - x0) * t, valueToY(v));
        }
      } else {
        const spline = computeCubicSpline(
          track.keyframes.map((k) => k.time),
          track.keyframes.map((k) => k.value[0])
        );

        if (spline.length > 0) {
          const steps = 20;
          for (let s = 0; s <= steps; s++) {
            const t = k0.time + (k1.time - k0.time) * (s / steps);
            const v = evaluateCubicSpline(spline, t);
            ctx.lineTo(timeToX(t), valueToY(v));
          }
        } else {
          ctx.lineTo(x1, y1);
        }
      }
    }

    ctx.stroke();
  };

  const drawKeyframes = (
    ctx: CanvasRenderingContext2D,
    track: AnimationTrack,
    globalTrackIndex: number,
    timeToX: (time: number) => number,
    valueToY: (value: number) => number
  ) => {
    const color = TRACK_COLORS[track.component] || '#64748b';

    track.keyframes.forEach((keyframe, keyframeIdx) => {
      const x = timeToX(keyframe.time);
      const y = valueToY(keyframe.value[0]);

      const isSelected = editorState.selectedKeyframes.some(
        (k) =>
          k.clipUuid === activeClip?.uuid &&
          k.trackIndex === globalTrackIndex &&
          k.keyframeIndex === keyframeIdx
      );

      if (isSelected && keyframe.interpolation === 'bezier') {
        drawTangentHandles(ctx, track, keyframeIdx, x, y, color);
      }

      ctx.save();
      ctx.translate(x, y);
      ctx.rotate(Math.PI / 4);

      const size = isSelected ? KEYFRAME_SIZE + 2 : KEYFRAME_SIZE;

      ctx.fillStyle = isSelected ? '#fbbf24' : color;
      ctx.strokeStyle = isSelected ? '#f59e0b' : '#ffffff';
      ctx.lineWidth = 2;

      ctx.fillRect(-size / 2, -size / 2, size, size);
      ctx.strokeRect(-size / 2, -size / 2, size, size);

      ctx.restore();
    });
  };

  const drawTangentHandles = (
    ctx: CanvasRenderingContext2D,
    track: AnimationTrack,
    keyframeIdx: number,
    x: number,
    y: number,
    color: string
  ) => {
    const keyframe = track.keyframes[keyframeIdx];
    const prevKeyframe = track.keyframes[keyframeIdx - 1];
    const nextKeyframe = track.keyframes[keyframeIdx + 1];

    if (prevKeyframe && keyframe.inTangent) {
      const handleX = x + keyframe.inTangent[0] * transform.pixelsPerSecond;
      const handleY = y - keyframe.inTangent[1] * transform.pixelsPerUnit;

      ctx.strokeStyle = '#a78bfa';
      ctx.lineWidth = 1.5;
      ctx.setLineDash([3, 3]);
      ctx.beginPath();
      ctx.moveTo(x, y);
      ctx.lineTo(handleX, handleY);
      ctx.stroke();
      ctx.setLineDash([]);

      ctx.fillStyle = '#a78bfa';
      ctx.strokeStyle = '#ffffff';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(handleX, handleY, TANGENT_HANDLE_SIZE, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();
    }

    if (nextKeyframe && keyframe.outTangent) {
      const handleX = x + keyframe.outTangent[0] * transform.pixelsPerSecond;
      const handleY = y - keyframe.outTangent[1] * transform.pixelsPerUnit;

      ctx.strokeStyle = '#f472b6';
      ctx.lineWidth = 1.5;
      ctx.setLineDash([3, 3]);
      ctx.beginPath();
      ctx.moveTo(x, y);
      ctx.lineTo(handleX, handleY);
      ctx.stroke();
      ctx.setLineDash([]);

      ctx.fillStyle = '#f472b6';
      ctx.strokeStyle = '#ffffff';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(handleX, handleY, TANGENT_HANDLE_SIZE, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();
    }
  };

  const drawPlayhead = (ctx: CanvasRenderingContext2D, x: number, height: number) => {
    ctx.strokeStyle = '#ef4444';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(x, AXIS_LABEL_MARGIN);
    ctx.lineTo(x, height - AXIS_LABEL_MARGIN);
    ctx.stroke();

    ctx.fillStyle = '#ef4444';
    ctx.beginPath();
    ctx.moveTo(x - 6, AXIS_LABEL_MARGIN);
    ctx.lineTo(x + 6, AXIS_LABEL_MARGIN);
    ctx.lineTo(x, AXIS_LABEL_MARGIN + 8);
    ctx.closePath();
    ctx.fill();
  };

  const hitTestKeyframe = useCallback(
    (mouseX: number, mouseY: number): { clipUuid: string; trackIndex: number; keyframeIndex: number } | null => {
      if (!activeClip) return null;

      const { timeToX, valueToY } = transform;
      const hitRadius = KEYFRAME_SIZE + 4;

      for (let trackIdx = 0; trackIdx < filteredTracks.length; trackIdx++) {
        const track = filteredTracks[trackIdx];
        for (let keyframeIdx = 0; keyframeIdx < track.keyframes.length; keyframeIdx++) {
          const k = track.keyframes[keyframeIdx];
          const x = timeToX(k.time);
          const y = valueToY(k.value[0]);
          const dist = Math.sqrt((mouseX - x) ** 2 + (mouseY - y) ** 2);

          if (dist < hitRadius) {
            return { clipUuid: activeClip.uuid, trackIndex: trackIdx, keyframeIdx };
          }
        }
      }

      return null;
    },
    [activeClip, filteredTracks, transform]
  );

  const hitTestTangent = useCallback(
    (
      mouseX: number,
      mouseY: number
    ): {
      clipUuid: string;
      trackIndex: number;
      keyframeIndex: number;
      type: 'tangentIn' | 'tangentOut';
    } | null => {
      if (!activeClip) return null;

      const { timeToX, valueToY } = transform;
      const hitRadius = TANGENT_HANDLE_SIZE + 4;

      for (let trackIdx = 0; trackIdx < filteredTracks.length; trackIdx++) {
        const track = filteredTracks[trackIdx];
        for (let keyframeIdx = 0; keyframeIdx < track.keyframes.length; keyframeIdx++) {
          const k = track.keyframes[keyframeIdx];
          if (k.interpolation !== 'bezier') continue;

          const x = timeToX(k.time);
          const y = valueToY(k.value[0]);

          if (k.inTangent && keyframeIdx > 0) {
            const handleX = x + k.inTangent[0] * transform.pixelsPerSecond;
            const handleY = y - k.inTangent[1] * transform.pixelsPerUnit;
            const dist = Math.sqrt((mouseX - handleX) ** 2 + (mouseY - handleY) ** 2);
            if (dist < hitRadius) {
              return { clipUuid: activeClip.uuid, trackIndex: trackIdx, keyframeIndex: keyframeIdx, type: 'tangentIn' };
            }
          }

          if (k.outTangent && keyframeIdx < track.keyframes.length - 1) {
            const handleX = x + k.outTangent[0] * transform.pixelsPerSecond;
            const handleY = y - k.outTangent[1] * transform.pixelsPerUnit;
            const dist = Math.sqrt((mouseX - handleX) ** 2 + (mouseY - handleY) ** 2);
            if (dist < hitRadius) {
              return { clipUuid: activeClip.uuid, trackIndex: trackIdx, keyframeIndex: keyframeIdx, type: 'tangentOut' };
            }
          }
        }
      }

      return null;
    },
    [activeClip, filteredTracks, transform]
  );

  const handleCanvasMouseDown = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      const rect = canvasRef.current?.getBoundingClientRect();
      if (!rect) return;

      const mouseX = e.clientX - rect.left;
      const mouseY = e.clientY - rect.top;

      if (e.button === 1) {
        setDragState({
          isDragging: true,
          type: 'pan',
          startX: e.clientX,
          startY: e.clientY,
          startValueX: editorState.panOffset.x,
          startValueY: editorState.panOffset.y,
          clipUuid: null,
          trackIndex: -1,
          keyframeIndex: -1,
          tangentBroken: false,
        });
        return;
      }

      if (e.button === 2) {
        return;
      }

      const mode = editorState.mode;

      if (mode === 'tangent') {
        const tangentHit = hitTestTangent(mouseX, mouseY);
        if (tangentHit && activeClip) {
          const track = filteredTracks[tangentHit.trackIndex];
          const keyframe = track.keyframes[tangentHit.keyframeIndex];

          setDragState({
            isDragging: true,
            type: tangentHit.type,
            startX: e.clientX,
            startY: e.clientY,
            startValueX: keyframe.time,
            startValueY: keyframe.value[0],
            clipUuid: tangentHit.clipUuid,
            trackIndex: tangentHit.trackIndex,
            keyframeIndex: tangentHit.keyframeIndex,
            tangentBroken: e.altKey,
          });
          return;
        }
      }

      if (mode === 'select' || mode === 'move') {
        const keyframeHit = hitTestKeyframe(mouseX, mouseY);
        if (keyframeHit) {
          selectKeyframe(keyframeHit.clipUuid, keyframeHit.trackIndex, keyframeHit.keyframeIndex, e.shiftKey);

          if (mode === 'move' || e.shiftKey) {
            setDragState({
              isDragging: true,
              type: 'keyframe',
              startX: e.clientX,
              startY: e.clientY,
              startValueX: transform.xToTime(mouseX),
              startValueY: transform.yToValue(mouseY),
              clipUuid: keyframeHit.clipUuid,
              trackIndex: keyframeHit.trackIndex,
              keyframeIndex: keyframeHit.keyframeIndex,
              tangentBroken: false,
            });
          }
          return;
        }

        if (mode === 'select') {
          clearSelection();
          setSelectionBox({ x: mouseX, y: mouseY, width: 0, height: 0 });
          setDragState({
            isDragging: true,
            type: 'selection',
            startX: mouseX,
            startY: mouseY,
            startValueX: 0,
            startValueY: 0,
            clipUuid: null,
            trackIndex: -1,
            keyframeIndex: -1,
            tangentBroken: false,
          });
          return;
        }
      }

      if (mode === 'add') {
        if (!selectedBoneUuid || visibleTracks.length === 0) return;

        const time = transform.xToTime(mouseX);
        const value = transform.yToValue(mouseY);

        const targetTrack = visibleTracks[0];
        addKeyframeAtTime(
          targetTrack.boneUuid,
          targetTrack.property,
          targetTrack.component,
          time,
          [value]
        );
        return;
      }

      if (mode === 'delete') {
        const keyframeHit = hitTestKeyframe(mouseX, mouseY);
        if (keyframeHit) {
          selectKeyframe(keyframeHit.clipUuid, keyframeHit.trackIndex, keyframeHit.keyframeIndex, false);
          setTimeout(() => deleteSelectedKeyframes(), 0);
        }
        return;
      }

      if (mouseX > AXIS_LABEL_MARGIN && mouseY < canvasSize.height - AXIS_LABEL_MARGIN) {
        const time = transform.xToTime(mouseX);
        setCurrentTime(Math.max(0, Math.min(time, timeRange.max)));
        setDragState({
          isDragging: true,
          type: 'playhead',
          startX: e.clientX,
          startY: e.clientY,
          startValueX: time,
          startValueY: 0,
          clipUuid: null,
          trackIndex: -1,
          keyframeIndex: -1,
          tangentBroken: false,
        });
      }
    },
    [
      editorState,
      hitTestKeyframe,
      hitTestTangent,
      selectKeyframe,
      clearSelection,
      addKeyframeAtTime,
      deleteSelectedKeyframes,
      setCurrentTime,
      transform,
      canvasSize,
      timeRange,
      activeClip,
      filteredTracks,
      selectedBoneUuid,
      visibleTracks,
    ]
  );

  const handleCanvasMouseMove = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      const rect = canvasRef.current?.getBoundingClientRect();
      if (!rect) return;

      const mouseX = e.clientX - rect.left;
      const mouseY = e.clientY - rect.top;

      if (dragState.isDragging) {
        const { type, startX, startY, startValueX, startValueY, clipUuid, trackIndex, keyframeIndex } = dragState;

        if (type === 'pan') {
          const deltaX = e.clientX - startX;
          const deltaY = e.clientY - startY;
          setPanOffset(startValueX + deltaX, startValueY + deltaY);
          return;
        }

        if (type === 'playhead') {
          const time = transform.xToTime(mouseX);
          setCurrentTime(Math.max(0, Math.min(time, timeRange.max)));
          return;
        }

        if (type === 'selection') {
          setSelectionBox({
            x: Math.min(startX, mouseX),
            y: Math.min(startY, mouseY),
            width: Math.abs(mouseX - startX),
            height: Math.abs(mouseY - startY),
          });

          if (activeClip) {
            filteredTracks.forEach((track, tIdx) => {
              track.keyframes.forEach((k, kIdx) => {
                const kx = transform.timeToX(k.time);
                const ky = transform.valueToY(k.value[0]);

                const inBox =
                  kx >= Math.min(startX, mouseX) &&
                  kx <= Math.max(startX, mouseX) &&
                  ky >= Math.min(startY, mouseY) &&
                  ky <= Math.max(startY, mouseY);

                if (inBox) {
                  selectKeyframe(activeClip.uuid, tIdx, kIdx, true);
                }
              });
            });
          }
          return;
        }

        if (type === 'keyframe' && clipUuid && trackIndex >= 0 && keyframeIndex >= 0) {
          const deltaTime = transform.xToTime(mouseX) - startValueX;
          const deltaValue = transform.yToValue(mouseY) - startValueY;

          if (e.shiftKey) {
            moveSelectedKeyframes(deltaTime, deltaValue);
          } else {
            moveSelectedKeyframes(deltaTime, 0);
          }
          return;
        }

        if ((type === 'tangentIn' || type === 'tangentOut') && clipUuid && trackIndex >= 0 && keyframeIndex >= 0 && activeClip) {
          const track = filteredTracks[trackIndex];
          const keyframe = track.keyframes[keyframeIndex];

          const kx = transform.timeToX(keyframe.time);
          const ky = transform.valueToY(keyframe.value[0]);

          const tangentX = (mouseX - kx) / transform.pixelsPerSecond;
          const tangentY = -(mouseY - ky) / transform.pixelsPerUnit;

          if (type === 'tangentIn') {
            const newInTangent = [tangentX, tangentY];
            const newOutTangent = dragState.tangentBroken
              ? keyframe.outTangent
              : [-tangentX, -tangentY];

            updateKeyframeTangents(clipUuid, trackIndex, keyframeIndex, newInTangent, newOutTangent);
          } else {
            const newOutTangent = [tangentX, tangentY];
            const newInTangent = dragState.tangentBroken
              ? keyframe.inTangent
              : [-tangentX, -tangentY];

            updateKeyframeTangents(clipUuid, trackIndex, keyframeIndex, newInTangent, newOutTangent);
          }
          return;
        }
      }

      const keyframeHit = hitTestKeyframe(mouseX, mouseY);
      const tangentHit = hitTestTangent(mouseX, mouseY);

      const canvas = canvasRef.current;
      if (canvas) {
        if (tangentHit) {
          canvas.style.cursor = 'crosshair';
        } else if (keyframeHit) {
          canvas.style.cursor = editorState.mode === 'delete' ? 'not-allowed' : 'pointer';
        } else if (mouseX > AXIS_LABEL_MARGIN && mouseY < canvasSize.height - AXIS_LABEL_MARGIN) {
          if (editorState.mode === 'add') {
            canvas.style.cursor = 'crosshair';
          } else if (e.buttons === 1) {
            canvas.style.cursor = 'grabbing';
          } else {
            canvas.style.cursor = 'default';
          }
        } else {
          canvas.style.cursor = 'default';
        }
      }
    },
    [
      dragState,
      transform,
      timeRange,
      setCurrentTime,
      setPanOffset,
      moveSelectedKeyframes,
      updateKeyframeTangents,
      hitTestKeyframe,
      hitTestTangent,
      editorState.mode,
      canvasSize.height,
      activeClip,
      filteredTracks,
      selectKeyframe,
    ]
  );

  const handleCanvasMouseUp = useCallback(() => {
    setSelectionBox(null);
    setDragState((prev) => ({ ...prev, isDragging: false }));
  }, []);

  const handleCanvasContextMenu = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      e.preventDefault();

      const rect = canvasRef.current?.getBoundingClientRect();
      if (!rect) return;

      const mouseX = e.clientX - rect.left;
      const mouseY = e.clientY - rect.top;

      const keyframeHit = hitTestKeyframe(mouseX, mouseY);

      if (keyframeHit) {
        selectKeyframe(keyframeHit.clipUuid, keyframeHit.trackIndex, keyframeHit.keyframeIndex, false);
        setContextMenu({
          visible: true,
          x: e.clientX,
          y: e.clientY,
          clipUuid: keyframeHit.clipUuid,
          trackIndex: keyframeHit.trackIndex,
          keyframeIndex: keyframeHit.keyframeIndex,
        });
      }
    },
    [hitTestKeyframe, selectKeyframe]
  );

  const handleCanvasWheel = useCallback(
    (e: React.WheelEvent<HTMLCanvasElement>) => {
      e.preventDefault();

      const delta = e.deltaY > 0 ? -0.1 : 0.1;
      const newZoom = Math.max(0.1, Math.min(10, editorState.zoom + delta));
      setZoom(newZoom);
    },
    [editorState.zoom, setZoom]
  );

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
        return;
      }

      if (e.key === 'Delete' || e.key === 'Backspace') {
        e.preventDefault();
        deleteSelectedKeyframes();
      }

      if (e.key === 'a' && (e.ctrlKey || e.metaKey)) {
        e.preventDefault();
        if (activeClip) {
          filteredTracks.forEach((track, tIdx) => {
            track.keyframes.forEach((_, kIdx) => {
              selectKeyframe(activeClip.uuid, tIdx, kIdx, true);
            });
          });
        }
      }

      if (e.key === 'd' && (e.ctrlKey || e.metaKey)) {
        e.preventDefault();
        duplicateSelectedKeyframes();
      }

      if (e.key === 'c' && (e.ctrlKey || e.metaKey)) {
        e.preventDefault();
        if (editorState.selectedKeyframes.length > 0 && activeClip) {
          const { clipUuid, trackIndex, keyframeIndex } = editorState.selectedKeyframes[0];
          const clip = animationClips.find((c) => c.uuid === clipUuid);
          if (clip && clip.tracks[trackIndex] && clip.tracks[trackIndex].keyframes[keyframeIndex]) {
            setClipboardKeyframe({ ...clip.tracks[trackIndex].keyframes[keyframeIndex] });
          }
        }
      }

      if (e.key === 'v' && (e.ctrlKey || e.metaKey)) {
        e.preventDefault();
        if (clipboardKeyframe && editorState.selectedKeyframes.length > 0 && activeClip) {
          const { clipUuid, trackIndex } = editorState.selectedKeyframes[0];
          const clip = animationClips.find((c) => c.uuid === clipUuid);
          if (clip && clip.tracks[trackIndex]) {
            const track = clip.tracks[trackIndex];
            const insertIndex = track.keyframes.findIndex((k) => k.time > currentTime);
            const newKeyframe = { ...clipboardKeyframe, time: currentTime };

            if (insertIndex === -1) {
              track.keyframes.push(newKeyframe);
            } else {
              track.keyframes.splice(insertIndex, 0, newKeyframe);
            }

            if (clipUuid === activeClip.uuid) {
              updateKeyframe(clipUuid, trackIndex, 0, track.keyframes[0]);
            }
          }
        }
      }

      if (e.key === 'Escape') {
        clearSelection();
        setContextMenu({ visible: false, x: 0, y: 0, clipUuid: null, trackIndex: -1, keyframeIndex: -1 });
      }

      if (e.key === '1') setEditMode('select');
      if (e.key === '2') setEditMode('add');
      if (e.key === '3') setEditMode('delete');
      if (e.key === '4') setEditMode('move');
      if (e.key === '5') setEditMode('tangent');
    },
    [
      deleteSelectedKeyframes,
      duplicateSelectedKeyframes,
      selectKeyframe,
      clearSelection,
      setEditMode,
      activeClip,
      filteredTracks,
      editorState.selectedKeyframes,
      animationClips,
      clipboardKeyframe,
      currentTime,
      updateKeyframe,
    ]
  );

  const handleInterpolationChange = useCallback(
    (interpolation: 'linear' | 'smooth' | 'step' | 'bezier' | 'spline') => {
      setSelectedInterpolation(interpolation);
      editorState.selectedKeyframes.forEach(({ clipUuid, trackIndex, keyframeIndex }) => {
        updateKeyframeInterpolation(clipUuid, trackIndex, keyframeIndex, interpolation);
      });
      setContextMenu({ visible: false, x: 0, y: 0, clipUuid: null, trackIndex: -1, keyframeIndex: -1 });
    },
    [editorState.selectedKeyframes, updateKeyframeInterpolation]
  );

  const handleCopyKeyframe = useCallback(() => {
    if (editorState.selectedKeyframes.length > 0 && activeClip) {
      const { clipUuid, trackIndex, keyframeIndex } = editorState.selectedKeyframes[0];
      const clip = animationClips.find((c) => c.uuid === clipUuid);
      if (clip && clip.tracks[trackIndex] && clip.tracks[trackIndex].keyframes[keyframeIndex]) {
        setClipboardKeyframe({ ...clip.tracks[trackIndex].keyframes[keyframeIndex] });
      }
    }
    setContextMenu({ visible: false, x: 0, y: 0, clipUuid: null, trackIndex: -1, keyframeIndex: -1 });
  }, [editorState.selectedKeyframes, activeClip, animationClips]);

  const handlePasteKeyframe = useCallback(() => {
    if (clipboardKeyframe && editorState.selectedKeyframes.length > 0 && activeClip) {
      const { clipUuid, trackIndex } = editorState.selectedKeyframes[0];
      const clip = animationClips.find((c) => c.uuid === clipUuid);
      if (clip && clip.tracks[trackIndex]) {
        const track = clip.tracks[trackIndex];
        const insertIndex = track.keyframes.findIndex((k) => k.time > currentTime);
        const newKeyframe = { ...clipboardKeyframe, time: currentTime };

        if (insertIndex === -1) {
          track.keyframes.push(newKeyframe);
        } else {
          track.keyframes.splice(insertIndex, 0, newKeyframe);
        }

        if (clipUuid === activeClip.uuid && track.keyframes.length > 0) {
          updateKeyframe(clipUuid, trackIndex, 0, track.keyframes[0]);
        }
      }
    }
    setContextMenu({ visible: false, x: 0, y: 0, clipUuid: null, trackIndex: -1, keyframeIndex: -1 });
  }, [clipboardKeyframe, editorState.selectedKeyframes, activeClip, animationClips, currentTime, updateKeyframe]);

  const handleDeleteKeyframe = useCallback(() => {
    deleteSelectedKeyframes();
    setContextMenu({ visible: false, x: 0, y: 0, clipUuid: null, trackIndex: -1, keyframeIndex: -1 });
  }, [deleteSelectedKeyframes]);

  const handleFitToView = useCallback(() => {
    setZoom(1);
    setPanOffset(0, 0);
  }, [setZoom, setPanOffset]);

  const handleBreakTangents = useCallback(() => {
    editorState.selectedKeyframes.forEach(({ clipUuid, trackIndex, keyframeIndex }) => {
      const clip = animationClips.find((c) => c.uuid === clipUuid);
      if (!clip || !clip.tracks[trackIndex] || !clip.tracks[trackIndex].keyframes[keyframeIndex]) return;

      const keyframe = clip.tracks[trackIndex].keyframes[keyframeIndex];
      if (keyframe.interpolation !== 'bezier') {
        updateKeyframeInterpolation(clipUuid, trackIndex, keyframeIndex, 'bezier');
      }

      const inTangent = keyframe.inTangent || [-0.1, 0];
      const outTangent = keyframe.outTangent || [0.1, 0];

      updateKeyframeTangents(clipUuid, trackIndex, keyframeIndex, [...inTangent], [...outTangent]);
    });
    setContextMenu({ visible: false, x: 0, y: 0, clipUuid: null, trackIndex: -1, keyframeIndex: -1 });
  }, [editorState.selectedKeyframes, animationClips, updateKeyframeInterpolation, updateKeyframeTangents]);

  const handleUnifyTangents = useCallback(() => {
    editorState.selectedKeyframes.forEach(({ clipUuid, trackIndex, keyframeIndex }) => {
      const clip = animationClips.find((c) => c.uuid === clipUuid);
      if (!clip || !clip.tracks[trackIndex] || !clip.tracks[trackIndex].keyframes[keyframeIndex]) return;

      const keyframe = clip.tracks[trackIndex].keyframes[keyframeIndex];
      if (keyframe.interpolation !== 'bezier') {
        updateKeyframeInterpolation(clipUuid, trackIndex, keyframeIndex, 'bezier');
      }

      const outTangent = keyframe.outTangent || [0.1, 0];
      const inTangent = [-outTangent[0], -outTangent[1]];

      updateKeyframeTangents(clipUuid, trackIndex, keyframeIndex, inTangent, outTangent);
    });
    setContextMenu({ visible: false, x: 0, y: 0, clipUuid: null, trackIndex: -1, keyframeIndex: -1 });
  }, [editorState.selectedKeyframes, animationClips, updateKeyframeInterpolation, updateKeyframeTangents]);

  useEffect(() => {
    draw();
  }, [draw]);

  useEffect(() => {
    const handleResize = () => {
      const canvas = canvasRef.current;
      const container = containerRef.current;
      if (!canvas || !container) return;

      const rect = container.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;

      canvas.width = (rect.width - TRACK_HEADER_WIDTH) * dpr;
      canvas.height = (rect.height - TOOLBAR_HEIGHT) * dpr;
      canvas.style.width = `${rect.width - TRACK_HEADER_WIDTH}px`;
      canvas.style.height = `${rect.height - TOOLBAR_HEIGHT}px`;

      const ctx = canvas.getContext('2d');
      if (ctx) {
        ctx.scale(dpr, dpr);
      }
    };

    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (
        contextMenu.visible &&
        contextMenuRef.current &&
        !contextMenuRef.current.contains(e.target as Node)
      ) {
        setContextMenu({ visible: false, x: 0, y: 0, clipUuid: null, trackIndex: -1, keyframeIndex: -1 });
      }
    };

    if (contextMenu.visible) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [contextMenu.visible]);

  const getTrackLabel = (track: AnimationTrack) => {
    const bone = skeleton.find((b) => b.uuid === track.boneUuid);
    const propertyLabels: Record<string, string> = {
      position: '位置',
      rotation: '旋转',
      scale: '缩放',
    };
    return `${bone?.name || track.boneUuid} - ${propertyLabels[track.property]}.${track.component.toUpperCase()}`;
  };

  const editModes: { mode: CurveEditMode; icon: typeof MousePointer2; label: string; shortcut: string }[] = [
    { mode: 'select', icon: MousePointer2, label: '选择', shortcut: '1' },
    { mode: 'add', icon: Plus, label: '添加', shortcut: '2' },
    { mode: 'delete', icon: Trash2, label: '删除', shortcut: '3' },
    { mode: 'move', icon: Move, label: '移动', shortcut: '4' },
    { mode: 'tangent', icon: PenTool, label: '切线', shortcut: '5' },
  ];

  const interpolationTypes: { value: 'linear' | 'smooth' | 'step' | 'bezier' | 'spline'; label: string }[] = [
    { value: 'linear', label: '线性' },
    { value: 'smooth', label: '平滑' },
    { value: 'step', label: '阶梯' },
    { value: 'bezier', label: '贝塞尔' },
    { value: 'spline', label: '样条' },
  ];

  return (
    <div ref={containerRef} className="h-full flex flex-col bg-space-800/50 border border-space-600 rounded-lg overflow-hidden">
      <div className="flex items-center gap-2 px-3 py-2 border-b border-space-600 bg-space-800/80" style={{ height: TOOLBAR_HEIGHT }}>
        <div className="flex items-center gap-1 pr-2 border-r border-space-600">
          {editModes.map(({ mode, icon: Icon, label, shortcut }) => (
            <Button
              key={mode}
              variant={editorState.mode === mode ? 'primary' : 'ghost'}
              size="sm"
              onClick={() => setEditMode(mode)}
              title={`${label} (${shortcut})`}
            >
              <Icon size={16} />
              <span className="hidden sm:inline text-xs ml-1">{label}</span>
            </Button>
          ))}
        </div>

        <div className="flex items-center gap-1 px-2 border-r border-space-600">
          <Button variant="ghost" size="sm" onClick={handleFitToView} title="适配视图">
            <Maximize2 size={16} />
            <span className="hidden sm:inline text-xs ml-1">适配</span>
          </Button>
          <Button
            variant={showGrid ? 'secondary' : 'ghost'}
            size="sm"
            onClick={() => setShowGrid(!showGrid)}
            title="显示网格"
          >
            <Grid3X3 size={16} />
            <span className="hidden sm:inline text-xs ml-1">网格</span>
          </Button>
          <Button
            variant={editorState.snapToGrid ? 'secondary' : 'ghost'}
            size="sm"
            onClick={toggleSnapToGrid}
            title="吸附网格"
          >
            <Magnet size={16} />
            <span className="hidden sm:inline text-xs ml-1">吸附</span>
          </Button>
        </div>

        <div className="flex items-center gap-1 px-2 border-r border-space-600">
          <span className="text-xs text-gray-400 mr-1">插值:</span>
          {interpolationTypes.map(({ value, label }) => (
            <Button
              key={value}
              variant={selectedInterpolation === value ? 'secondary' : 'ghost'}
              size="sm"
              onClick={() => handleInterpolationChange(value)}
              title={label}
            >
              <span className="text-xs">{label}</span>
            </Button>
          ))}
        </div>

        <div className="flex-1" />

        <div className="flex items-center gap-2 text-xs text-gray-400">
          <span>缩放: {(editorState.zoom * 100).toFixed(0)}%</span>
          <span>选中: {editorState.selectedKeyframes.length}</span>
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden">
        <div
          className="flex-shrink-0 border-r border-space-600 bg-space-800/50 overflow-y-auto"
          style={{ width: TRACK_HEADER_WIDTH }}
        >
          <div className="px-3 py-2 text-xs text-gray-400 border-b border-space-600 bg-space-800/80 font-medium">
            曲线轨道
          </div>
          <div className="py-1">
            {filteredTracks.map((track, index) => {
              const isSelected = editorState.selectedTrackIndices.includes(index);
              const isVisible = editorState.selectedTrackIndices.length === 0 || isSelected;
              const color = TRACK_COLORS[track.component];

              return (
                <div
                  key={`${track.boneUuid}-${track.property}-${track.component}`}
                  className={cn(
                    'flex items-center gap-2 px-3 py-1.5 text-sm cursor-pointer transition-colors',
                    isVisible ? 'text-gray-200' : 'text-gray-500',
                    'hover:bg-space-700/50'
                  )}
                  onClick={() => toggleTrackSelection(index)}
                >
                  <ChevronRight
                    size={14}
                    className={cn('transition-transform', isVisible && 'rotate-90 text-cyber-400')}
                  />
                  <div
                    className="w-3 h-3 rounded-sm flex-shrink-0"
                    style={{ backgroundColor: color }}
                  />
                  <span className="truncate text-xs">{getTrackLabel(track)}</span>
                </div>
              );
            })}
          </div>
        </div>

        <div className="flex-1 relative overflow-hidden">
          <canvas
            ref={canvasRef}
            className="block"
            onMouseDown={handleCanvasMouseDown}
            onMouseMove={handleCanvasMouseMove}
            onMouseUp={handleCanvasMouseUp}
            onMouseLeave={handleCanvasMouseUp}
            onContextMenu={handleCanvasContextMenu}
            onWheel={handleCanvasWheel}
          />
        </div>
      </div>

      {contextMenu.visible && (
        <div
          ref={contextMenuRef}
          className="fixed z-50 min-w-[160px] bg-space-800 border border-space-600 rounded-md shadow-lg py-1"
          style={{ left: contextMenu.x, top: contextMenu.y }}
        >
          <div className="px-3 py-1.5 text-xs text-gray-500 border-b border-space-700">
            插值类型
          </div>
          {interpolationTypes.map(({ value, label }) => (
            <button
              key={value}
              className="w-full px-3 py-1.5 text-left text-sm text-gray-300 hover:bg-space-700 hover:text-cyber-400 flex items-center gap-2 transition-colors"
              onClick={() => handleInterpolationChange(value)}
            >
              <span className="w-2 h-2 rounded-sm" style={{
                backgroundColor: value === 'linear' ? '#3b82f6' : value === 'smooth' ? '#22c55e' : value === 'step' ? '#eab308' : '#a78bfa'
              }} />
              {label}
            </button>
          ))}

          <div className="my-1 border-t border-space-700" />

          <div className="px-3 py-1.5 text-xs text-gray-500 border-b border-space-700">
            切线
          </div>
          <button
            className="w-full px-3 py-1.5 text-left text-sm text-gray-300 hover:bg-space-700 hover:text-cyber-400 flex items-center gap-2 transition-colors"
            onClick={handleBreakTangents}
          >
            <Unlink size={14} />
            断开切线
          </button>
          <button
            className="w-full px-3 py-1.5 text-left text-sm text-gray-300 hover:bg-space-700 hover:text-cyber-400 flex items-center gap-2 transition-colors"
            onClick={handleUnifyTangents}
          >
            <Link size={14} />
            统一切线
          </button>

          <div className="my-1 border-t border-space-700" />

          <button
            className="w-full px-3 py-1.5 text-left text-sm text-gray-300 hover:bg-space-700 hover:text-cyber-400 flex items-center gap-2 transition-colors"
            onClick={handleCopyKeyframe}
          >
            <Copy size={14} />
            复制
          </button>
          <button
            className="w-full px-3 py-1.5 text-left text-sm text-gray-300 hover:bg-space-700 hover:text-cyber-400 flex items-center gap-2 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            onClick={handlePasteKeyframe}
            disabled={!clipboardKeyframe}
          >
            <Clipboard size={14} />
            粘贴
          </button>

          <div className="my-1 border-t border-space-700" />

          <button
            className="w-full px-3 py-1.5 text-left text-sm text-red-400 hover:bg-red-500/10 hover:text-red-300 flex items-center gap-2 transition-colors"
            onClick={handleDeleteKeyframe}
          >
            <Trash2 size={14} />
            删除
          </button>
        </div>
      )}
    </div>
  );
};

CurveEditor.displayName = 'CurveEditor';

export { CurveEditor };
