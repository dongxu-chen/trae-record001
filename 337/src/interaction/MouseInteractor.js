import * as THREE from 'three'

export class MouseInteractor {
  constructor(canvas, particleEngine, camera) {
    this.canvas = canvas
    this.particleEngine = particleEngine
    this.camera = camera
    this.enabled = true
    this.mode = 'repel'
    
    this.strength = 50
    this.radius = 5
    this.falloff = 2
    
    this.isMouseDown = false
    this.isDragging = false
    this.mousePosition = new THREE.Vector3()
    this.lastMousePosition = new THREE.Vector3()
    this.mouseVelocity = new THREE.Vector3()
    
    this.raycaster = new THREE.Raycaster()
    this.ndc = new THREE.Vector2()
    this.plane = new THREE.Plane(new THREE.Vector3(0, 0, 1), 0)
    
    this.interactionPoints = []
    this.maxInteractionPoints = 10
    
    this.bindEvents()
  }
  
  bindEvents() {
    this.canvas.addEventListener('mousedown', this.onMouseDown.bind(this))
    this.canvas.addEventListener('mousemove', this.onMouseMove.bind(this))
    this.canvas.addEventListener('mouseup', this.onMouseUp.bind(this))
    this.canvas.addEventListener('mouseleave', this.onMouseUp.bind(this))
    this.canvas.addEventListener('wheel', this.onWheel.bind(this))
    
    this.canvas.addEventListener('touchstart', this.onTouchStart.bind(this), { passive: false })
    this.canvas.addEventListener('touchmove', this.onTouchMove.bind(this), { passive: false })
    this.canvas.addEventListener('touchend', this.onTouchEnd.bind(this))
  }
  
  getMouseWorldPosition(clientX, clientY) {
    const rect = this.canvas.getBoundingClientRect()
    this.ndc.x = ((clientX - rect.left) / rect.width) * 2 - 1
    this.ndc.y = -((clientY - rect.top) / rect.height) * 2 + 1
    
    this.raycaster.setFromCamera(this.ndc, this.camera)
    
    const target = new THREE.Vector3()
    this.raycaster.ray.intersectPlane(this.plane, target)
    
    return target || new THREE.Vector3()
  }
  
  onMouseDown(event) {
    if (!this.enabled) return
    
    this.isMouseDown = true
    this.isDragging = true
    this.mousePosition.copy(this.getMouseWorldPosition(event.clientX, event.clientY))
    this.lastMousePosition.copy(this.mousePosition)
    
    this.addInteractionPoint(this.mousePosition.clone(), true)
  }
  
  onMouseMove(event) {
    if (!this.enabled) return
    
    const worldPos = this.getMouseWorldPosition(event.clientX, event.clientY)
    
    if (this.isDragging) {
      this.mouseVelocity.copy(worldPos).sub(this.lastMousePosition)
      this.mousePosition.copy(worldPos)
      this.lastMousePosition.copy(worldPos)
      
      this.addInteractionPoint(this.mousePosition.clone(), false)
    } else {
      this.mousePosition.copy(worldPos)
    }
  }
  
  onMouseUp() {
    this.isMouseDown = false
    this.isDragging = false
    this.mouseVelocity.set(0, 0, 0)
  }
  
  onWheel(event) {
    // 滚轮缩放由OrbitControls处理
  }
  
  onTouchStart(event) {
    event.preventDefault()
    if (!this.enabled || event.touches.length === 0) return
    
    const touch = event.touches[0]
    this.onMouseDown({ clientX: touch.clientX, clientY: touch.clientY })
  }
  
  onTouchMove(event) {
    event.preventDefault()
    if (!this.enabled || event.touches.length === 0) return
    
    const touch = event.touches[0]
    this.onMouseMove({ clientX: touch.clientX, clientY: touch.clientY })
  }
  
  onTouchEnd() {
    this.onMouseUp()
  }
  
