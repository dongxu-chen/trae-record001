<template>
  <div class="app">
    <header class="app-header">
      <h1>📄 简历生成器</h1>
      <div class="header-actions">
        <button @click="showShareModal = true" class="share-btn">
          🔗 分享
        </button>
        <button @click="exportPDF" class="export-btn" :disabled="isExporting">
          {{ isExporting ? '导出中...' : '导出PDF' }}
        </button>
      </div>
    </header>
    
    <div class="template-selector">
      <span class="template-label">选择模板：</span>
      <button 
        v-for="template in AVAILABLE_TEMPLATES" 
        :key="template.id"
        @click="setTemplate(template.id)"
        class="template-btn"
        :class="{ active: currentTemplate === template.id }"
        :style="{ '--template-color': template.color }"
      >
        {{ template.name }}
      </button>
    </div>
    
    <div class="validation-summary" v-if="validationErrors.length > 0">
      <h4>⚠️ 请修复以下问题：</h4>
      <ul>
        <li v-for="(error, index) in validationErrors" :key="index">{{ error }}</li>
      </ul>
    </div>
    
    <div class="app-content">
      <aside class="form-panel">
        <PersonalInfoForm :personal-info="resume.personalInfo" :errors="personalInfoErrors" />
        <ExperienceForm 
          :experiences="resume.experiences" 
          :errors="experienceErrors"
          @add="addExperience" 
          @remove="removeExperience" 
          @move="moveExperience"
        />
        <SkillsForm 
          :skills="resume.skills" 
          :errors="skillErrors"
          @add="addSkill" 
          @remove="removeSkill" 
        />
      </aside>
      
      <main class="preview-panel">
        <ResumePreview ref="previewRef" :resume="resume" :template="currentTemplate" />
      </main>
    </div>
    
    <div v-if="showShareModal" class="modal-overlay" @click.self="showShareModal = false">
      <div class="modal">
        <div class="modal-header">
          <h3>🔗 分享简历</h3>
          <button @click="showShareModal = false" class="close-btn">×</button>
        </div>
        <div class="modal-body">
          <p>复制以下链接分享你的简历：</p>
          <div class="link-container">
            <input type="text" :value="shareLink" readonly ref="shareInput" />
            <button @click="copyLink" class="copy-btn">
              {{ copied ? '已复制!' : '复制' }}
            </button>
          </div>
          <p class="hint">链接包含所有简历数据，任何人打开即可查看完整简历</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import html2pdf from 'html2pdf.js'
import { useResume, AVAILABLE_TEMPLATES } from './composables/useResume'
import { validateResume } from './utils/validation.js'
import PersonalInfoForm from './components/PersonalInfoForm.vue'
import ExperienceForm from './components/ExperienceForm.vue'
import SkillsForm from './components/SkillsForm.vue'
import ResumePreview from './components/ResumePreview.vue'

const { resume, currentTemplate, addExperience, removeExperience, moveExperience, addSkill, removeSkill, setTemplate, generateShareLink, loadFromShareLink } = useResume()
const previewRef = ref(null)
const isExporting = ref(false)
const validationErrors = ref([])
const showShareModal = ref(false)
const shareInput = ref(null)
const copied = ref(false)

const shareLink = computed(() => generateShareLink())

const validationResults = computed(() => {
  return validateResume(resume)
})

const personalInfoErrors = computed(() => validationResults.value.personalInfoErrors)
const experienceErrors = computed(() => validationResults.value.experienceErrors)
const skillErrors = computed(() => validationResults.value.skillErrors)

onMounted(() => {
  loadFromShareLink()
})

const copyLink = async () => {
  try {
    await navigator.clipboard.writeText(shareLink.value)
    copied.value = true
    setTimeout(() => {
      copied.value = false
    }, 2000)
  } catch (e) {
    shareInput.value.select()
    document.execCommand('copy')
    copied.value = true
    setTimeout(() => {
      copied.value = false
    }, 2000)
  }
}

