import { reactive, ref } from 'vue'

export const AVAILABLE_TEMPLATES = [
  { id: 'default', name: '经典蓝', color: '#4a90d9' },
  { id: 'elegant', name: '优雅紫', color: '#9f7aea' },
  { id: 'modern', name: '现代绿', color: '#38b2ac' },
  { id: 'professional', name: '专业灰', color: '#718096' }
]

export function useResume() {
  const currentTemplate = ref('default')
  
  const resume = reactive({
    personalInfo: {
      name: '张三',
      title: '前端开发工程师',
      email: 'zhangsan@example.com',
      phone: '138-0000-0000',
      location: '北京市',
      summary: '拥有5年前端开发经验，熟悉Vue、React等主流框架，热爱技术，追求卓越。'
    },
    experiences: [
      {
        id: 1,
        company: '某某科技有限公司',
        position: '高级前端工程师',
        startDate: '2021-01',
        endDate: '至今',
        description: '负责公司核心产品的前端开发与维护，带领团队完成多个重要项目。'
      }
    ],
    skills: [
      { id: 1, name: 'Vue.js', level: 90 },
      { id: 2, name: 'React', level: 80 },
      { id: 3, name: 'JavaScript', level: 95 },
      { id: 4, name: 'CSS/SCSS', level: 85 }
    ]
  })

  const addExperience = () => {
    resume.experiences.push({
      id: Date.now(),
      company: '',
      position: '',
      startDate: '',
      endDate: '',
      description: ''
    })
  }

  const removeExperience = (id) => {
    const index = resume.experiences.findIndex(exp => exp.id === id)
    if (index > -1) {
      resume.experiences.splice(index, 1)
    }
  }

  const moveExperience = (fromIndex, toIndex) => {
    const item = resume.experiences.splice(fromIndex, 1)[0]
    resume.experiences.splice(toIndex, 0, item)
  }

  const addSkill = () => {
    resume.skills.push({
      id: Date.now(),
      name: '',
      level: 50
    })
  }

  const removeSkill = (id) => {
    const index = resume.skills.findIndex(skill => skill.id === id)
    if (index > -1) {
      resume.skills.splice(index, 1)
    }
  }

  const setTemplate = (templateId) => {
    if (AVAILABLE_TEMPLATES.find(t => t.id === templateId)) {
      currentTemplate.value = templateId
    }
  }

  const generateShareLink = () => {
    const resumeData = {
      template: currentTemplate.value,
      data: JSON.parse(JSON.stringify(resume))
    }
    const encoded = btoa(encodeURIComponent(JSON.stringify(resumeData)))
    return `${window.location.origin}${window.location.pathname}#share=${encoded}`
  }

  const loadFromShareLink = () => {
    const hash = window.location.hash
    if (hash.startsWith('#share=')) {
      try {
        const encoded = hash.replace('#share=', '')
        const decoded = JSON.parse(decodeURIComponent(atob(encoded)))
        if (decoded.template) {
          currentTemplate.value = decoded.template
        }
        if (decoded.data) {
          Object.assign(resume, decoded.data)
        }
        return true
      } catch (e) {
        console.error('Failed to load share data:', e)
        return false
      }
    }
    return false
  }

  return {
    resume,
    currentTemplate,
    addExperience,
    removeExperience,
    moveExperience,
    addSkill,
    removeSkill,
    setTemplate,
    generateShareLink,
    loadFromShareLink
  }
}
