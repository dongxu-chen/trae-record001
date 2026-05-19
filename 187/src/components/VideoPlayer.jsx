import { useRef, useState, useEffect } from 'react'
import { productVideo } from '../data/productData'

const VideoPlayer = () => {
  const videoRef = useRef(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [showControls, setShowControls] = useState(true)
  const [progress, setProgress] = useState(0)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const [isLoaded, setIsLoaded] = useState(false)
  const controlsTimeoutRef = useRef(null)

  const togglePlay = () => {
    if (videoRef.current) {
      if (isPlaying) {
        videoRef.current.pause()
      } else {
        videoRef.current.play()
      }
      setIsPlaying(!isPlaying)
    }
  }

  const handleTimeUpdate = () => {
    if (videoRef.current) {
      const current = videoRef.current.currentTime
      const total = videoRef.current.duration
      setCurrentTime(current)
      setProgress((current / total) * 100)
    }
  }

  const handleLoadedMetadata = () => {
    if (videoRef.current) {
      setDuration(videoRef.current.duration)
      setIsLoaded(true)
    }
  }

  const handleSeek = (e) => {
    if (videoRef.current) {
      const rect = e.currentTarget.getBoundingClientRect()
      const percent = (e.clientX - rect.left) / rect.width
      videoRef.current.currentTime = percent * videoRef.current.duration
    }
  }

  const handleMouseMove = () => {
    setShowControls(true)
    if (controlsTimeoutRef.current) {
      clearTimeout(controlsTimeoutRef.current)
    }
    if (isPlaying) {
      controlsTimeoutRef.current = setTimeout(() => {
        setShowControls(false)
      }, 3000)
    }
  }

  const formatTime = (seconds) => {
    if (!seconds) return '00:00'
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }

  useEffect(() => {
    return () => {
      if (controlsTimeoutRef.current) {
        clearTimeout(controlsTimeoutRef.current)
      }
    }
  }, [])

  return (
    <div className="video-player">
      <div className="section-header">
        <h3 className="section-title">视频讲解</h3>
        <span className="video-duration">⏱️ {productVideo.duration}</span>
      </div>

      <div
        className="video-container"
        onMouseMove={handleMouseMove}
        onMouseLeave={() => isPlaying && setShowControls(false)}
      >
        {!isPlaying && !isLoaded && (
          <div className="video-thumbnail">
            <img src={productVideo.thumbnail} alt={productVideo.title} />
            <div className="play-overlay" onClick={togglePlay}>
              <div className="play-button">
                <svg viewBox="0 0 24 24" fill="currentColor">
                  <path d="M8 5v14l11-7z" />
                </svg>
              </div>
              <p className="video-title-small">{productVideo.title}</p>
            </div>
          </div>
        )}

        <video
          ref={videoRef}
          className={`video-element ${isLoaded ? 'loaded' : ''}`}
          src={productVideo.videoUrl}
          onTimeUpdate={handleTimeUpdate}
          onLoadedMetadata={handleLoadedMetadata}
          onEnded={() => setIsPlaying(false)}
          onClick={togglePlay}
          playsInline
          preload="metadata"
        />

        <div className={`video-controls ${showControls || !isPlaying ? 'visible' : ''}`}>
          <div className="progress-bar" onClick={handleSeek}>
            <div className="progress-fill" style={{ width: `${progress}%` }} />
            <div
              className="progress-handle"
              style={{ left: `calc(${progress}% - 6px)` }}
            />
          </div>

          <div className="controls-row">
            <button className="control-btn" onClick={togglePlay}>
              {isPlaying ? (
                <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
                  <path d="M6 4h4v16H6V4zm8 0h4v16h-4V4z" />
                </svg>
              ) : (
                <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
                  <path d="M8 5v14l11-7z" />
                </svg>
              )}
            </button>

            <div className="time-display">
              {formatTime(currentTime)} / {formatTime(duration)}
            </div>

            <div className="controls-right">
              <button
                className="control-btn"
                onClick={() => {
                  if (videoRef.current) {
                    videoRef.current.currentTime = Math.max(0, videoRef.current.currentTime - 10)
                  }
                }}
                title="后退10秒"
              >
                ⏪
              </button>
              <button
                className="control-btn"
                onClick={() => {
                  if (videoRef.current) {
                    videoRef.current.currentTime = Math.min(duration, videoRef.current.currentTime + 10)
                  }
                }}
                title="前进10秒"
              >
                ⏩
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="video-info">
        <h4 className="video-title">{productVideo.title}</h4>
        <p className="video-desc">专业评测团队深度解读，全面了解产品特性与使用技巧</p>
      </div>

      <style jsx>{`
        .video-player {
          background: #fff;
          margin-top: 12px;
          padding: 16px;
          border-radius: 12px;
        }
        .section-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 16px;
          padding-bottom: 12px;
          border-bottom: 1px solid #f0f0f0;
        }
        .section-title {
          font-size: 16px;
          font-weight: 600;
          color: #333;
          margin: 0;
        }
        .video-duration {
          font-size: 13px;
          color: #999;
        }
        .video-container {
          position: relative;
          width: 100%;
          aspect-ratio: 16 / 9;
          background: #000;
          border-radius: 12px;
          overflow: hidden;
        }
        .video-thumbnail {
          position: absolute;
          inset: 0;
        }
        .video-thumbnail img {
          width: 100%;
          height: 100%;
          object-fit: cover;
        }
        .play-overlay {
          position: absolute;
          inset: 0;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          background: rgba(0, 0, 0, 0.3);
          cursor: pointer;
          transition: background 0.3s;
        }
        .play-overlay:hover {
          background: rgba(0, 0, 0, 0.4);
        }
        .play-button {
          width: 72px;
          height: 72px;
          border-radius: 50%;
          background: rgba(255, 77, 79, 0.9);
          display: flex;
          align-items: center;
          justify-content: center;
          color: #fff;
          transition: transform 0.3s;
        }
        .play-overlay:hover .play-button {
          transform: scale(1.1);
        }
        .play-button svg {
          width: 36px;
          height: 36px;
          margin-left: 4px;
        }
        .video-title-small {
          margin-top: 12px;
          color: #fff;
          font-size: 14px;
          text-shadow: 0 2px 4px rgba(0, 0, 0, 0.5);
        }
        .video-element {
          width: 100%;
          height: 100%;
          object-fit: contain;
          display: none;
        }
        .video-element.loaded {
          display: block;
        }
        .video-controls {
          position: absolute;
          left: 0;
          right: 0;
          bottom: 0;
          padding: 12px;
          background: linear-gradient(transparent, rgba(0, 0, 0, 0.7));
          opacity: 0;
          transition: opacity 0.3s;
        }
        .video-controls.visible {
          opacity: 1;
        }
        .progress-bar {
          position: relative;
          height: 4px;
          background: rgba(255, 255, 255, 0.3);
          border-radius: 2px;
          cursor: pointer;
          margin-bottom: 8px;
        }
        .progress-fill {
          height: 100%;
          background: #ff4d4f;
          border-radius: 2px;
          transition: width 0.1s linear;
        }
        .progress-handle {
          position: absolute;
          top: 50%;
          transform: translateY(-50%);
          width: 12px;
          height: 12px;
          background: #ff4d4f;
          border-radius: 50%;
          box-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
        }
        .controls-row {
          display: flex;
          align-items: center;
          justify-content: space-between;
        }
        .control-btn {
          width: 36px;
          height: 36px;
          display: flex;
          align-items: center;
          justify-content: center;
          background: transparent;
          border: none;
          color: #fff;
          font-size: 18px;
          cursor: pointer;
          border-radius: 50%;
          transition: background 0.2s;
        }
        .control-btn:hover {
          background: rgba(255, 255, 255, 0.2);
        }
        .time-display {
          color: #fff;
          font-size: 13px;
          font-family: monospace;
        }
        .controls-right {
          display: flex;
          gap: 4px;
        }
        .video-info {
          margin-top: 16px;
        }
        .video-title {
          font-size: 15px;
          font-weight: 500;
          color: #333;
          margin: 0 0 6px 0;
        }
        .video-desc {
          font-size: 13px;
          color: #999;
          margin: 0;
        }
        @media (max-width: 768px) {
          .video-player {
            padding: 12px;
            border-radius: 0;
            margin-top: 0;
          }
          .play-button {
            width: 60px;
            height: 60px;
          }
          .play-button svg {
            width: 30px;
            height: 30px;
          }
        }
      `}</style>
    </div>
  )
}

export default VideoPlayer
