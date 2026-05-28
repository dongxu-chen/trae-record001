import { useRef, useState, useEffect } from 'react'
import { useEditorStore, generateClipId } from '../store/useEditorStore'
import { getAudioDuration, formatTime, formatTimeSamples, mergeMultipleTracks, downloadBlob } from '../utils/audioUtils'
import { waveformPyramid } from '../utils/WaveformPyramid'
import { audioTimeSynchronizer, formatDrift } from '../utils/AudioTimeSynchronizer'

interface FilePanelProps {
  onAudioContextReady?: (ctx: AudioContext) => void
}

export function FilePanel({ onAudioContextReady }: FilePanelProps) {
  const files = useEditorStore((s) => s.files)
  const addFile = useEditorStore((s) => s.addFile)
  const removeFile = useEditorStore((s) => s.removeFile)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [loading, setLoading] = useState(false)
  const [buildProgress, setBuildProgress] = useState<Map<string, number>>(new Map())

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const uploadedFiles = e.target.files
    if (!uploadedFiles) return

    setLoading(true)

    for (let i = 0; i < uploadedFiles.length; i++) {
      const file = uploadedFiles[i]
      const fileId = `file_${Date.now()}_${i}`
      const url = URL.createObjectURL(file)
      const duration = await getAudioDuration(file)

      addFile({
        id: fileId,
        name: file.name,
        file: file,
        url: url,
        duration: duration,
      })

      setBuildProgress((prev) => new Map(prev).set(fileId, 0))

      setTimeout(async () => {
        await waveformPyramid.buildPyramid(file, fileId)
        setBuildProgress((prev) => {
          const next = new Map(prev)
          next.delete(fileId)
          return next
        })
      }, 0)
    }

    setLoading(false)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const handleDragStart = (e: React.DragEvent, fileId: string) => {
    e.dataTransfer.setData('fileId', fileId)
  }

  const handleRemoveFile = (fileId: string) => {
    waveformPyramid.dispose(fileId)
    removeFile(fileId)
  }

  useEffect(() => {
    const AudioContextClass = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext
    const ctx = new AudioContextClass()
    waveformPyramid.setAudioContext(ctx)
    onAudioContextReady?.(ctx)
    return () => {
      ctx.close()
    }
  }, [onAudioContextReady])

  return (
    <div className="panel file-panel">
      <div className="panel-header">
        <h3>音频文件</h3>
        <button
          className="btn-primary"
          onClick={() => fileInputRef.current?.click()}
          disabled={loading}
        >
          {loading ? '加载中...' : '添加文件'}
        </button>
      </div>
      <input
        ref={fileInputRef}
        type="file"
        accept="audio/*"
        multiple
        onChange={handleFileUpload}
        className="hidden"
      />
      <div className="file-list">
        {files.length === 0 && (
          <div className="empty-state">
            <p>暂无音频文件</p>
            <p className="text-sm text-gray-400">点击"添加文件"上传音频</p>
          </div>
        )}
        {files.map((file) => (
          <div
            key={file.id}
            className="file-item"
            draggable={!buildProgress.has(file.id)}
            onDragStart={(e) => handleDragStart(e, file.id)}
          >
            <div className="file-icon">🎵</div>
            <div className="file-info">
              <span className="file-name">{file.name}</span>
              <span className="file-duration">{formatTime(file.duration)}</span>
              {buildProgress.has(file.id) && (
                <span className="file-processing">构建波形缓存中...</span>
              )}
            </div>
            <button
              className="btn-icon btn-danger btn-small"
              onClick={() => handleRemoveFile(file.id)}
            >
              ×
            </button>
          </div>
        ))}
      </div>
      <div className="panel-footer">
        <p className="text-sm text-gray-400">拖拽文件到轨道上使用</p>
      </div>
    </div>
  )
}

interface EffectsPanelProps {
  open: boolean
  onClose: () => void
}

