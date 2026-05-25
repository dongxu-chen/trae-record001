import { useRef, useState, useMemo } from 'react'
import { useEditorStore } from '@/lib/store'
import { animationEngine } from '@/lib/animationEngine'
import { KeyframeSnapOptions } from '@/types'

export function Timeline() {
  const { project, currentTime, setCurrentTime, isPlaying, setPlaying, selectedLayerId, selectLayer, updateKeyframe } = useEditorStore()
  const rulerRef = useRef<HTMLDivElement>(null)
  const [isDragging, setIsDragging] = useState(false)
  const [snapOptions, setSnapOptions] = useState<KeyframeSnapOptions>({
    enabled: true,
    gridSize: 100,
    snapToOtherKeyframes: true,
    snapToMarkers: true,
  })
  const [dragState, setDragState] = useState<{
    isDragging: boolean
    startX: number
    startTime: number
    layerId: string
    trackId: string
    keyframeId: string
  } | null>(null)
  const [snapGuides, setSnapGuides] = useState<number[]>([])
  const [activeGuide, setActiveGuide] = useState<number | null>(null)

  if (!project) return null

  const pixelsPerSecond = 100
  const timelineWidth = (project.duration / 1000) * pixelsPerSecond

  const allKeyframeTimes = useMemo(() => {
    const times: number[] = []
    project.layers.forEach((layer) => {
      layer.tracks.forEach((track) => {
        track.keyframes.forEach((kf) => {
          if (!times.includes(kf.time)) {
            times.push(kf.time)
          }
        })
      })
    })
    return times.sort((a, b) => a - b)
  }, [project])

  const gridSnapTimes = useMemo(() => {
    const times: number[] = []
    const gridMs = snapOptions.gridSize
    for (let t = 0; t <= project.duration; t += gridMs) {
      times.push(t)
    }
    return times
  }, [project.duration, snapOptions.gridSize])

  const snapTime = (time: number, excludeKeyframeId?: string): { snappedTime: number; guide: number | null } => {
    if (!snapOptions.enabled) {
      return { snappedTime: time, guide: null }
    }

    const snapThreshold = 10
    let closestTime = time
    let minDistance = Infinity
    let guideTime: number | null = null

    if (snapOptions.snapToMarkers) {
      for (const gridTime of gridSnapTimes) {
        const distance = Math.abs(time - gridTime)
        if (distance < snapThreshold && distance < minDistance) {
          closestTime = gridTime
          minDistance = distance
          guideTime = gridTime
        }
      }
    }

    if (snapOptions.snapToOtherKeyframes) {
      for (const kfTime of allKeyframeTimes) {
        if (excludeKeyframeId) {
          const isExcluded = project.layers.some((layer) =>
            layer.tracks.some((track) =>
              track.keyframes.some(
                (kf) => kf.id === excludeKeyframeId && kf.time === kfTime
              )
            )
          )
          if (isExcluded) continue
        }

        const distance = Math.abs(time - kfTime)
        if (distance < snapThreshold && distance < minDistance) {
          closestTime = kfTime
          minDistance = distance
          guideTime = kfTime
        }
      }
    }

    return { snappedTime: closestTime, guide: guideTime }
  }

  const handleRulerClick = (e: React.MouseEvent) => {
    if (!rulerRef.current) return
    const rect = rulerRef.current.getBoundingClientRect()
    const x = e.clientX - rect.left
    const time = Math.max(0, Math.min(project.duration, (x / pixelsPerSecond) * 1000))
    const { snappedTime } = snapTime(time)
    setCurrentTime(snappedTime)
    animationEngine.seek(snappedTime)
  }

  const handlePlayheadMouseDown = (e: React.MouseEvent) => {
    e.stopPropagation()
    setIsDragging(true)
  }

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging || !rulerRef.current) return
    const rect = rulerRef.current.getBoundingClientRect()
    const x = e.clientX - rect.left
    const time = Math.max(0, Math.min(project.duration, (x / pixelsPerSecond) * 1000))
    const { snappedTime } = snapTime(time)
    setCurrentTime(snappedTime)
    animationEngine.seek(snappedTime)
  }

  const handleMouseUp = () => {
    setIsDragging(false)
  }

  const handlePlay = () => {
    if (isPlaying) {
      animationEngine.pause()
      setPlaying(false)
    } else {
      if (currentTime >= project.duration) {
        animationEngine.stop()
        setCurrentTime(0)
      }
      animationEngine.play()
      setPlaying(true)
    }
  }

  const handleStop = () => {
    animationEngine.stop()
    setPlaying(false)
    setCurrentTime(0)
  }

  const handleKeyframeMouseDown = (
    e: React.MouseEvent,
    layerId: string,
    trackId: string,
    keyframeId: string
  ) => {
    e.stopPropagation()
    const kf = project.layers
      .find((l) => l.id === layerId)
      ?.tracks.find((t) => t.id === trackId)
      ?.keyframes.find((k) => k.id === keyframeId)
    if (!kf) return

    setDragState({
      isDragging: true,
      startX: e.clientX,
      startTime: kf.time,
      layerId,
      trackId,
      keyframeId,
    })
    setSnapGuides(allKeyframeTimes)

    const handleMouseMove = (moveEvent: MouseEvent) => {
      setDragState((prev) => {
        if (!prev) return null
        const deltaX = moveEvent.clientX - prev.startX
        const rawTime = Math.max(
          0,
          Math.min(project.duration, prev.startTime + (deltaX / pixelsPerSecond) * 1000)
        )
        const { snappedTime, guide } = snapTime(rawTime, prev.keyframeId)
        setActiveGuide(guide)
        updateKeyframe(prev.layerId, prev.trackId, prev.keyframeId, {
          time: Math.round(snappedTime),
        })
        return prev
      })
    }

    const handleMouseUp = () => {
      setDragState(null)
      setSnapGuides([])
      setActiveGuide(null)
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
    }

    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleMouseUp)
  }

  return (
    <div className="timeline-area">
      <div className="timeline-header">
        <div className="playback-controls">
          <button className="btn btn-secondary" onClick={handleStop}>
            ⏹
          </button>
          <button className="btn btn-primary" onClick={handlePlay}>
            {isPlaying ? '⏸' : '▶'}
          </button>
        </div>
        <div className="time-display">
          {(currentTime / 1000).toFixed(2)}s / {(project.duration / 1000).toFixed(2)}s
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '12px' }}>
            <input
              type="checkbox"
              checked={snapOptions.enabled}
              onChange={(e) => setSnapOptions({ ...snapOptions, enabled: e.target.checked })}
            />
            吸附
          </label>
          <select
            className="property-input"
            style={{ width: '80px', fontSize: '12px' }}
            value={snapOptions.gridSize}
            onChange={(e) => setSnapOptions({ ...snapOptions, gridSize: parseInt(e.target.value) })}
          >
            <option value={50}>50ms</option>
            <option value={100}>100ms</option>
            <option value={200}>200ms</option>
            <option value={500}>500ms</option>
            <option value={1000}>1000ms</option>
          </select>
        </div>
        <div style={{ flex: 1 }} />
        <div style={{ fontSize: '13px', color: '#888' }}>FPS: {project.framerate}</div>
      </div>

      <div className="timeline-content">
        <div className="timeline-layers">
          {project.layers.map((layer) => (
            <div
              key={layer.id}
              className={`timeline-layer ${selectedLayerId === layer.id ? 'active' : ''}`}
              onClick={() => selectLayer(layer.id)}
            >
              {layer.name}
            </div>
          ))}
        </div>

        <div
          className="timeline-tracks"
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
        >
          <div
            ref={rulerRef}
            className="timeline-ruler"
            onClick={handleRulerClick}
            style={{ width: timelineWidth, position: 'relative', cursor: 'pointer' }}
          >
            {snapOptions.enabled &&
              gridSnapTimes.map((time, i) => (
                <div
                  key={`grid-${i}`}
                  style={{
                    position: 'absolute',
                    left: (time / 1000) * pixelsPerSecond,
                    top: 0,
                    height: '100%',
                    borderLeft: time % 1000 === 0 ? '1px solid #1a4a7a' : '1px dashed #1a4a7a40',
                    paddingLeft: '4px',
                    fontSize: time % 1000 === 0 ? '11px' : '0px',
                    color: '#888',
                  }}
                >
                  {time % 1000 === 0 ? `${time / 1000}s` : ''}
                </div>
              ))}

            {snapGuides.map((time) => (
              <div
                key={`guide-${time}`}
                style={{
                  position: 'absolute',
                  left: (time / 1000) * pixelsPerSecond,
                  top: 0,
                  height: '100%',
                  borderLeft: '2px dashed #e94560',
                  opacity: activeGuide === time ? 1 : 0.3,
                  pointerEvents: 'none',
                  zIndex: 5,
                }}
              />
            ))}

            <div
              className="playhead"
              style={{ left: (currentTime / 1000) * pixelsPerSecond }}
              onMouseDown={handlePlayheadMouseDown}
            />
          </div>

          {project.layers.map((layer) => (
            <div
              key={layer.id}
              className="timeline-track"
              style={{ width: timelineWidth }}
              onClick={() => selectLayer(layer.id)}
            >
              {layer.tracks.map((track) =>
                track.keyframes.map((keyframe) => (
                  <div
                    key={keyframe.id}
                    className="keyframe"
                    style={{
                      left: (keyframe.time / 1000) * pixelsPerSecond - 6,
                      transform: 'translateY(-50%) rotate(45deg)',
                      zIndex: dragState?.keyframeId === keyframe.id ? 10 : 1,
                    }}
                    onMouseDown={(e) =>
                      handleKeyframeMouseDown(e, layer.id, track.id, keyframe.id)
                    }
                    title={`${(keyframe.time / 1000).toFixed(2)}s - ${track.property}`}
                  />
                ))
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
