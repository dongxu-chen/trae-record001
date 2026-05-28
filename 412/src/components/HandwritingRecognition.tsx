import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { DrawingCanvas, type DrawingCanvasHandle, type Stroke } from './DrawingCanvas'
import type { Candidate, Segment, WorkerResponse } from './types'
import { segmentStrokes } from './segmentation'
import RecognitionWorker from './recognition.worker.ts?worker'
import { applyDomainReRank, listDomains } from './domainVocab'
import {
  loadUserSamples,
  addUserSample,
  computeBBox,
  computeNormUint8,
  clearUserSamples,
  type UserSample,
} from './personalLearning'
import { speak, stopSpeak, isSpeechSupported } from './tts'

interface Props {
  width?: number
  height?: number
  topK?: number
  onTextChange?: (text: string) => void
}

export function HandwritingRecognition({
  width = 640,
  height = 240,
  topK = 6,
  onTextChange,
}: Props) {
  const canvasRef = useRef<DrawingCanvasHandle | null>(null)
  const workerRef = useRef<Worker | null>(null)
  const debounceRef = useRef<number | null>(null)
  const strokesRef = useRef<Stroke[]>([])
  const userSamplesRef = useRef<Map<string, UserSample>>(new Map())

  const [ready, setReady] = useState(false)
  const [loading, setLoading] = useState(true)
  const [warmupPercent, setWarmupPercent] = useState(0)
  const [allStrokes, setAllStrokes] = useState<Stroke[]>([])
  const [segments, setSegments] = useState<Segment[]>([])
  const [candidates, setCandidates] = useState<Candidate[][]>([])
  const [text, setText] = useState('')
  const [committedText, setCommittedText] = useState('')
  const [domain, setDomain] = useState('general')
  const [voiceEnabled, setVoiceEnabled] = useState(false)
  const [personalLearnEnabled, setPersonalLearnEnabled] = useState(true)
  const [learnedCount, setLearnedCount] = useState(0)
  const [saveFeedback, setSaveFeedback] = useState<string | null>(null)

  useEffect(() => {
    userSamplesRef.current = loadUserSamples()
    setLearnedCount(userSamplesRef.current.size)
  }, [])

  useEffect(() => {
    const worker = new RecognitionWorker()
    workerRef.current = worker
    worker.onmessage = (ev: MessageEvent<WorkerResponse>) => {
      const msg = ev.data
      if (msg.type === 'warmupProgress') {
        setWarmupPercent(msg.percent)
      } else if (msg.type === 'ready') {
        setReady(true)
        setLoading(false)
        setWarmupPercent(100)
        for (const sample of userSamplesRef.current.values()) {
          worker.postMessage({
            type: 'addUserTemplate',
            char: sample.char,
            pixels: sample.pixels,
            norm: computeNormUint8(sample.pixels),
          })
        }
      } else if (msg.type === 'recognized') {
        const rerankedCandidates = applyDomainReRank(
          msg.results.map((r) => r.map((c) => c.char)),
          domain,
        )
        const withScores: Candidate[][] = msg.results.map((origRow, i) =>
          rerankedCandidates[i].map((char, j) => {
            const orig = origRow.find((c) => c.char === char)
            return orig ?? { char, score: Math.max(0, 1 - j * 0.05) }
          }),
        )
        setCandidates(withScores)
        setSegments(msg.segments)
        const newText = withScores.map((r) => r[0]?.char ?? '').join('')
        setText(newText)
        onTextChange?.(newText)
      } else if (msg.type === 'userTemplateAdded') {
        setLearnedCount(userSamplesRef.current.size)
      } else if (msg.type === 'error') {
        console.error('[HR worker] error:', msg.message)
      }
    }
    worker.postMessage({ type: 'init' })
    return () => {
      worker.terminate()
      workerRef.current = null
    }
  }, [onTextChange, domain])

  useEffect(() => {
    if (voiceEnabled && text && ready) {
      speak(text, 0.95, 1.0)
    }
    return () => {
      if (voiceEnabled) stopSpeak()
    }
  }, [text, voiceEnabled, ready])

  const recognize = useCallback((strokes: Stroke[]) => {
    if (strokes.length === 0) {
      setCandidates([])
      setSegments([])
      setText('')
      onTextChange?.('')
      return
    }
    const previewSegs = segmentStrokes(strokes)
    setSegments(previewSegs)
    workerRef.current?.postMessage({ type: 'recognize', strokes, topK })
  }, [topK, onTextChange])

  const scheduleRecognize = useCallback((strokes: Stroke[]) => {
    if (debounceRef.current !== null) {
      window.clearTimeout(debounceRef.current)
    }
    debounceRef.current = window.setTimeout(() => {
      recognize(strokes)
    }, 180)
  }, [recognize])

  const handleStrokeEnd = useCallback((_stroke: Stroke, all: Stroke[]) => {
    strokesRef.current = all
    setAllStrokes(all)
    scheduleRecognize(all)
  }, [scheduleRecognize])

  const handleStrokeStart = useCallback(() => {
    if (debounceRef.current !== null) {
      window.clearTimeout(debounceRef.current)
      debounceRef.current = null
    }
  }, [])

  const handleClear = useCallback(() => {
    canvasRef.current?.clear()
    strokesRef.current = []
    setAllStrokes([])
    setSegments([])
    setCandidates([])
    setText('')
    onTextChange?.('')
    setSaveFeedback(null)
  }, [onTextChange])

  const handleCommit = useCallback(() => {
    if (!text) return
    if (personalLearnEnabled && segments.length > 0 && segments.length === text.length) {
      for (let i = 0; i < segments.length; i++) {
        const seg = segments[i]
        const char = text[i]
        if (!char || seg.strokes.length === 0) continue
        const bbox = computeBBox(seg.strokes)
        if (bbox.w < 1 || bbox.h < 1) continue
        const sample = addUserSample(userSamplesRef.current, char, seg.strokes)
        workerRef.current?.postMessage({
          type: 'addUserTemplate',
          char,
          pixels: sample.pixels,
          norm: computeNormUint8(sample.pixels),
        })
      }
      setSaveFeedback(`✓ 已学习 "${text}" 的笔迹风格`)
      setTimeout(() => setSaveFeedback(null), 2500)
    }
    setCommittedText((prev) => prev + text)
    handleClear()
  }, [text, segments, personalLearnEnabled, handleClear])

  const handleBackspace = useCallback(() => {
    setCommittedText((prev) => prev.slice(0, -1))
  }, [])

  const handlePickCandidate = useCallback((segIdx: number, char: string) => {
    setCandidates((prev) => {
      const next = prev.map((r) => r.slice())
      next[segIdx] = [{ char, score: 1 }]
      return next
    })
    const newText = candidates
      .map((r, i) => (i === segIdx ? char : r[0]?.char ?? ''))
      .join('')
    setText(newText)
    onTextChange?.(newText)
  }, [candidates, onTextChange])

  const handleClearLearned = useCallback(() => {
    clearUserSamples()
    userSamplesRef.current.clear()
    setLearnedCount(0)
    workerRef.current?.postMessage({ type: 'clearUserTemplates' })
    setSaveFeedback('已清空个人笔迹库')
    setTimeout(() => setSaveFeedback(null), 2000)
  }, [])

  const toggleVoice = useCallback(() => {
    setVoiceEnabled((v) => {
      const next = !v
      if (!next) stopSpeak()
      return next
    })
  }, [])

  const segmentsInfo = useMemo(() => segments, [segments])
  const domains = useMemo(() => listDomains(), [])

  const statusText = loading
    ? `模型加载中 ${warmupPercent}%…`
    : ready
    ? '就绪'
    : '未就绪'

  const speechSupported = isSpeechSupported()

  return (
    <div className="handwriting">
      <div className="handwriting__header">
        <div className="handwriting__status">
          {statusText}
        </div>
        <div className="handwriting__actions">
          <button type="button" onClick={handleBackspace} disabled={!committedText && !text}>
            ⌫ 退格
          </button>
          <button type="button" onClick={handleCommit} disabled={!text}>
            ✓ 确认{personalLearnEnabled ? ' + 学习' : ''}
          </button>
          <button type="button" onClick={handleClear}>
            🗑 清空
          </button>
        </div>
      </div>

      <div className="handwriting__toolbar">
        <div className="handwriting__toolbar-group">
          <label className="handwriting__toolbar-label">领域：</label>
          <select
            value={domain}
            onChange={(e) => setDomain(e.target.value)}
            className="handwriting__select"
          >
            {domains.map((d) => (
              <option key={d.id} value={d.id}>{d.name}</option>
            ))}
          </select>
        </div>

        <div className="handwriting__toolbar-group">
          <label className="handwriting__checkbox">
            <input
              type="checkbox"
              checked={personalLearnEnabled}
              onChange={(e) => setPersonalLearnEnabled(e.target.checked)}
            />
            <span>学习笔迹</span>
          </label>
          <span className="handwriting__count">({learnedCount}个)</span>
          {learnedCount > 0 && (
            <button type="button" className="handwriting__mini-btn" onClick={handleClearLearned}>
              清空
            </button>
          )}
        </div>

        <div className="handwriting__toolbar-group">
          <label className="handwriting__checkbox">
            <input
              type="checkbox"
              checked={voiceEnabled}
              onChange={toggleVoice}
              disabled={!speechSupported}
            />
            <span>🔊 朗读</span>
          </label>
        </div>
      </div>

      {saveFeedback && (
        <div className="handwriting__feedback">{saveFeedback}</div>
      )}

      {loading && (
        <div className="handwriting__warmup">
          <div className="handwriting__warmup-bar">
            <div
              className="handwriting__warmup-fill"
              style={{ width: `${warmupPercent}%` }}
            />
          </div>
        </div>
      )}

      <div className="handwriting__canvas-wrapper">
        <DrawingCanvas
          ref={canvasRef}
          width={width}
          height={height}
          onStrokeStart={handleStrokeStart}
          onStrokeEnd={handleStrokeEnd}
        />
      </div>

      <div className="handwriting__output" aria-live="polite">
        <span className="handwriting__output-label">已确认：</span>
        <span className="handwriting__output-committed">{committedText || '\u00A0'}</span>
        <span className="handwriting__output-current">{text || '\u00A0'}</span>
      </div>

      {candidates.length > 0 && (
        <div className="handwriting__candidates">
          {candidates.map((segCandidates, segIdx) => (
            <div key={segIdx} className="handwriting__candidate-row">
              <span className="handwriting__candidate-index">第 {segIdx + 1} 字</span>
              <div className="handwriting__candidate-list">
                {segCandidates.map((c, i) => (
                  <button
                    key={`${segIdx}-${i}`}
                    className={
                      'handwriting__candidate' +
                      (i === 0 ? ' handwriting__candidate--top' : '')
                    }
                    onClick={() => handlePickCandidate(segIdx, c.char)}
                    title={`得分 ${(c.score * 100).toFixed(1)}%`}
                  >
                    {c.char}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="handwriting__segments-info">
        笔画 {allStrokes.length} 笔 · 识别为 {segmentsInfo.length} 字
        {domain !== 'general' && ` · 领域：${domains.find((d) => d.id === domain)?.name}`}
      </div>
    </div>
  )
}
