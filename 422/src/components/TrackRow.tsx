import { useState, useRef, useEffect } from 'react'
import type { Clip, Track } from '../store/useEditorStore'
import { useEditorStore, generateClipId } from '../store/useEditorStore'
import { waveformPyramid } from '../utils/WaveformPyramid'
import { audioTimeSynchronizer } from '../utils/AudioTimeSynchronizer'

interface ClipItemProps {
  clip: Clip
  track: Track
  isSelected: boolean
  pixelsPerSecond: number
  onSelect: () => void
  onUpdate: (updates: Partial<Clip>) => void
}

export function ClipItem({ clip, track, isSelected, pixelsPerSecond, onSelect, onUpdate }: ClipItemProps) {
  const store = useEditorStore()
  const [isDragging, setIsDragging] = useState(false)
  const [isResizingLeft, setIsResizingLeft] = useState(false)
  const [isResizingRight, setIsResizingRight] = useState(false)
  const dragStartRef = useRef({ x: 0, startTime: 0 })
  const resizeStartRef = useRef({ x: 0, startTime: 0, endTime: 0 })
  const canvasRef = useRef<HTMLCanvasElement>(null)

  const file = store.files.find((f) => f.name === clip.name)
  const clipDuration = clip.endTime - clip.startTime
  const width = Math.max(10, clipDuration * pixelsPerSecond)
  const left = clip.offset * pixelsPerSecond

  useEffect(() => {
    if (!canvasRef.current || !file) return

    const canvas = canvasRef.current
    canvas.width = Math.max(1, Math.floor(width))
    canvas.height = 36

    const rendered = waveformPyramid.renderToCanvas(
      file.id,
      canvas,
      clip.startTime,
      clip.endTime,
      'rgba(255, 255, 255, 0.7)'
    )

    if (!rendered) {
      const ctx = canvas.getContext('2d')
      if (ctx) {
        ctx.fillStyle = 'rgba(255, 255, 255, 0.5)'
        for (let i = 0; i < canvas.width; i += 3) {
          const barHeight = Math.random() * canvas.height * 0.7 + canvas.height * 0.15
          ctx.fillRect(i, (canvas.height - barHeight) / 2, 2, barHeight)
        }
      }
    }
  }, [file, clip.startTime, clip.endTime, width])

  const handleMouseDown = (e: React.MouseEvent) => {
    e.stopPropagation()
    onSelect()
    setIsDragging(true)
    dragStartRef.current = { x: e.clientX, startTime: clip.offset }
  }

  const handleResizeLeft = (e: React.MouseEvent) => {
    e.stopPropagation()
    onSelect()
    setIsResizingLeft(true)
    resizeStartRef.current = { x: e.clientX, startTime: clip.startTime, endTime: clip.endTime }
  }

  const handleResizeRight = (e: React.MouseEvent) => {
    e.stopPropagation()
    onSelect()
    setIsResizingRight(true)
    resizeStartRef.current = { x: e.clientX, startTime: clip.startTime, endTime: clip.endTime }
  }

  const handleMouseMove = (e: React.MouseEvent) => {
    if (isDragging) {
      const deltaX = e.clientX - dragStartRef.current.x
      const deltaTime = deltaX / pixelsPerSecond
      const newOffset = Math.max(0, dragStartRef.current.startTime + deltaTime)
      const alignedOffset = audioTimeSynchronizer.snapToSampleBoundary(newOffset)
      store.saveHistory()
      onUpdate({ offset: alignedOffset })
    }
    if (isResizingLeft) {
      const deltaX = e.clientX - resizeStartRef.current.x
      const deltaTime = deltaX / pixelsPerSecond
      const newStartTime = Math.min(resizeStartRef.current.startTime + deltaTime, clip.endTime - 0.1)
      const alignedStartTime = audioTimeSynchronizer.snapToSampleBoundary(Math.max(0, newStartTime))
      store.saveHistory()
      onUpdate({ startTime: alignedStartTime })
    }
    if (isResizingRight) {
      const deltaX = e.clientX - resizeStartRef.current.x
      const deltaTime = deltaX / pixelsPerSecond
      const newEndTime = Math.max(resizeStartRef.current.endTime + deltaTime, clip.startTime + 0.1)
      const alignedEndTime = audioTimeSynchronizer.snapToSampleBoundary(newEndTime)
      store.saveHistory()
      onUpdate({ endTime: alignedEndTime })
    }
  }

  const handleMouseUp = () => {
    setIsDragging(false)
    setIsResizingLeft(false)
    setIsResizingRight(false)
  }

  return (
    <div
      className={`clip-item ${isSelected ? 'clip-selected' : ''}`}
      style={{
        left: `${left}px`,
        width: `${width}px`,
        backgroundColor: track.color,
        opacity: track.muted ? 0.4 : 1,
      }}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
    >
      <div className="clip-resize-handle clip-resize-left" onMouseDown={handleResizeLeft} />
      <div className="clip-content">
        {file && <canvas ref={canvasRef} className="clip-thumbnail" style={{ width: '100%', height: '36px' }} />}
        <div className="clip-label">{clip.name}</div>
      </div>
      {clip.fadeIn > 0 && (
        <div
          className="clip-fade clip-fade-in"
          style={{ width: `${clip.fadeIn * pixelsPerSecond}px` }}
        />
      )}
      {clip.fadeOut > 0 && (
        <div
          className="clip-fade clip-fade-out"
          style={{ width: `${clip.fadeOut * pixelsPerSecond}px` }}
        />
      )}
      <div className="clip-resize-handle clip-resize-right" onMouseDown={handleResizeRight} />
    </div>
  )
}

