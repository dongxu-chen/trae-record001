import * as THREE from 'three'

const vertexShader = `
  precision highp float;

  attribute vec3 instancePosition;
  attribute vec3 instanceVelocity;
  attribute float instanceLife;
  attribute float instanceMaxLife;
  attribute float instanceSize;
  attribute vec3 instanceColor;
  attribute float instanceRotation;
  attribute float instanceRotationSpeed;
  attribute float instanceActive;

  uniform float uTime;
  uniform float uDeltaTime;
  uniform vec3 uGravity;
  uniform float uPixelRatio;

  varying float vLife;
  varying float vMaxLife;
  varying vec3 vColor;
  varying float vRotation;
  varying float vActive;

  void main() {
    vLife = instanceLife;
    vMaxLife = instanceMaxLife;
    vColor = instanceColor;
    vRotation = instanceRotation;
    vActive = instanceActive;

    if (instanceActive < 0.5) {
      gl_Position = vec4(2.0, 2.0, 2.0, 1.0);
      gl_PointSize = 0.0;
      return;
    }

    vec3 pos = instancePosition;
    vec3 vel = instanceVelocity;
    float life = instanceLife;
    float rotation = instanceRotation;

    if (life > 0.0) {
      vel += uGravity * uDeltaTime;
      pos += vel * uDeltaTime;
      life -= uDeltaTime;
      rotation += instanceRotationSpeed * uDeltaTime;
    }

    vec4 mvPosition = modelViewMatrix * vec4(pos, 1.0);
    float lifeRatio = life / instanceMaxLife;
    
    gl_PointSize = instanceSize * uPixelRatio * (1.0 - lifeRatio * 0.5) * (300.0 / -mvPosition.z);
    gl_Position = projectionMatrix * mvPosition;
  }
`

const fragmentShader = `
  precision highp float;

  varying float vLife;
  varying float vMaxLife;
  varying vec3 vColor;
  varying float vRotation;
  varying float vActive;

  void main() {
    if (vActive < 0.5 || vLife <= 0.0) {
      discard;
    }

    vec2 center = gl_PointCoord - vec2(0.5);
    
    float cosR = cos(vRotation);
    float sinR = sin(vRotation);
    vec2 rotated = vec2(
      center.x * cosR - center.y * sinR,
      center.x * sinR + center.y * cosR
    );
    
    float dist = length(rotated);
    float alpha = 1.0 - smoothstep(0.0, 0.5, dist);
    
    float lifeRatio = vLife / vMaxLife;
    alpha *= lifeRatio;
    
    if (alpha < 0.01) discard;
    
    gl_FragColor = vec4(vColor, alpha);
  }
`

export class ParticleEngine {
  constructor(scene, config = {}) {
    this.scene = scene
    this.config = {
      maxParticles: 1000000,
      particleCount: 50000,
      emissionRate: 5000,
      speed: { min: 1, max: 3 },
      life: { min: 1, max: 3 },
      size: { min: 0.1, max: 0.5 },
      color: { start: '#ff6600', end: '#ff0000' },
      direction: { x: 0, y: 1, z: 0 },
      spread: 0.5,
      gravity: { x: 0, y: -0.5, z: 0 },
      emitterPosition: { x: 0, y: 0, z: 0 },
      emitterShape: 'point',
      emitterRadius: 1,
      rotationSpeed: { min: 0, max: 2 },
      blending: 'additive',
      ...config
    }

    this.time = 0
    this.deltaTime = 0
    this.emissionAccumulator = 0
    this.paused = false
    this.particleCount = 0

    this.initGeometry()
    this.initMaterial()
    this.initPoints()
    this.initParticleData()
  }

