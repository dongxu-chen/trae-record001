import React, { useState, useRef, useEffect, useCallback } from 'react'
import { captchaApi } from '../services/api'
import './RotateCaptcha.css'

const RotateCaptcha = ({ onSuccess, onError }) => {
  const [loading, setLoading] = useState(false)
  const [captchaData, setCaptchaData] = useState(null)
  const [status, setStatus] = useState('idle')
  const [message, setMessage] = useState('')
  const [currentAngle, setCurrentAngle] = useState(0)
  const [isDragging, setIsDragging] = useState(false)
  const [imageLoaded, setImageLoaded] = useState(false)

  const canvasRef = useRef(null)
  const sliderRef = useRef(null)
  const containerRef = useRef(null)
  const startXRef = useRef(0)
  const startAngleRef = useRef(0)
  const bgImageRef = useRef(null)

  const renderImage = useCallback((data, angle) => {
    const canvas = canvasRef.current
    if (!canvas || !data || !bgImageRef.current) return

    const ctx = canvas.getContext('2d')
    const size = data.size || 300
    const drawSize = size * 0.7

    ctx.clearRect(0, 0, size, size)

    ctx.save()
    ctx.translate(size / 2, size / 2)
    ctx.rotate((angle * Math.PI) / 180)

    ctx.save()
    ctx.beginPath()
    ctx.arc(0, 0, drawSize / 2, 0, Math.PI * 2)
    ctx.closePath()
    ctx.clip()
    ctx.drawImage(bgImageRef.current, -drawSize / 2, -drawSize / 2, drawSize, drawSize)
    ctx.restore()

    ctx.beginPath()
    ctx.arc(0, 0, drawSize / 2, 0, Math.PI * 2)
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.8)'
    ctx.lineWidth = 4
    ctx.stroke()

    ctx.restore()

    ctx.save()
    ctx.beginPath()
    ctx.arc(size / 2, size / 2, drawSize / 2 + 4, 0, Math.PI * 2)
    ctx.strokeStyle = 'rgba(102, 126, 234, 0.6)'
    ctx.lineWidth = 3
    ctx.setLineDash([8, 4])
    ctx.stroke()
    ctx.restore()

    ctx.save()
    const arrowY = size / 2 - drawSize / 2 - 12
    ctx.beginPath()
    ctx.moveTo(size / 2, arrowY)
    ctx.lineTo(size / 2 - 12, arrowY - 16)
    ctx.lineTo(size / 2 + 12, arrowY - 16)
    ctx.closePath()
    ctx.fillStyle = '#ff4757'
    ctx.fill()
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.8)'
    ctx.lineWidth = 2
    ctx.stroke()
    ctx.restore()

    ctx.save()
    ctx.font = 'bold 14px Arial'
    ctx.textAlign = 'center'
    ctx.textBaseline = 'top'
    ctx.fillStyle = '#ff4757'
    ctx.fillText('▲ 正向', size / 2, arrowY - 36)
    ctx.restore()
  }, [])

  const loadCaptcha = useCallback(async () => {
    setLoading(true)
    setStatus('idle')
    setMessage('')
    setCurrentAngle(0)
    setImageLoaded(false)
    bgImageRef.current = null

    try {
      const response = await captchaApi.generateRotateCaptcha()
      if (response.data.success) {
        const data = response.data
        setCaptchaData(data)

        const img = new Image()
        img.crossOrigin = 'anonymous'
        img.onload = () => {
          bgImageRef.current = img
          setImageLoaded(true)
          renderImage(data, 0)
        }
        img.onerror = () => {
          const canvas = document.createElement('canvas')
          canvas.width = 300
          canvas.height = 300
          const ctx = canvas.getContext('2d')
          const gradient = ctx.createLinearGradient(0, 0, 300, 300)
          gradient.addColorStop(0, '#667eea')
          gradient.addColorStop(1, '#764ba2')
          ctx.fillStyle = gradient
          ctx.fillRect(0, 0, 300, 300)

          for (let i = 0; i < 15; i++) {
            ctx.save()
            ctx.translate(Math.random() * 300, Math.random() * 300)
            ctx.rotate(Math.random() * Math.PI * 2)
            ctx.fillStyle = `hsla(${Math.random() * 360}, 70%, 60%, 0.8)`
            ctx.fillRect(-20, -20, 40, 40)
            ctx.restore()
          }

          const tempImg = new Image()
          tempImg.onload = () => {
            bgImageRef.current = tempImg
            setImageLoaded(true)
            renderImage(data, 0)
          }
          tempImg.src = canvas.toDataURL()
        }
        img.src = data.imageUrl
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
  }, [renderImage])

  useEffect(() => {
    loadCaptcha()
  }, [loadCaptcha])

  useEffect(() => {
    if (captchaData && imageLoaded) {
      renderImage(captchaData, currentAngle)
    }
  }, [currentAngle, captchaData, imageLoaded, renderImage])

  const handleSliderMouseDown = (e) => {
    if (status === 'success' || loading || !imageLoaded) return

    const clientX = e.clientX || e.touches?.[0]?.clientX
    if (clientX === undefined) return

    setIsDragging(true)
    setStatus('dragging')
    startXRef.current = clientX
    startAngleRef.current = currentAngle
  }

  const handleMouseMove = (e) => {
    if (!isDragging) return

    const clientX = e.clientX || e.touches?.[0]?.clientX
    if (clientX === undefined) return

    const deltaX = clientX - startXRef.current
    const sensitivity = 1.5
    let newAngle = startAngleRef.current + deltaX * sensitivity

    newAngle = ((newAngle % 360) + 360) % 360
    setCurrentAngle(newAngle)
  }

  const handleMouseUp = async () => {
    if (!isDragging) return
    setIsDragging(false)

    if (!captchaData) return

    setStatus('verifying')
    setMessage('验证中...')

    try {
      const response = await captchaApi.verifyRotateCaptcha(
        captchaData.captchaId,
        Math.round(currentAngle)
      )

      if (response.data.success) {
        setStatus('success')
        setMessage('验证成功！')
        onSuccess?.(captchaData.captchaId)
      } else {
        setStatus('error')
        setMessage(response.data.message || '验证失败')
        onError?.(response.data)

        if (!response.data.locked) {
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

  useEffect(() => {
    const handleGlobalMouseMove = (e) => handleMouseMove(e)
    const handleGlobalMouseUp = () => {
      if (isDragging) {
        handleMouseUp()
      }
    }

    window.addEventListener('mousemove', handleGlobalMouseMove)
    window.addEventListener('touchmove', handleGlobalMouseMove)
    window.addEventListener('mouseup', handleGlobalMouseUp)
    window.addEventListener('touchend', handleGlobalMouseUp)

    return () => {
      window.removeEventListener('mousemove', handleGlobalMouseMove)
      window.removeEventListener('touchmove', handleGlobalMouseMove)
      window.removeEventListener('mouseup', handleGlobalMouseUp)
      window.removeEventListener('touchend', handleGlobalMouseUp)
    }
  }, [isDragging, currentAngle, captchaData])

  const handleSliderInput = (e) => {
    if (status === 'success' || loading || !imageLoaded) return
    setStatus('dragging')
    setCurrentAngle(Number(e.target.value))
  }

  const handleSliderChangeComplete = () => {
    if (status !== 'dragging') return
    handleMouseUp()
  }

  return (
    <div className="rotate-captcha-container" ref={containerRef}>
      <div className="captcha-canvas-wrapper">
        <canvas
          ref={canvasRef}
          width={300}
          height={300}
          className="rotate-canvas"
        />

        {loading && (
          <div className="captcha-loading-overlay">
            <div className="captcha-spinner" />
            <span>加载中...</span>
          </div>
        )}
      </div>

      <div className="angle-display">
        当前角度: <span className="angle-value">{Math.round(currentAngle)}°</span>
      </div>

      <div className="rotate-slider-container">
        <div className="rotate-slider-track">
          <input
            ref={sliderRef}
            type="range"
            min="0"
            max="360"
            value={currentAngle}
            onChange={handleSliderInput}
            onMouseDown={handleSliderMouseDown}
            onMouseUp={handleSliderChangeComplete}
            onTouchStart={handleSliderMouseDown}
            onTouchEnd={handleSliderChangeComplete}
            className="rotate-slider"
            disabled={loading || status === 'success' || status === 'verifying' || !imageLoaded}
            aria-label="旋转角度滑块"
          />
        </div>
        <div
          className="rotate-handle"
          onMouseDown={handleSliderMouseDown}
          onTouchStart={handleSliderMouseDown}
          style={{ left: `${(currentAngle / 360) * 100}%` }}
        >
          <span className="rotate-handle-icon">↻</span>
        </div>
      </div>

      <div className="captcha-controls">
        <div className={`captcha-status status-${status}`}>
          {message || (status === 'idle' && '请拖动滑块将图片旋转至正确角度')}
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

export default RotateCaptcha
