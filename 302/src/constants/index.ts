import { Language, LanguageCode } from '../types'

export const LANGUAGES: Language[] = [
  { code: 'zh', name: 'Chinese', nativeName: '中文' },
  { code: 'en', name: 'English', nativeName: 'English' },
  { code: 'ja', name: 'Japanese', nativeName: '日本語' },
  { code: 'ko', name: 'Korean', nativeName: '한국어' },
  { code: 'fr', name: 'French', nativeName: 'Français' },
  { code: 'de', name: 'German', nativeName: 'Deutsch' },
]

export const LANGUAGE_MAP: Record<LanguageCode, Language> = LANGUAGES.reduce(
  (acc, lang) => {
    acc[lang.code] = lang
    return acc
  },
  {} as Record<LanguageCode, Language>
)

export const DB_NAME = 'translator_db'
export const DB_VERSION = 1

export const STORE_TERMS = 'terms'
export const STORE_TRANSLATION_MEMORY = 'translation_memory'
export const STORE_DOCUMENTS = 'documents'
export const STORE_HISTORY = 'history'

export const API_PROVIDERS = [
  { id: 'mock', name: 'Mock (Demo)', needKey: false },
  { id: 'google', name: 'Google Translate', needKey: true },
  { id: 'deepl', name: 'DeepL', needKey: true },
]
