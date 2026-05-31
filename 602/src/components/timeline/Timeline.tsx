import React, { useRef, useState, useCallback, useEffect } from 'react';
import { Play, Pause, SkipBack, SkipForward, Repeat, ZoomIn, ZoomOut } from 'lucide-react';
import { useProjectStore } from '@/store/useProjectStore';
import { useEditorStore } from '@/store/useEditorStore';

export const Timeline: React.FC = () => {
  const { project } = useProjectStore();
  const {
    currentTime,
    setCurrentTime,
    isPlaying,
    setIsPlaying,
    isLooping,
    setIsLooping,
    zoom,
    setZoom,
  } = useEditorStore();
  
  const timelineRef = useRef<HTMLDivElement>(null);
  const [isDraggingPlayhead, setIsDraggingPlayhead] = useState(false);
  const playheadRef = useRef<HTMLDivElement>(null);

  const duration = project.duration;
  const pixelsPerSecond = 100 * zoom;

  const getTimelineTime = useCallback((clientX: number) => {
    if (!timelineRef.current) return 0;
    const rect = timelineRef.current.getBoundingClientRect();
    const x = clientX - rect.left - 200;
    return Math.max(0, Math.min(duration, x / pixelsPerSecond));
  }, [duration, pixelsPerSecond]);

  const handleTimelineClick = useCallback((e: React.MouseEvent) => {
    const time = getTimelineTime(e.clientX);
    setCurrentTime(time);
  }, [getTimelineTime, setCurrentTime]);

  const handlePlayheadMouseDown = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    setIsDraggingPlayhead(true);
  }, []);

  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (isDraggingPlayhead) {
      const time = getTimelineTime(e.clientX);
      setCurrentTime(time);
    }
  }, [isDraggingPlayhead, getTimelineTime, setCurrentTime]);

  const handleMouseUp = useCallback(() => {
    setIsDraggingPlayhead(false);
  }, []);

  useEffect(() => {
    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [handleMouseMove, handleMouseUp]);

  useEffect(() => {
    let animationFrame: number;
    let lastTime = performance.now();

    const animate = (now: number) => {
      if (!isPlaying) return;

      const delta = (now - lastTime) / 1000;
      lastTime = now;

      const newTime = currentTime + delta;

      if (newTime >= duration) {
        if (isLooping) {
          setCurrentTime(0);
        } else {
          setIsPlaying(false);
          setCurrentTime(duration);
        }
      } else {
        setCurrentTime(newTime);
      }

      animationFrame = requestAnimationFrame(animate);
    };

    if (isPlaying) {
      lastTime = performance.now();
      animationFrame = requestAnimationFrame(animate);
    }

    return () => {
      if (animationFrame) {
        cancelAnimationFrame(animationFrame);
      }
    };
  }, [isPlaying, isLooping, currentTime, duration, setCurrentTime, setIsPlaying]);

  const formatTime = (time: number) => {
    const minutes = Math.floor(time / 60);
    const seconds = Math.floor(time % 60);
    const ms = Math.floor((time % 1) * 100);
    return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}.${ms.toString().padStart(2, '0')}`;
  };

  const renderTimeMarkers = () => {
    const markers = [];
    const interval = zoom > 2 ? 0.1 : zoom > 1 ? 0.5 : 1;
    
    for (let t = 0; t <= duration; t += interval) {
      const isMajor = t % 1 === 0;
      markers.push(
        <div
          key={t}
          className="absolute"
          style={{ left: t * pixelsPerSecond }}
        >
          <div
            className={`border-l ${isMajor ? 'border-text-muted h-4' : 'border-border-primary h-2'}`}
          />
          {isMajor && (
            <span className="absolute text-[10px] text-text-muted -ml-3 top-4">
              {t}s
            </span>
          )}
        </div>
      );
    }
    return markers;
  };

  return (
    <div className="h-full flex flex-col bg-bg-secondary border-t border-border-primary">
      <div className="flex items-center justify-between px-4 py-2 border-b border-border-primary">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setCurrentTime(0)}
            className="btn-icon text-text-secondary hover:text-text-primary"
            title="Go to start"
          >
            <SkipBack size={16} />
          </button>
          
          <button
            onClick={() => setIsPlaying(!isPlaying)}
            className="btn-icon bg-bg-tertiary text-accent-success hover:bg-accent-success hover:text-bg-primary transition-colors"
            title={isPlaying ? 'Pause' : 'Play'}
          >
            {isPlaying ? <Pause size={18} /> : <Play size={18} />}
          </button>
          
          <button
            onClick={() => setCurrentTime(duration)}
            className="btn-icon text-text-secondary hover:text-text-primary"
            title="Go to end"
          >
            <SkipForward size={16} />
          </button>
          
          <button
            onClick={() => setIsLooping(!isLooping)}
            className={`btn-icon ${isLooping ? 'text-accent-secondary' : 'text-text-secondary hover:text-text-primary'}`}
            title="Toggle loop"
          >
            <Repeat size={16} />
          </button>
        </div>

        <div className="flex items-center gap-4">
          <span className="font-mono text-sm text-text-secondary">
            {formatTime(currentTime)} / {formatTime(duration)}
          </span>
          
          <div className="flex items-center gap-1">
            <button
              onClick={() => setZoom(zoom * 0.8)}
              className="btn-icon text-text-secondary hover:text-text-primary"
              title="Zoom out"
            >
              <ZoomOut size={14} />
            </button>
            <span className="text-xs text-text-muted w-12 text-center">
              {Math.round(zoom * 100)}%
            </span>
            <button
              onClick={() => setZoom(zoom * 1.25)}
              className="btn-icon text-text-secondary hover:text-text-primary"
              title="Zoom in"
            >
              <ZoomIn size={14} />
            </button>
          </div>
        </div>
      </div>

      <div
        ref={timelineRef}
        className="flex-1 overflow-auto relative"
        onClick={handleTimelineClick}
      >
        <div className="h-8 border-b border-border-primary relative sticky top-0 bg-bg-secondary z-10">
          <div className="absolute left-[200px] right-0 top-0 h-full">
            {renderTimeMarkers()}
          </div>
        </div>

        <div className="relative">
          <div
            className="absolute top-0 w-0.5 bg-accent-primary z-20 pointer-events-none"
            style={{
              left: 200 + currentTime * pixelsPerSecond,
              height: '100%',
            }}
          >
            <div
              ref={playheadRef}
              className="absolute -top-0 -left-2 w-4 h-4 bg-accent-primary rounded cursor-ew-resize pointer-events-auto"
              onMouseDown={handlePlayheadMouseDown}
              style={{
                clipPath: 'polygon(50% 100%, 0% 0%, 100% 0%)',
              }}
            />
          </div>

          <div className="relative">
            {project.tracks.length === 0 ? (
              <div className="absolute left-[200px] right-0 top-8 text-center text-text-muted text-sm py-8">
                No animation tracks
                <br />
                <span className="text-xs">
                  Select an element and add animations in the Properties panel
                </span>
              </div>
            ) : (
              project.tracks.map((track, index) => (
                <div
                  key={track.id}
                  className="flex border-b border-border-primary hover:bg-bg-tertiary/30 transition-colors"
                  style={{ height: 32 }}
                >
                  <div className="w-[200px] flex-shrink-0 px-3 flex items-center border-r border-border-primary bg-bg-secondary/50">
                    <span className="text-xs text-text-secondary truncate">
                      {track.elementName}
                    </span>
                    <span className="text-xs text-text-muted ml-2">
                      {track.property}
                    </span>
                  </div>

                  <div className="flex-1 relative">
                    <div
                      className="absolute top-1/2 -translate-y-1/2 h-1 bg-bg-tertiary rounded"
                      style={{
                        left: track.delay * pixelsPerSecond,
                        width: track.duration * pixelsPerSecond,
                      }}
                    />

                    {track.keyframes.map((keyframe) => (
                      <div
                        key={keyframe.id}
                        className="absolute top-1/2 -translate-y-1/2 w-3 h-3 rounded-full bg-accent-primary cursor-pointer hover:scale-125 transition-transform z-10"
                        style={{
                          left: keyframe.time * pixelsPerSecond - 6,
                        }}
                        title={`${keyframe.time.toFixed(2)}s`}
                      />
                    ))}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
