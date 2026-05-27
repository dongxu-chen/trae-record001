import { pinyin } from 'pinyin-pro';

interface PinyinResult {
  full: string;
  first: string;
}

export const getPinyin = (text: string): PinyinResult => {
  const fullPinyin = pinyin(text, { toneType: 'none', separator: '' }).toLowerCase();
  const firstLetter = pinyin(text, { toneType: 'none', pattern: 'first', separator: '' }).toLowerCase();
  
  return {
    full: fullPinyin,
    first: firstLetter,
  };
};

export const matchByPinyin = (text: string, query: string): boolean => {
  const { full, first } = getPinyin(text);
  const lowerQuery = query.toLowerCase();
  
  return (
    text.toLowerCase().includes(lowerQuery) ||
    full.includes(lowerQuery) ||
    first.includes(lowerQuery)
  );
};

export const matchTagsByPinyin = (tags: string[], query: string): boolean => {
  return tags.some(tag => matchByPinyin(tag, query));
};
