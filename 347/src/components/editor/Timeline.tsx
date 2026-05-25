import { useState, useRef, useEffect, useMemo, useCallback } from 'react';
import {
  Play,
  Pause,
  SkipBack,
  SkipForward,
  Square,
  Repeat,
  Repeat1,
  ArrowLeftRight,
  Copy,
  Trash2,
  Clipboard,
} from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { NumberInput } from '@/components/ui/NumberInput';
import { useEditorStore } from '@/store/editorStore';
import { useKeyframeEditor } from '@/hooks/useKeyframeEditor';
import { cn } from '@/lib/utils';
import type { BoneNode } from '@/types/skeleton';
import type { Keyframe, AnimationTrack } from '@/types/animation';

interface SelectedKeyframe {
  clipUuid: string;
  trackIndex: number;
  keyframeIndex: number;
}

interface ContextMenuState {
  visible: boolean;
  x: number;
  y: number;
  keyframe: SelectedKeyframe | null;
}

const PLAYBACK_SPEEDS = [0.25, 0.5, 1, 2, 4];
const TRACK_HEIGHT = 28;
const TIMELINE_HEADER_HEIGHT = 32;
const RULER_HEIGHT = 36;
const TRACK_HEADER_WIDTH = 180;
const MIN_PIXELS_PER_SECOND = 10;
const MAX_PIXELS_PER_SECOND = 200;

