import React, { useState, useRef, useEffect, useCallback } from 'react'
import { captchaApi } from '../services/api'
import './SlideCaptcha.css'

const PADDING = 20
const TRAJECTORY_SAMPLE_RATE = 10

const SlideCaptcha = ({ onSuccess, onError }) => {
  const [loading, setLoading] = useState(false)
  const [captchaData, setCaptchaData] = useState(null)
  const [status, setStatus] = useState('idle')
  const [message, setMessage] = useState('')
  const [puzzlePos, setPuzzlePos] = useState(0)
  const [isDragging, setIsDragging] = useState(false)
  const [difficulty, setDifficulty] = useState('medium')
  const [attempts, setAttempts] = useState(1)

  const containerRef = useRef(null)
  const dragStartRef = useRef({ clientX: 0, startPos: 0, startTime: 0 })
  const trajectoryRef = useRef([])
  const lastSampleRef = useRef(0)
  const loadStartTime = useRef(0)

  const loadCaptcha = useCallback(async (targetDifficulty) => {
    setLoading(true)
    setStatus('idle')
    setMessage('')
    setPuzzlePos(0)
    setAttempts(1)
    trajectoryRef.current = []
    loadStartTime.current = Date.now()

    try {
      const response = await captchaApi.generateSlideCaptcha(targetDifficulty || difficulty)
      if (response.data.success) {
        setCaptchaData(response.data)
        setDifficulty(response.data.difficulty || 'medium')
        setPuzzlePos(0)
      } else {
        setStatus('error')
        setMessage(response.data.message || '加载失败')
      }
    } catch (error) {
      setStatus('error')
      setMessage('网络错误，请重试')
      console.error('Load captcha error:', error)
    } finally {
      setLoading(false)
    }
  }, [difficulty])

  useEffect(() => {
    loadCaptcha()
  }, [])

  const recordTrajectoryPoint = useCallback((x, y) => {
    const now = Date.now()
    if (now - lastSampleRef.current >= TRAJECTORY_SAMPLE_RATE) {
      trajectoryRef.current.push({ x, y, t: now })
      lastSampleRef.current = now
    }
  }, [])

  const handleMouseDown = useCallback((e) => {
    if (status === 'success' || loading || !captchaData) return
    const clientX = e.clientX ?? e.touches?.[0]?.clientX
    const clientY = e.clientY ?? e.touches?.[0]?.clientY
    if (clientX === undefined) return

    const rect = containerRef.current.getBoundingClientRect()
    const clickX = clientX - rect.left
    const puzzleSize = captchaData.puzzleSize || 50
    const pieceWidth = puzzleSize + PADDING * 2

    if (clickX >= puzzlePos && clickX <= puzzlePos + pieceWidth) {
      setIsDragging(true)
      setStatus('dragging')
      trajectoryRef.current = []
      const relativeX = clientX - rect.left
      const relativeY = clientY - rect.top
      recordTrajectoryPoint(relativeX, relativeY)
      dragStartRef.current = { clientX, startPos: puzzlePos, startTime: Date.now() }
    }
  }, [status, loading, captchaData, puzzlePos, recordTrajectoryPoint])

  const handleMouseMove = useCallback((e) => {
    if (!isDragging) return
    const clientX = e.clientX ?? e.touches?.[0]?.clientX
    const clientY = e.clientY ?? e.touches?.[0]?.clientY
    if (clientX === undefined) return

    const rect = containerRef.current.getBoundingClientRect()
    const relativeX = clientX - rect.left
    const relativeY = clientY - rect.top
    recordTrajectoryPoint(relativeX, relativeY)

    const dx = clientX - dragStartRef.current.clientX
    const width = captchaData?.width || 400
    const puzzleSize = captchaData?.puzzleSize || 50
    const maxPos = width - puzzleSize - PADDING
    const newX = Math.max(-PADDING, Math.min(maxPos, dragStartRef.current.startPos + dx))
    setPuzzlePos(newX)
  }, [isDragging, captchaData, recordTrajectoryPoint])

  const handleMouseUp = useCallback(async () => {
    if (!isDragging) return
    setIsDragging(false)

    if (!captchaData) return

    const answerX = Math.round(puzzlePos + PADDING)
    const duration = Date.now() - loadStartTime.current

    setStatus('verifying')
    setMessage('验证中...')

    try {
      const response = await captchaApi.verifySlideCaptcha(
        captchaData.captchaId,
        answerX,
        captchaData.puzzleY,
        trajectoryRef.current,
        attempts,
        duration
      )

      if (response.data.success) {
        setStatus('success')
        const riskMsg = response.data.riskLevel
          ? ` (风险等级: ${response.data.riskLevel === 'low' ? '低' : response.data.riskLevel === 'medium' ? '中' : '高'})`
          : ''
        setMessage(`验证成功！${riskMsg}`)
        onSuccess?.(captchaData.captchaId)
      } else {
        setStatus('error')
        const riskMsg = response.data.riskLevel
          ? ` (风险等级: ${response.data.riskLevel === 'low' ? '低' : response.data.riskLevel === 'medium' ? '中' : '高'})`
          : ''
        setMessage(`${response.data.message || '验证失败'}${riskMsg}`)
        onError?.(response.data)

        if (response.data.upgradeDifficulty && difficulty !== 'hard') {
          setTimeout(() => {
            setDifficulty('hard')
            loadCaptcha('hard')
          }, 1500)
        } else if (!response.data.locked) {
          setAttempts(prev => prev + 1)
          setTimeout(() => {
            loadCaptcha()
          }, 1500)
        }
      }
    } catch (error) {
      setStatus('error')
      setMessage('网络错误，请重试')
      console.error('Verify error:', error)
    }
  }, [isDragging, puzzlePos, captchaData, attempts, difficulty, onSuccess, onError, loadCaptcha])

  useEffect(() => {
    const onMouseUp = () => {
      if (isDragging) handleMouseUp()
    }

    window.addEventListener('mouseup', onMouseUp)
    window.addEventListener('touchend', onMouseUp)

    return () => {
      window.removeEventListener('mouseup', onMouseUp)
      window.removeEventListener('touchend', onMouseUp)
    }
  }, [isDragging, handleMouseUp])

  const puzzleSize = captchaData?.puzzleSize || 50
  const pieceWidth = puzzleSize + PADDING * 2

  return (
    <div className="slide-captcha-container">
      <div
        ref={containerRef}
        className="captcha-canvas-wrapper"
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onTouchStart={handleMouseDown}
        onTouchMove={handleMouseMove}
        style={{ cursor: isDragging ? 'grabbing' : 'default' }}
      >
        {captchaData && (
          <img
            src={captchaData.originalImage}
            alt=""
            className="captcha-bg-img"
            draggable={false}
          />
        )}

        {captchaData && (
          <img
            src={captchaData.puzzleImage}
            alt=""
            className="captcha-puzzle-img"
            draggable={false}
            style={{
              left: `${puzzlePos}px`,
              top: `${(captchaData.puzzleY || 0) - PADDING}px`,
              width: `${pieceWidth}px`,
              cursor: isDragging ? 'grabbing' : 'grab',
            }}
          />
        )}

        {loading && (
          <div className="captcha-loading-overlay">
            <div className="captcha-spinner" />
            <span>加载中...</span>
          </div>
        )}
      </div>

      <div className="captcha-controls">
        <div className={`captcha-status status-${status}`}>
          {message || (status === 'idle' && '请拖动滑块到正确位置')}
        </div>
        <button
          className="captcha-refresh-btn"
          onClick={loadCaptcha}
          disabled={loading || isDragging || status === 'verifying'}
          aria-label="刷新验证码"
        >
          🔄 刷新
        </button>
      </div>
    </div>
  )
}

export default SlideCaptcha
