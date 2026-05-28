import { useEffect, useRef, useState } from 'react'
import { useEditorStore } from '../store/useEditorStore'
import { formatTime } from '../utils/audioUtils'

interface TransportControlsProps {
  onPlayPause: () => void
  isPlaying: boolean
  currentTime: number
  duration: number
}

export function TransportControls({
  onPlayPause,
  isPlaying,
  currentTime,
  duration,
}: TransportControlsProps) {
  const undo = useEditorStore((s) => s.undo)
  const redo = useEditorStore((s) => s.redo)
  const canUndo = useEditorStore((s) => s.canUndo)
  const canRedo = useEditorStore((s) => s.canRedo)
  const zoom = useEditorStore((s) => s.zoom)
  const setZoom = useEditorStore((s) => s.setZoom)
  const [onExportClick] = useState<() => void>(() => () => {})

  return (
    <div className="transport-controls">
      <div className="transport-left">
        <button
          className="btn-transport"
          onClick={undo}
          disabled={!canUndo()}
          title="撤销 (Ctrl+Z)"
        >
          ↶
        </button>
        <button
          className="btn-transport"
          onClick={redo}
          disabled={!canRedo()}
          title="重做 (Ctrl+Y)"
        >
          ↷
        </button>
      </div>

      <div className="transport-center">
        <button
          className="btn-transport"
          onClick={() => useEditorStore.getState().setCurrentTime(0)}
          title="回到开始"
        >
          ⏮
        </button>
        <button
          className={`btn-play ${isPlaying ? 'playing' : ''}`}
          onClick={onPlayPause}
          title={isPlaying ? '暂停' : '播放'}
        >
          {isPlaying ? '⏸' : '▶'}
        </button>
        <button
          className="btn-transport"
          onClick={() => useEditorStore.getState().setCurrentTime(duration)}
          title="跳到结尾"
        >
          ⏭
        </button>
      </div>

      <div className="transport-right">
        <div className="time-display">
          <span className="current-time">{formatTime(currentTime)}</span>
          <span className="time-separator">/</span>
          <span className="total-time">{formatTime(duration)}</span>
        </div>
        <div className="zoom-controls">
          <button
            className="btn-transport btn-small"
            onClick={() => setZoom(zoom - 10)}
            title="缩小"
          >
            −
          </button>
          <span className="zoom-level">{zoom}%</span>
          <button
            className="btn-transport btn-small"
            onClick={() => setZoom(zoom + 10)}
            title="放大"
          >
            +
          </button>
        </div>
      </div>
    </div>
  )
}

interface TimelineProps {
  duration: number
  currentTime: number
  pixelsPerSecond: number
  onSeek: (time: number) => void
}

export function Timeline({ duration, currentTime, pixelsPerSecond, onSeek }: TimelineProps) {
  const timelineRef = useRef<HTMLDivElement>(null)
  const [isDragging, setIsDragging] = useState(false)
  const totalWidth = duration * pixelsPerSecond

  const handleClick = (e: React.MouseEvent) => {
    if (!timelineRef.current) return
    const rect = timelineRef.current.getBoundingClientRect()
    const x = e.clientX - rect.left
    const time = x / pixelsPerSecond
    onSeek(Math.max(0, Math.min(duration, time)))
  }

  const handleMouseDown = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      setIsDragging(true)
      handleClick(e)
    }
  }

  const handleMouseMove = (e: React.MouseEvent) => {
    if (isDragging) {
      handleClick(e)
    }
  }

  const handleMouseUp = () => {
    setIsDragging(false)
  }

  const playheadPosition = currentTime * pixelsPerSecond

  const generateTicks = () => {
    const ticks = []
    const tickInterval = pixelsPerSecond > 50 ? 1 : pixelsPerSecond > 25 ? 5 : 10
    for (let i = 0; i <= duration; i += tickInterval) {
      ticks.push(
        <div
          key={i}
          className="timeline-tick"
          style={{ left: `${i * pixelsPerSecond}px` }}
        >
          {i % (tickInterval * 5) === 0 && (
            <span className="tick-label">{formatTime(i).slice(0, 5)}</span>
          )}
        </div>
      )
    }
    return ticks
  }

  return (
    <div
      className="timeline"
      ref={timelineRef}
      style={{ minWidth: `${totalWidth}px` }}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
    >
      <div className="timeline-ruler">
        {generateTicks()}
      </div>
      <div
        className="playhead"
        style={{ left: `${playheadPosition}px` }}
        onMouseDown={(e) => {
          e.stopPropagation()
          setIsDragging(true)
        }}
      />
    </div>
  )
}

