import * as THREE from 'three'
import type { ForceField, ColorZone, Emitter, Vector2 } from '@/types'

export interface GPGPUSettings {
  width: number
  height: number
  renderer: THREE.WebGLRenderer
}

export class TexturePool {
  private pool: Map<string, THREE.WebGLRenderTarget[]> = new Map()
  private width: number
  private height: number
  private type: THREE.TextureDataType

  constructor(width: number, height: number, type: THREE.TextureDataType = THREE.HalfFloatType) {
    this.width = width
    this.height = height
    this.type = type
  }

  acquire(key: string): THREE.WebGLRenderTarget {
    const pool = this.pool.get(key) || []
    if (pool.length > 0) {
      return pool.pop()!
    }
    return this.createRenderTarget()
  }

  release(key: string, rt: THREE.WebGLRenderTarget): void {
    const pool = this.pool.get(key) || []
    pool.push(rt)
    this.pool.set(key, pool)
  }

  private createRenderTarget(): THREE.WebGLRenderTarget {
    return new THREE.WebGLRenderTarget(this.width, this.height, {
      minFilter: THREE.LinearFilter,
      magFilter: THREE.LinearFilter,
      format: THREE.RGBAFormat,
      type: this.type,
      wrapS: THREE.ClampToEdgeWrapping,
      wrapT: THREE.ClampToEdgeWrapping,
      depthBuffer: false,
      stencilBuffer: false,
    })
  }

  resize(width: number, height: number): void {
    this.width = width
    this.height = height
    this.pool.forEach((rts) => rts.forEach((rt) => rt.dispose()))
    this.pool.clear()
  }

  dispose(): void {
    this.pool.forEach((rts) => rts.forEach((rt) => rt.dispose()))
    this.pool.clear()
  }
}

export class GPGPU {
  private renderer: THREE.WebGLRenderer
  private width: number
  private height: number
  private scene: THREE.Scene
  private camera: THREE.OrthographicCamera
  private mesh: THREE.Mesh
  private texturePool: TexturePool

  constructor(settings: GPGPUSettings) {
    this.renderer = settings.renderer
    this.width = settings.width
    this.height = settings.height

    this.scene = new THREE.Scene()
    this.camera = new THREE.OrthographicCamera(-0.5, 0.5, 0.5, -0.5, 0, 1)
    this.mesh = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), null)
    this.scene.add(this.mesh)

    this.texturePool = new TexturePool(this.width, this.height)
  }

  getPool(): TexturePool {
    return this.texturePool
  }

  createRenderTarget(
    type: THREE.TextureDataType = THREE.HalfFloatType
  ): THREE.WebGLRenderTarget {
    return new THREE.WebGLRenderTarget(this.width, this.height, {
      minFilter: THREE.LinearFilter,
      magFilter: THREE.LinearFilter,
      format: THREE.RGBAFormat,
      type,
      wrapS: THREE.ClampToEdgeWrapping,
      wrapT: THREE.ClampToEdgeWrapping,
      depthBuffer: false,
      stencilBuffer: false,
    })
  }

  render(
    shaderMaterial: THREE.ShaderMaterial,
    output: THREE.WebGLRenderTarget | null
  ): void {
    this.mesh.material = shaderMaterial
    this.renderer.setRenderTarget(output)
    this.renderer.render(this.scene, this.camera)
    this.renderer.setRenderTarget(null)
  }

  resize(width: number, height: number): void {
    this.width = width
    this.height = height
    this.texturePool.resize(width, height)
  }
}

interface PingPongRT {
  read: THREE.WebGLRenderTarget
  write: THREE.WebGLRenderTarget
  swap(): void
}

function createPingPongRT(gpgpu: GPGPU): PingPongRT {
  const read = gpgpu.createRenderTarget()
  const write = gpgpu.createRenderTarget()
  return {
    read,
    write,
    swap() {
      const temp = this.read
      this.read = this.write
      this.write = temp
    },
  }
}

export class FluidSolver {
  private gpgpu: GPGPU
  private velocity: PingPongRT
  private density: PingPongRT
  private pressure: PingPongRT
  private vorticity: THREE.WebGLRenderTarget
  private divergence: THREE.WebGLRenderTarget
  private coloredDensity: PingPongRT

  private advectionMaterial: THREE.ShaderMaterial
  private divergenceMaterial: THREE.ShaderMaterial
  private pressureMaterial: THREE.ShaderMaterial
  private gradientMaterial: THREE.ShaderMaterial
  private splatMaterial: THREE.ShaderMaterial
  private vorticityMaterial: THREE.ShaderMaterial
  private vorticityConfinementMaterial: THREE.ShaderMaterial
  private applyForceMaterial: THREE.ShaderMaterial
  private applyColorZonesMaterial: THREE.ShaderMaterial
  private emitParticlesMaterial: THREE.ShaderMaterial

