import { useState, useEffect, useRef, useCallback } from 'react'

function Countdown({ initialTime, isRunning, onComplete, onTick }) {
  const [timeLeft, setTimeLeft] = useState(initialTime)
  const intervalRef = useRef(null)
  const hasCompletedRef = useRef(false)
  const audioRef = useRef(null)

  useEffect(() => {
    setTimeLeft(initialTime)
    hasCompletedRef.current = false
    if (audioRef.current) {
      audioRef.current.pause()
      audioRef.current.currentTime = 0
    }
  }, [initialTime])

  const playCompletionSound = useCallback(() => {
    try {
      if (!audioRef.current) {
        const audioContext = new (window.AudioContext || window.webkitAudioContext)()
        const oscillator = audioContext.createOscillator()
        const gainNode = audioContext.createGain()
        
        oscillator.connect(gainNode)
        gainNode.connect(audioContext.destination)
        
        oscillator.frequency.value = 880
        oscillator.type = 'sine'
        gainNode.gain.setValueAtTime(0.3, audioContext.currentTime)
        gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.5)
        
        oscillator.start(audioContext.currentTime)
        oscillator.stop(audioContext.currentTime + 0.5)
      }
    } catch (error) {
      console.log('Audio not supported:', error)
    }
  }, [])

  const tick = useCallback(() => {
    setTimeLeft((prev) => {
      if (prev <= 1 && !hasCompletedRef.current) {
        hasCompletedRef.current = true
        if (intervalRef.current) {
          clearInterval(intervalRef.current)
          intervalRef.current = null
        }
        playCompletionSound()
        if (onComplete) onComplete()
        return 0
      }
      const newTime = prev - 1
      if (onTick) onTick(newTime)
      return newTime
    })
  }, [onComplete, onTick, playCompletionSound])

  useEffect(() => {
    if (isRunning) {
      intervalRef.current = setInterval(tick, 1000)
    } else {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
    }
  }, [isRunning, tick])

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }

  const progress = ((initialTime - timeLeft) / initialTime) * 100

  return (
    <div className="countdown-container">
      <div className="countdown-ring">
        <svg width="200" height="200" className="countdown-svg">
          <circle
            cx="100"
            cy="100"
            r="90"
            stroke="#e0e0e0"
            strokeWidth="8"
            fill="none"
          />
          <circle
            cx="100"
            cy="100"
            r="90"
            stroke="#ff6b6b"
            strokeWidth="8"
            fill="none"
            strokeDasharray={2 * Math.PI * 90}
            strokeDashoffset={2 * Math.PI * 90 * (1 - progress / 100)}
            strokeLinecap="round"
            transform="rotate(-90 100 100)"
            className="countdown-progress"
          />
        </svg>
        <div className="countdown-text">
          {formatTime(timeLeft)}
        </div>
      </div>
    </div>
  )
}

export default Countdown
