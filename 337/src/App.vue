<template>
  <div class="app">
    <div class="canvas-container" ref="canvasContainer"></div>
    <ControlPanel
      :config="currentConfig"
      :current-preset="currentPreset"
      :is-playing="isPlaying"
      :mouse-interactor="mouseInteractor"
      @load-preset="loadPreset"
      @update-config="updateConfig"
      @play="play"
      @pause="pause"
      @reset="reset"
      @export="exportConfig"
      @import="importConfig"
      @play-animation="playAnimation"
      @animation-play="animationPlay"
      @animation-pause="animationPause"
      @animation-restart="animationRestart"
      @animation-stop="animationStop"
      @play-animation-with-bezier="playAnimationWithBezier"
      @apply-bezier-ease="applyBezierEase"
      @apply-template="applyTemplate"
      @save-template="saveTemplate"
    />
    <div class="status-bar">
      <div class="status-item">
        <span class="status-label">FPS</span>
        <span class="status-value">{{ fps }}</span>
      </div>
      <div class="status-item">
        <span class="status-label">粒子数</span>
        <span class="status-value">{{ activeParticles }}</span>
      </div>
      <div class="status-item">
        <span class="status-label">当前预设</span>
        <span class="status-value">{{ getPresetName(currentPreset) }}</span>
      </div>
      <div class="status-item">
        <span class="status-label">状态</span>
        <span class="status-value" :class="{ playing: isPlaying }">
          {{ isPlaying ? '播放中' : '已暂停' }}
        </span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import * as THREE from 'three'
import { SceneManager } from './engine/SceneManager.js'
import { KeyframeAnimator } from './animation/KeyframeAnimator.js'
import { MouseInteractor } from './interaction/MouseInteractor.js'
import { particlePresets } from './presets/particlePresets.js'
import { TemplateMarket } from './market/TemplateMarket.js'
import { downloadConfig, estimateDiffSize, DEFAULT_CONFIG } from './utils/ConfigManager.js'
import ControlPanel from './components/ControlPanel.vue'

const canvasContainer = ref(null)
const currentPreset = ref('fire')
const isPlaying = ref(true)
const fps = ref(60)
const activeParticles = ref(0)

let sceneManager = null
let particleEngine = null
let keyframeAnimator = null
let mouseInteractor = null
let templateMarket = null
let fpsCounter = 0
let fpsTime = 0
let animationFrameId = null

const defaultConfig = JSON.parse(JSON.stringify(particlePresets.fire.config))
const currentConfig = reactive(JSON.parse(JSON.stringify(defaultConfig)))

function getPresetName(key) {
  return particlePresets[key]?.name || key
}

function initScene() {
  if (!canvasContainer.value) return

  sceneManager = new SceneManager(canvasContainer.value)
  particleEngine = sceneManager.addParticleSystem(currentPreset.value)
  keyframeAnimator = new KeyframeAnimator(particleEngine)

  const canvas = canvasContainer.value.querySelector('canvas')
  if (canvas && sceneManager.camera) {
    mouseInteractor = new MouseInteractor(canvas, particleEngine, sceneManager.camera)
  }

  templateMarket = new TemplateMarket()

  updateFps()
}

function updateFps() {
  fpsCounter++
  const now = performance.now()
  
  if (now - fpsTime >= 1000) {
    fps.value = fpsCounter
    fpsCounter = 0
    fpsTime = now
  }

  if (particleEngine) {
    activeParticles.value = particleEngine.particles.length
  }

  animationFrameId = requestAnimationFrame(updateFps)
}

function loadPreset(presetName) {
  if (!sceneManager || !particlePresets[presetName]) return

  currentPreset.value = presetName
  const presetConfig = particlePresets[presetName].config

  Object.assign(currentConfig, JSON.parse(JSON.stringify(presetConfig)))

  sceneManager.clearAllParticleSystems()
  particleEngine = sceneManager.addParticleSystem(presetName)
  
  if (keyframeAnimator) {
    keyframeAnimator.dispose()
  }
  keyframeAnimator = new KeyframeAnimator(particleEngine)
}

function updateConfig(newConfig) {
  if (!particleEngine) return

  Object.assign(currentConfig, newConfig)
  particleEngine.updateConfig(newConfig)
}

function play() {
  if (sceneManager) {
    sceneManager.play()
    isPlaying.value = true
  }
}

function pause() {
  if (sceneManager) {
    sceneManager.pause()
    isPlaying.value = false
  }
}