  private resolution: { x: number; y: number }
  private timeStep: number = 0.016
  private dissipation: number = 0.998
  private velocityDissipation: number = 0.995
  private pressureIterations: number = 25
  private vorticityScale: number = 0.15
  private advectionOrder: number = 2

  private forceFields: ForceField[] = []
  private colorZones: ColorZone[] = []
  private emitters: Emitter[] = []

  constructor(gpgpu: GPGPU, vertexShader: string, shaders: Record<string, string>) {
    this.gpgpu = gpgpu
    this.resolution = { x: gpgpu['width'], y: gpgpu['height'] }

    this.velocity = createPingPongRT(gpgpu)
    this.density = createPingPongRT(gpgpu)
    this.pressure = createPingPongRT(gpgpu)
    this.vorticity = gpgpu.createRenderTarget()
    this.divergence = gpgpu.createRenderTarget()
    this.coloredDensity = createPingPongRT(gpgpu)

    this.advectionMaterial = new THREE.ShaderMaterial({
      vertexShader,
      fragmentShader: shaders.advection,
      uniforms: {
        uVelocity: { value: null },
        uSource: { value: null },
        uResolution: { value: new THREE.Vector2(this.resolution.x, this.resolution.y) },
        uTimeStep: { value: this.timeStep },
        uDissipation: { value: this.dissipation },
        uOrder: { value: this.advectionOrder },
      },
    })

    this.divergenceMaterial = new THREE.ShaderMaterial({
      vertexShader,
      fragmentShader: shaders.divergence,
      uniforms: {
        uVelocity: { value: null },
        uResolution: { value: new THREE.Vector2(this.resolution.x, this.resolution.y) },
      },
    })

    this.pressureMaterial = new THREE.ShaderMaterial({
      vertexShader,
      fragmentShader: shaders.pressure,
      uniforms: {
        uPressure: { value: null },
        uDivergence: { value: null },
        uResolution: { value: new THREE.Vector2(this.resolution.x, this.resolution.y) },
      },
    })

    this.gradientMaterial = new THREE.ShaderMaterial({
      vertexShader,
      fragmentShader: shaders.gradient,
      uniforms: {
        uPressure: { value: null },
        uVelocity: { value: null },
        uResolution: { value: new THREE.Vector2(this.resolution.x, this.resolution.y) },
      },
    })

    this.splatMaterial = new THREE.ShaderMaterial({
      vertexShader,
      fragmentShader: shaders.splat,
      uniforms: {
        uTarget: { value: null },
        uPoint: { value: new THREE.Vector2() },
        uColor: { value: new THREE.Color() },
        uRadius: { value: 500 },
        uResolution: { value: new THREE.Vector2(this.resolution.x, this.resolution.y) },
      },
    })

    this.vorticityMaterial = new THREE.ShaderMaterial({
      vertexShader,
      fragmentShader: shaders.vorticity,
      uniforms: {
        uVelocity: { value: null },
        uResolution: { value: new THREE.Vector2(this.resolution.x, this.resolution.y) },
      },
    })

    this.vorticityConfinementMaterial = new THREE.ShaderMaterial({
      vertexShader,
      fragmentShader: shaders.vorticityConfinement,
      uniforms: {
        uVelocity: { value: null },
        uVorticity: { value: null },
        uResolution: { value: new THREE.Vector2(this.resolution.x, this.resolution.y) },
        uEpsilon: { value: 2.4414e-4 },
        uVorticityScale: { value: this.vorticityScale },
      },
    })

    this.applyForceMaterial = new THREE.ShaderMaterial({
      vertexShader,
      fragmentShader: shaders.applyForce,
      uniforms: {
        uVelocity: { value: null },
        uPosition: { value: new THREE.Vector2() },
        uDirection: { value: new THREE.Vector2() },
        uStrength: { value: 0 },
        uRadius: { value: 0 },
        uResolution: { value: new THREE.Vector2(this.resolution.x, this.resolution.y) },
        uTime: { value: 0 },
      },
    })

    this.applyColorZonesMaterial = new THREE.ShaderMaterial({
      vertexShader,
      fragmentShader: shaders.applyColorZones,
      uniforms: {
        uDensity: { value: null },
        uVelocity: { value: null },
        uZonePositions: { value: new Array(8).fill(0).map(() => new THREE.Vector2()) },
        uZoneColors: { value: new Array(8).fill(0).map(() => new THREE.Color()) },
        uZoneRadii: { value: new Array(8).fill(0) },
        uZoneCount: { value: 0 },
        uResolution: { value: new THREE.Vector2(this.resolution.x, this.resolution.y) },
        uBlendFactor: { value: 0.8 },
      },
    })

    this.emitParticlesMaterial = new THREE.ShaderMaterial({
      vertexShader,
      fragmentShader: shaders.emitParticles,
      uniforms: {
        uTarget: { value: null },
        uPosition: { value: new THREE.Vector2() },
        uDirection: { value: new THREE.Vector2() },
        uRate: { value: 0 },
        uColor: { value: new THREE.Color() },
        uTime: { value: 0 },
        uResolution: { value: new THREE.Vector2(this.resolution.x, this.resolution.y) },
      },
    })
  }

