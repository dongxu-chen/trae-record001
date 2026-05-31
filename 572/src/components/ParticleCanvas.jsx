import { useEffect, useRef } from 'react'
import { ParticleSystem } from '../core/ParticleSystem'

export default function ParticleCanvas({ config, onParticleCount }) {
  const canvasRef = useRef(null)
  const particleSystemRef = useRef(null)
  const prevConfigRef = useRef(null)
  const isDraggingRef = useRef(false)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    canvas.width = canvas.offsetWidth
    canvas.height = canvas.offsetHeight

    particleSystemRef.current = new ParticleSystem(canvas, config)
    particleSystemRef.current.createParticlesFromText()
    particleSystemRef.current.start()

    prevConfigRef.current = { ...config }

    const handleResize = () => {
      if (particleSystemRef.current) {
        particleSystemRef.current.resize(canvas.offsetWidth, canvas.offsetHeight)
      }
    }

    const handleMouseDown = (e) => {
      isDraggingRef.current = true
      updateMousePos(e)
    }

    const handleMouseMove = (e) => {
      updateMousePos(e)
    }

    const handleMouseUp = (e) => {
      isDraggingRef.current = false
      if (particleSystemRef.current) {
        const rect = canvas.getBoundingClientRect()
        particleSystemRef.current.setMousePos({
          x: e.clientX - rect.left,
          y: e.clientY - rect.top
        }, false)
      }
    }

    const handleMouseLeave = () => {
      isDraggingRef.current = false
      if (particleSystemRef.current) {
        particleSystemRef.current.setMousePos(null, false)
      }
    }

    const updateMousePos = (e) => {
      if (particleSystemRef.current) {
        const rect = canvas.getBoundingClientRect()
        particleSystemRef.current.setMousePos({
          x: e.clientX - rect.left,
          y: e.clientY - rect.top
        }, isDraggingRef.current)
      }
    }

    window.addEventListener('resize', handleResize)
    canvas.addEventListener('mousedown', handleMouseDown)
    canvas.addEventListener('mousemove', handleMouseMove)
    canvas.addEventListener('mouseup', handleMouseUp)
    canvas.addEventListener('mouseleave', handleMouseLeave)

    return () => {
      if (particleSystemRef.current) {
        particleSystemRef.current.destroy()
        particleSystemRef.current = null
      }
      window.removeEventListener('resize', handleResize)
      canvas.removeEventListener('mousedown', handleMouseDown)
      canvas.removeEventListener('mousemove', handleMouseMove)
      canvas.removeEventListener('mouseup', handleMouseUp)
      canvas.removeEventListener('mouseleave', handleMouseLeave)
    }
  }, [])

  useEffect(() => {
    const ps = particleSystemRef.current
    if (!ps) return

    const prev = prevConfigRef.current
    if (!prev) return

    if (config.text !== prev.text) {
      ps.setText(config.text)
    }

    if (config.particleSpacing !== prev.particleSpacing) {
      ps.setParticleSpacing(config.particleSpacing)
    }

    ps.setAnimationType(config.animationType)
    ps.setSpeed(config.speed)
    ps.setParticleSize(config.particleSize)
    ps.setParticleColor(config.particleColor)
    ps.setTrailLength(config.trailLength)
    ps.setShowTrail(config.showTrail)
    ps.setBackgroundColor(config.backgroundColor)
    ps.setBackgroundEffect(config.backgroundEffect)

    ps.setPhysicsEnabled(config.physicsEnabled)
    ps.setGravity(config.gravity)
    ps.setBounce(config.bounce)
    ps.setCollision(config.collision)
    ps.setMouseRadius(config.mouseRadius)
    ps.setMouseForce(config.mouseForce)

    prevConfigRef.current = { ...config }

    if (onParticleCount) {
      onParticleCount(ps.getParticleCount())
    }
  }, [config, onParticleCount])

  const handleReset = () => {
    if (particleSystemRef.current) {
      particleSystemRef.current.reset()
    }
  }

  return (
    <canvas
      ref={canvasRef}
      style={{
        width: '100%',
        height: '100%',
        display: 'block',
        cursor: 'grab'
      }}
      onMouseDown={(e) => e.target.style.cursor = 'grabbing'}
      onMouseUp={(e) => e.target.style.cursor = 'grab'}
      onMouseLeave={(e) => e.target.style.cursor = 'grab'}
      onClick={handleReset}
    />
  )
}
