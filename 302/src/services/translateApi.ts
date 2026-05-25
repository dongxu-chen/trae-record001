import { LanguageCode, TranslationResult, TranslateApiConfig } from '../types'

const MOCK_TRANSLATIONS: Record<string, Record<string, string>> = {
  zh: {
    en: 'Hello',
    ja: 'こんにちは',
    ko: '안녕하세요',
    fr: 'Bonjour',
    de: 'Hallo',
  },
  en: {
    zh: '你好',
    ja: 'こんにちは',
    ko: '안녕하세요',
    fr: 'Bonjour',
    de: 'Hallo',
  },
}

const mockTranslate = async (
  text: string,
  source: LanguageCode,
  target: LanguageCode
): Promise<string> => {
  await new Promise(resolve => setTimeout(resolve, 500))
  
  const lowerText = text.toLowerCase().trim()
  
  if (lowerText === 'hello' || lowerText === '你好' || lowerText === 'こんにちは') {
    return MOCK_TRANSLATIONS[source]?.[target] || text
  }
  
  if (lowerText === 'world' || lowerText === '世界') {
    const translations: Record<string, string> = {
      zh: '世界',
      en: 'World',
      ja: '世界',
      ko: '세계',
      fr: 'Monde',
      de: 'Welt',
    }
    return translations[target] || text
  }
  
  if (lowerText === 'thank you' || lowerText === '谢谢' || lowerText === 'ありがとう') {
    const translations: Record<string, string> = {
      zh: '谢谢',
      en: 'Thank you',
      ja: 'ありがとう',
      ko: '감사합니다',
      fr: 'Merci',
      de: 'Danke',
    }
    return translations[target] || text
  }
  
  const prefix: Record<string, string> = {
    zh: '[翻译]',
    en: '[Translated]',
    ja: '[翻訳]',
    ko: '[번역]',
    fr: '[Traduit]',
    de: '[Übersetzt]',
  }
  
  return `${prefix[target] || '[T]'} ${text}`
}

const googleTranslate = async (
  text: string,
  source: LanguageCode,
  target: LanguageCode,
  apiKey: string
): Promise<string> => {
  const url = `https://translation.googleapis.com/language/translate/v2?key=${apiKey}`
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      q: text,
      source: source === 'zh' ? 'zh-CN' : source,
      target: target === 'zh' ? 'zh-CN' : target,
      format: 'text',
    }),
  })
  
  if (!response.ok) {
    throw new Error('Google Translate API request failed')
  }
  
  const data = await response.json()
  return data.data.translations[0].translatedText
}

const deeplTranslate = async (
  text: string,
  source: LanguageCode,
  target: LanguageCode,
  apiKey: string,
  endpoint?: string
): Promise<string> => {
  const baseUrl = endpoint || 'https://api-free.deepl.com/v2/translate'
  const response = await fetch(baseUrl, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
      'Authorization': `DeepL-Auth-Key ${apiKey}`,
    },
    body: new URLSearchParams({
      text: text,
      source_lang: source.toUpperCase(),
      target_lang: target.toUpperCase(),
    }),
  })
  
  if (!response.ok) {
    throw new Error('DeepL API request failed')
  }
  
  const data = await response.json()
  return data.translations[0].text
}

export const translateText = async (
  text: string,
  source: LanguageCode,
  target: LanguageCode,
  config: TranslateApiConfig
): Promise<TranslationResult> => {
  if (!text.trim()) {
    return {
      translatedText: '',
      source,
      target,
      originalText: text,
      timestamp: Date.now(),
    }
  }
  
  let translatedText: string
  
  switch (config.provider) {
    case 'google':
      if (!config.apiKey) {
        throw new Error('Google Translate API key is required')
      }
      translatedText = await googleTranslate(text, source, target, config.apiKey)
      break
    case 'deepl':
      if (!config.apiKey) {
        throw new Error('DeepL API key is required')
      }
      translatedText = await deeplTranslate(text, source, target, config.apiKey, config.endpoint)
      break
    case 'mock':
    default:
      translatedText = await mockTranslate(text, source, target)
      break
  }
  
  return {
    translatedText,
    source,
    target,
    originalText: text,
    timestamp: Date.now(),
  }
}

export const detectLanguage = async (
  text: string,
  config: TranslateApiConfig
): Promise<LanguageCode> => {
  await new Promise(resolve => setTimeout(resolve, 200))
  
  const chinesePattern = /[\u4e00-\u9fa5]/
  const japanesePattern = /[\u3040-\u30ff\u31f0-\u31ff]/
  const koreanPattern = /[\uac00-\ud7af]/
  const frenchPattern = /[àâäçéèêëîïôöùûüÿœ]/i
  const germanPattern = /[äöüß]/i
  
  if (chinesePattern.test(text)) return 'zh'
  if (japanesePattern.test(text)) return 'ja'
  if (koreanPattern.test(text)) return 'ko'
  if (germanPattern.test(text)) return 'de'
  if (frenchPattern.test(text)) return 'fr'
  
  return 'en'
}