function reset() {
  if (sceneManager) {
    sceneManager.reset()
  }
}

function exportConfig() {
  if (!particleEngine) return

  const config = particleEngine.getConfig()
  
  const basePreset = particlePresets[currentPreset.value] ? currentPreset.value : null
  const sizeInfo = estimateDiffSize(config, basePreset)
  
  console.log(`导出配置：完整大小 ${sizeInfo.fullSize} 字节，差量大小 ${sizeInfo.diffSize} 字节，节省 ${sizeInfo.savedPercent}%`)
  
  const filename = `particle-${currentPreset.value}-${Date.now()}.json`
  downloadConfig(config, filename, {
    name: getPresetName(currentPreset.value),
    preset: currentPreset.value,
    sizeInfo: sizeInfo
  }, {
    useDiff: true,
    basePreset: basePreset,
    prettyPrint: true
  })
}

function importConfig(config) {
  if (!sceneManager) return

  Object.assign(currentConfig, config)

  sceneManager.clearAllParticleSystems()
  particleEngine = sceneManager.addParticleSystem('fire', config)
  
  if (keyframeAnimator) {
    keyframeAnimator.dispose()
  }
  keyframeAnimator = new KeyframeAnimator(particleEngine)
  
  currentPreset.value = 'custom'
}

function playAnimation(type) {
  if (!keyframeAnimator) return

  keyframeAnimator.stopAll()
  keyframeAnimator.createPresetAnimation(type)
  keyframeAnimator.play()
}

function animationPlay() {
  if (keyframeAnimator) {
    keyframeAnimator.play()
  }
}

function animationPause() {
  if (keyframeAnimator) {
    keyframeAnimator.pause()
  }
}

function animationRestart() {
  if (keyframeAnimator) {
    keyframeAnimator.restart()
  }
}

function animationStop() {
  if (keyframeAnimator) {
    keyframeAnimator.stopAll()
  }
}

function playAnimationWithBezier({ animation, bezier }) {
  if (!keyframeAnimator) return

  console.log(`使用自定义贝塞尔曲线播放动画 ${animation}:`, bezier)
  
  keyframeAnimator.stopAll()
  keyframeAnimator.playAnimationWithCustomEase(animation, bezier)
}

function applyBezierEase(params) {
  if (!keyframeAnimator) return

  console.log('应用贝塞尔缓动:', params)
  
  keyframeAnimator.setCustomBezierEase(params)
}

function applyTemplate(template) {
  if (!sceneManager || !template.config) return

  console.log('应用模板:', template.name)

  Object.assign(currentConfig, JSON.parse(JSON.stringify(template.config)))

  sceneManager.clearAllParticleSystems()
  particleEngine = sceneManager.addParticleSystem('fire', template.config)
  
  if (keyframeAnimator) {
    keyframeAnimator.dispose()
  }
  keyframeAnimator = new KeyframeAnimator(particleEngine)

  if (mouseInteractor) {
    mouseInteractor.particleEngine = particleEngine
  }
  
  currentPreset.value = template.name
}

function saveTemplate({ name, config }) {
  if (!templateMarket) return

  const template = templateMarket.saveUserTemplate(name, config, '用户保存的特效')
  console.log('保存模板:', template.name)
  alert(`模板 "${name}" 已保存！`)
}

onMounted(() => {
  initScene()
})

onUnmounted(() => {
  if (animationFrameId) {
    cancelAnimationFrame(animationFrameId)
  }
  if (keyframeAnimator) {
    keyframeAnimator.dispose()
  }
  if (mouseInteractor) {
    mouseInteractor.dispose()
  }
  if (sceneManager) {
    sceneManager.dispose()
  }
})
</script>

<style scoped>
.app {
  width: 100vw;
  height: 100vh;
  display: flex;
  position: relative;
  overflow: hidden;
}

.canvas-container {
  flex: 1;
  position: relative;
}

.canvas-container :deep(canvas) {
  display: block;
}

.status-bar {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 380px;
  height: 40px;
  background: rgba(15, 15, 25, 0.9);
  backdrop-filter: blur(10px);
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  display: flex;
  align-items: center;
  padding: 0 20px;
  gap: 30px;
}

.status-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-label {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.5);
  text-transform: uppercase;
  letter-spacing: 1px;
}

.status-value {
  font-size: 13px;
  font-family: 'Monaco', 'Consolas', monospace;
  color: #667eea;
  font-weight: 600;
}

.status-value.playing {
  color: #4ade80;
}
</style>
