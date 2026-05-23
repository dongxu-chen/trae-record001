import { useState, useRef, useEffect, useCallback } from 'react'
import { findCurrentLyricIndex } from '../utils/lrcParser'

export default function FloatingLyrics({ lyrics, currentTime, isPlaying, onClose }) {
  const [position, setPosition] = useState({ x: window.innerWidth / 2 - 200, y: 100 })
  const [opacity, setOpacity] = useState(0.9)
  const [isDragging, setIsDragging] = useState(false)
  const [showControls, setShowControls] = useState(false)
  const dragOffset = useRef({ x: 0, y: 0 })
  const containerRef = useRef(null)

  const currentIndex = findCurrentLyricIndex(lyrics, currentTime)
  const currentLyric = lyrics[currentIndex]?.text || ''
  const nextLyric = lyrics[currentIndex + 1]?.text || ''

  const handleMouseDown = useCallback((e) => {
    if (e.target.closest('.floating-controls')) return
    setIsDragging(true)
    dragOffset.current = {
      x: e.clientX - position.x,
      y: e.clientY - position.y
    }
  }, [position])

  const handleMouseMove = useCallback((e) => {
    if (!isDragging) return
    setPosition({
      x: e.clientX - dragOffset.current.x,
      y: e.clientY - dragOffset.current.y
    })
  }, [isDragging])

  const handleMouseUp = useCallback(() => {
    setIsDragging(false)
  }, [])

  useEffect(() => {
    if (isDragging) {
      document.addEventListener('mousemove', handleMouseMove)
      document.addEventListener('mouseup', handleMouseUp)
    }
    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
    }
  }, [isDragging, handleMouseMove, handleMouseUp])

  const handleTouchStart = useCallback((e) => {
    if (e.target.closest('.floating-controls')) return
    const touch = e.touches[0]
    setIsDragging(true)
    dragOffset.current = {
      x: touch.clientX - position.x,
      y: touch.clientY - position.y
    }
  }, [position])

  const handleTouchMove = useCallback((e) => {
    if (!isDragging) return
    const touch = e.touches[0]
    setPosition({
      x: touch.clientX - dragOffset.current.x,
      y: touch.clientY - dragOffset.current.y
    })
  }, [isDragging])

  const handleTouchEnd = useCallback(() => {
    setIsDragging(false)
  }, [])

  return (
    <div
      ref={containerRef}
      className="floating-lyrics"
      style={{
        left: position.x,
        top: position.y,
        opacity: opacity
      }}
      onMouseDown={handleMouseDown}
      onMouseEnter={() => setShowControls(true)}
      onMouseLeave={() => !isDragging && setShowControls(false)}
      onTouchStart={handleTouchStart}
      onTouchMove={handleTouchMove}
      onTouchEnd={handleTouchEnd}
    >
      <div className={`floating-controls ${showControls ? 'visible' : ''}`}>
        <div className="opacity-control">
          <svg viewBox="0 0 24 24" fill="currentColor" width="14" height="14">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8z"/>
          </svg>
          <input
            type="range"
            min="0.3"
            max="1"
            step="0.1"
            value={opacity}
            onChange={(e) => setOpacity(parseFloat(e.target.value))}
          />
        </div>
        <button className="close-btn" onClick={onClose}>
          <svg viewBox="0 0 24 24" fill="currentColor" width="16" height="16">
            <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
          </svg>
        </button>
      </div>
      
      <div className="lyrics-content-float">
        <div className={`next-lyric ${isPlaying ? '' : 'paused'}`}>
          {nextLyric}
        </div>
        <div className={`current-lyric ${isPlaying ? '' : 'paused'}`}>
          {currentLyric || (isPlaying ? '正在播放...' : '暂停播放')}
        </div>
      </div>
    </div>
  )
}
