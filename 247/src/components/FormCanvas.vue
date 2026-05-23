<template>
  <div class="canvas-container">
    <div class="canvas" ref="canvasRef">
      <div v-if="formItems.length === 0" class="canvas-placeholder">
        从左侧拖拽组件到此处
      </div>
      <div
        v-for="(item, index) in formItems"
        :key="item.id"
        class="form-item-wrapper"
        :class="{ 
          selected: selectedId === item.id,
          'form-item-hidden': isItemHidden(item)
        }"
        :data-id="item.id"
        @click="selectItem(item, $event)"
      >
        <button class="delete-btn" @click.stop="deleteItem(index)">×</button>
        <div class="form-item-content">
          <label class="form-label">
            <span v-if="item.required" class="required">*</span>
            {{ item.label }}
          </label>
          
          <input
            v-if="item.type === 'input'"
            type="text"
            class="form-input"
            :placeholder="item.placeholder"
            :value="item.defaultValue"
            readonly
          />
          
          <textarea
            v-else-if="item.type === 'textarea'"
            class="form-input"
            :placeholder="item.placeholder"
            :value="item.defaultValue"
            readonly
            rows="3"
          ></textarea>
          
          <input
            v-else-if="item.type === 'number'"
            type="number"
            class="form-input"
            :placeholder="item.placeholder"
            :min="item.min"
            :max="item.max"
            :step="item.step"
            :value="item.defaultValue"
            readonly
          />
          
          <input
            v-else-if="item.type === 'date'"
            type="date"
            class="form-input"
            :value="item.defaultValue"
            readonly
          />
          
          <div v-else-if="item.type === 'radio'" class="form-radio-group">
            <label v-for="opt in item.options" :key="opt.value" class="form-radio">
              <input type="radio" :name="'radio_' + item.id" disabled />
              {{ opt.label }}
            </label>
          </div>
          
          <div v-else-if="item.type === 'checkbox'" class="form-checkbox-group">
            <label v-for="opt in item.options" :key="opt.value" class="form-checkbox">
              <input type="checkbox" disabled />
              {{ opt.label }}
            </label>
          </div>
          
          <select v-else-if="item.type === 'select'" class="form-select" disabled>
            <option value="">{{ item.placeholder || '请选择' }}</option>
            <option v-for="opt in item.options" :key="opt.value" :value="opt.value">
              {{ opt.label }}
            </option>
          </select>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted, computed } from 'vue'
import Sortable from 'sortablejs'
import { evaluateExpression, generateLinkageExpression } from './ExpressionParser.js'

const props = defineProps({
  formItems: {
    type: Array,
    default: () => []
  },
  selectedId: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['selectItem', 'deleteItem', 'update:formItems'])

const canvasRef = ref(null)
let sortable = null

const selectItem = (item, e) => {
  e.stopPropagation()
  emit('selectItem', item.id)
}

const deleteItem = (index) => {
  const newItems = [...props.formItems]
  newItems.splice(index, 1)
  emit('update:formItems', newItems)
}

const formDataContext = computed(() => {
  const context = {}
  props.formItems.forEach(item => {
    context[item.field] = item.defaultValue || ''
  })
  return { formData: context }
})

const isItemHidden = (item) => {
  if (!item.linkage?.enabled || !item.linkage.rules?.length) return false
  
  for (const rule of item.linkage.rules) {
    const expression = generateLinkageExpression(rule, props.formItems)
    if (!expression) continue
    
    const isMatch = evaluateExpression(expression, formDataContext.value)
    if (isMatch) {
      return rule.action === 'hide'
    }
  }
  
  return false
}

const initSortable = () => {
  if (!canvasRef.value) return
  
  sortable = Sortable.create(canvasRef.value.querySelector('.canvas'), {
    animation: 150,
    handle: '.form-item-wrapper',
    ghostClass: 'sortable-ghost',
    chosenClass: 'sortable-chosen',
    draggable: '.form-item-wrapper',
    onEnd: (evt) => {
      const { oldIndex, newIndex } = evt
      if (oldIndex === newIndex) return
      
      const newItems = [...props.formItems]
      const [removed] = newItems.splice(oldIndex, 1)
      newItems.splice(newIndex, 0, removed)
      emit('update:formItems', newItems)
    }
  })
}

onMounted(() => {
  initSortable()
})

onUnmounted(() => {
  if (sortable) {
    sortable.destroy()
  }
})

watch(() => props.formItems, () => {
  if (sortable) {
    sortable.destroy()
  }
  setTimeout(initSortable, 100)
}, { deep: true })
</script>