interface PreviewPlayerProps {
  audioContext: AudioContext | null
}

export function PreviewPlayer({ audioContext }: PreviewPlayerProps) {
  const tracks = useEditorStore((s) => s.tracks)
  const files = useEditorStore((s) => s.files)
  const isPlaying = useEditorStore((s) => s.isPlaying)
  const currentTime = useEditorStore((s) => s.currentTime)
  const setCurrentTime = useEditorStore((s) => s.setCurrentTime)
  const setPlaying = useEditorStore((s) => s.setPlaying)

  const sourcesRef = useRef<Map<string, AudioBufferSourceNode>>(new Map())
  const gainNodesRef = useRef<Map<string, GainNode>>(new Map())
  const animationRef = useRef<number>()

  const stopAllSources = () => {
    sourcesRef.current.forEach((source) => {
      try {
        source.stop()
      } catch (e) {
        // already stopped
      }
    })
    sourcesRef.current.clear()
    gainNodesRef.current.clear()
  }

  useEffect(() => {
    if (!audioContext) return

    if (isPlaying) {
      const playClips = async () => {
        stopAllSources()

        const hasSolo = tracks.some((t) => t.solo)

        for (const track of tracks) {
          if (track.muted) continue
          if (hasSolo && !track.solo) continue

          for (const clip of track.clips) {
            if (currentTime < clip.offset || currentTime > clip.offset + (clip.endTime - clip.startTime)) continue

            const file = files.find((f) => f.name === clip.name)
            if (!file) continue

            try {
              const arrayBuffer = await file.file.arrayBuffer()
              const audioBuffer = await audioContext.decodeAudioData(arrayBuffer.slice(0))

              const source = audioContext.createBufferSource()
              source.buffer = audioBuffer

              const gainNode = audioContext.createGain()
              gainNode.gain.value = clip.volume * track.volume

              const trackGainNode = audioContext.createGain()
              trackGainNode.gain.value = track.volume

              if (clip.fadeIn > 0) {
                const now = audioContext.currentTime
                gainNode.gain.setValueAtTime(0, now)
                gainNode.gain.linearRampToValueAtTime(clip.volume * track.volume, now + clip.fadeIn)
              }

              source.connect(gainNode)
              gainNode.connect(trackGainNode)
              trackGainNode.connect(audioContext.destination)

              const offsetInClip = currentTime - clip.offset + clip.startTime
              source.start(0, offsetInClip)

              sourcesRef.current.set(clip.id, source)
              gainNodesRef.current.set(clip.id, gainNode)
            } catch (e) {
              console.error('Error playing clip:', e)
            }
          }
        }

        const startTime = Date.now()
        const startCurrentTime = currentTime

        const updateTime = () => {
          const elapsed = (Date.now() - startTime) / 1000
          const newTime = startCurrentTime + elapsed
          setCurrentTime(newTime)
          animationRef.current = requestAnimationFrame(updateTime)
        }
        updateTime()
      }

      playClips()
    } else {
      stopAllSources()
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current)
      }
    }

    return () => {
      stopAllSources()
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current)
      }
    }
  }, [isPlaying, audioContext, tracks, files, currentTime, setCurrentTime])

  return null
}