  addInteractionPoint(position, isClick) {
    const point = {
      position: position.clone(),
      strength: isClick ? this.strength * 2 : this.strength,
      radius: this.radius,
      falloff: this.falloff,
      lifetime: isClick ? 0.5 : 0.1,
      age: 0,
      mode: this.mode,
      isClick: isClick
    }
    
    this.interactionPoints.push(point)
    
    if (this.interactionPoints.length > this.maxInteractionPoints) {
      this.interactionPoints.shift()
    }
  }
  
  update(deltaTime) {
    if (!this.enabled || this.interactionPoints.length === 0 || !this.particleEngine) {
      return
    }
    
    for (let i = this.interactionPoints.length - 1; i >= 0; i--) {
      const point = this.interactionPoints[i]
      point.age += deltaTime
      
      if (point.age >= point.lifetime) {
        this.interactionPoints.splice(i, 1)
        continue
      }
      
      const lifeRatio = 1 - point.age / point.lifetime
      const currentStrength = point.strength * lifeRatio
      
      this.applyForceToParticles(point.position, currentStrength, point.radius, point.falloff, point.mode)
    }
  }
  
  applyForceToParticles(center, strength, radius, falloff, mode) {
    if (!this.particleEngine.activeIndices) return
    
    const positions = this.particleEngine.instancePosition
    const velocities = this.particleEngine.instanceVelocity
    
    const radiusSq = radius * radius
    
    for (const index of this.particleEngine.activeIndices) {
      const i3 = index * 3
      
      const dx = positions[i3] - center.x
      const dy = positions[i3 + 1] - center.y
      const dz = positions[i3 + 2] - center.z
      
      const distSq = dx * dx + dy * dy + dz * dz
      
      if (distSq > radiusSq) continue
      
      const dist = Math.sqrt(distSq) || 0.001
      const force = strength * Math.pow(1 - dist / radius, falloff)
      
      let fx, fy, fz
      
      switch (mode) {
        case 'attract':
          fx = -dx / dist * force
          fy = -dy / dist * force
          fz = -dz / dist * force
          break
          
        case 'repel':
          fx = dx / dist * force
          fy = dy / dist * force
          fz = dz / dist * force
          break
          
        case 'vortex':
          fx = -dy / dist * force
          fy = dx / dist * force
          fz = 0
          break
          
        case 'upward':
          fx = 0
          fy = force
          fz = 0
          break
          
        case 'downward':
          fx = 0
          fy = -force
          fz = 0
          break
          
        default:
          fx = dx / dist * force
          fy = dy / dist * force
          fz = dz / dist * force
      }
      
      velocities[i3] += fx
      velocities[i3 + 1] += fy
      velocities[i3 + 2] += fz
    }
    
    this.particleEngine.geometry.attributes.instanceVelocity.needsUpdate = true
  }
  
  setMode(mode) {
    this.mode = mode
  }
  
  setStrength(strength) {
    this.strength = strength
  }
  
  setRadius(radius) {
    this.radius = radius
  }
  
  setEnabled(enabled) {
    this.enabled = enabled
  }
  
  dispose() {
    this.canvas.removeEventListener('mousedown', this.onMouseDown)
    this.canvas.removeEventListener('mousemove', this.onMouseMove)
    this.canvas.removeEventListener('mouseup', this.onMouseUp)
    this.canvas.removeEventListener('mouseleave', this.onMouseUp)
    this.canvas.removeEventListener('wheel', this.onWheel)
    this.canvas.removeEventListener('touchstart', this.onTouchStart)
    this.canvas.removeEventListener('touchmove', this.onTouchMove)
    this.canvas.removeEventListener('touchend', this.onTouchEnd)
    
    this.interactionPoints = []
  }
}

export const InteractionModes = {
  ATTRACT: 'attract',
  REPEL: 'repel',
  VORTEX: 'vortex',
  UPWARD: 'upward',
  DOWNWARD: 'downward'
}
