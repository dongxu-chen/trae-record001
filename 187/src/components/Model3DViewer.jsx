import { useRef, useState, useEffect, useCallback } from 'react'
import { observer } from 'mobx-react-lite'

const Model3DViewer = observer(({ images }) => {
  const containerRef = useRef(null)
  const [isDragging, setIsDragging] = useState(false)
  const [rotation, setRotation] = useState(0)
  const [scale, setScale] = useState(1)
  const [currentFrame, setCurrentFrame] = useState(0)
  const [isAutoPlay, setIsAutoPlay] = useState(false)
  const lastXRef = useRef(0)
  const lastYRef = useRef(0)
  const pinchStartRef = useRef(0)
  const autoPlayRef = useRef(null)

  const totalFrames = images.length

  const handleStart = useCallback((clientX, clientY) => {
    setIsDragging(true)
    lastXRef.current = clientX
    lastYRef.current = clientY
    setIsAutoPlay(false)
  }, [])

  const handleMove = useCallback((clientX, clientY, clientX2, clientY2) => {
    if (!isDragging) return

    if (clientX2 !== undefined && clientY2 !== undefined) {
      const currentDistance = Math.hypot(clientX2 - clientX, clientY2 - clientY)
      if (pinchStartRef.current > 0) {
        const scaleChange = currentDistance / pinchStartRef.current
        setScale(prev => Math.max(0.5, Math.min(2, prev * scaleChange)))
      }
      pinchStartRef.current = currentDistance
    } else {
      const deltaX = clientX - lastXRef.current
      const frameChange = Math.round(deltaX / 20)
      if (Math.abs(frameChange) > 0) {
        setCurrentFrame(prev => {
          let next = prev + frameChange
          if (next >= totalFrames) next = next % totalFrames
          if (next < 0) next = totalFrames + (next % totalFrames)
          return next
        })
        lastXRef.current = clientX
      }
      pinchStartRef.current = 0
    }
  }, [isDragging, totalFrames])

  const handleEnd = useCallback(() => {
    setIsDragging(false)
    pinchStartRef.current = 0
  }, [])

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    const onMouseDown = (e) => {
      e.preventDefault()
      handleStart(e.clientX, e.clientY)
    }
    const onMouseMove = (e) => {
      e.preventDefault()
      handleMove(e.clientX, e.clientY)
    }
    const onMouseUp = () => handleEnd()
    const onMouseLeave = () => handleEnd()
    const onWheel = (e) => {
      e.preventDefault()
      const delta = e.deltaY > 0 ? -0.1 : 0.1
      setScale(prev => Math.max(0.5, Math.min(2, prev + delta)))
    }

    container.addEventListener('mousedown', onMouseDown)
    window.addEventListener('mousemove', onMouseMove)
    window.addEventListener('mouseup', onMouseUp)
    window.addEventListener('mouseleave', onMouseLeave)
    container.addEventListener('wheel', onWheel, { passive: false })

    return () => {
      container.removeEventListener('mousedown', onMouseDown)
      window.removeEventListener('mousemove', onMouseMove)
      window.removeEventListener('mouseup', onMouseUp)
      window.removeEventListener('mouseleave', onMouseLeave)
      container.removeEventListener('wheel', onWheel)
    }
  }, [handleStart, handleMove, handleEnd])

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    const onTouchStart = (e) => {
      e.preventDefault()
      const touch = e.touches[0]
      if (e.touches.length === 2) {
        const touch2 = e.touches[1]
        handleStart(touch.clientX, touch.clientY, touch2.clientX, touch2.clientY)
      } else {
        handleStart(touch.clientX, touch.clientY)
      }
    }
    const onTouchMove = (e) => {
      e.preventDefault()
      const touch = e.touches[0]
      if (e.touches.length === 2) {
        const touch2 = e.touches[1]
        handleMove(touch.clientX, touch.clientY, touch2.clientX, touch2.clientY)
      } else {
        handleMove(touch.clientX, touch.clientY)
      }
    }
    const onTouchEnd = () => handleEnd()

    container.addEventListener('touchstart', onTouchStart, { passive: false })
    container.addEventListener('touchmove', onTouchMove, { passive: false })
    container.addEventListener('touchend', onTouchEnd)

    return () => {
      container.removeEventListener('touchstart', onTouchStart)
      container.removeEventListener('touchmove', onTouchMove)
      container.removeEventListener('touchend', onTouchEnd)
    }
  }, [handleStart, handleMove, handleEnd])

  useEffect(() => {
    if (isAutoPlay) {
      autoPlayRef.current = setInterval(() => {
        setCurrentFrame(prev => (prev + 1) % totalFrames)
      }, 100)
    } else {
      if (autoPlayRef.current) {
        clearInterval(autoPlayRef.current)
      }
    }
    return () => {
      if (autoPlayRef.current) {
        clearInterval(autoPlayRef.current)
      }
    }
  }, [isAutoPlay, totalFrames])

  const resetView = () => {
    setCurrentFrame(0)
    setScale(1)
    setIsAutoPlay(false)
  }

  return (
    <div className="model-3d-viewer">
      <div className="section-header">
        <h3 className="section-title">3D 商品展示</h3>
        <div className="viewer-controls">
          <button
            className={`ctrl-btn ${isAutoPlay ? 'active' : ''}`}
            onClick={() => setIsAutoPlay(!isAutoPlay)}
            title="自动旋转"
          >
            {isAutoPlay ? '⏸️' : '▶️'}
          </button>
          <button className="ctrl-btn" onClick={resetView} title="重置视角">
            🔄
          </button>
        </div>
      </div>

      <div
        ref={containerRef}
        className={`viewer-container ${isDragging ? 'dragging' : ''}`}
      >
        <div
          className="model-wrapper"
          style={{
            transform: `scale(${scale})`,
            transition: isDragging ? 'none' : 'transform 0.3s ease'
          }}
        >
          <img
            src={images[currentFrame % totalFrames]}
            alt="3D 商品视图"
            draggable={false}
          />
        </div>

        <div className="viewer-hint">
          <span>👆 拖动旋转 | 双指/滚轮缩放</span>
        </div>

        <div className="frame-indicator">
          {images.map((_, idx) => (
            <div
              key={idx}
              className={`frame-dot ${idx === currentFrame % totalFrames ? 'active' : ''}`}
              onClick={() => setCurrentFrame(idx)}
            />
          ))}
        </div>
      </div>

      <div className="zoom-controls">
        <button className="zoom-btn" onClick={() => setScale(s => Math.max(0.5, s - 0.2))}>
          −
        </button>
        <div className="zoom-level">{Math.round(scale * 100)}%</div>
        <button className="zoom-btn" onClick={() => setScale(s => Math.min(2, s + 0.2))}>
          +
        </button>
      </div>

      <style jsx>{`
        .model-3d-viewer {
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
        .viewer-controls {
          display: flex;
          gap: 8px;
        }
        .ctrl-btn {
          width: 36px;
          height: 36px;
          border-radius: 50%;
          border: 1px solid #e0e0e0;
          background: #fff;
          font-size: 16px;
          cursor: pointer;
          transition: all 0.2s;
        }
        .ctrl-btn:hover {
          background: #f5f5f5;
          border-color: #ff4d4f;
        }
        .ctrl-btn.active {
          background: #fff2f0;
          border-color: #ff4d4f;
        }
        .viewer-container {
          position: relative;
          width: 100%;
          aspect-ratio: 1;
          background: linear-gradient(135deg, #fafafa 0%, #f0f0f0 100%);
          border-radius: 12px;
          overflow: hidden;
          cursor: grab;
          user-select: none;
          touch-action: none;
        }
        .viewer-container.dragging {
          cursor: grabbing;
        }
        .model-wrapper {
          width: 100%;
          height: 100%;
          display: flex;
          align-items: center;
          justify-content: center;
          pointer-events: none;
        }
        .model-wrapper img {
          max-width: 80%;
          max-height: 80%;
          object-fit: contain;
          filter: drop-shadow(0 10px 30px rgba(0, 0, 0, 0.15));
        }
        .viewer-hint {
          position: absolute;
          bottom: 40px;
          left: 50%;
          transform: translateX(-50%);
          background: rgba(0, 0, 0, 0.6);
          color: #fff;
          padding: 6px 12px;
          border-radius: 12px;
          font-size: 12px;
          white-space: nowrap;
          pointer-events: none;
        }
        .frame-indicator {
          position: absolute;
          bottom: 12px;
          left: 50%;
          transform: translateX(-50%);
          display: flex;
          gap: 6px;
        }
        .frame-dot {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          background: rgba(0, 0, 0, 0.2);
          cursor: pointer;
          transition: all 0.2s;
        }
        .frame-dot:hover {
          background: rgba(0, 0, 0, 0.4);
        }
        .frame-dot.active {
          background: #ff4d4f;
          width: 20px;
          border-radius: 4px;
        }
        .zoom-controls {
          display: flex;
          justify-content: center;
          align-items: center;
          gap: 16px;
          margin-top: 16px;
        }
        .zoom-btn {
          width: 36px;
          height: 36px;
          border-radius: 50%;
          border: 1px solid #e0e0e0;
          background: #fff;
          font-size: 18px;
          font-weight: bold;
          color: #666;
          cursor: pointer;
          transition: all 0.2s;
        }
        .zoom-btn:hover {
          background: #f5f5f5;
          border-color: #ff4d4f;
          color: #ff4d4f;
        }
        .zoom-level {
          font-size: 14px;
          color: #666;
          min-width: 50px;
          text-align: center;
        }
        @media (max-width: 768px) {
          .model-3d-viewer {
            padding: 12px;
            border-radius: 0;
            margin-top: 0;
          }
          .viewer-hint {
            font-size: 11px;
          }
        }
      `}</style>
    </div>
  )
})

export default Model3DViewer
