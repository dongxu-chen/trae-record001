import { Particle } from './Particle'

export class ParticleSystem {
  constructor(canvas, options = {}) {
    this.canvas = canvas
    this.ctx = canvas.getContext('2d')
    this.particles = []
    this.text = options.text || 'Hello'
    this.fontSize = options.fontSize || 120
    this.fontFamily = options.fontFamily || 'Arial Black'
    this.animationType = options.animationType || 'gather'
    this.speed = options.speed || 1
    this.particleSize = options.particleSize || 2
    this.particleColor = options.particleColor || '#00d4ff'
    this.trailLength = options.trailLength || 10
    this.showTrail = options.showTrail || false
    this.mouseState = { pos: null, isDragging: false }
    this.isRunning = false
    this.animationId = null
    this.backgroundColor = options.backgroundColor || '#0a0a1a'
    this.backgroundEffect = options.backgroundEffect || 'none'
    this.particleSpacing = options.particleSpacing || 4
    this.physics = {
      enabled: options.physicsEnabled || false,
      gravity: options.gravity || 0.15,
      bounce: options.bounce || false,
      collision: options.collision || false,
      mouseRadius: options.mouseRadius || 120,
      mouseForce: options.mouseForce || 0.8
    }
  }

  getTextPoints(text) {
    const { width, height } = this.canvas
    const tempCanvas = document.createElement('canvas')
    tempCanvas.width = width
    tempCanvas.height = height
    const tempCtx = tempCanvas.getContext('2d')

    tempCtx.fillStyle = '#ffffff'
    tempCtx.font = `bold ${this.fontSize}px ${this.fontFamily}`
    tempCtx.textAlign = 'center'
    tempCtx.textBaseline = 'middle'
    tempCtx.fillText(text, width / 2, height / 2)

    const imageData = tempCtx.getImageData(0, 0, width, height)
    const data = imageData.data
    const points = []
    const centerX = width / 2
    const centerY = height / 2

    for (let y = 0; y < height; y += this.particleSpacing) {
      for (let x = 0; x < width; x += this.particleSpacing) {
        const index = (y * width + x) * 4
        const alpha = data[index + 3]

        if (alpha > 128) {
          const dx = x - centerX
          const dy = y - centerY
          const disperseAngle = Math.atan2(dy, dx) + (Math.random() - 0.5) * 0.6
          points.push({ x, y, disperseAngle })
        }
      }
    }

    return points
  }

  createParticlesFromText() {
    const points = this.getTextPoints(this.text)
    this.particles = points.map(p =>
      new Particle(p.x, p.y, {
        size: this.particleSize,
        color: this.particleColor,
        speed: this.speed,
        trailLength: this.trailLength,
        disperseAngle: p.disperseAngle
      })
    )
  }

  morphToText(newText) {
    const newPoints = this.getTextPoints(newText)
    this.text = newText

    if (newPoints.length === 0) return

    const oldCount = this.particles.length
    const newCount = newPoints.length

    if (oldCount === 0) {
      this.createParticlesFromText()
      return
    }

    if (newCount > oldCount) {
      const diff = newCount - oldCount
      for (let i = 0; i < diff; i++) {
        const idx = Math.floor(Math.random() * oldCount)
        const sourceP = this.particles[idx]
        const newP = new Particle(sourceP.x, sourceP.y, {
          size: this.particleSize,
          color: this.particleColor,
          speed: this.speed,
          trailLength: this.trailLength,
          disperseAngle: Math.random() * Math.PI * 2
        })
        newP.alpha = 0
        this.particles.push(newP)
      }
    } else if (newCount < oldCount) {
      const toRemove = oldCount - newCount
      for (let i = 0; i < toRemove; i++) {
        if (this.particles.length > newCount) {
          this.particles.pop()
        }
      }
    }

    for (let i = 0; i < this.particles.length; i++) {
      const targetIdx = i % newPoints.length
      const target = newPoints[targetIdx]
      this.particles[i].setTarget(target.x, target.y)
      this.particles[i].disperseAngle = target.disperseAngle
    }

    this.prevAnimationType = this.animationType
    this.animationType = 'morph'

    setTimeout(() => {
      if (this.animationType === 'morph') {
        this.particles.forEach(p => {
          p.setOrigin(p.targetX, p.targetY)
          p.isMorphing = false
        })
        this.animationType = this.prevAnimationType || 'gather'
      }
    }, 2000)
  }

  update() {
    const { width, height } = this.canvas

    this.particles.forEach(p => {
      p.canvasWidth = width
      p.canvasHeight = height
    })

    if (this.physics.collision && this.particles.length < 500) {
      this.handleParticleCollisions()
    }

    this.particles.forEach(particle => {
      particle.update(this.animationType, this.speed, this.mouseState, this.physics)
    })
  }

  handleParticleCollisions() {
    const particles = this.particles
    const count = particles.length
    const restitution = 0.6

    for (let i = 0; i < count; i++) {
      for (let j = i + 1; j < count; j++) {
        const p1 = particles[i]
        const p2 = particles[j]
        const dx = p2.x - p1.x
        const dy = p2.y - p1.y
        const dist = Math.sqrt(dx * dx + dy * dy)
        const minDist = p1.size + p2.size

        if (dist < minDist && dist > 0) {
          const nx = dx / dist
          const ny = dy / dist
          const overlap = (minDist - dist) / 2

          p1.x -= nx * overlap
          p1.y -= ny * overlap
          p2.x += nx * overlap
          p2.y += ny * overlap

          const dvx = p1.vx - p2.vx
          const dvy = p1.vy - p2.vy
          const dvDotN = dvx * nx + dvy * ny

          if (dvDotN > 0) {
            const impulse = dvDotN * restitution
            p1.vx -= impulse * nx
            p1.vy -= impulse * ny
            p2.vx += impulse * nx
            p2.vy += impulse * ny
          }
        }
      }
    }
  }

