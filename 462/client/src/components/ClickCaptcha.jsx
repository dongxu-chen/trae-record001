import React, { useState, useRef, useEffect, useCallback } from 'react'
import { captchaApi } from '../services/api'
import './ClickCaptcha.css'

const ClickCaptcha = ({ onSuccess, onError }) => {
  const [loading, setLoading] = useState(false)
  const [captchaData, setCaptchaData] = useState(null)
  const [status, setStatus] = useState('idle')
  const [message, setMessage] = useState('')
  const [clickedPoints, setClickedPoints] = useState([])
  const [hoverPos, setHoverPos] = useState(null)
  const [difficulty, setDifficulty] = useState('medium')
  const [attempts, setAttempts] = useState(1)

  const canvasRef = useRef(null)
  const containerRef = useRef(null)
  const clickTimesRef = useRef([])
  const loadStartTime = useRef(0)

  const renderImage = useCallback((data, points) => {
    const canvas = canvasRef.current
    if (!canvas || !data) return

    const ctx = canvas.getContext('2d')
    const width = data.width || 350
    const height = data.height || 200

    ctx.clearRect(0, 0, width, height)

    const gradientColors = data.gradientColors || ['#667eea', '#764ba2']
    const gradient = ctx.createLinearGradient(0, 0, width, height)
    gradient.addColorStop(0, gradientColors[0])
    gradient.addColorStop(1, gradientColors[1])
    ctx.fillStyle = gradient
    ctx.fillRect(0, 0, width, height)

    for (let i = 0; i < 8; i++) {
      ctx.beginPath()
      ctx.arc(
        Math.random() * width,
        Math.random() * height,
        Math.random() * 30 + 10,
        0,
        Math.PI * 2
      )
      ctx.fillStyle = `rgba(255, 255, 255, ${Math.random() * 0.3 + 0.1})`
      ctx.fill()
    }

    for (let i = 0; i < 50; i++) {
      ctx.beginPath()
      ctx.moveTo(Math.random() * width, Math.random() * height)
      ctx.lineTo(Math.random() * width, Math.random() * height)
      ctx.strokeStyle = `rgba(255, 255, 255, ${Math.random() * 0.3})`
      ctx.lineWidth = 1
      ctx.stroke()
    }

    const fontSize = 36
    data.chars.forEach((charData) => {
      ctx.save()
      ctx.translate(charData.x, charData.y)
      ctx.rotate((charData.rotateAngle * Math.PI) / 180)
      ctx.font = `bold ${fontSize}px ${charData.font || 'Arial'}`
      ctx.textAlign = 'center'
      ctx.textBaseline = 'middle'
      ctx.fillStyle = charData.color
      ctx.strokeStyle = 'rgba(0, 0, 0, 0.3)'
      ctx.lineWidth = 2
      ctx.strokeText(charData.char, 0, 0)
      ctx.fillText(charData.char, 0, 0)
      ctx.restore()
    })

    points.forEach((point, index) => {
      ctx.save()
      ctx.beginPath()
      ctx.arc(point.x, point.y, 18, 0, Math.PI * 2)
      ctx.fillStyle = 'rgba(102, 126, 234, 0.8)'
      ctx.fill()
      ctx.strokeStyle = 'white'
      ctx.lineWidth = 3
      ctx.stroke()

      ctx.fillStyle = 'white'
      ctx.font = 'bold 16px Arial'
      ctx.textAlign = 'center'
      ctx.textBaseline = 'middle'
      ctx.fillText(String(index + 1), point.x, point.y)
      ctx.restore()
    })

    if (hoverPos) {
      ctx.save()
      ctx.beginPath()
      ctx.arc(hoverPos.x, hoverPos.y, 20, 0, Math.PI * 2)
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.6)'
      ctx.lineWidth = 2
      ctx.setLineDash([5, 5])
      ctx.stroke()
      ctx.restore()
    }
  }, [hoverPos])

  const loadCaptcha = useCallback(async (targetDifficulty) => {
    setLoading(true)
    setStatus('idle')
    setMessage('')
    setClickedPoints([])
    setHoverPos(null)
    setAttempts(1)
    clickTimesRef.current = []
    loadStartTime.current = Date.now()

    try {
      const response = await captchaApi.generateClickCaptcha(targetDifficulty || difficulty)
      if (response.data.success) {
        setCaptchaData(response.data)
        setDifficulty(response.data.difficulty || 'medium')
        setMessage(response.data.tipText)
        renderImage(response.data, [])
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
  }, [renderImage, difficulty])

  useEffect(() => {
    loadCaptcha()
  }, [loadCaptcha])

  useEffect(() => {
    if (captchaData) {
      renderImage(captchaData, clickedPoints)
    }
  }, [clickedPoints, hoverPos, captchaData, renderImage])

  const handleCanvasClick = (e) => {
    if (status === 'success' || status === 'verifying' || loading || !captchaData) return

    const rect = canvasRef.current.getBoundingClientRect()
    const scaleX = canvasRef.current.width / rect.width
    const scaleY = canvasRef.current.height / rect.height

    const x = (e.clientX - rect.left) * scaleX
    const y = (e.clientY - rect.top) * scaleY
    const t = Date.now()

    clickTimesRef.current.push({ x: Math.round(x), y: Math.round(y), t })

    const newPoints = [...clickedPoints, { x: Math.round(x), y: Math.round(y) }]
    setClickedPoints(newPoints)

    if (newPoints.length >= captchaData.clickCount) {
      verifyCaptcha(newPoints)
    }
  }

  const handleCanvasMouseMove = (e) => {
    if (status === 'success' || status === 'verifying' || loading) {
      setHoverPos(null)
      return
    }

    const rect = canvasRef.current.getBoundingClientRect()
    const scaleX = canvasRef.current.width / rect.width
    const scaleY = canvasRef.current.height / rect.height

    const x = (e.clientX - rect.left) * scaleX
    const y = (e.clientY - rect.top) * scaleY

    setHoverPos({ x, y })
  }

  const handleCanvasMouseLeave = () => {
    setHoverPos(null)
  }

  const verifyCaptcha = async (points) => {
    if (!captchaData) return

    setStatus('verifying')
    setMessage('验证中...')
    const duration = Date.now() - loadStartTime.current

    try {
      const response = await captchaApi.verifyClickCaptcha(
        captchaData.captchaId,
        points,
        clickTimesRef.current,
        attempts,
        duration
      )

      if (response.data.success) {
        setStatus('success')
        const riskMsg = response.data.behaviorScore !== undefined
          ? ` (行为风险: ${Math.round(response.data.behaviorScore)}%)`
          : ''
        setMessage(`验证成功！${riskMsg}`)
        onSuccess?.(captchaData.captchaId)
      } else {
        setStatus('error')
        const riskMsg = response.data.behaviorScore !== undefined
          ? ` (行为风险: ${Math.round(response.data.behaviorScore)}%)`
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
  }

  const handleUndo = () => {
    if (clickedPoints.length > 0 && status !== 'verifying') {
      setClickedPoints(prev => prev.slice(0, -1))
    }
  }

  const handleReset = () => {
    if (status !== 'verifying') {
      setClickedPoints([])
    }
  }

  return (
    <div className="click-captcha-container" ref={containerRef}>
      <div className="captcha-tip">
        <span className="tip-icon">👆</span>
        <span className="tip-text">{message || captchaData?.tipText}</span>
      </div>

      <div className="captcha-canvas-wrapper">
        <canvas
          ref={canvasRef}
          width={captchaData?.width || 350}
          height={captchaData?.height || 200}
          className="click-canvas"
          onClick={handleCanvasClick}
          onMouseMove={handleCanvasMouseMove}
          onMouseLeave={handleCanvasMouseLeave}
          style={{
            cursor: status === 'success' || status === 'verifying' ? 'not-allowed' : 'crosshair',
          }}
        />

        {loading && (
          <div className="captcha-loading-overlay">
            <div className="captcha-spinner" />
            <span>加载中...</span>
          </div>
        )}
      </div>

      <div className="click-progress">
        <span className="progress-text">
          已选择: {clickedPoints.length} / {captchaData?.clickCount || 3}
        </span>
        <div className="progress-dots">
          {Array.from({ length: captchaData?.clickCount || 3 }).map((_, i) => (
            <div
              key={i}
              className={`progress-dot ${i < clickedPoints.length ? 'active' : ''}`}
            />
          ))}
        </div>
      </div>

      <div className="captcha-controls">
        <div className={`captcha-status status-${status}`}>
          {status === 'idle' && '请按顺序点击图中的文字'}
          {status === 'verifying' && '验证中...'}
          {status === 'success' && '验证成功！'}
          {status === 'error' && message}
        </div>
        <div className="control-buttons">
          <button
            className="captcha-action-btn"
            onClick={handleUndo}
            disabled={loading || clickedPoints.length === 0 || status === 'verifying' || status === 'success'}
            aria-label="撤销"
          >
            ↩️ 撤销
          </button>
          <button
            className="captcha-action-btn"
            onClick={handleReset}
            disabled={loading || clickedPoints.length === 0 || status === 'verifying' || status === 'success'}
            aria-label="重置"
          >
            🔄 重置
          </button>
          <button
            className="captcha-refresh-btn"
            onClick={loadCaptcha}
            disabled={loading || status === 'verifying'}
            aria-label="刷新验证码"
          >
            🆕 换一张
          </button>
        </div>
      </div>
    </div>
  )
}

export default ClickCaptcha