export function EffectsPanel({ open, onClose }: EffectsPanelProps) {
  const selectedClipId = useEditorStore((s) => s.selectedClipId)
  const tracks = useEditorStore((s) => s.tracks)
  const files = useEditorStore((s) => s.files)
  const updateClip = useEditorStore((s) => s.updateClip)
  const saveHistory = useEditorStore((s) => s.saveHistory)
  const [sampleRate, setSampleRate] = useState<number | null>(null)
  const [syncInfo, setSyncInfo] = useState<{ drift: number; aligned: boolean } | null>(null)

  const selectedClip = tracks
    .flatMap((t) => t.clips)
    .find((c) => c.id === selectedClipId)

  useEffect(() => {
    if (!selectedClip) {
      setSampleRate(null)
      setSyncInfo(null)
      return
    }

    const file = files.find((f) => f.name === selectedClip.name)
    if (file) {
      const AudioContextClass = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext
      const ctx = new AudioContextClass()
      file.file.arrayBuffer().then((buffer) => {
        ctx.decodeAudioData(buffer.slice(0)).then((audioBuffer) => {
          setSampleRate(audioBuffer.sampleRate)

          const synced = audioTimeSynchronizer.syncClipTiming(
            selectedClip,
            audioBuffer.sampleRate,
            audioBuffer.duration
          )
          setSyncInfo({
            drift: synced.driftCorrection * 1000,
            aligned: Math.abs(synced.driftCorrection) < 0.0001,
          })

          ctx.close()
        })
      })
    }
  }, [selectedClip, files])

  if (!open || !selectedClip) {
    if (!open) return null
    return (
      <div className="panel effects-panel">
        <div className="panel-header">
          <h3>效果设置</h3>
          <button className="btn-close" onClick={onClose}>×</button>
        </div>
        <div className="empty-state">
          <p>请先选择一个剪辑</p>
        </div>
      </div>
    )
  }

  const handleChange = (key: keyof typeof selectedClip, value: number) => {
    saveHistory()
    updateClip(selectedClip.id, { [key]: value })
  }

  const handleChangeAligned = (key: keyof typeof selectedClip, value: number) => {
    const alignedValue = audioTimeSynchronizer.snapToSampleBoundary(value)
    handleChange(key, alignedValue)
  }

  return (
    <div className="panel effects-panel">
      <div className="panel-header">
        <h3>效果设置</h3>
        <button className="btn-close" onClick={onClose}>×</button>
      </div>
      <div className="effects-content">
        <div className="effect-group">
          <label>剪辑: {selectedClip.name}</label>
        </div>

        {sampleRate && (
          <div className="effect-group">
            <label>采样率: {sampleRate} Hz → 44100 Hz</label>
            <div className="sync-status">
              <span className={`sync-badge ${syncInfo?.aligned ? 'sync-good' : 'sync-warning'}`}>
                {syncInfo?.aligned ? '✓ 已对齐' : '⚠ 已校准'}
              </span>
              <span className="sync-drift">漂移: {formatDrift(syncInfo?.drift || 0)}</span>
            </div>
          </div>
        )}

        <div className="effect-group">
          <label>音量: {(selectedClip.volume * 100).toFixed(0)}%</label>
          <input
            type="range"
            min="0"
            max="2"
            step="0.01"
            value={selectedClip.volume}
            onChange={(e) => handleChange('volume', parseFloat(e.target.value))}
            className="effect-slider"
          />
        </div>

        <div className="effect-group">
          <label>淡入: {selectedClip.fadeIn.toFixed(2)}秒</label>
          <input
            type="range"
            min="0"
            max="10"
            step="0.1"
            value={selectedClip.fadeIn}
            onChange={(e) => handleChange('fadeIn', parseFloat(e.target.value))}
            className="effect-slider"
          />
        </div>

        <div className="effect-group">
          <label>淡出: {selectedClip.fadeOut.toFixed(2)}秒</label>
          <input
            type="range"
            min="0"
            max="10"
            step="0.1"
            value={selectedClip.fadeOut}
            onChange={(e) => handleChange('fadeOut', parseFloat(e.target.value))}
            className="effect-slider"
          />
        </div>

        <div className="effect-group">
          <label>起始时间: {formatTimeSamples(selectedClip.startTime, 44100)}</label>
          <input
            type="number"
            min="0"
            step="0.00001"
            value={selectedClip.startTime}
            onChange={(e) => handleChangeAligned('startTime', parseFloat(e.target.value))}
          />
        </div>

        <div className="effect-group">
          <label>结束时间: {formatTimeSamples(selectedClip.endTime, 44100)}</label>
          <input
            type="number"
            min="0"
            step="0.00001"
            value={selectedClip.endTime}
            onChange={(e) => handleChangeAligned('endTime', parseFloat(e.target.value))}
          />
        </div>

        <div className="effect-group">
          <label>偏移位置: {formatTimeSamples(selectedClip.offset, 44100)}</label>
          <input
            type="number"
            min="0"
            step="0.00001"
            value={selectedClip.offset}
            onChange={(e) => handleChangeAligned('offset', parseFloat(e.target.value))}
          />
        </div>
      </div>
    </div>
  )
}

