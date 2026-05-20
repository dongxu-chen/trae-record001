import {
  validateName,
  validateTitle,
  validateEmail,
  validatePhone,
  validateSummary,
  validateCompany,
  validatePosition,
  validateDateRange,
  validateDescription,
  validateSkillName,
  validateSkillLevel
} from './security.js'

export function validatePersonalInfo(personalInfo) {
  const errors = []
  
  if (!validateName(personalInfo.name)) {
    errors.push('姓名长度应在2-20个字符之间')
  }
  
  if (!validateTitle(personalInfo.title)) {
    errors.push('职位长度应在2-50个字符之间')
  }
  
  if (personalInfo.email && !validateEmail(personalInfo.email)) {
    errors.push('请输入有效的邮箱地址')
  }
  
  if (personalInfo.phone && !validatePhone(personalInfo.phone)) {
    errors.push('请输入有效的手机号码')
  }
  
  if (personalInfo.summary && !validateSummary(personalInfo.summary)) {
    errors.push('个人简介长度应在10-500个字符之间')
  }
  
  return errors
}

export function validateExperience(exp) {
  const errors = []
  
  if (!validateCompany(exp.company)) {
    errors.push('公司名称长度应在2-50个字符之间')
  }
  
  if (!validatePosition(exp.position)) {
    errors.push('职位长度应在2-30个字符之间')
  }
  
  if (!validateDateRange(exp.startDate, exp.endDate)) {
    errors.push('请输入有效的开始和结束时间（如：2021-01），结束时间需大于开始时间')
  }
  
  if (exp.description && !validateDescription(exp.description)) {
    errors.push('工作描述长度应在10-300个字符之间')
  }
  
  return errors
}

export function validateSkill(skill) {
  const errors = []
  
  if (!validateSkillName(skill.name)) {
    errors.push('技能名称长度应在1-30个字符之间')
  }
  
  if (!validateSkillLevel(skill.level)) {
    errors.push('熟练程度应在0-100之间')
  }
  
  return errors
}

export function validateResume(resume) {
  const personalInfoErrors = validatePersonalInfo(resume.personalInfo || {})
  
  const experienceErrors = (resume.experiences || []).map(exp => validateExperience(exp))
  
  const skillErrors = (resume.skills || []).map(skill => validateSkill(skill))
  
  return {
    personalInfoErrors,
    experienceErrors,
    skillErrors
  }
}

export async function validateResumeAsync(resume) {
  return new Promise((resolve) => {
    setTimeout(() => {
      const forbiddenWords = ['测试敏感词', '违法内容', '违规词汇']
      
      const backendErrors = []
      
      const checkText = (text) => {
        if (!text) return false
        return forbiddenWords.some(word => text.includes(word))
      }
      
      if (checkText(resume.personalInfo?.name)) {
        backendErrors.push('姓名包含敏感词汇')
      }
      if (checkText(resume.personalInfo?.title)) {
        backendErrors.push('职位包含敏感词汇')
      }
      if (checkText(resume.personalInfo?.summary)) {
        backendErrors.push('个人简介包含敏感词汇')
      }
      
      resume.experiences?.forEach((exp, index) => {
        if (checkText(exp.company)) {
          backendErrors.push(`工作经历${index + 1} - 公司名称包含敏感词汇`)
        }
        if (checkText(exp.position)) {
          backendErrors.push(`工作经历${index + 1} - 职位包含敏感词汇`)
        }
        if (checkText(exp.description)) {
          backendErrors.push(`工作经历${index + 1} - 描述包含敏感词汇`)
        }
      })
      
      resume.skills?.forEach((skill, index) => {
        if (checkText(skill.name)) {
          backendErrors.push(`技能${index + 1} - 名称包含敏感词汇`)
        }
      })
      
      resolve({
        valid: backendErrors.length === 0,
        errors: backendErrors
      })
    }, 1000)
  })
}
