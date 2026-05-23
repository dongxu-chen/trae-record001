<template>
  <div class="ai-panel">
    <div class="panel-section">
      <h3>🤖 AI 智能抠图</h3>
      
      <div class="method-selector">
        <label>抠图模式:</label>
        <div class="btn-group">
          <button
            class="btn small"
            :class="{ active: removeMethod === 'auto' }"
            @click="removeMethod = 'auto'"
          >
            自动
          </button>
          <button
            class="btn small"
            :class="{ active: removeMethod === 'green' }"
            @click="removeMethod = 'green'"
          >
            绿幕
          </button>
          <button
            class="btn small"
            :class="{ active: removeMethod === 'blue' }"
            @click="removeMethod = 'blue'"
          >
            蓝幕
          </button>
          <button
            class="btn small"
            :class="{ active: removeMethod === 'custom' }"
            @click="removeMethod = 'custom'"
          >
            自定义
          </button>
        </div>
      </div>

      <div v-if="removeMethod === 'custom'" class="color-picker-group">
        <label>背景颜色:</label>
        <input
          type="color"
          v-model="customBgColor"
          class="color-picker"
        />
      </div>

      <div class="slider-group">
        <label>容差值: {{ colorTolerance }}</label>
        <input
          type="range"
          v-model.number="colorTolerance"
          min="10"
          max="100"
          step="5"
        />
      </div>

      <div class="checkbox-group">
        <label>
          <input
            type="checkbox"
            v-model="edgeSmoothing"
          />
          边缘平滑
        </label>
      </div>

      <button
        class="btn btn-primary full-width"
        :disabled="!hasImage || isProcessing"
        @click="removeBackground"
      >
        {{ isProcessing ? '处理中...' : '✨ 一键去除背景' }}
      </button>

      <div class="hint-text">
        💡 提示: 上传图片后选择背景颜色，点击一键抠图
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  canvas: Object,
  hasImage: Boolean
})

const emit = defineEmits(['processing', 'complete'])

const removeMethod = ref('auto')
const colorTolerance = ref(40)
const edgeSmoothing = ref(true)
const customBgColor = ref('#ffffff')
const isProcessing = ref(false)

async function removeBackground() {
  if (!props.canvas || isProcessing.value) return

  const activeObj = props.canvas.getActiveObject()
  if (!activeObj || activeObj.type !== 'image') {
    alert('请先选择一张图片')
    return
  }

  const imgElement = activeObj.getElement()
  if (!imgElement) return

  isProcessing.value = true
  emit('processing', true)

  try {
    const { aiBackgroundRemover } = await import('../utils/AIBackgroundRemover.js')
    
    let bgColor = null
    if (removeMethod.value === 'custom') {
      const hex = customBgColor.value.replace('#', '')
      bgColor = {
        r: parseInt(hex.substr(0, 2), 16),
        g: parseInt(hex.substr(2, 2), 16),
        b: parseInt(hex.substr(4, 2), 16)
      }
    }

    const resultCanvas = await aiBackgroundRemover.removeBackground(imgElement, {
      method: removeMethod.value,
      backgroundColor: bgColor,
      colorTolerance: colorTolerance.value,
      edgeDetection: edgeSmoothing.value
    })

    const fabric = await import('fabric')
    return new Promise((resolve) => {
      fabric.default.Image.fromURL(resultCanvas.toDataURL(), (newImg) => {
        newImg.set({
          left: activeObj.left,
          top: activeObj.top,
          scaleX: activeObj.scaleX,
          scaleY: activeObj.scaleY,
          angle: activeObj.angle
        })
        newImg.layerId = activeObj.layerId
        
        props.canvas.remove(activeObj)
        props.canvas.add(newImg)
        props.canvas.setActiveObject(newImg)
        props.canvas.renderAll()
        
        isProcessing.value = false
        emit('processing', false)
        emit('complete', newImg)
        resolve()
      })
    })
  } catch (error) {
    console.error('Remove background error:', error)
    isProcessing.value = false
    emit('processing', false)
  }
}
</script>

<style scoped>
.ai-panel {
  margin-bottom: 24px;
}

.method-selector {
  margin-bottom: 16px;
}

.method-selector label {
  display: block;
  margin-bottom: 8px;
  font-size: 13px;
  color: #a0a0c0;
}

.btn.small {
  padding: 6px 10px;
  font-size: 11px;
}

.color-picker-group {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.color-picker-group label {
  font-size: 13px;
  color: #a0a0c0;
}

.color-picker {
  width: 50px;
  height: 36px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  background: transparent;
}

.checkbox-group {
  margin-bottom: 16px;
}

.checkbox-group label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #a0a0c0;
  cursor: pointer;
}

.btn.full-width {
  width: 100%;
}

.hint-text {
  margin-top: 12px;
  padding: 10px;
  background: rgba(233, 69, 96, 0.1);
  border-radius: 6px;
  font-size: 11px;
  color: #e94560;
  line-height: 1.5;
}
</style>