const Timeline = () => {
  const {
    skeleton,
    selectedBoneUuid,
    currentTime,
    isPlaying,
    playbackSpeed,
    loopMode,
    frameRate,
    togglePlay,
    setCurrentTime,
    setPlaybackSpeed,
    setLoopMode,
    nextFrame,
    prevFrame,
    stop,
    getDuration,
    animationClips,
    updateKeyframe,
    deleteKeyframe,
  } = useEditorStore();

  const { activeClip } = useKeyframeEditor();

  const [zoom, setZoom] = useState(50);
  const [panOffset, setPanOffset] = useState(0);
  const [selectedKeyframes, setSelectedKeyframes] = useState<SelectedKeyframe[]>([]);
  const [contextMenu, setContextMenu] = useState<ContextMenuState>({
    visible: false,
    x: 0,
    y: 0,
    keyframe: null,
  });
  const [clipboardKeyframe, setClipboardKeyframe] = useState<Keyframe | null>(null);
  const [isDraggingPlayhead, setIsDraggingPlayhead] = useState(false);
  const [isDraggingKeyframe, setIsDraggingKeyframe] = useState(false);
  const [isPanning, setIsPanning] = useState(false);
  const [dragStartX, setDragStartX] = useState(0);
  const [dragStartTime, setDragStartTime] = useState(0);
  const [panStartX, setPanStartX] = useState(0);
  const [panStartOffset, setPanStartOffset] = useState(0);
  const [timeDisplayMode, setTimeDisplayMode] = useState<'frame' | 'seconds'>('seconds');

  const timelineRef = useRef<HTMLDivElement>(null);
  const rulerRef = useRef<HTMLDivElement>(null);
  const contextMenuRef = useRef<HTMLDivElement>(null);

  const duration = useMemo(() => getDuration(), [getDuration]);
  const pixelsPerSecond = useMemo(
    () => MIN_PIXELS_PER_SECOND + (zoom / 100) * (MAX_PIXELS_PER_SECOND - MIN_PIXELS_PER_SECOND),
    [zoom]
  );
  const timelineWidth = useMemo(() => duration * pixelsPerSecond, [duration, pixelsPerSecond]);

  const boneTracks = useMemo(() => {
    const tracks: { bone: BoneNode; tracks: AnimationTrack[] }[] = [];
    const boneMap = new Map(skeleton.map((b) => [b.uuid, b]));

    const processedBones = new Set<string>();

    if (activeClip) {
      activeClip.tracks.forEach((track) => {
        if (!processedBones.has(track.boneUuid)) {
          processedBones.add(track.boneUuid);
          const bone = boneMap.get(track.boneUuid);
          if (bone) {
            const boneTracks = activeClip.tracks.filter((t) => t.boneUuid === track.boneUuid);
            tracks.push({ bone, tracks: boneTracks });
          }
        }
      });
    }

    skeleton.forEach((bone) => {
      if (!processedBones.has(bone.uuid)) {
        processedBones.add(bone.uuid);
        tracks.push({ bone, tracks: [] });
      }
    });

    return tracks;
  }, [skeleton, activeClip]);

  const totalTrackHeight = useMemo(
    () => boneTracks.length * TRACK_HEIGHT,
    [boneTracks.length]
  );

  const currentFrame = useMemo(
    () => Math.floor(currentTime * frameRate),
    [currentTime, frameRate]
  );

  const totalFrames = useMemo(
    () => Math.ceil(duration * frameRate),
    [duration, frameRate]
  );

  const handlePlayheadMouseDown = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDraggingPlayhead(true);
      setDragStartX(e.clientX);
      setDragStartTime(currentTime);
    },
    [currentTime]
  );

  const handleTimelineMouseDown = useCallback(
    (e: React.MouseEvent) => {
      if (e.button === 0 && e.target === timelineRef.current) {
        setIsPanning(true);
        setPanStartX(e.clientX);
        setPanStartOffset(panOffset);
      } else if (e.button === 0) {
        const rect = timelineRef.current?.getBoundingClientRect();
        if (rect) {
          const x = e.clientX - rect.left - panOffset;
          const time = Math.max(0, Math.min(x / pixelsPerSecond, duration));
          setCurrentTime(time);
          setIsDraggingPlayhead(true);
          setDragStartX(e.clientX);
          setDragStartTime(time);
        }
      }
      setSelectedKeyframes([]);
    },
    [panOffset, pixelsPerSecond, duration, setCurrentTime]
  );

  const handleMouseMove = useCallback(
    (e: MouseEvent) => {
      if (isDraggingPlayhead) {
        const deltaX = e.clientX - dragStartX;
        const deltaTime = deltaX / pixelsPerSecond;
        const newTime = Math.max(0, Math.min(dragStartTime + deltaTime, duration));
        setCurrentTime(newTime);
      }

      if (isDraggingKeyframe && selectedKeyframes.length > 0 && activeClip) {
        const deltaX = e.clientX - dragStartX;
        const deltaTime = deltaX / pixelsPerSecond;

        selectedKeyframes.forEach(({ clipUuid, trackIndex, keyframeIndex }) => {
          const clip = animationClips.find((c) => c.uuid === clipUuid);
          if (clip && clip.tracks[trackIndex] && clip.tracks[trackIndex].keyframes[keyframeIndex]) {
            const keyframe = clip.tracks[trackIndex].keyframes[keyframeIndex];
            const newTime = Math.max(0, Math.min(keyframe.time + deltaTime, duration));
            updateKeyframe(clipUuid, trackIndex, keyframeIndex, {
              ...keyframe,
              time: newTime,
            });
          }
        });

        setDragStartX(e.clientX);
      }

      if (isPanning) {
        const deltaX = e.clientX - panStartX;
        setPanOffset(Math.min(0, panStartOffset + deltaX));
      }
    },
    [
      isDraggingPlayhead,
      isDraggingKeyframe,
      isPanning,
      dragStartX,
      dragStartTime,
      pixelsPerSecond,
      duration,
      setCurrentTime,
      selectedKeyframes,
      activeClip,
      animationClips,
      updateKeyframe,
      panStartX,
      panStartOffset,
    ]
  );

  const handleMouseUp = useCallback(() => {
    setIsDraggingPlayhead(false);
    setIsDraggingKeyframe(false);
    setIsPanning(false);
  }, []);

  const handleWheel = useCallback(
    (e: React.WheelEvent) => {
      e.preventDefault();
      e.stopPropagation();

      const delta = e.deltaY > 0 ? -5 : 5;
      const newZoom = Math.max(0, Math.min(100, zoom + delta));

      if (timelineRef.current) {
        const rect = timelineRef.current.getBoundingClientRect();
        const mouseX = e.clientX - rect.left - panOffset;
        const timeAtMouse = mouseX / pixelsPerSecond;

        const newPixelsPerSecond =
          MIN_PIXELS_PER_SECOND +
          (newZoom / 100) * (MAX_PIXELS_PER_SECOND - MIN_PIXELS_PER_SECOND);
        const newMouseX = timeAtMouse * newPixelsPerSecond;
        const newPanOffset = e.clientX - rect.left - newMouseX;

        setZoom(newZoom);
        setPanOffset(Math.min(0, newPanOffset));
      } else {
        setZoom(newZoom);
      }
    },
    [zoom, panOffset, pixelsPerSecond]
  );

  useEffect(() => {
    if (isDraggingPlayhead || isDraggingKeyframe || isPanning) {
      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleMouseUp);
    }

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDraggingPlayhead, isDraggingKeyframe, isPanning, handleMouseMove, handleMouseUp]);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (
        contextMenu.visible &&
        contextMenuRef.current &&
        !contextMenuRef.current.contains(e.target as Node)
      ) {
        setContextMenu({ visible: false, x: 0, y: 0, keyframe: null });
      }
    };

    if (contextMenu.visible) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [contextMenu.visible]);

  useEffect(() => {
    if (!isPlaying) return;

    const interval = setInterval(() => {
      const { currentTime, loopMode, getDuration, setCurrentTime } = useEditorStore.getState();
      const dur = getDuration();
      const frameTime = 1 / frameRate;
      const deltaTime = frameTime * playbackSpeed;

      if (loopMode === 'once') {
        const newTime = currentTime + deltaTime;
        if (newTime >= dur) {
          setCurrentTime(dur);
          useEditorStore.setState({ isPlaying: false });
        } else {
          setCurrentTime(newTime);
        }
      } else if (loopMode === 'loop') {
        const newTime = (currentTime + deltaTime) % dur;
        setCurrentTime(newTime);
      } else if (loopMode === 'pingpong') {
        const state = useEditorStore.getState();
        const pingpongDirection = (state as unknown as { pingpongDirection?: number }).pingpongDirection ?? 1;
        let newTime = currentTime + deltaTime * pingpongDirection;
        let newDirection = pingpongDirection;

        if (newTime >= dur) {
          newTime = dur - (newTime - dur);
          newDirection = -1;
        } else if (newTime <= 0) {
          newTime = -newTime;
          newDirection = 1;
        }

        setCurrentTime(newTime);
        useEditorStore.setState({ pingpongDirection: newDirection } as unknown as Partial<typeof state>);
      }
    }, 1000 / frameRate);

    return () => clearInterval(interval);
  }, [isPlaying, playbackSpeed, loopMode, frameRate]);

  const handleKeyframeClick = useCallback(
    (
      e: React.MouseEvent,
      clipUuid: string,
      trackIndex: number,
      keyframeIndex: number
    ) => {
      e.stopPropagation();

      const existing = selectedKeyframes.find(
        (k) =>
          k.clipUuid === clipUuid &&
          k.trackIndex === trackIndex &&
          k.keyframeIndex === keyframeIndex
      );

      if (e.shiftKey) {
        if (existing) {
          setSelectedKeyframes(
            selectedKeyframes.filter(
              (k) =>
                !(
                  k.clipUuid === clipUuid &&
                  k.trackIndex === trackIndex &&
                  k.keyframeIndex === keyframeIndex
                )
            )
          );
        } else {
          setSelectedKeyframes([
            ...selectedKeyframes,
            { clipUuid, trackIndex, keyframeIndex },
          ]);
        }
      } else {
        if (!existing) {
          setSelectedKeyframes([{ clipUuid, trackIndex, keyframeIndex }]);
        }
        setIsDraggingKeyframe(true);
        setDragStartX(e.clientX);
      }
    },
    [selectedKeyframes]
  );

  const handleKeyframeContextMenu = useCallback(
    (
      e: React.MouseEvent,
      clipUuid: string,
      trackIndex: number,
      keyframeIndex: number
    ) => {
      e.preventDefault();
      e.stopPropagation();

      const existing = selectedKeyframes.find(
        (k) =>
          k.clipUuid === clipUuid &&
          k.trackIndex === trackIndex &&
          k.keyframeIndex === keyframeIndex
      );

      if (!existing) {
        setSelectedKeyframes([{ clipUuid, trackIndex, keyframeIndex }]);
      }

      setContextMenu({
        visible: true,
        x: e.clientX,
        y: e.clientY,
        keyframe: { clipUuid, trackIndex, keyframeIndex },
      });
    },
    [selectedKeyframes]
  );

  const handleCopyKeyframe = useCallback(() => {
    if (selectedKeyframes.length > 0 && activeClip) {
      const { clipUuid, trackIndex, keyframeIndex } = selectedKeyframes[0];
      const clip = animationClips.find((c) => c.uuid === clipUuid);
      if (clip && clip.tracks[trackIndex] && clip.tracks[trackIndex].keyframes[keyframeIndex]) {
        const keyframe = clip.tracks[trackIndex].keyframes[keyframeIndex];
        setClipboardKeyframe({ ...keyframe });
      }
    }
    setContextMenu({ visible: false, x: 0, y: 0, keyframe: null });
  }, [selectedKeyframes, activeClip, animationClips]);

  const handlePasteKeyframe = useCallback(() => {
    if (clipboardKeyframe && selectedKeyframes.length > 0 && activeClip) {
      const { clipUuid, trackIndex } = selectedKeyframes[0];
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
      }
    }
    setContextMenu({ visible: false, x: 0, y: 0, keyframe: null });
  }, [clipboardKeyframe, selectedKeyframes, activeClip, animationClips, currentTime]);

  const handleDeleteKeyframe = useCallback(() => {
    const sorted = [...selectedKeyframes].sort(
      (a, b) => b.keyframeIndex - a.keyframeIndex
    );

    sorted.forEach(({ clipUuid, trackIndex, keyframeIndex }) => {
      deleteKeyframe(clipUuid, trackIndex, keyframeIndex);
    });

    setSelectedKeyframes([]);
    setContextMenu({ visible: false, x: 0, y: 0, keyframe: null });
  }, [selectedKeyframes, deleteKeyframe]);

  const handleTimeInputChange = useCallback(
    (value: number) => {
      if (timeDisplayMode === 'frame') {
        setCurrentTime(value / frameRate);
      } else {
        setCurrentTime(value);
      }
    },
    [timeDisplayMode, frameRate, setCurrentTime]
  );

  const handleSpeedClick = useCallback(
    (speed: number) => {
      if (playbackSpeed === speed) {
        setPlaybackSpeed(1);
      } else {
        setPlaybackSpeed(speed);
      }
    },
    [playbackSpeed, setPlaybackSpeed]
  );

  const handleLoopModeClick = useCallback(() => {
    const modes: ('once' | 'loop' | 'pingpong')[] = ['once', 'loop', 'pingpong'];
    const currentIndex = modes.indexOf(loopMode);
    const nextIndex = (currentIndex + 1) % modes.length;
    setLoopMode(modes[nextIndex]);
  }, [loopMode, setLoopMode]);

  const formatTime = useCallback(
    (time: number) => {
      if (timeDisplayMode === 'frame') {
        return Math.floor(time * frameRate);
      }
      return time.toFixed(2);
    },
    [timeDisplayMode, frameRate]
  );

  const renderRulerTicks = useMemo(() => {
    const ticks: { time: number; label: string; major: boolean }[] = [];
    const pixelsPerTick = pixelsPerSecond;
    const tickInterval = pixelsPerTick >= 100 ? 0.1 : pixelsPerTick >= 50 ? 0.5 : 1;

    for (let t = 0; t <= duration; t += tickInterval) {
      const isMajor = Math.abs(t - Math.round(t)) < 0.001;
      ticks.push({
        time: t,
        label: isMajor ? `${t.toFixed(0)}s` : '',
        major: isMajor,
      });
    }

    return ticks;
  }, [duration, pixelsPerSecond]);

  const isKeyframeSelected = useCallback(
    (clipUuid: string, trackIndex: number, keyframeIndex: number) => {
      return selectedKeyframes.some(
        (k) =>
          k.clipUuid === clipUuid &&
          k.trackIndex === trackIndex &&
          k.keyframeIndex === keyframeIndex
      );
    },
    [selectedKeyframes]
  );

  const LoopIcon = loopMode === 'once' ? Repeat1 : loopMode === 'pingpong' ? ArrowLeftRight : Repeat;

  return (
    <div className="h-full flex flex-col bg-space-800/50 border border-space-600 rounded-lg overflow-hidden">
      <div className="flex items-center gap-2 px-3 py-2 border-b border-space-600 bg-space-800/80">
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="sm" onClick={prevFrame} title="上一帧">
            <SkipBack size={16} />
          </Button>
          <Button variant="primary" size="sm" onClick={togglePlay} title={isPlaying ? '暂停' : '播放'}>
            {isPlaying ? <Pause size={16} /> : <Play size={16} />}
          </Button>
          <Button variant="ghost" size="sm" onClick={nextFrame} title="下一帧">
            <SkipForward size={16} />
          </Button>
          <Button variant="ghost" size="sm" onClick={stop} title="停止">
            <Square size={16} />
          </Button>
        </div>

        <div className="w-px h-6 bg-space-600 mx-1" />

        <div className="flex items-center gap-1">
          {PLAYBACK_SPEEDS.map((speed) => (
            <Button
              key={speed}
              variant={playbackSpeed === speed ? 'secondary' : 'ghost'}
              size="sm"
              onClick={() => handleSpeedClick(speed)}
              className="px-2 min-w-[44px]"
            >
              {speed}x
            </Button>
          ))}
        </div>

        <div className="w-px h-6 bg-space-600 mx-1" />

        <Button
          variant="ghost"
          size="sm"
          onClick={handleLoopModeClick}
          title={`循环模式: ${loopMode === 'once' ? '单次' : loopMode === 'loop' ? '循环' : '乒乓'}`}
          className={cn(loopMode !== 'loop' && 'text-cyber-400')}
        >
          <LoopIcon size={16} />
          <span className="text-xs ml-1">
            {loopMode === 'once' ? '单次' : loopMode === 'loop' ? '循环' : '乒乓'}
          </span>
        </Button>

        <div className="flex-1" />

        <div className="flex items-center gap-2">
          <button
            className={cn(
              'text-xs px-2 py-1 rounded transition-colors',
              timeDisplayMode === 'seconds'
                ? 'bg-cyber-500/20 text-cyber-400'
                : 'text-gray-400 hover:text-gray-300'
            )}
            onClick={() => setTimeDisplayMode('seconds')}
          >
            秒
          </button>
          <button
            className={cn(
              'text-xs px-2 py-1 rounded transition-colors',
              timeDisplayMode === 'frame'
                ? 'bg-cyber-500/20 text-cyber-400'
                : 'text-gray-400 hover:text-gray-300'
            )}
            onClick={() => setTimeDisplayMode('frame')}
          >
            帧
          </button>
          <NumberInput
            value={timeDisplayMode === 'frame' ? currentFrame : currentTime}
            onChange={handleTimeInputChange}
            min={0}
            max={timeDisplayMode === 'frame' ? totalFrames : duration}
            step={timeDisplayMode === 'frame' ? 1 : 0.1}
            precision={timeDisplayMode === 'frame' ? 0 : 2}
            className="w-24"
          />
          <span className="text-xs text-gray-500">
            / {timeDisplayMode === 'frame' ? totalFrames : duration.toFixed(2)}
          </span>
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden">
        <div
          className="flex-shrink-0 border-r border-space-600 bg-space-800/50"
          style={{ width: TRACK_HEADER_WIDTH }}
        >
          <div
            className="flex items-center px-3 text-xs text-gray-400 border-b border-space-600 bg-space-800/80"
            style={{ height: RULER_HEIGHT }}
          >
            轨道
          </div>
          <div className="overflow-hidden">
            {boneTracks.map(({ bone }) => (
              <div
                key={bone.uuid}
                className={cn(
                  'flex items-center px-3 text-sm border-b border-space-600/50 cursor-pointer transition-colors',
                  selectedBoneUuid === bone.uuid
                    ? 'bg-cyber-500/20 text-cyber-400'
                    : 'text-gray-300 hover:bg-space-700/50'
                )}
                style={{ height: TRACK_HEIGHT }}
                onClick={() => useEditorStore.getState().setSelectedBone(bone.uuid)}
              >
                <span className="truncate">{bone.name}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="flex-1 flex flex-col overflow-hidden">
          <div
            ref={rulerRef}
            className="flex-shrink-0 overflow-hidden border-b border-space-600 bg-space-800/80"
            style={{ height: RULER_HEIGHT }}
            onWheel={handleWheel}
          >
            <div
              className="relative h-full"
              style={{ width: timelineWidth, transform: `translateX(${panOffset}px)` }}
            >
              {renderRulerTicks.map((tick) => (
                <div
                  key={tick.time}
                  className="absolute top-0 bottom-0 flex flex-col items-center"
                  style={{ left: tick.time * pixelsPerSecond }}
                >
                  <div
                    className={cn(
                      'w-px',
                      tick.major ? 'h-full bg-space-500' : 'h-3 bg-space-600'
                    )}
                  />
                  {tick.label && (
                    <span className="text-[10px] text-gray-500 mt-1">{tick.label}</span>
                  )}
                </div>
              ))}
            </div>
          </div>

          <div
            ref={timelineRef}
            className="flex-1 overflow-auto cursor-grab active:cursor-grabbing"
            style={{ scrollbarWidth: 'thin' }}
            onMouseDown={handleTimelineMouseDown}
            onWheel={handleWheel}
          >
            <div
              className="relative"
              style={{
                width: timelineWidth,
                height: totalTrackHeight,
                transform: `translateX(${panOffset}px)`,
              }}
            >
              {boneTracks.map(({ bone, tracks }, trackGroupIndex) => (
                <div
                  key={bone.uuid}
                  className={cn(
                    'relative border-b border-space-600/50 transition-colors',
                    selectedBoneUuid === bone.uuid
                      ? 'bg-cyber-500/5'
                      : trackGroupIndex % 2 === 0
                      ? 'bg-space-800/30'
                      : 'bg-space-900/30'
                  )}
                  style={{ height: TRACK_HEIGHT }}
                >
                  {renderRulerTicks
                    .filter((t) => t.major)
                    .map((tick) => (
                      <div
                        key={tick.time}
                        className="absolute top-0 bottom-0 w-px bg-space-700/50"
                        style={{ left: tick.time * pixelsPerSecond }}
                      />
                    ))}

                  {tracks.flatMap((track, trackIdx) =>
                    track.keyframes.map((keyframe, keyframeIdx) => {
                      const trackIndex = activeClip?.tracks.findIndex(
                        (t) =>
                          t.boneUuid === track.boneUuid &&
                          t.property === track.property &&
                          t.component === track.component
                      ) ?? -1;

                      const selected =
                        activeClip &&
                        isKeyframeSelected(activeClip.uuid, trackIndex, keyframeIdx);

                      return (
                        <div
                          key={`${trackIdx}-${keyframeIdx}`}
                          className={cn(
                            'absolute top-1/2 -translate-y-1/2 cursor-pointer transition-transform hover:scale-125',
                            selected && 'z-10'
                          )}
                          style={{
                            left: keyframe.time * pixelsPerSecond - 6,
                          }}
                          onClick={(e) =>
                            activeClip &&
                            handleKeyframeClick(e, activeClip.uuid, trackIndex, keyframeIdx)
                          }
                          onContextMenu={(e) =>
                            activeClip &&
                            handleKeyframeContextMenu(
                              e,
                              activeClip.uuid,
                              trackIndex,
                              keyframeIdx
                            )
                          }
                        >
                          <div
                            className={cn(
                              'w-3 h-3 rotate-45 border-2',
                              selected
                                ? 'bg-yellow-400 border-yellow-300 shadow-lg shadow-yellow-500/50'
                                : 'bg-amber-500 border-amber-400 hover:bg-amber-400'
                            )}
                          />
                        </div>
                      );
                    })
                  )}
                </div>
              ))}

              <div
                className="absolute top-0 bottom-0 w-0.5 bg-red-500 z-20 cursor-ew-resize pointer-events-auto"
                style={{
                  left: currentTime * pixelsPerSecond - 1,
                }}
                onMouseDown={handlePlayheadMouseDown}
              >
                <div className="absolute -top-1 left-1/2 -translate-x-1/2 w-0 h-0 border-l-[6px] border-l-transparent border-r-[6px] border-r-transparent border-t-[8px] border-t-red-500" />
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="flex items-center justify-between px-3 py-1.5 border-t border-space-600 bg-space-800/80 text-xs text-gray-400">
        <div className="flex items-center gap-4">
          <span>总时长: {duration.toFixed(2)}s</span>
          <span>当前帧: {currentFrame}</span>
          <span>帧率: {frameRate} FPS</span>
        </div>
        <div className="flex items-center gap-2">
          <span>缩放: {zoom}%</span>
          <span>关键帧: {selectedKeyframes.length} 选中</span>
        </div>
      </div>

      {contextMenu.visible && (
        <div
          ref={contextMenuRef}
          className="fixed z-50 min-w-[140px] bg-space-800 border border-space-600 rounded-md shadow-lg py-1"
          style={{ left: contextMenu.x, top: contextMenu.y }}
        >
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
          <div className="my-1 border-t border-space-600" />
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

Timeline.displayName = 'Timeline';

export { Timeline };