const exportPDF = async () => {
  const frontendValidation = validateResume(resume)
  
  const allErrors = [
    ...frontendValidation.personalInfoErrors,
    ...frontendValidation.experienceErrors.flat(),
    ...frontendValidation.skillErrors.flat()
  ]
  
  validationErrors.value = allErrors
  
  if (allErrors.length > 0) {
    alert(`请先修复以下 ${allErrors.length} 个问题后再导出`)
    return
  }
  
  try {
    isExporting.value = true
    validationErrors.value = []
    
    const element = previewRef.value.resumeContent
    
    const pdfStyle = document.createElement('style')
    pdfStyle.textContent = `
      * { font-family: 'Microsoft YaHei', 'SimHei', 'PingFang SC', 'Heiti SC', sans-serif !important; }
      .resume-content { 
        width: 210mm !important; 
        min-height: 297mm !important;
        padding: 20mm !important;
        box-sizing: border-box !important;
      }
    `
    element.prepend(pdfStyle)
    
    const opt = {
      margin: [0, 0, 0, 0],
      filename: '我的简历.pdf',
      image: { type: 'png', quality: 1.0 },
      html2canvas: {
        scale: 3,
        useCORS: true,
        letterRendering: true,
        allowTaint: true,
        logging: false
      },
      jsPDF: {
        unit: 'mm',
        format: 'a4',
        orientation: 'portrait',
        compress: true
      },
      pagebreak: { mode: ['avoid-all', 'css', 'legacy'] }
    }
    
    await html2pdf().set(opt).from(element).save()
    
    pdfStyle.remove()
    
  } catch (error) {
    console.error('PDF导出失败:', error)
    validationErrors.value = ['PDF导出失败，请重试']
  } finally {
    isExporting.value = false
  }
}
</script>

<style scoped>
.app {
  min-height: 100vh;
  background: #f5f7fa;
}

.app-header {
  background: linear-gradient(135deg, #4a90d9, #6ab0f3);
  color: white;
  padding: 15px 40px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 2px 10px rgba(74, 144, 217, 0.3);
}

.app-header h1 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.share-btn {
  background: rgba(255, 255, 255, 0.2);
  color: white;
  border: 1px solid rgba(255, 255, 255, 0.3);
  padding: 8px 16px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s;
}

.share-btn:hover {
  background: rgba(255, 255, 255, 0.3);
}

.export-btn {
  background: white;
  color: #4a90d9;
  border: none;
  padding: 8px 16px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.export-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.export-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.template-selector {
  background: white;
  padding: 12px 40px;
  display: flex;
  align-items: center;
  gap: 10px;
  border-bottom: 1px solid #e2e8f0;
}

.template-label {
  font-size: 14px;
  color: #666;
  font-weight: 500;
}

.template-btn {
  padding: 6px 16px;
  border: 2px solid #e2e8f0;
  background: white;
  border-radius: 20px;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.3s;
  color: #666;
}

.template-btn:hover {
  border-color: var(--template-color, #4a90d9);
  color: var(--template-color, #4a90d9);
}

.template-btn.active {
  background: var(--template-color, #4a90d9);
  border-color: var(--template-color, #4a90d9);
  color: white;
}

.validation-summary {
  background: #fff5f5;
  border: 1px solid #feb2b2;
  border-radius: 6px;
  padding: 12px 20px;
  margin: 10px 40px 0;
  color: #c53030;
}

.validation-summary h4 {
  margin: 0 0 8px 0;
  font-size: 14px;
}

.validation-summary ul {
  margin: 0;
  padding-left: 20px;
  font-size: 13px;
}

.validation-summary li {
  margin-bottom: 4px;
}

.app-content {
  display: grid;
  grid-template-columns: 400px 1fr;
  gap: 20px;
  padding: 20px;
  height: calc(100vh - 130px - (validationErrors.length > 0 ? 60px : 0));
}

.form-panel {
  overflow-y: auto;
  padding-right: 10px;
}

.form-panel::-webkit-scrollbar {
  width: 6px;
}

.form-panel::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 3px;
}

.form-panel::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 3px;
}

.form-panel::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}

.preview-panel {
  height: 100%;
  overflow-y: auto;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  background: white;
  border-radius: 12px;
  width: 90%;
  max-width: 500px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  border-bottom: 1px solid #e2e8f0;
}

.modal-header h3 {
  margin: 0;
  font-size: 18px;
  color: #333;
}

.close-btn {
  background: none;
  border: none;
  font-size: 24px;
  color: #999;
  cursor: pointer;
  line-height: 1;
}

.close-btn:hover {
  color: #666;
}

.modal-body {
  padding: 20px;
}

.modal-body p {
  margin: 0 0 15px 0;
  color: #666;
  font-size: 14px;
}

.link-container {
  display: flex;
  gap: 10px;
  margin-bottom: 15px;
}

.link-container input {
  flex: 1;
  padding: 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 13px;
  background: #f8f9fa;
}

.copy-btn {
  padding: 12px 20px;
  background: #4a90d9;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.3s;
  white-space: nowrap;
}

.copy-btn:hover {
  background: #3a7bc8;
}

.hint {
  font-size: 12px;
  color: #999;
  margin: 0;
}
</style>
