import { useEffect, useRef } from 'react'

export default function Visualizer({ audioContext, analyser, isPlaying }) {
  const canvasRef = useRef(null)
  const animationRef = useRef(null)
  const offscreenCanvasRef = useRef(null)
  const previousDataRef = useRef(null)
  const barPositionsRef = useRef([])

  useEffect(() => {
    if (!analyser || !canvasRef.current) return

    const canvas = canvasRef.current
    const ctx = canvas.getContext('2d', { alpha: false })
    
    const offscreenCanvas = document.createElement('canvas')
    const offscreenCtx = offscreenCanvas.getContext('2d', { alpha: false })
    offscreenCanvasRef.current = offscreenCanvas

    analyser.fftSize = 512
    const bufferLength = analyser.frequencyBinCount
    const dataArray = new Uint8Array(bufferLength)
    previousDataRef.current = new Uint8Array(bufferLength)

    let gradient = null
    let reflectionGradient = null
    let barWidth = 0
    let displayWidth = 0
    let displayHeight = 0

    const setupDimensions = () => {
      const rect = canvas.getBoundingClientRect()
      const dpr = window.devicePixelRatio || 1
      
      canvas.width = rect.width * dpr
      canvas.height = rect.height * dpr
      offscreenCanvas.width = rect.width * dpr
      offscreenCanvas.height = rect.height * dpr
      
      ctx.scale(dpr, dpr)
      offscreenCtx.scale(dpr, dpr)
      
      displayWidth = rect.width
      displayHeight = rect.height
      
      barWidth = (displayWidth / bufferLength) * 2.5
      
      gradient = ctx.createLinearGradient(0, 0, 0, displayHeight)
      gradient.addColorStop(0, '#e94560')
      gradient.addColorStop(0.3, '#9b59b6')
      gradient.addColorStop(0.6, '#3498db')
      gradient.addColorStop(1, '#2ecc71')
      
      reflectionGradient = ctx.createLinearGradient(0, displayHeight * 0.5, 0, displayHeight)
      reflectionGradient.addColorStop(0, 'rgba(233, 69, 96, 0.4)')
      reflectionGradient.addColorStop(1, 'rgba(233, 69, 96, 0)')
      
      barPositionsRef.current = []
      for (let i = 0; i < bufferLength; i++) {
        barPositionsRef.current.push(i * barWidth)
      }
    }

    setupDimensions()
    window.addEventListener('resize', setupDimensions)

    const draw = () => {
      animationRef.current = requestAnimationFrame(draw)
      analyser.getByteFrequencyData(dataArray)

      offscreenCtx.fillStyle = '#0a0a1a'
      offscreenCtx.fillRect(0, 0, displayWidth, displayHeight)

      const halfHeight = displayHeight * 0.5
      let x = 0

      for (let i = 0; i < bufferLength; i++) {
        const barHeight = (dataArray[i] / 255) * halfHeight * 0.9
        const prevBarHeight = (previousDataRef.current[i] / 255) * halfHeight * 0.9
        
        if (Math.abs(barHeight - prevBarHeight) < 1) {
          x += barWidth
          continue
        }

        const y = halfHeight - barHeight
        
        offscreenCtx.fillStyle = gradient
        offscreenCtx.fillRect(x, y, barWidth - 1, barHeight)
        
        offscreenCtx.fillStyle = reflectionGradient
        offscreenCtx.fillRect(x, halfHeight, barWidth - 1, barHeight * 0.35)

        previousDataRef.current[i] = dataArray[i]
        x += barWidth
      }

      ctx.drawImage(offscreenCanvas, 0, 0, displayWidth, displayHeight, 0, 0, displayWidth, displayHeight)
    }

    draw()

    return () => {
      window.removeEventListener('resize', setupDimensions)
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current)
      }
    }
  }, [analyser])

  return (
    <canvas
      ref={canvasRef}
      className="visualizer"
      style={{ display: 'block' }}
    />
  )
}
