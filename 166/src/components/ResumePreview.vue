<template>
  <div class="preview-section">
    <div class="preview-header">
      <h3>简历预览</h3>
    </div>
    
    <div ref="resumeContent" class="resume-content" :class="[`template-${template}`]">
      <div class="resume-header">
        <h1>{{ safeResume.personalInfo.name || '姓名'}}</h1>
        <p class="title">{{ safeResume.personalInfo.title || '职位'}}</p>
        <div class="contact-info">
          <span v-if="safeResume.personalInfo.email">📧 {{ safeResume.personalInfo.email }}</span>
          <span v-if="safeResume.personalInfo.phone">📱 {{ safeResume.personalInfo.phone }}</span>
          <span v-if="safeResume.personalInfo.location">📍 {{ safeResume.personalInfo.location }}</span>
        </div>
        <p v-if="safeResume.personalInfo.summary" class="summary">{{ safeResume.personalInfo.summary }}</p>
      </div>
      
      <div v-if="safeResume.experiences && safeResume.experiences.length > 0" class="resume-section">
        <h2>工作经历</h2>
        <div v-for="exp in safeResume.experiences" :key="exp.id" class="experience-item">
          <div class="exp-header">
          <h3>{{ exp.company || '公司名称' }}</h3>
          <span class="date">{{ exp.startDate }} - {{ exp.endDate }}</span>
          </div>
          <p class="position">{{ exp.position || '职位' }}</p>
          <p v-if="exp.description" class="description">{{ exp.description }}</p>
        </div>
      </div>
      
      <div v-if="safeResume.skills && safeResume.skills.length > 0" class="resume-section">
        <h2>专业技能</h2>
        <div class="skills-grid">
          <div v-for="skill in safeResume.skills" :key="skill.id" class="skill-item">
            <span class="skill-name">{{ skill.name || '技能名称' }}</span>
            <div class="skill-bar">
              <div class="skill-fill" :style="{ width: Math.max(0, Math.min(100, skill.level)) + '%' }"></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { escapeHtml, sanitizeText } from '../utils/security.js'

const props = defineProps({
  resume: {
    type: Object,
    required: true
  },
  template: {
    type: String,
    default: 'default'
  }
})

const safeResume = computed(() => {
  const safe = {
    personalInfo: {},
    experiences: [],
    skills: []
  }
  
  if (props.resume.personalInfo) {
    safe.personalInfo = {
      name: escapeHtml(sanitizeText(props.resume.personalInfo.name || '')),
      title: escapeHtml(sanitizeText(props.resume.personalInfo.title || '')),
      email: escapeHtml(sanitizeText(props.resume.personalInfo.email || '')),
      phone: escapeHtml(sanitizeText(props.resume.personalInfo.phone || '')),
      location: escapeHtml(sanitizeText(props.resume.personalInfo.location || '')),
      summary: escapeHtml(sanitizeText(props.resume.personalInfo.summary || ''))
    }
  }
  
  if (props.resume.experiences && Array.isArray(props.resume.experiences)) {
    safe.experiences = props.resume.experiences.map(exp => ({
      id: exp.id,
      company: escapeHtml(sanitizeText(exp.company || '')),
      position: escapeHtml(sanitizeText(exp.position || '')),
      startDate: escapeHtml(sanitizeText(exp.startDate || '')),
      endDate: escapeHtml(sanitizeText(exp.endDate || '')),
      description: escapeHtml(sanitizeText(exp.description || ''))
    }))
  }
  
  if (props.resume.skills && Array.isArray(props.resume.skills)) {
    safe.skills = props.resume.skills.map(skill => ({
      id: skill.id,
      name: escapeHtml(sanitizeText(skill.name || '')),
      level: Math.max(0, Math.min(100, Number(skill.level) || 0))
    }))
  }
  
  return safe
})

const resumeContent = ref(null)

defineExpose({
  resumeContent
})
</script>

<style scoped>
.preview-section {
  background: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  height: 100%;
  overflow-y: auto;
}

.preview-header {
  margin-bottom: 20px;
  padding-bottom: 10px;
  border-bottom: 2px solid #4a90d9;
}

.preview-header h3 {
  color: #333;
  font-size: 18px;
  margin: 0;
}

.resume-content {
  background: white;
  padding: 40px;
  min-height: 800px;
  width: 210mm;
  margin: 0 auto;
  box-sizing: border-box;
  font-family: 'Microsoft YaHei', 'SimHei', 'PingFang SC', 'Heiti SC', sans-serif;
}

/* 经典蓝模板 */
.template-default .resume-header {
  text-align: center;
  margin-bottom: 30px;
  padding-bottom: 20px;
  border-bottom: 2px solid #4a90d9;
}

.template-default .resume-header h1 {
  font-size: 32px;
  color: #222;
  margin-bottom: 10px;
  font-weight: bold;
}

.template-default .resume-header .title {
  font-size: 18px;
  color: #4a90d9;
  margin-bottom: 15px;
  font-weight: 500;
}

.template-default .resume-section h2 {
  font-size: 18px;
  color: #333;
  margin-bottom: 15px;
  padding-bottom: 8px;
  border-bottom: 1px solid #4a90d9;
  font-weight: bold;
}

