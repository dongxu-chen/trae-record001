import type { ValidationRule, ValidationResult } from '@/types/table'

export function validateValue(
  value: unknown,
  rules?: ValidationRule
): ValidationResult {
  if (!rules) {
    return { isValid: true }
  }

  const stringValue = String(value ?? '')
  const numValue = Number(value)

  if (rules.required && (!value || stringValue.trim() === '')) {
    return { isValid: false, error: '此字段为必填项' }
  }

  if (rules.min !== undefined && !isNaN(numValue) && numValue < rules.min) {
    return { isValid: false, error: `值不能小于 ${rules.min}` }
  }

  if (rules.max !== undefined && !isNaN(numValue) && numValue > rules.max) {
    return { isValid: false, error: `值不能大于 ${rules.max}` }
  }

  if (rules.minLength !== undefined && stringValue.length < rules.minLength) {
    return { isValid: false, error: `长度不能少于 ${rules.minLength} 个字符` }
  }

  if (rules.maxLength !== undefined && stringValue.length > rules.maxLength) {
    return { isValid: false, error: `长度不能超过 ${rules.maxLength} 个字符` }
  }

  if (rules.pattern && !rules.pattern.test(stringValue)) {
    return { isValid: false, error: '格式不正确' }
  }

  if (rules.custom) {
    const customResult = rules.custom(value)
    if (customResult !== true) {
      return {
        isValid: false,
        error: typeof customResult === 'string' ? customResult : '验证失败',
      }
    }
  }

  return { isValid: true }
}

export const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

export const urlPattern = /^(https?:\/\/)?([\da-z.-]+)\.([a-z.]{2,6})([\/\w .-]*)*\/?$/

export const phonePattern = /^1[3-9]\d{9}$/

export function validateEmail(email: string): ValidationResult {
  if (!emailPattern.test(email)) {
    return { isValid: false, error: '请输入有效的邮箱地址' }
  }
  return { isValid: true }
}

export function validateSalary(salary: number): ValidationResult {
  if (isNaN(salary) || salary < 0) {
    return { isValid: false, error: '薪资必须为正数' }
  }
  if (salary > 1000000) {
    return { isValid: false, error: '薪资不能超过 1,000,000' }
  }
  return { isValid: true }
}

export function validatePerformance(performance: number): ValidationResult {
  if (isNaN(performance) || performance < 0 || performance > 100) {
    return { isValid: false, error: '绩效必须在 0-100 之间' }
  }
  return { isValid: true }
}

export function validateDate(dateStr: string): ValidationResult {
  const date = new Date(dateStr)
  if (isNaN(date.getTime())) {
    return { isValid: false, error: '请输入有效的日期' }
  }
  const minDate = new Date('2000-01-01')
  const maxDate = new Date()
  if (date < minDate) {
    return { isValid: false, error: '日期不能早于 2000-01-01' }
  }
  if (date > maxDate) {
    return { isValid: false, error: '日期不能晚于今天' }
  }
  return { isValid: true }
}
