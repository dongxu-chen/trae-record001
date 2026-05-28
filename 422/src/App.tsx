import { useState, useEffect, useRef, useCallback } from 'react'
import { useEditorStore } from './store/useEditorStore'
import { TrackRow } from './components/TrackRow'
import { FilePanel, EffectsPanel, ExportPanel } from './components/Panels'
import { TransportControls, Timeline, PreviewPlayer } from './components/TransportControls'
import { AIPanel } from './components/AIPanel'
import { audioTimeSynchronizer } from './utils/AudioTimeSynchronizer'
import './styles/App.css'

export default function App() {
  const tracks = useEditorStore((s) => s.tracks)
  const addTrack = useEditorStore((s) => s.addTrack)
  const selectedClipId = useEditorStore((s) => s.selectedClipId)
  const isPlaying = useEditorStore((s) => s.isPlaying)
  const setPlaying = useEditorStore((s) => s.setPlaying)
  const currentTime = useEditorStore((s) => s.currentTime)
  const setCurrentTime = useEditorStore((s) => s.setCurrentTime)
  const totalDuration = useEditorStore((s) => s.totalDuration)
  const zoom = useEditorStore((s) => s.zoom)
  const undo = useEditorStore((s) => s.undo)
  const redo = useEditorStore((s) => s.redo)
  const selectTrack = useEditorStore((s) => s.selectTrack)
  const selectedTrackId = useEditorStore((s) => s.selectedTrackId)

  const [audioContext, setAudioContext] = useState<AudioContext | null>(null)
  const [showEffects, setShowEffects] = useState(false)
  const [showExport, setShowExport] = useState(false)
  const [showAI, setShowAI] = useState(false)
  const timelineContainerRef = useRef<HTMLDivElement>(null)

  const pixelsPerSecond = zoom

  const handleAudioContextReady = useCallback((ctx: AudioContext) => {
    setAudioContext(ctx)
  }, [])

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.ctrlKey || e.metaKey) {
        if (e.key === 'z') {
          e.preventDefault()
          undo()
        } else if (e.key === 'y' || (e.shiftKey && e.key === 'Z')) {
          e.preventDefault()
          redo()
        }
      } else if (e.code === 'Space') {
        e.preventDefault()
        if (audioContext?.state === 'suspended') {
          audioContext.resume()
        }
        setPlaying(!isPlaying)
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isPlaying, setPlaying, audioContext, undo, redo])

  const handlePlayPause = useCallback(() => {
    if (audioContext?.state === 'suspended') {
      audioContext.resume()
    }
    setPlaying(!isPlaying)
  }, [isPlaying, setPlaying, audioContext])

  const handleSeek = useCallback((time: number) => {
    if (isPlaying) {
      setPlaying(false)
    }
    const alignedTime = audioTimeSynchronizer.snapToSampleBoundary(time)
    setCurrentTime(alignedTime)
  }, [isPlaying, setPlaying, setCurrentTime])

  return (
    <div className="app">
      <header className="app-header">
        <div className="app-logo">🎵 音频剪辑工具 Pro</div>
        <div className="app-actions">
          <button
            className="btn-primary"
            onClick={() => {
              addTrack()
            }}
          >
            + 添加轨道
          </button>
          <button
            className="btn-secondary"
            onClick={() => setShowEffects(true)}
            disabled={!selectedClipId}
          >
            效果
          </button>
          <button
            className="btn-secondary"
            onClick={() => setShowAI(true)}
          >
            🤖 AI
          </button>
          <button
            className="btn-success"
            onClick={() => setShowExport(true)}
          >
            导出
          </button>
        </div>
      </header>

      <div className="app-main">
        <aside className="app-sidebar">
          <FilePanel onAudioContextReady={handleAudioContextReady} />
        </aside>

        <main className="app-content">
          <TransportControls
            onPlayPause={handlePlayPause}
            isPlaying={isPlaying}
            currentTime={currentTime}
            duration={totalDuration}
          />

          <div className="timeline-container" ref={timelineContainerRef}>
            <div
              className="timeline-scroll"
              style={{ width: `${totalDuration * pixelsPerSecond}px` }}
            >
              <Timeline
                duration={totalDuration}
                currentTime={currentTime}
                pixelsPerSecond={pixelsPerSecond}
                onSeek={handleSeek}
              />

              <div className="tracks-container">
                {tracks.length === 0 && (
                  <div className="empty-tracks">
                    <div className="empty-tracks-content">
                      <div className="empty-icon">🎶</div>
                      <p>点击"添加轨道"开始编辑</p>
                      <p className="text-sm text-gray-400">从左侧拖拽音频文件到轨道上</p>
                    </div>
                  </div>
                )}
                {tracks.map((track) => (
                  <TrackRow
                    key={track.id}
                    track={track}
                    isSelected={selectedTrackId === track.id}
                    pixelsPerSecond={pixelsPerSecond}
                    onSelectTrack={() => selectTrack(track.id)}
                  />
                ))}
              </div>
            </div>
          </div>
        </main>

        {showEffects && (
          <EffectsPanel
            open={showEffects}
            onClose={() => setShowEffects(false)}
          />
        )}

        {showAI && (
          <AIPanel
            open={showAI}
            onClose={() => setShowAI(false)}
          />
        )}
      </div>

      <ExportPanel
        open={showExport}
        onClose={() => setShowExport(false)}
      />

      <PreviewPlayer audioContext={audioContext} />
    </div>
  )
}
