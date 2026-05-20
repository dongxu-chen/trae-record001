<template>
  <div class="sidebar">
    <div class="sidebar-section">
      <div class="sidebar-section-title">节点面板</div>
      <div class="node-palette">
        <div class="palette-item" @click="$emit('addNode', 'rectangle')">
          <div style="width: 40px; height: 24px; border: 2px solid #1890ff; border-radius: 4px; margin: 0 auto 4px; background: #fff;"></div>
          矩形
        </div>
        <div class="palette-item" @click="$emit('addNode', 'circle')">
          <div style="width: 30px; height: 30px; border: 2px solid #52c41a; border-radius: 50%; margin: 0 auto 4px; background: #fff;"></div>
          圆形
        </div>
        <div class="palette-item" @click="$emit('addNode', 'diamond')">
          <div style="width: 24px; height: 24px; border: 2px solid #faad14; margin: 0 auto 4px; background: #fff; transform: rotate(45deg);"></div>
          菱形
        </div>
        <div class="palette-item" @click="$emit('addNode', 'parallelogram')">
          <div style="width: 40px; height: 24px; border: 2px solid #722ed1; margin: 0 auto 4px; background: #fff; transform: skewX(-15deg);"></div>
          平行四边形
        </div>
        <div class="palette-item" @click="$emit('addNode', 'document')">
          <div style="width: 24px; height: 32px; border: 2px solid #eb2f96; border-radius: 2px 2px 4px 4px; margin: 0 auto 4px; background: #fff; position: relative;">
            <div style="position: absolute; top: 4px; right: -2px; width: 8px; height: 8px; border-top: 2px solid #eb2f96; border-right: 2px solid #eb2f96; background: #fff;"></div>
          </div>
          文档
        </div>
      </div>
    </div>

    <div class="sidebar-section">
      <div class="sidebar-section-title">属性面板</div>
      <div class="property-panel">
        <template v-if="selectedObject?.type === 'node'">
          <div class="property-item">
            <div class="property-label">标签</div>
            <input 
              class="property-input" 
              type="text" 
              :value="selectedObject.data.label"
              @input="updateNode('label', $event.target.value)"
            />
          </div>
          <div class="property-item">
            <div class="property-label">宽度</div>
            <input 
              class="property-input" 
              type="number" 
              :value="selectedObject.data.width"
              @input="updateNode('width', parseInt($event.target.value) || 0)"
            />
          </div>
          <div class="property-item">
            <div class="property-label">高度</div>
            <input 
              class="property-input" 
              type="number" 
              :value="selectedObject.data.height"
              @input="updateNode('height', parseInt($event.target.value) || 0)"
            />
          </div>
          <div class="property-item">
            <div class="property-label">X 坐标</div>
            <input 
              class="property-input" 
              type="number" 
              :value="Math.round(selectedObject.data.x)"
              @input="updateNode('x', parseInt($event.target.value) || 0)"
            />
          </div>
          <div class="property-item">
            <div class="property-label">Y 坐标</div>
            <input 
              class="property-input" 
              type="number" 
              :value="Math.round(selectedObject.data.y)"
              @input="updateNode('y', parseInt($event.target.value) || 0)"
            />
          </div>
          <div class="property-item">
            <div class="property-label">填充颜色</div>
            <input 
              class="property-input" 
              type="color" 
              :value="selectedObject.data.fill"
              @input="updateNode('fill', $event.target.value)"
            />
          </div>
          <div class="property-item">
            <div class="property-label">边框颜色</div>
            <input 
              class="property-input" 
              type="color" 
              :value="selectedObject.data.stroke"
              @input="updateNode('stroke', $event.target.value)"
            />
          </div>
          <div class="property-item">
            <div class="property-label">字体大小</div>
            <input 
              class="property-input" 
              type="number" 
              :value="selectedObject.data.fontSize"
              @input="updateNode('fontSize', parseInt($event.target.value) || 14)"
            />
          </div>
          <div class="property-item" v-if="selectedObject.data.isGroup">
            <div class="property-label">
              <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
                <input 
                  type="checkbox" 
                  :checked="selectedObject.data.collapsed"
                  @change="updateNode('collapsed', $event.target.checked)"
                />
                折叠分组
              </label>
            </div>
          </div>
        </template>

        <template v-else-if="selectedObject?.type === 'edge'">
          <div class="property-item">
            <div class="property-label">标签</div>
            <input 
              class="property-input" 
              type="text" 
              :value="selectedObject.data.label"
              @input="updateEdge('label', $event.target.value)"
            />
          </div>
          <div class="property-item">
            <div class="property-label">线条颜色</div>
            <input 
              class="property-input" 
              type="color" 
              :value="selectedObject.data.stroke"
              @input="updateEdge('stroke', $event.target.value)"
            />
          </div>
          <div class="property-item">
            <div class="property-label">线条宽度</div>
            <input 
              class="property-input" 
              type="number" 
              :value="selectedObject.data.strokeWidth"
              @input="updateEdge('strokeWidth', parseInt($event.target.value) || 2)"
            />
          </div>
          <div class="property-item">
            <div class="property-label">字体大小</div>
            <input 
              class="property-input" 
              type="number" 
              :value="selectedObject.data.fontSize"
              @input="updateEdge('fontSize', parseInt($event.target.value) || 12)"
            />
          </div>
        </template>

        <div v-else class="no-selection">
          选择节点或连线以编辑属性
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  selectedObject: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['updateNode', 'updateEdge', 'addNode'])

function updateNode(key, value) {
  emit('updateNode', props.selectedObject.data.id, { [key]: value })
}

function updateEdge(key, value) {
  emit('updateEdge', props.selectedObject.data.id, { [key]: value })
}
</script>
