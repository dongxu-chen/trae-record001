import type { NamingStyle, VariableType, Recommendation } from '../../shared/types';
import { convertStyle, parseToWords } from '../utils/namingUtils.js';
import { translateChinese, extractEnglishWords, zhToEnDict } from '../utils/translationDict.js';
import { expandAbbreviation, expandAbbreviations, abbreviateWords } from '../utils/abbreviationDict.js';
import { detectLanguage } from './languageService.js';
import { getWordWeight, calculateFrequencyBoost, filterLowFrequencyWords } from './learningService.js';
import { inferTypeFromContext, applyTypeNamingHints, getTypeNamingConventions } from './typeInferenceService.js';

const variableTypeKeywords: Record<VariableType, string[]> = {
  function: ['获取', '读取', '计算', '处理', '生成', '转换', '验证', '检查', '更新', '创建', '删除', 'get', 'calculate', 'process', 'generate', 'convert', 'validate', 'check', 'update', 'create', 'delete', 'find', 'search'],
  class: ['管理器', '控制器', '服务', '处理器', '工厂', '构建器', 'manager', 'controller', 'service', 'handler', 'factory', 'builder'],
  constant: ['最大', '最小', '默认', '配置', '常量', 'max', 'min', 'default', 'config', 'constant', 'timeout', 'interval'],
  boolean: ['是否', '是否是', '是否有', '启用', '禁用', '激活', '可见', '有效', 'is', 'has', 'can', 'should', 'enabled', 'disabled', 'active', 'visible', 'valid'],
  variable: []
};

const commonPrefixes = ['get', 'set', 'is', 'has', 'can', 'should', 'will', 'would', 'do', 'does', 'did', 'had', 'have', 'be', 'are', 'were', 'was'];
const commonSuffixes = ['count', 'list', 'array', 'map', 'set', 'id', 'name', 'type', 'status', 'date', 'time', 'info', 'data'];

function detectVariableType(input: string): VariableType {
  const lowerInput = input.toLowerCase();
  
  for (const [type, keywords] of Object.entries(variableTypeKeywords)) {
    for (const keyword of keywords) {
      if (lowerInput.includes(keyword.toLowerCase())) {
        return type as VariableType;
      }
    }
  }
  
  return 'variable';
}

function extractWords(input: string): string[] {
  const lang = detectLanguage(input);
  
  if (lang === 'zh') {
    return translateChinese(input);
  }
  
  let englishWords = extractEnglishWords(input);
  if (englishWords.length > 0) {
    return expandAbbreviations(englishWords);
  }
  
  const parsedWords = parseToWords(input);
  return expandAbbreviations(parsedWords);
}

function calculateConfidence(words: string[], style: NamingStyle, type: VariableType, name: string): number {
  let confidence = 0.7;
  
  if (words.length >= 2 && words.length <= 4) {
    confidence += 0.1;
  }
  
  const dictWords = words.filter(w => Object.values(zhToEnDict).includes(w.toLowerCase()));
  confidence += dictWords.length * 0.03;
  
  if (type === 'boolean' && words[0]?.match(/^(is|has|can|should)$/i)) {
    confidence += 0.1;
  }
  
  if (type === 'function' && commonPrefixes.some(p => words[0]?.toLowerCase() === p)) {
    confidence += 0.05;
  }
  
  const wordWeights = words.map(w => getWordWeight(w));
  const avgWordWeight = wordWeights.reduce((a, b) => a + b, 0) / wordWeights.length;
  confidence += (avgWordWeight - 1) * 0.1;
  
  const frequencyBoost = calculateFrequencyBoost(name, style);
  confidence += frequencyBoost;
  
  return Math.min(0.98, Math.max(0.3, confidence));
}

function generateVariations(words: string[]): string[][] {
  if (words.length === 0) return [];
  
  const variations: string[][] = [words];
  
  if (words.length > 2) {
    variations.push(words.slice(0, 2));
    variations.push(words.slice(0, 3));
  }
  
  if (commonSuffixes.some(s => words[words.length - 1]?.toLowerCase() === s) && words.length > 1) {
    variations.push([...words.slice(0, -1)]);
  }
  
  const abbreviated = abbreviateWords(words);
  if (abbreviated.some((w, i) => w !== words[i])) {
    variations.push(abbreviated);
  }
  
  return variations;
}

export function generateRecommendations(
  input: string,
  targetStyle: NamingStyle = 'camelCase',
  variableType?: VariableType,
  maxResults: number = 8,
  context?: string
): Recommendation[] {
  const words = extractWords(input);
  
  if (words.length === 0) {
    return [];
  }
  
  const typeInference = context || variableType 
    ? inferTypeFromContext(context || '', input)
    : null;
  
  let detectedType: VariableType;
  let typeConfidenceBoost = 0;
  
  if (variableType) {
    detectedType = variableType;
    typeConfidenceBoost = 0.1;
  } else if (typeInference && typeInference.confidence > 0.5) {
    detectedType = typeInference.type;
    typeConfidenceBoost = typeInference.confidence * 0.05;
  } else {
    detectedType = detectVariableType(input);
  }
  
  const enhancedWords = applyTypeNamingHints(words, detectedType);
  
  const typeConventions = getTypeNamingConventions(detectedType);
  const typePreferredStyles = typeConventions.preferredStyles;
  
  const variations = generateVariations(enhancedWords);
  const recommendations: Recommendation[] = [];
  const seenNames = new Set<string>();
  
  for (const variantWords of variations) {
    if (variantWords.length === 0) continue;
    
    const name = convertStyle(variantWords, targetStyle);
    
    if (seenNames.has(name)) continue;
    seenNames.add(name);
    
    let confidence = calculateConfidence(variantWords, targetStyle, detectedType, name);
    confidence += typeConfidenceBoost;
    
    if (typePreferredStyles.includes(targetStyle)) {
      confidence += 0.03;
    }
    
    recommendations.push({
      id: `rec-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      name,
      style: targetStyle,
      confidence: Math.min(0.98, confidence),
      type: detectedType,
      description: generateDescription(variantWords, detectedType)
    });
  }
  
  const otherStyles: NamingStyle[] = ['snake_case', 'PascalCase', 'kebab-case', 'SCREAMING_SNAKE_CASE'];
  for (const style of otherStyles) {
    if (style === targetStyle) continue;
    if (recommendations.length >= maxResults) break;
    
    const name = convertStyle(enhancedWords, style);
    if (seenNames.has(name)) continue;
    seenNames.add(name);
    
    let confidence = calculateConfidence(enhancedWords, style, detectedType, name) - 0.05;
    
    if (typePreferredStyles.includes(style)) {
      confidence += 0.05;
    }
    
    recommendations.push({
      id: `rec-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      name,
      style,
      confidence: Math.min(0.98, Math.max(0.3, confidence)),
      type: detectedType,
      description: generateDescription(enhancedWords, detectedType)
    });
  }
  
  return recommendations
    .sort((a, b) => b.confidence - a.confidence)
    .slice(0, maxResults);
}

function generateDescription(words: string[], type: VariableType): string {
  const typeNames: Record<VariableType, string> = {
    variable: '变量',
    function: '函数',
    class: '类',
    constant: '常量',
    boolean: '布尔值'
  };
  
  return `${typeNames[type]}，表示 ${words.join(' ')}`;
}

export function convertNamingStyle(name: string, targetStyle: NamingStyle): string {
  const words = parseToWords(name);
  return convertStyle(words, targetStyle);
}