  initGeometry() {
    const maxParticles = this.config.maxParticles

    this.geometry = new THREE.InstancedBufferGeometry()
    this.geometry.instanceCount = maxParticles

    const basePositions = new Float32Array([0, 0, 0])
    this.geometry.setAttribute('position', new THREE.BufferAttribute(basePositions, 3))

    this.instancePosition = new Float32Array(maxParticles * 3)
    this.instanceVelocity = new Float32Array(maxParticles * 3)
    this.instanceLife = new Float32Array(maxParticles)
    this.instanceMaxLife = new Float32Array(maxParticles)
    this.instanceSize = new Float32Array(maxParticles)
    this.instanceColor = new Float32Array(maxParticles * 3)
    this.instanceRotation = new Float32Array(maxParticles)
    this.instanceRotationSpeed = new Float32Array(maxParticles)
    this.instanceActive = new Float32Array(maxParticles)

    this.geometry.setAttribute('instancePosition', new THREE.InstancedBufferAttribute(this.instancePosition, 3))
    this.geometry.setAttribute('instanceVelocity', new THREE.InstancedBufferAttribute(this.instanceVelocity, 3))
    this.geometry.setAttribute('instanceLife', new THREE.InstancedBufferAttribute(this.instanceLife, 1))
    this.geometry.setAttribute('instanceMaxLife', new THREE.InstancedBufferAttribute(this.instanceMaxLife, 1))
    this.geometry.setAttribute('instanceSize', new THREE.InstancedBufferAttribute(this.instanceSize, 1))
    this.geometry.setAttribute('instanceColor', new THREE.InstancedBufferAttribute(this.instanceColor, 3))
    this.geometry.setAttribute('instanceRotation', new THREE.InstancedBufferAttribute(this.instanceRotation, 1))
    this.geometry.setAttribute('instanceRotationSpeed', new THREE.InstancedBufferAttribute(this.instanceRotationSpeed, 1))
    this.geometry.setAttribute('instanceActive', new THREE.InstancedBufferAttribute(this.instanceActive, 1))

    this.freeIndices = []
    for (let i = maxParticles - 1; i >= 0; i--) {
      this.freeIndices.push(i)
      this.instanceActive[i] = 0
    }
    this.activeIndices = []
  }

  initMaterial() {
    const blending = this.config.blending === 'additive' 
      ? THREE.AdditiveBlending 
      : THREE.NormalBlending

    this.material = new THREE.ShaderMaterial({
      uniforms: {
        uTime: { value: 0 },
        uDeltaTime: { value: 0 },
        uGravity: { value: new THREE.Vector3() },
        uPixelRatio: { value: Math.min(window.devicePixelRatio, 2) }
      },
      vertexShader,
      fragmentShader,
      transparent: true,
      blending,
      depthWrite: false
    })
  }

  initPoints() {
    this.points = new THREE.Points(this.geometry, this.material)
    this.points.frustumCulled = false
    this.scene.add(this.points)
  }

  initParticleData() {
    this.particles = new Array(this.config.maxParticles).fill(null).map((_, i) => ({
      active: false,
      index: i
    }))
  }

  emitParticle() {
    if (this.freeIndices.length === 0 || this.activeIndices.length >= this.config.particleCount) {
      return
    }

    const index = this.freeIndices.pop()
    this.activeIndices.push(index)

    const { emitterPosition, emitterShape, emitterRadius, direction, spread } = this.config

    let px = emitterPosition.x
    let py = emitterPosition.y
    let pz = emitterPosition.z

    if (emitterShape === 'sphere') {
      const theta = Math.random() * Math.PI * 2
      const phi = Math.acos(2 * Math.random() - 1)
      const r = Math.random() * emitterRadius
      px += r * Math.sin(phi) * Math.cos(theta)
      py += r * Math.sin(phi) * Math.sin(theta)
      pz += r * Math.cos(phi)
    } else if (emitterShape === 'circle') {
      const angle = Math.random() * Math.PI * 2
      const r = Math.random() * emitterRadius
      px += Math.cos(angle) * r
      pz += Math.sin(angle) * r
    } else if (emitterShape === 'box') {
      px += (Math.random() - 0.5) * emitterRadius * 2
      py += (Math.random() - 0.5) * emitterRadius * 2
      pz += (Math.random() - 0.5) * emitterRadius * 2
    }

    const dirX = direction.x + (Math.random() - 0.5) * spread
    const dirY = direction.y + (Math.random() - 0.5) * spread
    const dirZ = direction.z + (Math.random() - 0.5) * spread
    const dirLen = Math.sqrt(dirX * dirX + dirY * dirY + dirZ * dirZ)
    const speed = this.randomRange(this.config.speed.min, this.config.speed.max)

    const vx = (dirX / dirLen) * speed
    const vy = (dirY / dirLen) * speed
    const vz = (dirZ / dirLen) * speed

    const life = this.randomRange(this.config.life.min, this.config.life.max)
    const size = this.randomRange(this.config.size.min, this.config.size.max)

    const startColor = new THREE.Color(this.config.color.start)
    const endColor = new THREE.Color(this.config.color.end)
    const colorT = Math.random()
    const r = startColor.r + (endColor.r - startColor.r) * colorT
    const g = startColor.g + (endColor.g - startColor.g) * colorT
    const b = startColor.b + (endColor.b - startColor.b) * colorT

    const rotation = Math.random() * Math.PI * 2
    const rotationSpeed = this.randomRange(this.config.rotationSpeed.min, this.config.rotationSpeed.max)

    this.instancePosition[index * 3] = px
    this.instancePosition[index * 3 + 1] = py
    this.instancePosition[index * 3 + 2] = pz

    this.instanceVelocity[index * 3] = vx
    this.instanceVelocity[index * 3 + 1] = vy
    this.instanceVelocity[index * 3 + 2] = vz

    this.instanceLife[index] = life
    this.instanceMaxLife[index] = life
    this.instanceSize[index] = size

    this.instanceColor[index * 3] = r
    this.instanceColor[index * 3 + 1] = g
    this.instanceColor[index * 3 + 2] = b

    this.instanceRotation[index] = rotation
    this.instanceRotationSpeed[index] = rotationSpeed
    this.instanceActive[index] = 1

    this.geometry.attributes.instancePosition.needsUpdate = true
    this.geometry.attributes.instanceVelocity.needsUpdate = true
    this.geometry.attributes.instanceLife.needsUpdate = true
    this.geometry.attributes.instanceMaxLife.needsUpdate = true
    this.geometry.attributes.instanceSize.needsUpdate = true
    this.geometry.attributes.instanceColor.needsUpdate = true
    this.geometry.attributes.instanceRotation.needsUpdate = true
    this.geometry.attributes.instanceRotationSpeed.needsUpdate = true
    this.geometry.attributes.instanceActive.needsUpdate = true
  }