interface ExportPanelProps {
  open: boolean
  onClose: () => void
}

export function ExportPanel({ open, onClose }: ExportPanelProps) {
  const [format, setFormat] = useState<'mp3' | 'wav' | 'ogg' | 'm4a'>('mp3')
  const [exporting, setExporting] = useState(false)
  const [progress, setProgress] = useState(0)
  const [exportStage, setExportStage] = useState<string>('')
  const [useSegmented, setUseSegmented] = useState(true)
  const tracks = useEditorStore((s) => s.tracks)
  const files = useEditorStore((s) => s.files)

  const hasContent = tracks.some((t) => t.clips.length > 0)

  const handleExport = async () => {
    if (!hasContent) return
    setExporting(true)
    setProgress(0)
    setExportStage('准备导出...')

    try {
      const exportTracks: Array<{
        file: File
        offset: number
        volume: number
        startTime: number
        endTime: number
      }> = []

      for (const track of tracks) {
        if (track.muted) continue
        for (const clip of track.clips) {
          const file = files.find((f) => f.name === clip.name)
          if (file) {
            exportTracks.push({
              file: file.file,
              offset: clip.offset,
              volume: clip.volume * track.volume,
              startTime: clip.startTime,
              endTime: clip.endTime,
            })
          }
        }
      }

      if (exportTracks.length > 0) {
        setExportStage('合并轨道...')
        const blob = await mergeMultipleTracks(
          exportTracks,
          format === 'm4a' ? 'wav' : (format as 'wav' | 'mp3' | 'ogg'),
          (p) => {
            setProgress(p * 100)
          }
        )
        downloadBlob(blob, `audio_export_${Date.now()}.${format}`)
      }
    } catch (error) {
      console.error('Export failed:', error)
      setExportStage('导出失败: ' + (error as Error).message)
    } finally {
      setTimeout(() => {
        setExporting(false)
        setExportStage('')
      }, 1000)
    }
  }

  if (!open) return null

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>导出音频</h3>
          <button className="btn-close" onClick={onClose}>×</button>
        </div>
        <div className="modal-body">
          {!hasContent && (
            <div className="warning">
              <p>⚠️ 轨道中没有内容，请先添加音频剪辑</p>
            </div>
          )}
          <div className="form-group">
            <label>导出格式</label>
            <select
              value={format}
              onChange={(e) => setFormat(e.target.value as typeof format)}
              disabled={exporting}
            >
              <option value="wav">WAV (无损)</option>
              <option value="mp3">MP3 (通用)</option>
              <option value="ogg">OGG (开源)</option>
              <option value="m4a">M4A (Apple)</option>
            </select>
          </div>
          <div className="form-group">
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={useSegmented}
                onChange={(e) => setUseSegmented(e.target.checked)}
                disabled={exporting}
              />
              大文件分段处理 (超过60秒自动启用)
            </label>
          </div>
          {exporting && (
            <div className="export-progress">
              <div className="progress-bar">
                <div
                  className="progress-fill"
                  style={{ width: `${progress}%` }}
                />
                <span className="progress-text">{progress.toFixed(0)}%</span>
              </div>
              <p className="progress-stage">{exportStage}</p>
            </div>
          )}
        </div>
        <div className="modal-footer">
          <button className="btn-secondary" onClick={onClose} disabled={exporting}>
            取消
          </button>
          <button
            className="btn-primary"
            onClick={handleExport}
            disabled={!hasContent || exporting}
          >
            {exporting ? '导出中...' : '导出'}
          </button>
        </div>
      </div>
    </div>
  )
}