  splat(point: THREE.Vector2, color: THREE.Color, radius: number = 500): void {
    this.splatMaterial.uniforms.uPoint.value = point
    this.splatMaterial.uniforms.uColor.value = color
    this.splatMaterial.uniforms.uRadius.value = radius

    this.splatMaterial.uniforms.uTarget.value = this.velocity.read.texture
    this.gpgpu.render(this.splatMaterial, this.velocity.write)
    this.velocity.swap()

    this.splatMaterial.uniforms.uTarget.value = this.density.read.texture
    this.gpgpu.render(this.splatMaterial, this.density.write)
    this.density.swap()
  }

  applyForce(
    position: Vector2,
    direction: Vector2,
    strength: number,
    radius: number,
    time: number
  ): void {
    this.applyForceMaterial.uniforms.uVelocity.value = this.velocity.read.texture
    this.applyForceMaterial.uniforms.uPosition.value = new THREE.Vector2(position.x, position.y)
    this.applyForceMaterial.uniforms.uDirection.value = new THREE.Vector2(direction.x, direction.y)
    this.applyForceMaterial.uniforms.uStrength.value = strength
    this.applyForceMaterial.uniforms.uRadius.value = radius
    this.applyForceMaterial.uniforms.uTime.value = time
    this.gpgpu.render(this.applyForceMaterial, this.velocity.write)
    this.velocity.swap()
  }

  applyColorZones(): void {
    const enabledZones = this.colorZones.filter((z) => z.enabled).slice(0, 8)
    if (enabledZones.length === 0) return

    const positions = enabledZones.map(
      (z) => new THREE.Vector2(z.position.x, z.position.y)
    )
    const colors = enabledZones.map(
      (z) => new THREE.Color(z.color.r, z.color.g, z.color.b)
    )
    const radii = enabledZones.map((z) => z.radius)

    while (positions.length < 8) {
      positions.push(new THREE.Vector2())
      colors.push(new THREE.Color())
      radii.push(0)
    }

    this.applyColorZonesMaterial.uniforms.uDensity.value = this.density.read.texture
    this.applyColorZonesMaterial.uniforms.uVelocity.value = this.velocity.read.texture
    this.applyColorZonesMaterial.uniforms.uZonePositions.value = positions
    this.applyColorZonesMaterial.uniforms.uZoneColors.value = colors
    this.applyColorZonesMaterial.uniforms.uZoneRadii.value = radii
    this.applyColorZonesMaterial.uniforms.uZoneCount.value = enabledZones.length

    this.gpgpu.render(this.applyColorZonesMaterial, this.coloredDensity.write)
    this.coloredDensity.swap()
  }

  emitParticles(time: number): void {
    const enabledEmitters = this.emitters.filter((e) => e.enabled)
    for (const emitter of enabledEmitters) {
      this.emitParticlesMaterial.uniforms.uTarget.value = this.density.read.texture
      this.emitParticlesMaterial.uniforms.uPosition.value = new THREE.Vector2(
        emitter.position.x,
        emitter.position.y
      )
      this.emitParticlesMaterial.uniforms.uDirection.value = new THREE.Vector2(
        emitter.direction.x,
        emitter.direction.y
      )
      this.emitParticlesMaterial.uniforms.uRate.value = emitter.rate
      this.emitParticlesMaterial.uniforms.uColor.value = new THREE.Color(
        emitter.color.r,
        emitter.color.g,
        emitter.color.b
      )
      this.emitParticlesMaterial.uniforms.uTime.value = time
      this.gpgpu.render(this.emitParticlesMaterial, this.density.write)
      this.density.swap()

      this.emitParticlesMaterial.uniforms.uTarget.value = this.velocity.read.texture
      this.gpgpu.render(this.emitParticlesMaterial, this.velocity.write)
      this.velocity.swap()
    }
  }

