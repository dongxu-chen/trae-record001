import { useEffect, useRef, useState } from 'react'
import lottie from 'lottie-web'
import { useEditorStore } from '@/lib/store'
import { exportToLottie } from '@/lib/lottieExporter'

export function PreviewModal({ onClose }: { onClose: () => void }) {
  const { project } = useEditorStore()
  const containerRef = useRef<HTMLDivElement>(null)
  const animationRef = useRef<any>(null)
  const [isPlaying, setIsPlaying] = useState(true)

  useEffect(() => {
    if (!project || !containerRef.current) return

    const lottieData = exportToLottie(project)

    animationRef.current = lottie.loadAnimation({
      container: containerRef.current,
      renderer: 'svg',
      loop: true,
      autoplay: true,
      animationData: lottieData,
    })

    return () => {
      if (animationRef.current) {
        animationRef.current.destroy()
      }
    }
  }, [project])

  const handlePlayPause = () => {
    if (!animationRef.current) return
    if (isPlaying) {
      animationRef.current.pause()
    } else {
      animationRef.current.play()
    }
    setIsPlaying(!isPlaying)
  }

  if (!project) return null

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0,0,0,0.85)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
      }}
      onClick={onClose}
    >
      <div
        style={{
          background: '#16213e',
          padding: '24px',
          borderRadius: '12px',
          maxWidth: '90vw',
          maxHeight: '90vh',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <h2 style={{ color: '#e94560' }}>动画预览</h2>
          <button className="btn btn-secondary" onClick={onClose}>
            关闭
          </button>
        </div>

        <div
          style={{
            background: 'white',
            borderRadius: '8px',
            padding: '20px',
            marginBottom: '20px',
          }}
        >
          <div
            ref={containerRef}
            style={{
              width: Math.min(project.width, 500),
              height: Math.min(project.height, 500),
            }}
          />
        </div>

        <div style={{ display: 'flex', gap: '10px', justifyContent: 'center' }}>
          <button className="btn btn-secondary" onClick={handlePlayPause}>
            {isPlaying ? '⏸ 暂停' : '▶ 播放'}
          </button>
        </div>
      </div>
    </div>
  )
}
