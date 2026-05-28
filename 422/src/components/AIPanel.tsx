import { useState, useRef } from 'react'
import { useEditorStore } from '../store/useEditorStore'
import { audioDenoise } from '../utils/AudioDenoise'
import { speechToText } from '../utils/SpeechToText'
import { audioFingerprintService } from '../utils/AudioFingerprint'
import { formatTime } from '../utils/audioUtils'
import type { TranscriptSegment, TranscriptResult } from '../utils/SpeechToText'
import type { CopyrightInfo, RecognitionResult } from '../utils/AudioFingerprint'

interface AIPanelProps {
  open: boolean
  onClose: () => void
}

type AITab = 'denoise' | 'transcribe' | 'fingerprint'

export function AIPanel({ open, onClose }: AIPanelProps) {
  const [activeTab, setActiveTab] = useState<AITab>('denoise')
  const files = useEditorStore((s) => s.files)
  const selectedClipId = useEditorStore((s) => s.selectedClipId)
  const tracks = useEditorStore((s) => s.tracks)
  const addFile = useEditorStore((s) => s.addFile)
  const updateFileCopyright = useEditorStore((s) => s.updateFileCopyright)
  const addSubtitleTrack = useEditorStore((s) => s.addSubtitleTrack)
  const addSubtitleSegment = useEditorStore((s) => s.addSubtitleSegment)

  const selectedFile = selectedClipId
    ? files.find((f) =>
        tracks.some((t) =>
          t.clips.some((c) => c.id === selectedClipId && c.name === f.name)
        )
      ) || null
    : null

  if (!open) return null

  return (
    <div className="ai-panel">
      <div className="ai-panel-header">
        <h3>AI 音频处理</h3>
        <button className="btn-close" onClick={onClose}>×</button>
      </div>

      <div className="ai-tabs">
        <button
          className={`ai-tab ${activeTab === 'denoise' ? 'active' : ''}`}
          onClick={() => setActiveTab('denoise')}
        >
          🔇 降噪
        </button>
        <button
          className={`ai-tab ${activeTab === 'transcribe' ? 'active' : ''}`}
          onClick={() => setActiveTab('transcribe')}
        >
          🎤 转文字
        </button>
        <button
          className={`ai-tab ${activeTab === 'fingerprint' ? 'active' : ''}`}
          onClick={() => setActiveTab('fingerprint')}
        >
          🎵 版权识别
        </button>
      </div>

      <div className="ai-panel-content">
        {activeTab === 'denoise' && (
          <DenoiseTab selectedFile={selectedFile} files={files} onAddFile={addFile} />
        )}
        {activeTab === 'transcribe' && (
          <TranscribeTab
            selectedFile={selectedFile}
            files={files}
            onAddSubtitleTrack={addSubtitleTrack}
            onAddSubtitleSegment={addSubtitleSegment}
          />
        )}
        {activeTab === 'fingerprint' && (
          <FingerprintTab
            selectedFile={selectedFile}
            files={files}
            onUpdateCopyright={updateFileCopyright}
          />
        )}
      </div>
    </div>
  )
}

interface DenoiseTabProps {
  selectedFile: ReturnType<typeof useEditorStore.getState>['files'][0] | null
  files: ReturnType<typeof useEditorStore.getState>['files']
  onAddFile: (file: ReturnType<typeof useEditorStore.getState>['files'][0]) => void
}

