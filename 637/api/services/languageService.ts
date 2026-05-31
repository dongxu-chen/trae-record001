import { franc } from 'franc-min';
import type { Language } from '../../shared/types';

export function detectLanguage(text: string): Language {
  if (!text || text.trim().length === 0) {
    return 'en';
  }

  const hasChinese = /[\u4e00-\u9fa5]/.test(text);
  if (hasChinese) {
    return 'zh';
  }

  const hasJapanese = /[\u3040-\u30ff]/.test(text);
  if (hasJapanese) {
    return 'ja';
  }

  const hasKorean = /[\uac00-\ud7af]/.test(text);
  if (hasKorean) {
    return 'ko';
  }

  try {
    const lang = franc(text, { minLength: 3 });
    switch (lang) {
      case 'cmn':
        return 'zh';
      case 'jpn':
        return 'ja';
      case 'kor':
        return 'ko';
      case 'eng':
        return 'en';
      default:
        return 'other';
    }
  } catch {
    return 'en';
  }
}

export function getLanguageName(lang: Language): string {
  const names: Record<Language, string> = {
    zh: '中文',
    en: 'English',
    ja: '日本語',
    ko: '한국어',
    other: 'Other'
  };
  return names[lang];
}