  step(dt?: number, time: number = 0): void {
    const timeStep = dt || this.timeStep

    this.emitParticles(time)

    const enabledForces = this.forceFields.filter((f) => f.enabled)
    for (const force of enabledForces) {
      this.applyForce(force.position, force.direction, force.strength, force.radius, time)
    }

    this.vorticityMaterial.uniforms.uVelocity.value = this.velocity.read.texture
    this.gpgpu.render(this.vorticityMaterial, this.vorticity)

    this.vorticityConfinementMaterial.uniforms.uVelocity.value = this.velocity.read.texture
    this.vorticityConfinementMaterial.uniforms.uVorticity.value = this.vorticity.texture
    this.vorticityConfinementMaterial.uniforms.uVorticityScale.value = this.vorticityScale
    this.gpgpu.render(this.vorticityConfinementMaterial, this.velocity.write)
    this.velocity.swap()

    this.advectionMaterial.uniforms.uVelocity.value = this.velocity.read.texture
    this.advectionMaterial.uniforms.uSource.value = this.velocity.read.texture
    this.advectionMaterial.uniforms.uTimeStep.value = timeStep
    this.advectionMaterial.uniforms.uDissipation.value = this.velocityDissipation
    this.advectionMaterial.uniforms.uOrder.value = this.advectionOrder
    this.gpgpu.render(this.advectionMaterial, this.velocity.write)
    this.velocity.swap()

    this.advectionMaterial.uniforms.uSource.value = this.density.read.texture
    this.advectionMaterial.uniforms.uDissipation.value = this.dissipation
    this.gpgpu.render(this.advectionMaterial, this.density.write)
    this.density.swap()

    this.applyColorZones()

    this.divergenceMaterial.uniforms.uVelocity.value = this.velocity.read.texture
    this.gpgpu.render(this.divergenceMaterial, this.divergence)

    this.clearTarget(this.pressure.read)
    for (let i = 0; i < this.pressureIterations; i++) {
      this.pressureMaterial.uniforms.uPressure.value = this.pressure.read.texture
      this.pressureMaterial.uniforms.uDivergence.value = this.divergence.texture
      this.gpgpu.render(this.pressureMaterial, this.pressure.write)
      this.pressure.swap()
    }

    this.gradientMaterial.uniforms.uPressure.value = this.pressure.read.texture
    this.gradientMaterial.uniforms.uVelocity.value = this.velocity.read.texture
    this.gpgpu.render(this.gradientMaterial, this.velocity.write)
    this.velocity.swap()
  }

  setForceFields(fields: ForceField[]): void {
    this.forceFields = fields
  }

  setColorZones(zones: ColorZone[]): void {
    this.colorZones = zones
  }

  setEmitters(emitters: Emitter[]): void {
    this.emitters = emitters
  }

  private clearTarget(target: THREE.WebGLRenderTarget): void {
    const gl = this.gpgpu['renderer'].getContext()
    gl.bindFramebuffer(gl.FRAMEBUFFER, target.framebuffer)
    gl.clearColor(0, 0, 0, 1)
    gl.clear(gl.COLOR_BUFFER_BIT)
    gl.bindFramebuffer(gl.FRAMEBUFFER, null)
  }

  getVelocityTexture(): THREE.Texture {
    return this.velocity.read.texture
  }

  getDensityTexture(): THREE.Texture {
    const enabledZones = this.colorZones.filter((z) => z.enabled)
    if (enabledZones.length > 0) {
      return this.coloredDensity.read.texture
    }
    return this.density.read.texture
  }

  setTimeStep(dt: number): void {
    this.timeStep = dt
  }

  setDissipation(d: number): void {
    this.dissipation = d
  }

  setVelocityDissipation(d: number): void {
    this.velocityDissipation = d
  }

  setVorticityScale(s: number): void {
    this.vorticityScale = s
    this.vorticityConfinementMaterial.uniforms.uVorticityScale.value = s
  }

  setPressureIterations(n: number): void {
    this.pressureIterations = n
  }

  setAdvectionOrder(order: number): void {
    this.advectionOrder = order
  }

  dispose(): void {
    this.velocity.read.dispose()
    this.velocity.write.dispose()
    this.density.read.dispose()
    this.density.write.dispose()
    this.pressure.read.dispose()
    this.pressure.write.dispose()
    this.vorticity.dispose()
    this.divergence.dispose()
    this.coloredDensity.read.dispose()
    this.coloredDensity.write.dispose()

    this.advectionMaterial.dispose()
    this.divergenceMaterial.dispose()
    this.pressureMaterial.dispose()
    this.gradientMaterial.dispose()
    this.splatMaterial.dispose()
    this.vorticityMaterial.dispose()
    this.vorticityConfinementMaterial.dispose()
    this.applyForceMaterial.dispose()
    this.applyColorZonesMaterial.dispose()
    this.emitParticlesMaterial.dispose()

    this.gpgpu.getPool().dispose()
  }
}
