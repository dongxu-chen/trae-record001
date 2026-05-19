<template>
  <div class="form-section">
    <div class="section-header">
      <h3>专业技能</h3>
      <button @click="$emit('add')" class="add-btn">+ 添加</button>
    </div>
    
    <div v-for="(skill, index) in skills" :key="skill.id" class="skill-item">
      <div class="skill-header">
        <span class="skill-index">技能 {{ index + 1 }}</span>
        <button @click="$emit('remove', skill.id)" class="remove-btn">删除</button>
      </div>
      
      <div v-if="errors && errors[index] && errors[index].length > 0" class="error-box">
        <div v-for="(error, eIndex) in errors[index]" :key="eIndex" class="error-item">
          ⚠️ {{ error }}
        </div>
      </div>
      
      <div class="form-row">
        <div class="form-group">
          <label>技能名称 <span class="required">*</span></label>
          <input 
            v-model="skill.name" 
            type="text" 
            placeholder="如：Vue.js"
            maxlength="30"
          />
        </div>
        <div class="form-group">
          <label>熟练程度: {{ skill.level }}%</label>
          <input 
            v-model.number="skill.level" 
            type="range" 
            min="0" 
            max="100" 
            step="5"
            class="skill-range"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  skills: {
    type: Array,
    required: true
  },
  errors: {
    type: Array,
    default: () => []
  }
})

defineEmits(['add', 'remove'])
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

.skill-item {
  padding: 15px;
  background: #f8f9fa;
  border-radius: 6px;
  margin-bottom: 15px;
}

.skill-item:last-child {
  margin-bottom: 0;
}

.skill-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.skill-index {
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
  margin-bottom: 0;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  color: #555;
  font-size: 14px;
  font-weight: 500;
}

.form-group .required {
  color: #e53e3e;
}

.form-group input[type="text"] {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
  transition: all 0.3s;
  box-sizing: border-box;
}

.form-group input[type="text"]:focus {
  outline: none;
  border-color: #4a90d9;
  box-shadow: 0 0 0 3px rgba(74, 144, 217, 0.1);
}

.skill-range {
  width: 100%;
  height: 8px;
  border-radius: 4px;
  background: #ddd;
  outline: none;
  -webkit-appearance: none;
  cursor: pointer;
}

.skill-range::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #4a90d9;
  cursor: pointer;
  transition: background 0.3s;
}

.skill-range::-webkit-slider-thumb:hover {
  background: #3a7bc8;
}
</style>
