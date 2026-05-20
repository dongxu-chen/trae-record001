<template>
  <div class="form-section">
    <div class="section-header">
      <h3>工作经历</h3>
      <button @click="$emit('add')" class="add-btn">+ 添加</button>
    </div>
    
    <div 
      v-for="(exp, index) in experiences" 
      :key="exp.id" 
      class="experience-item"
      draggable="true"
      @dragstart="handleDragStart($event, index)"
      @dragover.prevent="handleDragOver($event, index)"
      @drop="handleDrop($event, index)"
      @dragend="handleDragEnd"
      :class="{ 'dragging': dragIndex === index, 'drag-over': dropIndex === index }"
    >
      <div class="item-header">
        <div class="drag-handle">
          <span class="item-index">{{ index + 1 }}</span>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
            <circle cx="9" cy="6" r="1.5"/>
            <circle cx="15" cy="6" r="1.5"/>
            <circle cx="9" cy="12" r="1.5"/>
            <circle cx="15" cy="12" r="1.5"/>
            <circle cx="9" cy="18" r="1.5"/>
            <circle cx="15" cy="18" r="1.5"/>
          </svg>
        </div>
        <button @click="$emit('remove', exp.id)" class="remove-btn">删除</button>
      </div>
      
      <div v-if="errors && errors[index] && errors[index].length > 0" class="error-box">
        <div v-for="(error, eIndex) in errors[index]" :key="eIndex" class="error-item">
          ⚠️ {{ error }}
        </div>
      </div>
      
      <div class="form-group">
        <label>公司名称 <span class="required">*</span></label>
        <input 
          v-model="exp.company" 
          type="text" 
          placeholder="请输入公司名称"
          maxlength="50"
        />
      </div>
      
      <div class="form-row">
        <div class="form-group">
          <label>职位 <span class="required">*</span></label>
          <input 
            v-model="exp.position" 
            type="text" 
            placeholder="请输入职位"
            maxlength="30"
          />
        </div>
      </div>
      
      <div class="form-row">
        <div class="form-group">
          <label>开始时间 <span class="required">*</span></label>
          <input 
            v-model="exp.startDate" 
            type="text" 
            placeholder="如：2021-01"
          />
        </div>
        <div class="form-group">
          <label>结束时间 <span class="required">*</span></label>
          <input 
            v-model="exp.endDate" 
            type="text" 
            placeholder="如：至今"
          />
        </div>
      </div>
      
      <div class="form-group">
        <label>工作描述</label>
        <textarea 
          v-model="exp.description" 
          rows="3" 
          placeholder="请描述工作内容和业绩"
          maxlength="300"
        ></textarea>
        <span class="char-count">{{ exp.description?.length || 0 }}/300</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

defineProps({
  experiences: {
    type: Array,
    required: true
  },
  errors: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['add', 'remove', 'move'])

const dragIndex = ref(null)
const dropIndex = ref(null)

const handleDragStart = (e, index) => {
  dragIndex.value = index
  e.dataTransfer.effectAllowed = 'move'
}

const handleDragOver = (e, index) => {
  if (dragIndex.value !== index) {
    dropIndex.value = index
  }
}

const handleDrop = (e, index) => {
  e.preventDefault()
  if (dragIndex.value !== null && dragIndex.value !== index) {
    emit('move', dragIndex.value, index)
  }
  dragIndex.value = null
  dropIndex.value = null
}

const handleDragEnd = () => {
  dragIndex.value = null
  dropIndex.value = null
}
</script>

<style scoped>
.form-section {
  background: white;
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
  border-bottom: 2px solid #4a90d9;
  padding-bottom: 10px;
}

.section-header h3 {
  color: #333;
  font-size: 18px;
  margin: 0;
}

.add-btn {
  background: #4a90d9;
  color: white;
  border: none;
  padding: 6px 16px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: background 0.3s;
}

.add-btn:hover {
  background: #3a7bc8;
}

.experience-item {
  padding: 15px;
  background: #f8f9fa;
  border-radius: 6px;
  margin-bottom: 15px;
  transition: all 0.2s ease;
  cursor: grab;
  user-select: none;
}

.experience-item:hover {
  background: #f1f3f5;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.experience-item.dragging {
  opacity: 0.5;
  cursor: grabbing;
  transform: scale(1.02);
}

.experience-item.drag-over {
  border-top: 3px solid #4a90d9;
  padding-top: 12px;
}

.experience-item:last-child {
  margin-bottom: 0;
}

.item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.drag-handle {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #666;
  cursor: grab;
}

.drag-handle:active {
  cursor: grabbing;
}

.drag-handle svg {
  opacity: 0.6;
  transition: opacity 0.2s;
}

.experience-item:hover .drag-handle svg {
  opacity: 1;
}

.item-index {
  font-weight: 600;
  color: #4a90d9;
  font-size: 14px;
}

.remove-btn {
  background: #ff4757;
  color: white;
  border: none;
  padding: 4px 12px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  transition: background 0.3s;
}

.remove-btn:hover {
  background: #ff3838;
}

.error-box {
  background: #fff5f5;
  border: 1px solid #feb2b2;
  border-radius: 6px;
  padding: 10px 15px;
  margin-bottom: 15px;
}

.error-item {
  color: #c53030;
  font-size: 13px;
  margin-bottom: 4px;
}

.error-item:last-child {
  margin-bottom: 0;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 15px;
}

.form-group {
  margin-bottom: 15px;
  position: relative;
}

.form-group label {
  display: block;
  margin-bottom: 5px;
  color: #555;
  font-size: 14px;
  font-weight: 500;
}

.form-group .required {
  color: #e53e3e;
}

.form-group input,
.form-group textarea {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
  transition: all 0.3s;
  box-sizing: border-box;
}

.form-group input:focus,
.form-group textarea:focus {
  outline: none;
  border-color: #4a90d9;
  box-shadow: 0 0 0 3px rgba(74, 144, 217, 0.1);
}

.form-group textarea {
  resize: vertical;
  min-height: 60px;
}

.char-count {
  position: absolute;
  right: 0;
  bottom: -18px;
  font-size: 12px;
  color: #999;
}
</style>