interface TrackRowProps {
  track: Track
  isSelected: boolean
  pixelsPerSecond: number
  onSelectTrack: () => void
}

export function TrackRow({ track, isSelected, pixelsPerSecond, onSelectTrack }: TrackRowProps) {
  const store = useEditorStore()
  const [isDragOver, setIsDragOver] = useState(false)

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(true)
  }

  const handleDragLeave = () => {
    setIsDragOver(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(false)
    const fileId = e.dataTransfer.getData('fileId')
    const file = store.files.find((f) => f.id === fileId)
    if (file) {
      const alignedEndTime = audioTimeSynchronizer.snapToSampleBoundary(file.duration)
      store.saveHistory()
      store.addClip(track.id, {
        id: generateClipId(),
        startTime: 0,
        endTime: alignedEndTime,
        offset: 0,
        volume: 1,
        fadeIn: 0,
        fadeOut: 0,
        name: file.name,
      })
    }
  }

  return (
    <div
      className={`track-row ${isSelected ? 'track-selected' : ''} ${isDragOver ? 'track-dragover' : ''}`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      onClick={onSelectTrack}
    >
      <div className="track-header">
        <div className="track-info">
          <div
            className="track-color-indicator"
            style={{ backgroundColor: track.color }}
          />
          <span className="track-name">{track.name}</span>
        </div>
        <div className="track-controls">
          <input
            type="range"
            min="0"
            max="1"
            step="0.01"
            value={track.volume}
            onChange={(e) => {
              store.saveHistory()
              store.setTrackVolume(track.id, parseFloat(e.target.value))
            }}
            className="volume-slider"
            onClick={(e) => e.stopPropagation()}
          />
          <button
            className={`btn-icon ${track.muted ? 'btn-active' : ''}`}
            onClick={(e) => {
              e.stopPropagation()
              store.saveHistory()
              store.toggleMute(track.id)
            }}
            title="静音"
          >
            M
          </button>
          <button
            className={`btn-icon ${track.solo ? 'btn-active' : ''}`}
            onClick={(e) => {
              e.stopPropagation()
              store.saveHistory()
              store.toggleSolo(track.id)
            }}
            title="独奏"
          >
            S
          </button>
          <button
            className="btn-icon btn-danger"
            onClick={(e) => {
              e.stopPropagation()
              store.saveHistory()
              store.removeTrack(track.id)
            }}
            title="删除轨道"
          >
            ×
          </button>
        </div>
      </div>
      <div className="track-timeline">
        {track.clips.map((clip) => (
          <ClipItem
            key={clip.id}
            clip={clip}
            track={track}
            isSelected={store.selectedClipId === clip.id}
            pixelsPerSecond={pixelsPerSecond}
            onSelect={() => store.selectClip(clip.id)}
            onUpdate={(updates) => store.updateClip(clip.id, updates)}
          />
        ))}
      </div>
    </div>
  )
}