  drawBackground() {
    const { width, height } = this.canvas

    const bgRgba = this.hexToRgba(this.backgroundColor, 0.12)
    this.ctx.fillStyle = bgRgba
    this.ctx.fillRect(0, 0, width, height)

    if (this.backgroundEffect === 'gradient') {
      const gradient = this.ctx.createRadialGradient(
        width / 2, height / 2, 0,
        width / 2, height / 2, Math.max(width, height) / 2
      )
      gradient.addColorStop(0, 'rgba(0, 50, 100, 0.08)')
      gradient.addColorStop(1, 'transparent')
      this.ctx.fillStyle = gradient
      this.ctx.fillRect(0, 0, width, height)
    } else if (this.backgroundEffect === 'stars') {
      this.drawStars()
    } else if (this.backgroundEffect === 'grid') {
      this.drawGrid()
    }
  }

  hexToRgba(hex, alpha) {
    const shorthand = /^#?([a-f\d])([a-f\d])([a-f\d])$/i
    hex = hex.replace(shorthand, (m, r, g, b) => r + r + g + g + b + b)
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex)
    if (!result) return `rgba(10, 10, 26, ${alpha})`
    return `rgba(${parseInt(result[1], 16)}, ${parseInt(result[2], 16)}, ${parseInt(result[3], 16)}, ${alpha})`
  }

  drawStars() {
    const { width, height } = this.canvas
    const starCount = 100
    this.ctx.fillStyle = 'rgba(255, 255, 255, 0.5)'
    for (let i = 0; i < starCount; i++) {
      const x = Math.random() * width
      const y = Math.random() * height
      const size = Math.random() * 2
      this.ctx.beginPath()
      this.ctx.arc(x, y, size, 0, Math.PI * 2)
      this.ctx.fill()
    }
  }

  drawGrid() {
    const { width, height } = this.canvas
    this.ctx.strokeStyle = 'rgba(255, 255, 255, 0.1)'
    this.ctx.lineWidth = 1
    const gridSize = 50

    for (let x = 0; x < width; x += gridSize) {
      this.ctx.beginPath()
      this.ctx.moveTo(x, 0)
      this.ctx.lineTo(x, height)
      this.ctx.stroke()
    }

    for (let y = 0; y < height; y += gridSize) {
      this.ctx.beginPath()
      this.ctx.moveTo(0, y)
      this.ctx.lineTo(width, y)
      this.ctx.stroke()
    }
  }

  draw() {
    this.particles.forEach(particle => {
      particle.draw(this.ctx, this.showTrail)
    })
  }

  animate() {
    if (this.isRunning) {
      this.drawBackground()
      this.update()
      this.draw()
      this.animationId = requestAnimationFrame(() => this.animate())
    }
  }

  start() {
    this.isRunning = true
    const { width, height } = this.canvas
    this.ctx.fillStyle = this.backgroundColor
    this.ctx.fillRect(0, 0, width, height)
    this.animate()
  }

  stop() {
    this.isRunning = false
    if (this.animationId) {
      cancelAnimationFrame(this.animationId)
      this.animationId = null
    }
  }

  destroy() {
    this.stop()
    this.particles = []
    this.mouseState = { pos: null, isDragging: false }
    this.ctx = null
    this.canvas = null
  }

  reset() {
    this.particles.forEach(particle => {
      particle.reset()
    })
  }

  setText(text) {
    if (text !== this.text) {
      this.morphToText(text)
    }
  }

  setAnimationType(type) {
    this.animationType = type
  }

  setSpeed(speed) {
    this.speed = speed
  }

  setParticleSize(size) {
    this.particleSize = size
    this.particles.forEach(p => p.size = size)
  }

  setParticleColor(color) {
    this.particleColor = color
    this.particles.forEach(p => p.color = color)
  }

  setTrailLength(length) {
    this.trailLength = length
    this.particles.forEach(p => p.maxTrailLength = length)
  }

  setShowTrail(show) {
    this.showTrail = show
  }

  setBackgroundColor(color) {
    this.backgroundColor = color
  }

  setBackgroundEffect(effect) {
    this.backgroundEffect = effect
  }

  setParticleSpacing(spacing) {
    if (spacing !== this.particleSpacing) {
      this.particleSpacing = spacing
      this.createParticlesFromText()
    }
  }

  setMousePos(pos, isDragging = false) {
    this.mouseState.pos = pos
    this.mouseState.isDragging = isDragging
  }

  setPhysicsEnabled(enabled) {
    this.physics.enabled = enabled
  }

  setGravity(gravity) {
    this.physics.gravity = gravity
  }

  setBounce(bounce) {
    this.physics.bounce = bounce
  }

  setCollision(collision) {
    this.physics.collision = collision
  }

  setMouseRadius(radius) {
    this.physics.mouseRadius = radius
  }

  setMouseForce(force) {
    this.physics.mouseForce = force
  }

  resize(width, height) {
    this.canvas.width = width
    this.canvas.height = height
    this.createParticlesFromText()
  }

  getParticleCount() {
    return this.particles.length
  }
}
