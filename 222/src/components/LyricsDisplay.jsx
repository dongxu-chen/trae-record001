import { useEffect, useRef } from 'react'
import { findCurrentLyricIndex } from '../utils/lrcParser'

export default function LyricsDisplay({ lyrics, currentTime }) {
  const containerRef = useRef(null)
  const currentLineRef = useRef(null)

  const currentIndex = findCurrentLyricIndex(lyrics, currentTime)

  useEffect(() => {
    if (currentLineRef.current && containerRef.current) {
      currentLineRef.current.scrollIntoView({
        behavior: 'smooth',
        block: 'center'
      })
    }
  }, [currentIndex])

  if (lyrics.length === 0) {
    return (
      <div className="lyrics-panel">
        <div className="lyrics-title">
          <svg viewBox="0 0 24 24" fill="currentColor" width="16" height="16">
            <path d="M14 2H6c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 1.99 2H18c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z"/>
          </svg>
          歌词
        </div>
        <div className="empty-lyrics">
          暂无歌词<br />
          <span style={{ fontSize: '0.75rem', color: '#555' }}>
            可上传同文件名的 .lrc 文件显示歌词
          </span>
        </div>
      </div>
    )
  }

  return (
    <div className="lyrics-panel" ref={containerRef}>
      <div className="lyrics-title">
        <svg viewBox="0 0 24 24" fill="currentColor" width="16" height="16">
          <path d="M14 2H6c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 1.99 2H18c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z"/>
        </svg>
        歌词
      </div>
      <div className="lyrics-content">
        {lyrics.map((line, index) => (
          <div
            key={index}
            ref={index === currentIndex ? currentLineRef : null}
            className={`lyrics-line ${
              index === currentIndex ? 'active' :
              index < currentIndex ? 'past' : ''
            }`}
          >
            {line.text}
          </div>
        ))}
      </div>
    </div>
  )
}
