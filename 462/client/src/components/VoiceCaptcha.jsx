import React, { useState, useRef, useCallback, useEffect } from 'react'
import { captchaApi } from '../services/api'
import './VoiceCaptcha.css'

const VoiceCaptcha = ({ onSuccess, onError }) => {
  const [loading, setLoading] = useState(false)
  const [captchaData, setCaptchaData] = useState(null)
  const [status, setStatus] = useState('idle')
  const [message, setMessage] = useState('')
  const [inputValue, setInputValue] = useState('')
  const [isPlaying, setIsPlaying] = useState(false)

  const canvasRef = useRef(null)
  const audioRef = useRef(null)
  const inputRef = useRef(null)

  const renderImage = useCallback((data) => {
    const canvas = canvasRef.current
    if (!canvas || !data) return

    const ctx = canvas.getContext('2d')
    const width = data.width || 200
    const height = data.height || 80

    ctx.clearRect(0, 0, width, height)

    const gradientColors = data.gradientColors || ['#f093fb', '#f5576c']
    const gradient = ctx.createLinearGradient(0, 0, width, height)
    gradient.addColorStop(0, gradientColors[0])
    gradient.addColorStop(1, gradientColors[1])
    ctx.fillStyle = gradient
    ctx.fillRect(0, 0, width, height)

    for (let i = 0; i < 20; i++) {
      ctx.beginPath()
      ctx.moveTo(Math.random() * width, Math.random() * height)
      ctx.lineTo(Math.random() * width, Math.random() * height)
      ctx.strokeStyle = `rgba(255, 255, 255, ${Math.random() * 0.5})`
      ctx.lineWidth = 1
      ctx.stroke()
    }

    data.chars.forEach((charData) => {
      ctx.save()
      ctx.translate(charData.x, charData.y)
      ctx.rotate(charData.rotateAngle)
      ctx.font = charData.font || 'bold 32px Arial'
      ctx.textAlign = 'center'
      ctx.textBaseline = 'middle'
      ctx.fillStyle = charData.color || '#ffffff'
      ctx.strokeStyle = 'rgba(0, 0, 0, 0.3)'
      ctx.lineWidth = 2
      ctx.strokeText(charData.char, 0, 0)
      ctx.fillText(charData.char, 0, 0)
      ctx.restore()
    })
  }, [])

  const loadCaptcha = useCallback(async () => {
    setLoading(true)
    setStatus('idle')
    setMessage('')
    setInputValue('')
    setIsPlaying(false)

    try {
      const response = await captchaApi.generateVoiceCaptcha()
      if (response.data && response.data.success) {
        const data = response.data
        setCaptchaData(data)
        setTimeout(() => renderImage(data), 0)
        setMessage(`请输入 ${data.codeLength || 6} 位验证码`)
      } else {
        setStatus('error')
        setMessage('加载失败，请重试')
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
    if (captchaData) {
      renderImage(captchaData)
    }
  }, [captchaData, renderImage])

  const playVoice = async () => {
    if (!captchaData || isPlaying) return

    setIsPlaying(true)
    setMessage('正在播放语音...')

    try {
      const response = await captchaApi.getVoiceCaptcha(captchaData.captchaId)
      const audioBlob = new Blob([response.data], { type: 'audio/wav' })
      const audioUrl = URL.createObjectURL(audioBlob)

      if (audioRef.current) {
        audioRef.current.src = audioUrl
        audioRef.current.onended = () => {
          setIsPlaying(false)
          setMessage('语音播放完成，请输入验证码')
          URL.revokeObjectURL(audioUrl)
        }
        audioRef.current.onerror = () => {
          setIsPlaying(false)
          speakText(captchaData.spokenText)
        }
        audioRef.current.play().catch(() => {
          speakText(captchaData.spokenText)
        })
      } else {
        speakText(captchaData.spokenText)
      }
    } catch (error) {
      speakText(captchaData.spokenText)
    }
  }

  const speakText = (text) => {
    if ('speechSynthesis' in window) {
      const utterance = new SpeechSynthesisUtterance(text)
      utterance.lang = 'en-US'
      utterance.rate = 0.8
      utterance.onend = () => {
        setIsPlaying(false)
        setMessage('语音播放完成，请输入验证码')
      }
      utterance.onerror = () => {
        setIsPlaying(false)
        setMessage('语音播放失败，请重试')
      }
      window.speechSynthesis.speak(utterance)
    } else {
      setIsPlaying(false)
      setMessage('您的浏览器不支持语音播放')
    }
  }

  const handleInputChange = (e) => {
    const value = e.target.value.toUpperCase().replace(/[^A-Z0-9]/g, '')
    setInputValue(value)

    if (value.length === captchaData?.codeLength) {
      verifyCaptcha(value)
    }
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    if (inputValue.length === captchaData?.codeLength) {
      verifyCaptcha(inputValue)
    } else {
      setMessage(`请输入完整的 ${captchaData?.codeLength || 6} 位验证码`)
    }
  }

  const verifyCaptcha = async (code) => {
    if (!captchaData) return

    setStatus('verifying')
    setMessage('验证中...')

    try {
      const response = await captchaApi.verifyVoiceCaptcha(
        captchaData.captchaId,
        code
      )

      if (response.data.success) {
        setStatus('success')
        setMessage('验证成功！')
        onSuccess?.(captchaData.captchaId)
      } else {
        setStatus('error')
        setMessage(response.data.message || '验证失败')
        setInputValue('')
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
      setInputValue('')
      console.error('Verify error:', error)
    }
  }

  return (
    <div className="voice-captcha-container">
      <div className="voice-header">
        <div className="voice-icon" aria-hidden="true">
          🔊
        </div>
        <div className="voice-title">
          <h3>语音验证码</h3>
          <p>无障碍验证模式</p>
        </div>
      </div>

      <div className="voice-content">
        <div className="voice-image-wrapper">
          <canvas
            ref={canvasRef}
            width={captchaData?.width || 200}
            height={captchaData?.height || 80}
            className="voice-canvas"
          />
        </div>

        <button
          className={`voice-play-btn ${isPlaying ? 'playing' : ''}`}
          onClick={playVoice}
          disabled={loading || isPlaying || status === 'success' || !captchaData}
          aria-label={isPlaying ? '正在播放' : '播放语音'}
        >
          <span className="play-icon">
            {isPlaying ? '🔊' : '▶️'}
          </span>
          <span className="play-text">
            {isPlaying ? '播放中...' : '点击播放语音'}
          </span>
          {isPlaying && <span className="playing-animation" />}
        </button>

        <form onSubmit={handleSubmit} className="voice-input-form">
          <div className="voice-input-wrapper">
            <input
              ref={inputRef}
              type="text"
              value={inputValue}
              onChange={handleInputChange}
              placeholder="请输入验证码"
              className="voice-input"
              maxLength={captchaData?.codeLength || 6}
              disabled={loading || status === 'success' || status === 'verifying'}
              autoComplete="off"
              autoCapitalize="characters"
              aria-label="验证码输入框"
            />
            <div className="input-underline">
              {Array.from({ length: captchaData?.codeLength || 6 }).map((_, i) => (
                <div
                  key={i}
                  className={`underline-box ${i < inputValue.length ? 'filled' : ''}`}
                >
                  {inputValue[i] || ''}
                </div>
              ))}
            </div>
          </div>

          <button
            type="submit"
            className="voice-submit-btn"
            disabled={
              loading ||
              status === 'success' ||
              status === 'verifying' ||
              inputValue.length !== captchaData?.codeLength
            }
          >
            验证
          </button>
        </form>
      </div>

      <audio ref={audioRef} style={{ display: 'none' }} />

      <div className={`captcha-status status-${status}`}>
        {message || '点击播放按钮获取语音验证码'}
      </div>

      <div className="voice-controls">
        <button
          className="captcha-refresh-btn"
          onClick={loadCaptcha}
          disabled={loading || isPlaying || status === 'verifying'}
          aria-label="刷新验证码"
        >
          🔄 换一个
        </button>
      </div>
    </div>
  )
}

export default VoiceCaptcha