function DenoiseTab({ selectedFile, files, onAddFile }: DenoiseTabProps) {
  const [processing, setProcessing] = useState(false)
  const [progress, setProgress] = useState(0)
  const [progressStage, setProgressStage] = useState('')
  const [selectedFileId, setSelectedFileId] = useState(selectedFile?.id || files[0]?.id || '')
  const [noiseThreshold, setNoiseThreshold] = useState(-40)
  const [spectralGating, setSpectralGating] = useState(0.7)
  const [resultUrl, setResultUrl] = useState<string | null>(null)

  const fileToProcess = files.find((f) => f.id === selectedFileId) || selectedFile

  const handleAnalyzeNoise = async () => {
    if (!fileToProcess) return
    setProcessing(true)
    setProgressStage('分析噪声特征...')

    try {
      await audioDenoise.analyzeNoise(fileToProcess.file, 500, 0)
      setProgressStage('噪声分析完成')
    } catch (error) {
      setProgressStage('分析失败: ' + (error as Error).message)
    } finally {
      setProcessing(false)
    }
  }

  const handleDenoise = async () => {
    if (!fileToProcess) return
    setProcessing(true)
    setProgress(0)
    setResultUrl(null)

    audioDenoise.setConfig({
      noiseThreshold,
      spectralGating,
    })

    try {
      const blob = await audioDenoise.denoiseFile(
        fileToProcess.file,
        (p, stage) => {
          setProgress(p * 100)
          setProgressStage(stage)
        }
      )

      const url = URL.createObjectURL(blob)
      setResultUrl(url)

      const newFile = {
        id: `denoised_${Date.now()}`,
        name: `[降噪] ${fileToProcess.name}`,
        file: new File([blob], `denoised_${fileToProcess.name}`, { type: 'audio/wav' }),
        url,
        duration: fileToProcess.duration,
      }
      onAddFile(newFile)

      setProgressStage('降噪完成！已添加到文件列表')
    } catch (error) {
      setProgressStage('降噪失败: ' + (error as Error).message)
    } finally {
      setProcessing(false)
    }
  }

  return (
    <div className="ai-tab-content">
      <div className="ai-section">
        <h4>AI 音频降噪</h4>
        <p className="ai-description">使用频谱减法算法去除背景杂音</p>
      </div>

      <div className="ai-section">
        <label>选择音频文件</label>
        <select
          value={selectedFileId}
          onChange={(e) => setSelectedFileId(e.target.value)}
          disabled={processing}
        >
          <option value="">-- 请选择 --</option>
          {files.map((f) => (
            <option key={f.id} value={f.id}>
              {f.name}
            </option>
          ))}
        </select>
      </div>

      <div className="ai-section">
        <label>噪声阈值: {noiseThreshold} dB</label>
        <input
          type="range"
          min="-60"
          max="-20"
          step="1"
          value={noiseThreshold}
          onChange={(e) => setNoiseThreshold(parseInt(e.target.value))}
          disabled={processing}
        />
      </div>

      <div className="ai-section">
        <label>频谱门限: {(spectralGating * 100).toFixed(0)}%</label>
        <input
          type="range"
          min="0.1"
          max="1"
          step="0.05"
          value={spectralGating}
          onChange={(e) => setSpectralGating(parseFloat(e.target.value))}
          disabled={processing}
        />
      </div>

      <div className="ai-section">
        <div className="ai-buttons">
          <button
            className="btn-secondary"
            onClick={handleAnalyzeNoise}
            disabled={!fileToProcess || processing}
          >
            分析噪声
          </button>
          <button
            className="btn-primary"
            onClick={handleDenoise}
            disabled={!fileToProcess || processing}
          >
            {processing ? '处理中...' : '开始降噪'}
          </button>
        </div>
      </div>

      {processing && (
        <div className="ai-progress">
          <div className="progress-bar">
            <div className="progress-fill" style={{ width: `${progress}%` }} />
            <span className="progress-text">{progress.toFixed(0)}%</span>
          </div>
          <p className="progress-stage">{progressStage}</p>
        </div>
      )}

      {resultUrl && !processing && (
        <div className="ai-section">
          <label>预览降噪结果</label>
          <audio controls src={resultUrl} className="audio-preview" />
        </div>
      )}
    </div>
  )
}

interface TranscribeTabProps {
  selectedFile: ReturnType<typeof useEditorStore.getState>['files'][0] | null
  files: ReturnType<typeof useEditorStore.getState>['files']
  onAddSubtitleTrack: () => void
  onAddSubtitleSegment: (trackId: string, segment: TranscriptSegment) => void
}

