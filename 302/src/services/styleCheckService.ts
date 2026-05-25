import { LanguageCode, StyleAnalysis, TranslationStyle } from '../types'
import { tokenize } from './database'

const generateId = (): string => `style_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`

const formalMarkers: Record<LanguageCode, string[]> = {
  zh: ['请', '您', '贵', '敬', '谨', '特此', '恳请', '承蒙', '不胜感激', '顺祝商祺', '阁下', '谨此', '敬启', '敬祝', '恭请'],
  en: ['please', 'would you', 'could you', 'kindly', 'sincerely', 'respectfully', 'grateful', 'appreciate', 'yours faithfully', 'yours sincerely', 'dear sir', 'dear madam', 'it is', 'we are', 'one should'],
  ja: ['お願いします', 'です', 'ます', 'ございます', 'いただきます', 'よろしくお願いいたします', 'お世話になります', '恐れ入ります', '承知いたしました', 'お疲れ様です'],
  ko: ['습니다', '합니다', '입니다', '시겠습니까', '주시겠습니까', '감사합니다', '안녕하십니까', '죄송합니다', '알겠습니다', '들어가십시오'],
  fr: ['veuillez', 's\'il vous plaît', 'je vous prie', 'nous vous serions', 'cordialement', 'monsieur', 'madame', 'je vous remercie', 'nous avons', 'il est'],
  de: ['bitte', 'würden Sie', 'könnten Sie', 'ich bitte Sie', 'mit freundlichen Grüßen', 'Sehr geehrte', 'Ich danke Ihnen', 'wir sind', 'es ist', 'man sollte'],
}

const friendlyMarkers: Record<LanguageCode, string[]> = {
  zh: ['嘿', '嗨', '哦', '啦', '呗', '嘛', '呢', '吧', '亲', '么么哒', '哈哈', '嘻嘻', '哇', '耶', '你', '咱们', '大家'],
  en: ['hey', 'hi', 'yo', 'guys', 'wanna', 'gonna', 'gotta', 'cool', 'awesome', 'great', 'nice', 'lol', 'haha', 'let\'s', 'you', 'we', 'i\'m', 'don\'t', 'can\'t'],
  ja: ['だよ', 'ね', 'よ', 'ちゃん', 'くん', 'だって', 'なんか', 'うん', 'あはは', 'わーい', 'やった', 'ねえ', 'なに'],
  ko: ['야', '너', '나', '해', '돼', '고', '야호', '헤이', '하하', '와', '대박', '짱', '응', '아니'],
  fr: ['salut', 'hey', 't\'es', 't\'as', 'on va', 'génial', 'super', 'cool', 'lol', 'haha', 'tu', 'je', 'on', 'c\'est'],
  de: ['hey', 'hi', 'du', 'deine', 'dein', 'geil', 'krass', 'super', 'cool', 'haha', 'lol', 'ich', 'du', 'wir', 'das ist'],
}

const technicalMarkers: Record<LanguageCode, string[]> = {
  zh: ['接口', '模块', '算法', '框架', '架构', '缓存', '集群', '负载均衡', '微服务', '数据库', '服务器', 'API', 'SDK', '部署', '优化'],
  en: ['interface', 'module', 'algorithm', 'framework', 'architecture', 'cache', 'cluster', 'microservice', 'API', 'SDK', 'database', 'server', 'deploy', 'optimize', 'config'],
  ja: ['インターフェース', 'モジュール', 'アルゴリズム', 'フレームワーク', 'アーキテクチャ', 'キャッシュ', 'クラスタ', 'API', 'データベース', 'サーバー'],
  ko: ['인터페이스', '모듈', '알고리즘', '프레임워크', '아키텍처', '캐시', '클러스터', 'API', '데이터베이스', '서버'],
  fr: ['interface', 'module', 'algorithme', 'framework', 'architecture', 'cache', 'cluster', 'API', 'base de données', 'serveur'],
  de: ['Interface', 'Modul', 'Algorithmus', 'Framework', 'Architektur', 'Cache', 'Cluster', 'API', 'Datenbank', 'Server'],
}

