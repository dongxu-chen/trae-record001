<template>
  <div class="form-section">
    <h3>个人信息</h3>
    
    <div v-if="errors && errors.length > 0" class="error-box">
      <div v-for="(error, index) in errors" :key="index" class="error-item">
        ⚠️ {{ error }}
      </div>
    </div>
    
    <div class="form-group">
      <label>姓名 <span class="required">*</span></label>
      <input 
        v-model="personalInfo.name" 
        type="text" 
        placeholder="请输入姓名"
        maxlength="20"
      />
    </div>
    <div class="form-group">
      <label>职位 <span class="required">*</span></label>
      <input 
        v-model="personalInfo.title" 
        type="text" 
        placeholder="请输入职位"
        maxlength="50"
      />
    </div>
    <div class="form-group">
      <label>邮箱</label>
      <input 
        v-model="personalInfo.email" 
        type="email" 
        placeholder="请输入邮箱"
      />
    </div>
    <div class="form-group">
      <label>电话</label>
      <input 
        v-model="personalInfo.phone" 
        type="tel" 
        placeholder="请输入电话"
      />
    </div>
    <div class="form-group">
      <label>所在地</label>
      <input 
        v-model="personalInfo.location" 
        type="text" 
        placeholder="请输入所在地"
      />
    </div>
    <div class="form-group">
      <label>个人简介</label>
      <textarea 
        v-model="personalInfo.summary" 
        rows="4" 
        placeholder="请输入个人简介"
        maxlength="500"
      ></textarea>
      <span class="char-count">{{ personalInfo.summary?.length || 0 }}/500</span>
    </div>
  </div>
</template>

<script setup>
defineProps({
  personalInfo: {
    type: Object,
    required: true
  },
  errors: {
    type: Array,
    default: () => []
  }
})
</script>

<style scoped>
.form-section {
  background: white;
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.form-section h3 {
  margin-bottom: 15px;
  color: #333;
  font-size: 18px;
  border-bottom: 2px solid #4a90d9;
  padding-bottom: 10px;
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
  min-height: 80px;
}

.char-count {
  position: absolute;
  right: 0;
  bottom: -18px;
  font-size: 12px;
  color: #999;
}
</style>