  randomRange(min, max) {
    return min + Math.random() * (max - min)
  }

  update(deltaTime) {
    if (this.paused) return

    this.time += deltaTime
    this.deltaTime = Math.min(deltaTime, 0.05)

    this.emissionAccumulator += this.config.emissionRate * this.deltaTime
    const emitCount = Math.floor(this.emissionAccumulator)
    for (let i = 0; i < emitCount; i++) {
      this.emitParticle()
    }
    this.emissionAccumulator -= emitCount

    for (let i = this.activeIndices.length - 1; i >= 0; i--) {
      const index = this.activeIndices[i]
      
      this.instanceLife[index] -= this.deltaTime
      
      if (this.instanceLife[index] <= 0) {
        this.instanceActive[index] = 0
        this.geometry.attributes.instanceActive.needsUpdate = true
        this.geometry.attributes.instanceLife.needsUpdate = true
        this.freeIndices.push(index)
        this.activeIndices.splice(i, 1)
        continue
      }

      this.instanceVelocity[index * 3] += this.config.gravity.x * this.deltaTime
      this.instanceVelocity[index * 3 + 1] += this.config.gravity.y * this.deltaTime
      this.instanceVelocity[index * 3 + 2] += this.config.gravity.z * this.deltaTime

      this.instancePosition[index * 3] += this.instanceVelocity[index * 3] * this.deltaTime
      this.instancePosition[index * 3 + 1] += this.instanceVelocity[index * 3 + 1] * this.deltaTime
      this.instancePosition[index * 3 + 2] += this.instanceVelocity[index * 3 + 2] * this.deltaTime

      this.instanceRotation[index] += this.instanceRotationSpeed[index] * this.deltaTime
    }

    if (this.activeIndices.length > 0) {
      this.geometry.attributes.instancePosition.needsUpdate = true
      this.geometry.attributes.instanceVelocity.needsUpdate = true
      this.geometry.attributes.instanceLife.needsUpdate = true
      this.geometry.attributes.instanceRotation.needsUpdate = true
    }

    this.material.uniforms.uTime.value = this.time
    this.material.uniforms.uDeltaTime.value = this.deltaTime
    this.material.uniforms.uGravity.value.set(
      this.config.gravity.x,
      this.config.gravity.y,
      this.config.gravity.z
    )

    this.particleCount = this.activeIndices.length
  }

  updateConfig(newConfig) {
    const oldBlending = this.config.blending
    Object.assign(this.config, newConfig)

    if (oldBlending !== this.config.blending) {
      this.material.blending = this.config.blending === 'additive' 
        ? THREE.AdditiveBlending 
        : THREE.NormalBlending
      this.material.needsUpdate = true
    }
  }

  getConfig() {
    return JSON.parse(JSON.stringify(this.config))
  }

  clear() {
    for (const index of this.activeIndices) {
      this.instanceActive[index] = 0
      this.freeIndices.push(index)
    }
    this.activeIndices = []
    this.particleCount = 0
    this.emissionAccumulator = 0
    
    this.geometry.attributes.instanceActive.needsUpdate = true
    this.geometry.attributes.instanceLife.needsUpdate = true
  }

  pause() {
    this.paused = true
  }

  resume() {
    this.paused = false
  }

  dispose() {
    this.scene.remove(this.points)
    this.geometry.dispose()
    this.material.dispose()
  }

  get particles() {
    return {
      length: this.particleCount
    }
  }
}
