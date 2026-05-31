import { useState, useEffect, useRef } from 'react'

export function usePerformance() {
  const [fps, setFps] = useState(60)
  const [frameTime, setFrameTime] = useState(0)
  const frameCountRef = useRef(0)
  const lastTimeRef = useRef(performance.now())

  useEffect(() => {
    let animationId: number

    const measure = () => {
      frameCountRef.current++
      const now = performance.now()
      const elapsed = now - lastTimeRef.current

      if (elapsed >= 1000) {
        setFps(Math.round((frameCountRef.current * 1000) / elapsed))
        setFrameTime(Math.round(elapsed / frameCountRef.current))
        frameCountRef.current = 0
        lastTimeRef.current = now
      }

      animationId = requestAnimationFrame(measure)
    }

    animationId = requestAnimationFrame(measure)

    return () => {
      cancelAnimationFrame(animationId)
    }
  }, [])

  return { fps, frameTime }
}
