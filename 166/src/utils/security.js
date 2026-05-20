export function escapeHtml(text) {
  if (!text) return ''
  const div = document.createElement('div')
  div.textContent = text
  return div.innerHTML
}

export function sanitizeText(text) {
  if (!text) return ''
  return text
    .replace(/<script[^>]*>[\s\S]*?<\/script>/gi, '')
    .replace(/<iframe[^>]*>[\s\S]*?<\/iframe>/gi, '')
    .replace(/javascript:/gi, '')
    .replace(/on\w+="[^"]*"/gi, '')
    .replace(/on\w+='[^']*'/gi, '')
    .trim()
}

export function validateEmail(email) {
  const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  return re.test(email)
}

export function validatePhone(phone) {
  const re = /^1[3-9]\d{9}$/
  return re.test(phone.replace(/[-\s]/g, ''))
}

export function validateName(name) {
  return name && name.trim().length >= 2 && name.trim().length <= 20
}

export function validateTitle(title) {
  return title && title.trim().length >= 2 && title.trim().length <= 50
}

export function validateSummary(summary) {
  return summary && summary.trim().length >= 10 && summary.trim().length <= 500
}

export function validateCompany(company) {
  return company && company.trim().length >= 2 && company.trim().length <= 50
}

export function validatePosition(position) {
  return position && position.trim().length >= 2 && position.trim().length <= 30
}

export function validateDateRange(startDate, endDate) {
  if (!startDate || !endDate) return false
  if (endDate === '至今') return true
  const start = new Date(startDate.replace('.', '-'))
  const end = new Date(endDate.replace('.', '-'))
  return !isNaN(start.getTime()) && !isNaN(end.getTime()) && end >= start
}

export function validateDescription(description) {
  return description && description.trim().length >= 10 && description.trim().length <= 300
}

export function validateSkillName(name) {
  return name && name.trim().length >= 1 && name.trim().length <= 30
}

export function validateSkillLevel(level) {
  return !isNaN(level) && level >= 0 && level <= 100
}
