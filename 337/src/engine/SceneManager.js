import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { ParticleEngine } from './ParticleEngine.js'
import { particlePresets } from '../presets/particlePresets.js'

export class SceneManager {
  constructor(container) {
    this.container = container
    this.particleEngines = []
    this.isPlaying = true
    this.animationId = null
    this.clock = new THREE.Clock()

    this.initScene()
    this.initCamera()
    this.initRenderer()
    this.initControls()
    this.initLights()
    this.animate()

    window.addEventListener('resize', this.onResize.bind(this))
  }

  initScene() {
    this.scene = new THREE.Scene()
    this.scene.background = new THREE.Color(0x0a0a0f)
    this.scene.fog = new THREE.Fog(0x0a0a0f, 10, 50)
  }

  initCamera() {
    this.camera = new THREE.PerspectiveCamera(
      75,
      this.container.clientWidth / this.container.clientHeight,
      0.1,
      1000
    )
    this.camera.position.set(0, 0, 8)
  }

  initRenderer() {
    this.renderer = new THREE.WebGLRenderer({
      antialias: true,
      powerPreference: 'high-performance'
    })
    this.renderer.setSize(this.container.clientWidth, this.container.clientHeight)
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    this.container.appendChild(this.renderer.domElement)
  }

  initControls() {
    this.controls = new OrbitControls(this.camera, this.renderer.domElement)
    this.controls.enableDamping = true
    this.controls.dampingFactor = 0.05
    this.controls.minDistance = 2
    this.controls.maxDistance = 50
  }

  initLights() {
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.5)
    this.scene.add(ambientLight)

    const directionalLight = new THREE.DirectionalLight(0xffffff, 1)
    directionalLight.position.set(5, 10, 7)
    this.scene.add(directionalLight)
  }

  addParticleSystem(presetName = 'fire', customConfig = {}) {
    const preset = particlePresets[presetName] || particlePresets.fire
    const config = { ...preset.config, ...customConfig }
    const engine = new ParticleEngine(this.scene, config)
    this.particleEngines.push(engine)
    return engine
  }

  removeParticleSystem(engine) {
    const index = this.particleEngines.indexOf(engine)
    if (index > -1) {
      engine.dispose()
      this.particleEngines.splice(index, 1)
    }
  }

  clearAllParticleSystems() {
    for (const engine of this.particleEngines) {
      engine.dispose()
    }
    this.particleEngines = []
  }

  updateParticleSystem(engine, newConfig) {
    if (engine) {
      engine.updateConfig(newConfig)
    }
  }

  animate() {
    this.animationId = requestAnimationFrame(this.animate.bind(this))

    const deltaTime = Math.min(this.clock.getDelta(), 0.1)

    if (this.isPlaying) {
      for (const engine of this.particleEngines) {
        engine.update(deltaTime)
      }
    }

    this.controls.update()
    this.renderer.render(this.scene, this.camera)
  }

  play() {
    this.isPlaying = true
    for (const engine of this.particleEngines) {
      engine.resume()
    }
  }

  pause() {
    this.isPlaying = false
    for (const engine of this.particleEngines) {
      engine.pause()
    }
  }

  reset() {
    for (const engine of this.particleEngines) {
      engine.clear()
    }
  }

  setBackgroundColor(color) {
    this.scene.background = new THREE.Color(color)
    if (this.scene.fog) {
      this.scene.fog.color = new THREE.Color(color)
    }
  }

  onResize() {
    this.camera.aspect = this.container.clientWidth / this.container.clientHeight
    this.camera.updateProjectionMatrix()
    this.renderer.setSize(this.container.clientWidth, this.container.clientHeight)
  }

  dispose() {
    if (this.animationId) {
      cancelAnimationFrame(this.animationId)
    }
    window.removeEventListener('resize', this.onResize.bind(this))
    this.clearAllParticleSystems()
    this.controls.dispose()
    this.renderer.dispose()
    this.container.removeChild(this.renderer.domElement)
  }
}
