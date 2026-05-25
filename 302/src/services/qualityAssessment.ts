import { LanguageCode, QualityAssessment, QualityScore, QualityIssue } from '../types'
import { termDB, calculateSimilarity, tokenize } from './database'

const generateIssueId = (): string => `issue_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`

const grammarPatterns: Record<string, Array<{ pattern: RegExp; message: string; suggestion?: string }>> = {
  en: [
    { pattern: /\s+[.,!?;:]/g, message: '标点符号前不应有空格', suggestion: '移除标点前的空格' },
    { pattern: /[.,!?;:](?=[a-zA-Z])/g, message: '标点符号后应有空格', suggestion: '在标点后添加空格' },
    { pattern: /\bi\s+/g, message: '第一人称"I"应大写', suggestion: '将"i"改为"I"' },
    { pattern: /\s{2,}/g, message: '存在多余空格', suggestion: '移除多余空格' },
    { pattern: /[a-z]+(?=[A-Z])/g, message: '可能缺少空格或标点', suggestion: '检查单词分隔' },
    { pattern: /\b(an)\s+[aeiou]/i, message: '冠词使用可能不正确', suggestion: '考虑使用"a"还是"an"' },
    { pattern: /\b(its)\s+it's\b/i, message: '"its"与"it\'s"混淆', suggestion: '检查所有格与缩写的正确使用' },
    { pattern: /\b(there)\s+(their|they're)\b/i, message: '同音词混淆', suggestion: '检查"there/their/they\'re"的正确使用' },
    { pattern: /\b(your)\s+(you're)\b/i, message: '"your"与"you\'re"混淆', suggestion: '检查所有格与缩写的正确使用' },
  ],
  zh: [
    { pattern: /[，。！？；：]\s+/g, message: '中文标点后不应有空格', suggestion: '移除标点后的空格' },
    { pattern: /\s+[，。！？；：]/g, message: '中文标点前不应有空格', suggestion: '移除标点前的空格' },
    { pattern: /[a-zA-Z]+[\u4e00-\u9fa5]/g, message: '英文与中文之间缺少空格', suggestion: '在中英文之间添加空格' },
    { pattern: /[\u4e00-\u9fa5]+[a-zA-Z]/g, message: '中文与英文之间缺少空格', suggestion: '在中英文之间添加空格' },
    { pattern: /[。！？]{2,}/g, message: '标点重复使用', suggestion: '检查标点使用' },
    { pattern: /\s{2,}/g, message: '存在多余空格', suggestion: '移除多余空格' },
    { pattern: /[，,]/g, message: '中英文标点混用', suggestion: '统一使用中文标点' },
  ],
  ja: [
    { pattern: /[。！？、；：]\s+/g, message: '日文标点后不应有空格', suggestion: '移除标点后的空格' },
    { pattern: /\s+[。！？、；：]/g, message: '日文标点前不应有空格', suggestion: '移除标点前的空格' },
    { pattern: /[a-zA-Z]+[\u3040-\u30ff\u4e00-\u9fa5]/g, message: '英文与日文之间缺少空格', suggestion: '在英日文之间添加空格' },
    { pattern: /\s{2,}/g, message: '存在多余空格', suggestion: '移除多余空格' },
  ],
  ko: [
    { pattern: /[。！？，；：]\s+/g, message: '韩文标点后不应有空格', suggestion: '移除标点后的空格' },
    { pattern: /\s+[。！？，；：]/g, message: '韩文标点前不应有空格', suggestion: '移除标点前的空格' },
    { pattern: /\s{2,}/g, message: '存在多余空格', suggestion: '移除多余空格' },
  ],
  fr: [
    { pattern: /\s+[.,!?;:]/g, message: '标点符号前不应有空格', suggestion: '移除标点前的空格' },
    { pattern: /[.,!?;:](?=[a-zA-Z])/g, message: '标点符号后应有空格', suggestion: '在标点后添加空格' },
    { pattern: /\s{2,}/g, message: '存在多余空格', suggestion: '移除多余空格' },
    { pattern: /\b[lL]e\s+[aeiouàâäéèêëîïôöùûü]/i, message: '冠词可能需要缩合', suggestion: '考虑使用"l\'"' },
  ],
  de: [
    { pattern: /\s+[.,!?;:]/g, message: '标点符号前不应有空格', suggestion: '移除标点前的空格' },
    { pattern: /[.,!?;:](?=[a-zA-Z])/g, message: '标点符号后应有空格', suggestion: '在标点后添加空格' },
    { pattern: /\s{2,}/g, message: '存在多余空格', suggestion: '移除多余空格' },
    { pattern: /\b(der|die|das)\s+[aeiou]/i, message: '可能需要使用变格形式', suggestion: '检查冠词变格' },
  ],
}

const formalPhrases: Record<string, string[]> = {
  zh: ['请', '您', '贵', '敬', '谨', '特此', '恳请', '承蒙', '不胜感激', '顺祝商祺'],
  en: ['please', 'would you', 'could you', 'kindly', 'sincerely', 'respectfully', 'grateful', 'appreciate'],
  ja: ['お願いします', 'です', 'ます', 'ございます', 'いただきます', 'よろしくお願いいたします'],
  ko: ['습니다', '합니다', '입니다', '시겠습니까', '주시겠습니까', '감사합니다'],
  fr: ['veuillez', 's\'il vous plaît', 'je vous prie', 'nous vous serions', 'cordialement'],
  de: ['bitte', 'würden Sie', 'könnten Sie', 'ich bitte Sie', 'mit freundlichen Grüßen'],
}

const casualPhrases: Record<string, string[]> = {
  zh: ['嘿', '嗨', '哦', '啦', '呗', '嘛', '呢', '吧', '亲', '么么哒'],
  en: ['hey', 'hi', 'yo', 'guys', 'wanna', 'gonna', 'gotta', 'cool', 'awesome'],
  ja: ['だよ', 'ね', 'よ', 'ちゃん', 'くん', 'だって', 'なんか'],
  ko: ['야', '너', '나', '해', '돼', '고', '야호', '헤이'],
  fr: ['salut', 'hey', 't\'es', 't\'as', 'on va', 'génial', 'super'],
  de: ['hey', 'hi', 'du', 'deine', 'dein', 'geil', 'krass', 'super'],
}

const technicalTerms: Record<string, string[]> = {
  zh: ['接口', '模块', '算法', '框架', '架构', '缓存', '集群', '负载均衡', '微服务'],
  en: ['interface', 'module', 'algorithm', 'framework', 'architecture', 'cache', 'cluster', 'microservice', 'API'],
  ja: ['インターフェース', 'モジュール', 'アルゴリズム', 'フレームワーク', 'アーキテクチャ'],
  ko: ['인터페이스', '모듈', '알고리즘', '프레임워크', '아키텍처'],
  fr: ['interface', 'module', 'algorithme', 'framework', 'architecture'],
  de: ['Interface', 'Modul', 'Algorithmus', 'Framework', 'Architektur'],
}

export const evaluateFluency = (text: string, lang: LanguageCode): { score: number; issues: QualityIssue[] } => {
  let score = 100
  const issues: QualityIssue[] = []
  
  const patterns = grammarPatterns[lang] || grammarPatterns.en
  
  for (const rule of patterns) {
    const matches = text.match(rule.pattern)
    if (matches) {
      const penalty = Math.min(15, matches.length * 3)
      score -= penalty
      
      matches.forEach(match => {
        const index = text.indexOf(match)
        if (index !== -1) {
          issues.push({
            id: generateIssueId(),
            type: 'grammar',
            severity: penalty > 5 ? 'medium' : 'low',
            message: rule.message,
            suggestion: rule.suggestion,
            targetText: match,
            startIndex: index,
            endIndex: index + match.length,
          })
        }
      })
    }
  }
  
  const sentences = text.split(/[.!?。！？]/).filter(s => s.trim())
  if (sentences.length > 0) {
    const avgLength = sentences.reduce((sum, s) => sum + s.trim().length, 0) / sentences.length
    
    if (avgLength > 80) {
      score -= 10
      issues.push({
        id: generateIssueId(),
        type: 'fluency',
        severity: 'medium',
        message: '存在过长句子，可能影响可读性',
        suggestion: '建议将长句子拆分为多个短句',
      })
    }
    
    if (avgLength < 10 && sentences.length > 5) {
      score -= 5
      issues.push({
        id: generateIssueId(),
        type: 'fluency',
        severity: 'low',
        message: '句子过短，可能影响阅读流畅性',
        suggestion: '考虑适当合并短句',
      })
    }
  }
  
  if (text.length > 0) {
    const uniqChars = new Set(text.toLowerCase()).size
    const ratio = uniqChars / text.length
    if (ratio < 0.1) {
      score -= 20
      issues.push({
        id: generateIssueId(),
        type: 'fluency',
        severity: 'high',
        message: '文本重复度极高，可能存在质量问题',
        suggestion: '检查是否存在重复内容或乱码',
      })
    }
  }
  
  const paragraphCount = text.split(/\n\n+/).length
  if (text.length > 500 && paragraphCount < 2) {
    score -= 8
    issues.push({
      id: generateIssueId(),
      type: 'fluency',
      severity: 'low',
      message: '长文本缺少段落分隔',
      suggestion: '建议按逻辑分段，提升可读性',
    })
  }
  
  return { score: Math.max(0, Math.min(100, score)), issues }
}

export const evaluateFidelity = async (
  sourceText: string,
  translatedText: string,
  sourceLang: LanguageCode,
  targetLang: LanguageCode
): Promise<{ score: number; issues: QualityIssue[] }> => {
  let score = 100
  const issues: QualityIssue[] = []
  
  const sourceTokens = tokenize(sourceText, sourceLang)
  const targetTokens = tokenize(translatedText, targetLang)
  
  const sourceLength = sourceText.length
  const targetLength = translatedText.length
  const lengthRatio = targetLength / sourceLength
  
  const expectedRatios: Record<LanguageCode, Record<LanguageCode, [number, number]>> = {
    zh: { en: [0.6, 1.4], ja: [0.7, 1.5], ko: [0.7, 1.5], fr: [0.5, 1.3], de: [0.5, 1.3], zh: [0.8, 1.2] },
    en: { zh: [0.7, 1.6], ja: [0.8, 1.6], ko: [0.8, 1.6], fr: [0.7, 1.4], de: [0.7, 1.4], en: [0.8, 1.2] },
    ja: { zh: [0.7, 1.5], en: [0.6, 1.4], ko: [0.8, 1.5], fr: [0.6, 1.3], de: [0.6, 1.3], ja: [0.8, 1.2] },
    ko: { zh: [0.7, 1.5], en: [0.6, 1.4], ja: [0.7, 1.5], fr: [0.6, 1.3], de: [0.6, 1.3], ko: [0.8, 1.2] },
    fr: { zh: [0.8, 1.8], en: [0.7, 1.4], ja: [0.8, 1.6], ko: [0.8, 1.6], de: [0.8, 1.3], fr: [0.8, 1.2] },
    de: { zh: [0.8, 1.8], en: [0.7, 1.4], ja: [0.8, 1.6], ko: [0.8, 1.6], fr: [0.8, 1.3], de: [0.8, 1.2] },
  }
  
  const [minRatio, maxRatio] = expectedRatios[sourceLang]?.[targetLang] || [0.5, 1.8]
  
  if (lengthRatio < minRatio || lengthRatio > maxRatio) {
    const penalty = Math.min(25, Math.abs(lengthRatio - 1) * 50)
    score -= penalty
    issues.push({
      id: generateIssueId(),
      type: 'fidelity',
      severity: penalty > 15 ? 'high' : 'medium',
      message: `译文字数比例异常（${(lengthRatio * 100).toFixed(0)}%）`,
      suggestion: `正常比例应为 ${(minRatio * 100).toFixed(0)}%-${(maxRatio * 100).toFixed(0)}%，请检查是否有漏译或冗余`,
    })
  }
  
  const terms = await termDB.search(sourceText, sourceLang, targetLang)
  for (const term of terms) {
    const sourceHasTerm = sourceText.toLowerCase().includes(term.sourceText.toLowerCase())
    const targetHasTerm = translatedText.toLowerCase().includes(term.translatedText.toLowerCase())
    
    if (sourceHasTerm && !targetHasTerm) {
      score -= 15
      issues.push({
        id: generateIssueId(),
        type: 'terminology',
        severity: 'high',
        message: `术语"${term.sourceText}"未按术语库翻译`,
        suggestion: `应翻译为"${term.translatedText}"`,
        sourceText: term.sourceText,
        targetText: term.translatedText,
      })
    }
  }
  
  const numbersInSource = sourceText.match(/\d+/g) || []
  const numbersInTarget = translatedText.match(/\d+/g) || []
  
  for (const num of numbersInSource) {
    if (!numbersInTarget.includes(num)) {
      score -= 10
      issues.push({
        id: generateIssueId(),
        type: 'fidelity',
        severity: 'high',
        message: `数字"${num}"在译文中缺失或被修改`,
        suggestion: '请检查数字翻译的准确性',
      })
    }
  }
  
  const properNouns = sourceText.match(/[A-Z][a-z]+|[A-Z]{2,}/g) || []
  for (const noun of properNouns.slice(0, 5)) {
    if (noun.length > 2 && !translatedText.includes(noun)) {
      score -= 5
      issues.push({
        id: generateIssueId(),
        type: 'fidelity',
        severity: 'medium',
        message: `专有名词"${noun}"可能未正确保留`,
        suggestion: '检查专有名词是否需要保留原文',
      })
    }
  }
  
  const sourceSentences = sourceText.split(/[.!?。！？]/).filter(s => s.trim())
  const targetSentences = translatedText.split(/[.!?。！？]/).filter(s => s.trim())
  
  if (Math.abs(sourceSentences.length - targetSentences.length) > Math.max(2, sourceSentences.length * 0.2)) {
    score -= 15
    issues.push({
      id: generateIssueId(),
      type: 'fidelity',
      severity: 'high',
      message: `句子数量差异过大（原文${sourceSentences.length}句，译文${targetSentences.length}句）`,
      suggestion: '请检查是否存在漏译或合并不当',
    })
  }
  
  const similarity = calculateSimilarity(sourceText, translatedText)
  if (similarity > 0.8) {
    score -= 30
    issues.push({
      id: generateIssueId(),
      type: 'fidelity',
      severity: 'high',
      message: '译文与原文相似度极高，可能未翻译',
      suggestion: '请确认是否为有效翻译',
    })
  }
  
  return { score: Math.max(0, Math.min(100, score)), issues }
}

export const evaluateTerminology = async (
  sourceText: string,
  translatedText: string,
  sourceLang: LanguageCode,
  targetLang: LanguageCode
): Promise<{ score: number; issues: QualityIssue[] }> => {
  let score = 100
  const issues: QualityIssue[] = []
  
  const terms = await termDB.search(sourceText, sourceLang, targetLang)
  let correctTerms = 0
  let totalTerms = 0
  
  for (const term of terms) {
    const sourceRegex = new RegExp(term.sourceText.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi')
    const sourceMatches = sourceText.match(sourceRegex)
    
    if (sourceMatches) {
      totalTerms += sourceMatches.length
      
      const targetRegex = new RegExp(term.translatedText.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi')
      const targetMatches = translatedText.match(targetRegex)
      
      if (targetMatches) {
        correctTerms += Math.min(sourceMatches.length, targetMatches.length)
      } else {
        score -= 10 * sourceMatches.length
        issues.push({
          id: generateIssueId(),
          type: 'terminology',
          severity: 'high',
          message: `术语"${term.sourceText}"未使用标准译法`,
          suggestion: `应译为"${term.translatedText}"`,
          sourceText: term.sourceText,
          targetText: term.translatedText,
        })
      }
    }
  }
  
  if (totalTerms > 0) {
    const accuracy = correctTerms / totalTerms
    score = Math.min(score, accuracy * 100)
    
    if (accuracy < 1) {
      issues.push({
        id: generateIssueId(),
        type: 'terminology',
        severity: accuracy < 0.7 ? 'high' : 'medium',
        message: `术语准确率：${(accuracy * 100).toFixed(1)}%（${correctTerms}/${totalTerms}）`,
        suggestion: '请确保所有术语都使用标准译法',
      })
    }
  }
  
  return { score: Math.max(0, Math.min(100, score)), issues }
}

export const evaluateStyle = (
  text: string,
  lang: LanguageCode,
  expectedStyle?: 'formal' | 'friendly' | 'neutral'
): { score: number; issues: QualityIssue[] } => {
  let score = 100
  const issues: QualityIssue[] = []
  
  const formal = formalPhrases[lang] || formalPhrases.en
  const casual = casualPhrases[lang] || casualPhrases.en
  const technical = technicalTerms[lang] || technicalTerms.en
  
  let formalCount = 0
  let casualCount = 0
  let technicalCount = 0
  
  const lowerText = text.toLowerCase()
  
  for (const phrase of formal) {
    if (lowerText.includes(phrase.toLowerCase())) {
      formalCount++
    }
  }
  
  for (const phrase of casual) {
    if (lowerText.includes(phrase.toLowerCase())) {
      casualCount++
    }
  }
  
  for (const phrase of technical) {
    if (lowerText.includes(phrase.toLowerCase())) {
      technicalCount++
    }
  }
  
  let detectedStyle: 'formal' | 'friendly' | 'neutral' | 'technical' = 'neutral'
  if (technicalCount > 2) {
    detectedStyle = 'technical'
  } else if (formalCount > casualCount * 2) {
    detectedStyle = 'formal'
  } else if (casualCount > formalCount * 2) {
    detectedStyle = 'friendly'
  }
  
  if (expectedStyle) {
    const styleMismatch = (expectedStyle === 'formal' && detectedStyle !== 'formal' && detectedStyle !== 'technical') ||
                         (expectedStyle === 'friendly' && detectedStyle !== 'friendly') ||
                         (expectedStyle === 'neutral' && detectedStyle === 'technical')
    
    if (styleMismatch) {
      score -= 20
      issues.push({
        id: generateIssueId(),
        type: 'style',
        severity: 'medium',
        message: `译文风格与预期不符（检测为${detectedStyle}，预期为${expectedStyle}）`,
        suggestion: `请调整语气风格为${expectedStyle === 'formal' ? '正式' : expectedStyle === 'friendly' ? '亲切' : '中性'}`,
      })
    }
  }
  
  if (formalCount > 0 && casualCount > 0) {
    score -= 15
    issues.push({
      id: generateIssueId(),
      type: 'style',
      severity: 'medium',
      message: '语气风格不一致，同时存在正式和非正式表达',
      suggestion: '请统一全文语气风格',
    })
  }
  
  if (lang === 'zh') {
    const hasPolite = /[您请]/.test(text)
    const hasCasual = /[嘛呗哦啦呢亲]/.test(text)
    if (hasPolite && hasCasual) {
      score -= 10
      issues.push({
        id: generateIssueId(),
        type: 'style',
        severity: 'medium',
        message: '敬语与口语混用',
        suggestion: '请统一使用敬语或口语',
      })
    }
  }
  
  if (technicalCount > 0 && expectedStyle !== 'technical') {
    score -= 5
    issues.push({
      id: generateIssueId(),
      type: 'style',
      severity: 'low',
      message: `检测到${technicalCount}个技术术语`,
      suggestion: '如非技术文档，请考虑使用更通俗的表达',
    })
  }
  
  return { score: Math.max(0, Math.min(100, score)), issues, detectedStyle } as any
}

export const evaluateTranslationQuality = async (
  sourceText: string,
  translatedText: string,
  sourceLang: LanguageCode,
  targetLang: LanguageCode,
  options?: {
    expectedStyle?: 'formal' | 'friendly' | 'neutral'
    checkTerminology?: boolean
    autoThreshold?: number
  }
): Promise<QualityAssessment> => {
  const { expectedStyle, checkTerminology = true, autoThreshold = 70 } = options || {}
  
  if (!sourceText.trim() || !translatedText.trim()) {
    return {
      score: { overall: 0, fluency: 0, fidelity: 0, terminology: 0, grammar: 0, style: 0 },
      issues: [],
      needsHumanReview: true,
      reviewReason: ['文本为空'],
      confidence: 0,
      timestamp: Date.now(),
    }
  }
  
  const fluencyResult = evaluateFluency(translatedText, targetLang)
  const fidelityResult = await evaluateFidelity(sourceText, translatedText, sourceLang, targetLang)
  const terminologyResult = checkTerminology 
    ? await evaluateTerminology(sourceText, translatedText, sourceLang, targetLang)
    : { score: 100, issues: [] }
  const styleResult = evaluateStyle(translatedText, targetLang, expectedStyle)
  
  const grammarIssues = fluencyResult.issues.filter(i => i.type === 'grammar')
  const grammarScore = grammarIssues.length > 0 
    ? Math.max(0, 100 - grammarIssues.length * 10)
    : 100
  
  const overallScore = Math.round(
    fluencyResult.score * 0.25 +
    fidelityResult.score * 0.35 +
    terminologyResult.score * 0.20 +
    grammarScore * 0.10 +
    styleResult.score * 0.10
  )
  
  const allIssues = [
    ...fluencyResult.issues,
    ...fidelityResult.issues,
    ...terminologyResult.issues,
    ...styleResult.issues,
  ]
  
  const highIssues = allIssues.filter(i => i.severity === 'high').length
  const mediumIssues = allIssues.filter(i => i.severity === 'medium').length
  
  const reviewReason: string[] = []
  let needsHumanReview = false
  
  if (overallScore < autoThreshold) {
    needsHumanReview = true
    reviewReason.push(`综合评分低于阈值${autoThreshold}分`)
  }
  
  if (highIssues > 0) {
    needsHumanReview = true
    reviewReason.push(`存在${highIssues}个严重问题`)
  }
  
  if (mediumIssues >= 3) {
    needsHumanReview = true
    reviewReason.push(`存在${mediumIssues}个中等问题`)
  }
  
  if (fidelityResult.score < 70) {
    needsHumanReview = true
    reviewReason.push('忠实度评分较低')
  }
  
  if (terminologyResult.score < 80) {
    needsHumanReview = true
    reviewReason.push('术语准确率较低')
  }
  
  const confidence = Math.round(
    (overallScore / 100) * 0.6 +
    (1 - (highIssues * 0.1 + mediumIssues * 0.05)) * 0.4
  )
  
  return {
    score: {
      overall: overallScore,
      fluency: Math.round(fluencyResult.score),
      fidelity: Math.round(fidelityResult.score),
      terminology: Math.round(terminologyResult.score),
      grammar: Math.round(grammarScore),
      style: Math.round(styleResult.score),
    },
    issues: allIssues,
    needsHumanReview,
    reviewReason,
    confidence: Math.max(0, Math.min(100, Math.round(confidence * 100))),
    timestamp: Date.now(),
  }
}

export const getQualityScoreColor = (score: number): string => {
  if (score >= 90) return 'text-green-600'
  if (score >= 70) return 'text-yellow-600'
  if (score >= 50) return 'text-orange-600'
  return 'text-red-600'
}

export const getQualityScoreBg = (score: number): string => {
  if (score >= 90) return 'bg-green-500'
  if (score >= 70) return 'bg-yellow-500'
  if (score >= 50) return 'bg-orange-500'
  return 'bg-red-500'
}

export const getQualityLabel = (score: number): string => {
  if (score >= 90) return '优秀'
  if (score >= 80) return '良好'
  if (score >= 70) return '中等'
  if (score >= 60) return '及格'
  return '较差'
}