const contractionPatterns: Record<LanguageCode, RegExp[]> = {
  zh: [],
  en: [/i'm/i, /you're/i, /he's/i, /she's/i, /it's/i, /we're/i, /they're/i, /i've/i, /you've/i, /we've/i, /they've/i, /i'll/i, /you'll/i, /he'll/i, /she'll/i, /we'll/i, /they'll/i, /i'd/i, /you'd/i, /he'd/i, /she'd/i, /we'd/i, /they'd/i, /don't/i, /can't/i, /won't/i, /isn't/i, /aren't/i, /wasn't/i, /weren't/i, /hasn't/i, /haven't/i, /hadn't/i, /doesn't/i, /don't/i, /didn't/i, /wouldn't/i, /shouldn't/i, /couldn't/i, /mightn't/i, /mustn't/i],
  ja: [],
  ko: [],
  fr: [/c'est/i, /t'es/i, /il est/i, /elle est/i, /on est/i, /j'ai/i, /t'as/i, /il a/i, /elle a/i, /on a/i, /je suis/i, /tu es/i, /nous sommes/i, /vous êtes/i, /ils sont/i],
  de: [/ich bin/i, /du bist/i, /er ist/i, /sie ist/i, /es ist/i, /wir sind/i, /ihr seid/i, /sie sind/i, /ich habe/i, /du hast/i, /er hat/i, /sie hat/i, /es hat/i, /wir haben/i, /ihr habt/i, /sie haben/i],
}

const honorificPatterns: Record<LanguageCode, RegExp[]> = {
  zh: [/您/, /贵/, /敬/, /谨/, /请/, /恳请/, /承蒙/, /不胜感激/, /顺祝商祺/],
  en: [/dear sir/i, /dear madam/i, /yours faithfully/i, /yours sincerely/i, /respectfully/i, /kindly/i],
  ja: [/お願いします/, /です/, /ます/, /ございます/, /いただきます/, /お世話になります/, /恐れ入ります/],
  ko: [/습니다/, /합니다/, /입니다/, /시겠습니까/, /주시겠습니까/, /감사합니다/, /안녕하십니까/],
  fr: [/monsieur/i, /madame/i, /veuillez/i, /je vous prie/i, /cordialement/],
  de: [/Sehr geehrte/i, /bitte/i, /würden Sie/i, /könnten Sie/i, /mit freundlichen Grüßen/i],
}

const pronounPatterns: Record<LanguageCode, { formal: RegExp[]; informal: RegExp[] }> = {
  zh: {
    formal: [/您/, /贵方/, /阁下/],
    informal: [/你/, /我/, /他/, /她/, /它/, /我们/, /你们/, /他们/],
  },
  en: {
    formal: [/one/i, /we/i, /the reader/i],
    informal: [/i/i, /you/i, /he/i, /she/i, /we/i, /they/i],
  },
  ja: {
    formal: [/私/, /貴方/, /彼/, /彼女/],
    informal: [/俺/, /僕/, /あたし/, /君/, /お前/, /あいつ/],
  },
  ko: {
    formal: [/저/, /당신/, /그/, /그녀/],
    informal: [/나/, /너/, /야/, /걔/],
  },
  fr: {
    formal: [/vous/i, /on/i, /le lecteur/i, /la lectrice/i],
    informal: [/tu/i, /je/i, /il/i, /elle/i, /on/i, /ils/i, /elles/i],
  },
  de: {
    formal: [/Sie/i, /man/i, /der Leser/i, /die Leserin/i],
    informal: [/du/i, /ich/i, /er/i, /sie/i, /es/i, /wir/i, /ihr/i],
  },
}

const modalVerbPatterns: Record<LanguageCode, RegExp[]> = {
  zh: [/应该/, /必须/, /需要/, /可以/, /能够/, /可能/, /会/, /要/],
  en: [/should/i, /must/i, /need/i, /can/i, /could/i, /may/i, /might/i, /shall/i, /will/i, /would/i, /ought to/i],
  ja: [/べき/, /しなければ/, /できる/, /可能/, /必要/, /した方がいい/],
  ko: [/해야/, /할 수/, /필요/, /가능/, /ㄹ 수/, /어야/],
  fr: [/doit/i, /devrait/i, /peut/i, /pourrait/i, /il faut/i, /il est nécessaire/i],
  de: [/muss/i, /soll/i, /kann/i, /könnte/i, /müssen/i, /sollen/i, /können/i, /dürfen/i],
}

export const analyzeStyle = (
  text: string,
  lang: LanguageCode,
  expectedStyle?: TranslationStyle
): StyleAnalysis => {
  const lowerText = text.toLowerCase()
  const sentences = text.split(/[.!?。！？]+/).filter(s => s.trim())
  const paragraphs = text.split(/\n\n+/).filter(p => p.trim())

  let formalCount = 0
  let friendlyCount = 0
  let technicalCount = 0

  const formal = formalMarkers[lang] || formalMarkers.en
  const friendly = friendlyMarkers[lang] || friendlyMarkers.en
  const technical = technicalMarkers[lang] || technicalMarkers.en

  for (const phrase of formal) {
    const regex = new RegExp(phrase.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi')
    const matches = lowerText.match(regex)
    if (matches) formalCount += matches.length
  }

  for (const phrase of friendly) {
    const regex = new RegExp(phrase.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi')
    const matches = lowerText.match(regex)
    if (matches) friendlyCount += matches.length
  }

  for (const phrase of technical) {
    const regex = new RegExp(phrase.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi')
    const matches = lowerText.match(regex)
    if (matches) technicalCount += matches.length
  }

  let contractionCount = 0
  const contractions = contractionPatterns[lang] || []
  for (const pattern of contractions) {
    const matches = text.match(pattern)
    if (matches) contractionCount += matches.length
  }

  let honorificCount = 0
  const honorifics = honorificPatterns[lang] || []
  for (const pattern of honorifics) {
    const matches = text.match(pattern)
    if (matches) honorificCount += matches.length
  }

  let formalPronounCount = 0
  let informalPronounCount = 0
  const pronouns = pronounPatterns[lang] || pronounPatterns.en
  for (const pattern of pronouns.formal) {
    const matches = text.match(pattern)
    if (matches) formalPronounCount += matches.length
  }
  for (const pattern of pronouns.informal) {
    const matches = text.match(pattern)
    if (matches) informalPronounCount += matches.length
  }

  let modalVerbCount = 0
  const modals = modalVerbPatterns[lang] || modalVerbPatterns.en
  for (const pattern of modals) {
    const matches = text.match(pattern)
    if (matches) modalVerbCount += matches.length
  }

  const avgSentenceLength = sentences.length > 0
    ? text.length / sentences.length
    : 0

  const tokens = tokenize(text, lang)
  const uniqueTokens = new Set(tokens.map(t => t.toLowerCase()))
  const vocabularyComplexity = tokens.length > 0
    ? uniqueTokens.size / tokens.length
    : 0

  const totalMarkers = formalCount + friendlyCount + technicalCount
  const formalityScore = totalMarkers > 0
    ? Math.min(100, Math.round((formalCount / totalMarkers) * 100 + honorificCount * 5))
    : 50
  const friendlinessScore = totalMarkers > 0
    ? Math.min(100, Math.round((friendlyCount / totalMarkers) * 100 + contractionCount * 3))
    : 50
  const technicalityScore = totalMarkers > 0
    ? Math.min(100, Math.round((technicalCount / totalMarkers) * 100))
    : 30

  let detectedStyle: TranslationStyle = 'neutral'
  let confidence = 0

  const maxScore = Math.max(formalityScore, friendlinessScore, technicalityScore)
  
  if (technicalityScore > 60 && technicalityScore >= maxScore) {
    detectedStyle = 'technical'
    confidence = technicalityScore
  } else if (formalityScore > 60 && formalityScore >= maxScore) {
    detectedStyle = 'formal'
    confidence = formalityScore
  } else if (friendlinessScore > 60 && friendlinessScore >= maxScore) {
    detectedStyle = 'friendly'
    confidence = friendlinessScore
  } else if (friendlinessScore > formalityScore * 1.5) {
    detectedStyle = 'casual'
    confidence = Math.round(friendlinessScore * 0.8)
  } else if (formalityScore > friendlinessScore * 1.5) {
    detectedStyle = 'formal'
    confidence = Math.round(formalityScore * 0.8)
  } else {
    detectedStyle = 'neutral'
    confidence = Math.round(50 + Math.abs(formalityScore - friendlinessScore) * 0.5)
  }

  const issues: StyleAnalysis['issues'] = []
  const suggestions: string[] = []

  if (formalCount > 0 && friendlyCount > 0) {
    const ratio = Math.max(formalCount, friendlyCount) / Math.min(formalCount, friendlyCount)
    if (ratio < 2) {
      issues.push({
        id: generateId(),
        type: 'inconsistency',
        severity: 'medium',
        message: `语气风格不一致，检测到${formalCount}个正式表达和${friendlyCount}个非正式表达`,
        suggestion: '请统一全文语气风格，避免正式与非正式表达混用',
      })
      suggestions.push('统一语气风格，选择正式或亲切中的一种并保持一致')
    }
  }

  if (expectedStyle && expectedStyle !== 'neutral') {
    const styleMismatch = 
      (expectedStyle === 'formal' && detectedStyle !== 'formal' && detectedStyle !== 'technical') ||
      (expectedStyle === 'friendly' && detectedStyle !== 'friendly' && detectedStyle !== 'casual') ||
      (expectedStyle === 'technical' && detectedStyle !== 'technical') ||
      (expectedStyle === 'casual' && detectedStyle !== 'casual' && detectedStyle !== 'friendly')

    if (styleMismatch) {
      issues.push({
        id: generateId(),
        type: 'tone_mismatch',
        severity: 'medium',
        message: `译文风格与预期不符（检测为${getStyleLabel(detectedStyle)}，预期为${getStyleLabel(expectedStyle)}）`,
        suggestion: `请调整语气风格为${getStyleLabel(expectedStyle)}`,
      })
      
      if (expectedStyle === 'formal') {
        suggestions.push('使用更正式的表达，如"您"代替"你"，避免使用缩写和口语化表达')
        suggestions.push('增加敬语使用，保持专业、礼貌的语气')
      } else if (expectedStyle === 'friendly' || expectedStyle === 'casual') {
        suggestions.push('使用更亲切的表达，如"你"代替"您"，适当使用口语化表达')
        suggestions.push('增加互动性，使用更轻松自然的语气')
      } else if (expectedStyle === 'technical') {
        suggestions.push('使用标准技术术语，保持精确、专业的表达')
      }
    }
  }

  if (lang === 'zh' && /[您]/.test(text) && /[你]/.test(text)) {
    issues.push({
      id: generateId(),
      type: 'formality_mismatch',
      severity: 'high',
      message: '中文敬语"您"与"你"混用',
      suggestion: '请统一使用"您"（正式）或"你"（亲切），敬语需保持一致',
      location: '全文',
    })
    suggestions.push('统一使用"您"或"你"，避免敬语与非敬语混用')
  }

  if (formalPronounCount > 0 && informalPronounCount > 0) {
    const ratio = Math.max(formalPronounCount, informalPronounCount) / Math.min(formalPronounCount, informalPronounCount)
    if (ratio < 3) {
      issues.push({
        id: generateId(),
        type: 'inconsistency',
        severity: 'medium',
        message: `人称代词使用不一致，正式代词${formalPronounCount}次，非正式代词${informalPronounCount}次`,
        suggestion: '请统一人称代词的正式程度',
      })
    }
  }

  if (avgSentenceLength > 40) {
    issues.push({
      id: generateId(),
      type: 'inconsistency',
      severity: 'low',
      message: `平均句长${avgSentenceLength.toFixed(1)}字符，部分句子可能过长`,
      suggestion: '建议将长句子拆分为多个短句，提升可读性',
    })
    suggestions.push('拆分过长句子，保持句子简洁明了')
  }

  if (avgSentenceLength > 0 && avgSentenceLength < 10 && sentences.length > 5) {
    issues.push({
      id: generateId(),
      type: 'inconsistency',
      severity: 'low',
      message: `平均句长${avgSentenceLength.toFixed(1)}字符，句子普遍过短`,
      suggestion: '考虑适当合并相关短句，提升阅读流畅性',
    })
  }

  if (vocabularyComplexity < 0.3) {
    issues.push({
      id: generateId(),
      type: 'inconsistency',
      severity: 'low',
      message: `词汇丰富度较低（${(vocabularyComplexity * 100).toFixed(1)}%），存在较多重复词汇`,
      suggestion: '考虑使用更多样的词汇表达',
    })
    suggestions.push('丰富词汇选择，避免重复用词')
  }

  const paragraphSentenceCounts = paragraphs.map(p => 
    p.split(/[.!?。！？]+/).filter(s => s.trim()).length
  )
  const maxParaSentences = Math.max(...paragraphSentenceCounts, 0)
  if (maxParaSentences > 15) {
    issues.push({
      id: generateId(),
      type: 'inconsistency',
      severity: 'low',
      message: `部分段落句子过多（最多${maxParaSentences}句）`,
      suggestion: '建议按逻辑拆分过长段落',
    })
    suggestions.push('拆分过长段落，保持适当的段落长度')
  }

  const consistencyScore = calculateConsistencyScore(text, lang, sentences, paragraphs)

  if (technicalCount > 0 && detectedStyle !== 'technical' && expectedStyle === 'formal') {
    suggestions.push('文档中包含技术术语，如需保持正式风格，请确保术语使用准确')
  }

  if (formalityScore >= 80) {
    suggestions.push('当前语气非常正式，适合商务、官方文档')
  } else if (formalityScore >= 60) {
    suggestions.push('当前语气较为正式，适合一般商务交流')
  }

  if (friendlinessScore >= 80) {
    suggestions.push('当前语气非常亲切，适合营销、社交内容')
  } else if (friendlinessScore >= 60) {
    suggestions.push('当前语气较为亲切，适合日常交流')
  }

  return {
    detectedStyle,
    confidence: Math.min(100, Math.round(confidence)),
    formalityScore: Math.min(100, formalityScore),
    friendlinessScore: Math.min(100, friendlinessScore),
    technicalityScore: Math.min(100, technicalityScore),
    consistencyScore: Math.min(100, Math.round(consistencyScore)),
    issues,
    suggestions,
    styleFeatures: {
      pronouns: formalPronounCount + informalPronounCount,
      modalVerbs: modalVerbCount,
      contractions: contractionCount,
      honorifics: honorificCount,
      sentenceLength: Math.round(avgSentenceLength),
      vocabularyComplexity: Math.round(vocabularyComplexity * 100),
    },
  }
}

const calculateConsistencyScore = (
  text: string,
  lang: LanguageCode,
  sentences: string[],
  paragraphs: string[]
): number => {
  let score = 100

  if (sentences.length < 2) return score

  const sentenceLengths = sentences.map(s => s.trim().length)
  const avgLength = sentenceLengths.reduce((a, b) => a + b, 0) / sentences.length
  const lengthVariance = sentenceLengths.reduce((sum, len) => 
    sum + Math.pow(len - avgLength, 2), 0) / sentences.length
  const lengthStdDev = Math.sqrt(lengthVariance)

  if (lengthStdDev > avgLength * 0.8) {
    score -= 20
  } else if (lengthStdDev > avgLength * 0.5) {
    score -= 10
  }

  const paragraphLengths = paragraphs.map(p => p.trim().length)
  if (paragraphLengths.length > 1) {
    const avgParaLength = paragraphLengths.reduce((a, b) => a + b, 0) / paragraphLengths.length
    const paraVariance = paragraphLengths.reduce((sum, len) => 
      sum + Math.pow(len - avgParaLength, 2), 0) / paragraphLengths.length
    const paraStdDev = Math.sqrt(paraVariance)

    if (paraStdDev > avgParaLength * 1.0) {
      score -= 15
    } else if (paraStdDev > avgParaLength * 0.6) {
      score -= 8
    }
  }

  const exclamationCount = (text.match(/[！!]/g) || []).length
  const questionCount = (text.match(/[？?]/g) || []).length
  const periodCount = (text.match(/[。.]/g) || []).length
  const totalPunctuation = exclamationCount + questionCount + periodCount

  if (totalPunctuation > 0) {
    const exclamationRatio = exclamationCount / totalPunctuation
    const questionRatio = questionCount / totalPunctuation

    if (exclamationRatio > 0.3 && sentences.length > 5) {
      score -= 15
    } else if (exclamationRatio > 0.2) {
      score -= 5
    }

    if (questionRatio > 0.4 && sentences.length > 5) {
      score -= 10
    }
  }

  const tokens = tokenize(text, lang)
  const uniqueTokens = new Set(tokens.map(t => t.toLowerCase()))
  const typeTokenRatio = uniqueTokens.size / tokens.length

  if (typeTokenRatio < 0.2) {
    score -= 10
  } else if (typeTokenRatio < 0.3) {
    score -= 5
  }

  return Math.max(0, score)
}

export const getStyleLabel = (style: TranslationStyle): string => {
  const labels: Record<TranslationStyle, string> = {
    formal: '正式',
    friendly: '亲切',
    neutral: '中性',
    technical: '技术',
    casual: '随意',
  }
  return labels[style] || style
}

export const getStyleColor = (style: TranslationStyle): string => {
  const colors: Record<TranslationStyle, string> = {
    formal: 'bg-blue-500',
    friendly: 'bg-green-500',
    neutral: 'bg-gray-500',
    technical: 'bg-purple-500',
    casual: 'bg-yellow-500',
  }
  return colors[style] || 'bg-gray-500'
}

export const getStyleIcon = (style: TranslationStyle): string => {
  const icons: Record<TranslationStyle, string> = {
    formal: '🎩',
    friendly: '😊',
    neutral: '⚖️',
    technical: '💻',
    casual: '🎈',
  }
  return icons[style] || '📝'
}

export const checkStyleConsistencyBatch = (
  segments: Array<{ id: string; text: string }>,
  lang: LanguageCode,
  expectedStyle?: TranslationStyle
): Array<{ id: string; analysis: StyleAnalysis; overallConsistency: number }> => {
  const analyses = segments.map(segment => ({
    id: segment.id,
    analysis: analyzeStyle(segment.text, lang, expectedStyle),
  }))

  const styleCounts: Record<string, number> = {}
  analyses.forEach(a => {
    const style = a.analysis.detectedStyle
    styleCounts[style] = (styleCounts[style] || 0) + 1
  })

  const dominantStyle = Object.entries(styleCounts).sort((a, b) => b[1] - a[1])[0]
  const overallConsistency = dominantStyle
    ? Math.round((dominantStyle[1] / segments.length) * 100)
    : 100

  return analyses.map(a => ({
    ...a,
    overallConsistency,
  }))
}