.template-default .skill-fill {
  background: linear-gradient(90deg, #4a90d9, #6ab0f3);
}

/* 优雅紫模板 */
.template-elegant .resume-header {
  background: linear-gradient(135deg, #9f7aea, #805ad5);
  color: white;
  padding: 30px;
  border-radius: 8px;
  margin-bottom: 30px;
  text-align: center;
}

.template-elegant .resume-header h1 {
  font-size: 32px;
  margin-bottom: 10px;
  font-weight: bold;
}

.template-elegant .resume-header .title {
  font-size: 18px;
  margin-bottom: 15px;
  font-weight: 500;
  opacity: 0.9;
}

.template-elegant .contact-info {
  color: rgba(255, 255, 255, 0.9);
}

.template-elegant .summary {
  color: rgba(255, 255, 255, 0.85);
  margin-top: 15px;
}

.template-elegant .resume-section h2 {
  font-size: 18px;
  color: #9f7aea;
  margin-bottom: 15px;
  padding-bottom: 8px;
  border-bottom: 2px solid #9f7aea;
  font-weight: bold;
}

.template-elegant .experience-item h3 {
  color: #805ad5;
}

.template-elegant .position {
  color: #9f7aea;
}

.template-elegant .skill-fill {
  background: linear-gradient(90deg, #9f7aea, #805ad5);
}

/* 现代绿模板 */
.template-modern .resume-header {
  display: flex;
  align-items: center;
  gap: 30px;
  margin-bottom: 30px;
  padding: 25px;
  background: #f7fffc;
  border-radius: 8px;
  border-left: 4px solid #38b2ac;
}

.template-modern .resume-header h1 {
  font-size: 32px;
  color: #222;
  margin-bottom: 8px;
  font-weight: bold;
}

.template-modern .resume-header .title {
  font-size: 18px;
  color: #38b2ac;
  font-weight: 500;
}

.template-modern .contact-info {
  margin-left: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-size: 13px;
}

.template-modern .summary {
  display: none;
}

.template-modern .resume-section h2 {
  font-size: 18px;
  color: #38b2ac;
  margin-bottom: 15px;
  font-weight: bold;
  position: relative;
  padding-left: 20px;
}

.template-modern .resume-section h2::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 10px;
  height: 10px;
  background: #38b2ac;
  border-radius: 50%;
}

.template-modern .experience-item {
  padding-left: 20px;
  border-left: 2px solid #81e6d9;
  margin-left: 4px;
}

.template-modern .skill-fill {
  background: linear-gradient(90deg, #38b2ac, #81e6d9);
}

/* 专业灰模板 */
.template-professional .resume-header {
  text-align: left;
  margin-bottom: 30px;
  padding: 20px 0;
  border-top: 4px solid #718096;
  border-bottom: 1px solid #e2e8f0;
}

.template-professional .resume-header h1 {
  font-size: 36px;
  color: #2d3748;
  margin-bottom: 5px;
  font-weight: 700;
  letter-spacing: 2px;
}

.template-professional .resume-header .title {
  font-size: 16px;
  color: #718096;
  text-transform: uppercase;
  letter-spacing: 3px;
  font-weight: 500;
}

.template-professional .contact-info {
  justify-content: flex-start;
  margin-top: 15px;
  color: #4a5568;
}

.template-professional .summary {
  margin-top: 20px;
  color: #4a5568;
  line-height: 1.8;
}

.template-professional .resume-section h2 {
  font-size: 16px;
  color: #2d3748;
  margin-bottom: 15px;
  text-transform: uppercase;
  letter-spacing: 2px;
  font-weight: 700;
}

.template-professional .experience-item h3 {
  color: #2d3748;
  font-size: 16px;
}

.template-professional .position {
  color: #718096;
  font-weight: 600;
}

.template-professional .date {
  color: #a0aec0;
  font-weight: 500;
}

.template-professional .skill-fill {
  background: linear-gradient(90deg, #4a5568, #718096);
}

.contact-info {
  display: flex;
  justify-content: center;
  gap: 20px;
  flex-wrap: wrap;
  font-size: 14px;
  color: #666;
  margin-bottom: 15px;
}

.resume-section {
  margin-bottom: 25px;
}

.experience-item {
  margin-bottom: 20px;
}

.experience-item:last-child {
  margin-bottom: 0;
}

.exp-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 5px;
}

.exp-header h3 {
  font-size: 16px;
  color: #333;
  margin: 0;
  font-weight: 600;
}

.exp-header .date {
  font-size: 14px;
  color: #666;
}

.experience-item .position {
  font-size: 14px;
  color: #4a90d9;
  font-weight: 500;
  margin-bottom: 8px;
}

.experience-item .description {
  font-size: 14px;
  color: #555;
  line-height: 1.8;
}

.skills-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 15px;
}

.skill-item {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.skill-name {
  font-size: 14px;
  color: #333;
  font-weight: 500;
}

.skill-bar {
  height: 8px;
  background: #eee;
  border-radius: 4px;
  overflow: hidden;
}

.skill-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.3s;
}
</style>