function TranscribeTab({
  selectedFile,
  files,
  onAddSubtitleTrack,
  onAddSubtitleSegment,
}: TranscribeTabProps) {
  const [processing, setProcessing] = useState(false)
  const [progress, setProgress] = useState(0)
  const [progressStage, setProgressStage] = useState('')
  const [selectedFileId, setSelectedFileId] = useState(selectedFile?.id || files[0]?.id || '')
  const [language, setLanguage] = useState('zh-CN')
  const [result, setResult] = useState<TranscriptResult | null>(null)
  const [isSupported, setIsSupported] = useState(speechToText.isSupported())

  const fileToProcess = files.find((f) => f.id === selectedFileId) || selectedFile

  const handleTranscribe = async () => {
    if (!fileToProcess) return
    setProcessing(true)
    setProgress(0)
    setResult(null)

    speechToText.setLanguage(language)

    try {
      const transcriptResult = await speechToText.transcribeFile(
        fileToProcess.file,
        (p, stage) => {
          setProgress(p * 100)
          setProgressStage(stage)
        }
      )

      setResult(transcriptResult)
      setProgressStage('转录完成！')

      if (transcriptResult.segments.length > 0) {
        onAddSubtitleTrack()
      }
    } catch (error) {
      setProgressStage('转录失败: ' + (error as Error).message)
    } finally {
      setProcessing(false)
    }
  }

  const handleExportSRT = () => {
    if (!result) return
    const content = speechToText.generateSRT(result.segments)
    const blob = new Blob([content], { type: 'application/x-subrip' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `subtitles_${Date.now()}.srt`
    a.click()
    URL.revokeObjectURL(url)
  }

  if (!isSupported) {
    return (
      <div className="ai-tab-content">
        <div className="ai-section">
          <h4>语音转文字</h4>
          <div className="ai-warning">
            ⚠️ 当前浏览器不支持语音识别功能，请使用 Chrome 或 Edge 浏览器
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="ai-tab-content">
      <div className="ai-section">
        <h4>AI 语音转文字</h4>
        <p className="ai-description">使用 Web Speech API 将音频转录为文字</p>
      </div>

      <div className="ai-section">
        <label>选择音频文件</label>
        <select
          value={selectedFileId}
          onChange={(e) => setSelectedFileId(e.target.value)}
          disabled={processing}
        >
          <option value="">-- 请选择 --</option>
          {files.map((f) => (
            <option key={f.id} value={f.id}>
              {f.name}
            </option>
          ))}
        </select>
      </div>

      <div className="ai-section">
        <label>识别语言</label>
        <select
          value={language}
          onChange={(e) => setLanguage(e.target.value)}
          disabled={processing}
        >
          <option value="zh-CN">中文（普通话）</option>
          <option value="zh-TW">中文（台湾）</option>
          <option value="en-US">英语（美国）</option>
          <option value="en-GB">英语（英国）</option>
          <option value="ja-JP">日语</option>
          <option value="ko-KR">韩语</option>
        </select>
      </div>

      <div className="ai-section">
        <button
          className="btn-primary"
          onClick={handleTranscribe}
          disabled={!fileToProcess || processing}
        >
          {processing ? '转录中...' : '开始转录'}
        </button>
      </div>

      {processing && (
        <div className="ai-progress">
          <div className="progress-bar">
            <div className="progress-fill" style={{ width: `${progress}%` }} />
            <span className="progress-text">{progress.toFixed(0)}%</span>
          </div>
          <p className="progress-stage">{progressStage}</p>
        </div>
      )}

      {result && !processing && (
        <>
          <div className="ai-section">
            <div className="ai-result-summary">
              <span>识别结果: {result.segments.length} 段</span>
              <span>总字数: {result.wordCount}</span>
              <span>时长: {formatTime(result.duration)}</span>
            </div>
          </div>

          <div className="ai-section">
            <label>转录内容</label>
            <div className="transcript-result">
              {result.segments.map((segment) => (
                <div key={segment.id} className="transcript-segment">
                  <span className="transcript-time">
                    [{formatTime(segment.startTime)} - {formatTime(segment.endTime)}]
                  </span>
                  <span className="transcript-text">{segment.text}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="ai-section">
            <button className="btn-secondary" onClick={handleExportSRT}>
              导出 SRT 字幕
            </button>
          </div>
        </>
      )}
    </div>
  )
}

interface FingerprintTabProps {
  selectedFile: ReturnType<typeof useEditorStore.getState>['files'][0] | null
  files: ReturnType<typeof useEditorStore.getState>['files']
  onUpdateCopyright: (id: string, info: CopyrightInfo | null) => void
}

function FingerprintTab({ selectedFile, files, onUpdateCopyright }: FingerprintTabProps) {
  const [processing, setProcessing] = useState(false)
  const [progress, setProgress] = useState(0)
  const [progressStage, setProgressStage] = useState('')
  const [selectedFileId, setSelectedFileId] = useState(selectedFile?.id || files[0]?.id || '')
  const [result, setResult] = useState<RecognitionResult | null>(null)

  const fileToProcess = files.find((f) => f.id === selectedFileId) || selectedFile

  const handleRecognize = async () => {
    if (!fileToProcess) return
    setProcessing(true)
    setProgress(0)
    setResult(null)

    try {
      const recognitionResult = await audioFingerprintService.recognize(
        fileToProcess.file,
        (p, stage) => {
          setProgress(p * 100)
          setProgressStage(stage)
        }
      )

      setResult(recognitionResult)

      if (recognitionResult.bestMatch) {
        onUpdateCopyright(fileToProcess.id, recognitionResult.bestMatch)
        setProgressStage('识别完成！已更新版权信息')
      } else {
        setProgressStage('未找到匹配的版权信息')
      }
    } catch (error) {
      setProgressStage('识别失败: ' + (error as Error).message)
    } finally {
      setProcessing(false)
    }
  }

  return (
    <div className="ai-tab-content">
      <div className="ai-section">
        <h4>音频指纹识别</h4>
        <p className="ai-description">分析音频指纹，识别背景音乐版权信息</p>
      </div>

      <div className="ai-section">
        <label>选择音频文件</label>
        <select
          value={selectedFileId}
          onChange={(e) => setSelectedFileId(e.target.value)}
          disabled={processing}
        >
          <option value="">-- 请选择 --</option>
          {files.map((f) => (
            <option key={f.id} value={f.id}>
              {f.name}
            </option>
          ))}
        </select>
      </div>

      <div className="ai-section">
        <button
          className="btn-primary"
          onClick={handleRecognize}
          disabled={!fileToProcess || processing}
        >
          {processing ? '识别中...' : '开始识别'}
        </button>
      </div>

      {processing && (
        <div className="ai-progress">
          <div className="progress-bar">
            <div className="progress-fill" style={{ width: `${progress}%` }} />
            <span className="progress-text">{progress.toFixed(0)}%</span>
          </div>
          <p className="progress-stage">{progressStage}</p>
        </div>
      )}

      {result && !processing && (
        <div className="ai-section">
          <label>识别结果</label>
          {result.bestMatch ? (
            <div className="copyright-result">
              <div className="copyright-item">
                <span className="copyright-label">标题:</span>
                <span className="copyright-value">{result.bestMatch.title}</span>
              </div>
              <div className="copyright-item">
                <span className="copyright-label">艺术家:</span>
                <span className="copyright-value">{result.bestMatch.artist}</span>
              </div>
              {result.bestMatch.album && (
                <div className="copyright-item">
                  <span className="copyright-label">专辑:</span>
                  <span className="copyright-value">{result.bestMatch.album}</span>
                </div>
              )}
              {result.bestMatch.genre && (
                <div className="copyright-item">
                  <span className="copyright-label">流派:</span>
                  <span className="copyright-value">{result.bestMatch.genre}</span>
                </div>
              )}
              <div className="copyright-item">
                <span className="copyright-label">版权状态:</span>
                <span className={`copyright-value ${result.bestMatch.isCopyrighted ? 'copyrighted' : 'free'}`}>
                  {result.bestMatch.isCopyrighted ? '⚠️ 受版权保护' : '✓ 可免费使用'}
                </span>
              </div>
              {result.bestMatch.licenseType && (
                <div className="copyright-item">
                  <span className="copyright-label">授权类型:</span>
                  <span className="copyright-value">{result.bestMatch.licenseType}</span>
                </div>
              )}
              {result.bestMatch.source && (
                <div className="copyright-item">
                  <span className="copyright-label">来源:</span>
                  <span className="copyright-value">{result.bestMatch.source}</span>
                </div>
              )}
              <div className="copyright-item">
                <span className="copyright-label">匹配置信度:</span>
                <span className="copyright-value">{(result.bestMatch.confidence * 100).toFixed(1)}%</span>
              </div>
            </div>
          ) : (
            <div className="ai-warning">
              未在版权库中找到匹配结果，该音频可能需要进一步检查
            </div>
          )}

          {result.matches.length > 1 && (
            <div className="copyright-alt-matches">
              <label>其他可能的匹配</label>
              {result.matches.slice(1, 4).map((match, index) => (
                <div key={index} className="copyright-alt-item">
                  <span>{match.title} - {match.artist}</span>
                  <span className="confidence">{(match.confidence * 100).toFixed(1)}%</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
