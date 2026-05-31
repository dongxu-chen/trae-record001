export class Particle {
  constructor(x, y, options = {}) {
    this.x = x
    this.y = y
    this.originX = x
    this.originY = y
    this.targetX = x
    this.targetY = y
    this.size = options.size || 2
    this.color = options.color || '#ffffff'
    this.speed = options.speed || 1
    this.alpha = 1
    this.vx = 0
    this.vy = 0
    this.trail = []
    this.maxTrailLength = options.trailLength || 10
    this.mass = 1 + Math.random() * 0.5
    this.friction = 0.96
    this.gravity = 0
    this.disperseAngle = options.disperseAngle || Math.random() * Math.PI * 2
    this.disperseForce = options.disperseForce || (1 + Math.random() * 2)
    this.isMorphing = false
    this.morphProgress = 0
  }

  update(animationType, speed, mouseState, physics) {
    if (physics.enabled) {
      this.applyPhysics(mouseState, physics)
    }

    switch (animationType) {
      case 'disperse':
        this.updateDisperse(speed)
        break
      case 'gather':
        this.updateGather(speed)
        break
      case 'trail':
        this.updateTrail(speed, mouseState?.pos)
        break
      case 'morph':
        this.updateMorph(speed)
        break
      default:
        this.updateGather(speed)
    }

    if (physics.bounce) {
      this.applyBoundaryBounce()
    }

    this.vx *= this.friction
    this.vy *= this.friction
    this.x += this.vx
    this.y += this.vy

    if (this.maxTrailLength > 0) {
      this.trail.push({ x: this.x, y: this.y })
      if (this.trail.length > this.maxTrailLength) {
        this.trail.shift()
      }
    }
  }

  applyPhysics(mouseState, physics) {
    this.vy += physics.gravity * this.mass

    if (mouseState?.pos) {
      const dx = this.x - mouseState.pos.x
      const dy = this.y - mouseState.pos.y
      const dist = Math.sqrt(dx * dx + dy * dy)

      if (dist < physics.mouseRadius && dist > 1) {
        const force = (physics.mouseRadius - dist) / physics.mouseRadius
        const strength = mouseState.isDragging
          ? physics.mouseForce * 2.5
          : physics.mouseForce
        this.vx += (dx / dist) * force * strength
        this.vy += (dy / dist) * force * strength
      }
    }
  }

  applyBoundaryBounce() {
    const canvasWidth = this.canvasWidth || window.innerWidth
    const canvasHeight = this.canvasHeight || window.innerHeight
    const bounce = 0.7

    if (this.x - this.size < 0) {
      this.x = this.size
      this.vx *= -bounce
    } else if (this.x + this.size > canvasWidth) {
      this.x = canvasWidth - this.size
      this.vx *= -bounce
    }

    if (this.y - this.size < 0) {
      this.y = this.size
      this.vy *= -bounce
    } else if (this.y + this.size > canvasHeight) {
      this.y = canvasHeight - this.size
      this.vy *= -bounce
    }
  }

  updateDisperse(speed) {
    const force = this.disperseForce * speed * 0.15
    this.vx += Math.cos(this.disperseAngle) * force
    this.vy += Math.sin(this.disperseAngle) * force
    this.alpha = Math.max(0, this.alpha - 0.003 * speed)
  }

  updateGather(speed) {
    const dx = this.originX - this.x
    const dy = this.originY - this.y
    const distance = Math.sqrt(dx * dx + dy * dy)

    if (distance > 1) {
      const force = distance * 0.06 * speed
      this.vx += (dx / distance) * force
      this.vy += (dy / distance) * force
    }

    this.alpha = Math.min(1, this.alpha + 0.02 * speed)
  }

  updateTrail(speed, mousePos) {
    if (mousePos) {
      const dx = mousePos.x - this.x
      const dy = mousePos.y - this.y
      const distance = Math.sqrt(dx * dx + dy * dy)

      if (distance < 150) {
        const force = (150 - distance) / 150 * speed * 2
        this.vx += (dx / distance) * force * 0.15
        this.vy += (dy / distance) * force * 0.15
      }
    }

    const dx = this.originX - this.x
    const dy = this.originY - this.y
    this.vx += dx * 0.025 * speed
    this.vy += dy * 0.025 * speed

    this.vx *= 0.92
    this.vy *= 0.92
  }

  updateMorph(speed) {
    const dx = this.targetX - this.x
    const dy = this.targetY - this.y
    const distance = Math.sqrt(dx * dx + dy * dy)

    if (distance > 0.5) {
      const force = Math.min(distance * 0.08, 3) * speed
      this.vx += (dx / distance) * force
      this.vy += (dy / distance) * force
    }

    this.alpha = Math.min(1, this.alpha + 0.03 * speed)
  }

  setTarget(x, y) {
    this.targetX = x
    this.targetY = y
    this.isMorphing = true
  }

  setOrigin(x, y) {
    this.originX = x
    this.originY = y
  }

  draw(ctx, showTrail = false) {
    ctx.save()
    ctx.globalAlpha = this.alpha

    if (showTrail && this.trail.length > 1) {
      for (let i = 1; i < this.trail.length; i++) {
        const t = this.trail[i]
        const prevT = this.trail[i - 1]
        ctx.globalAlpha = (i / this.trail.length) * this.alpha * 0.4
        ctx.strokeStyle = this.color
        ctx.lineWidth = this.size * (i / this.trail.length) * 0.8
        ctx.lineCap = 'round'
        ctx.beginPath()
        ctx.moveTo(prevT.x, prevT.y)
        ctx.lineTo(t.x, t.y)
        ctx.stroke()
      }
    }

    ctx.globalAlpha = this.alpha
    ctx.fillStyle = this.color
    ctx.beginPath()
    ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2)
    ctx.fill()

    ctx.restore()
  }

  reset() {
    this.x = this.originX
    this.y = this.originY
    this.vx = 0
    this.vy = 0
    this.alpha = 1
    this.trail = []
    this.disperseForce = (1 + Math.random() * 2)
    this.isMorphing = false
  }
}
