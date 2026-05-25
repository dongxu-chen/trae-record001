import { LanguageCode, TranslationResult, TranslateApiConfig, MemoryMatchConfig, TermMatchConfig } from '../types'
import { translateText } from './translateApi'
import { termDB, translationMemoryDB, historyDB, applyTermReplacements, applyTermReplacementsWithSegmentation } from './database'

export const translateWithEnhancements = async (
  text: string,
  source: LanguageCode,
  target: LanguageCode,
  config: TranslateApiConfig,
  options: {
    useTerms?: boolean
    useMemory?: boolean
    saveToHistory?: boolean
    saveToMemory?: boolean
    memoryConfig?: Partial<MemoryMatchConfig>
    termConfig?: Partial<TermMatchConfig>
  } = {}
): Promise<TranslationResult & { 
  memoryMatch?: {
    type: 'exact' | 'fuzzy' | 'contains' | null
    similarity: number
  }
  termMatches?: number
}> => {
  const {
    useTerms = true,
    useMemory = true,
    saveToHistory = true,
    saveToMemory = true,
    memoryConfig,
    termConfig,
  } = options

  if (!text.trim()) {
    return {
      translatedText: '',
      source,
      target,
      originalText: text,
      timestamp: Date.now(),
      memoryMatch: { type: null, similarity: 0 },
      termMatches: 0,
    }
  }

  let memoryMatchInfo: { type: 'exact' | 'fuzzy' | 'contains' | null; similarity: number } = { type: null, similarity: 0 }

  if (useMemory) {
    const bestMatch = await translationMemoryDB.findBestMatch(text, source, target, memoryConfig)
    
    if (bestMatch) {
      await translationMemoryDB.recordUsage(bestMatch.id!)
      memoryMatchInfo = {
        type: bestMatch.matchType as 'exact' | 'fuzzy' | 'contains',
        similarity: bestMatch.similarity,
      }
      
      const result: TranslationResult & {
        memoryMatch?: { type: string; similarity: number }
        termMatches?: number
      } = {
        translatedText: bestMatch.translatedText,
        source,
        target,
        originalText: text,
        timestamp: Date.now(),
        memoryMatch: memoryMatchInfo,
        termMatches: 0,
      }
      
      if (saveToHistory) {
        await historyDB.add(result)
      }
      return result
    }
  }

  let processedText = text
  let termMatchCount = 0
  
  if (useTerms) {
    const effectiveTermConfig: TermMatchConfig = {
      enabled: true,
      useSegmentation: termConfig?.useSegmentation ?? true,
      longTermFirst: termConfig?.longTermFirst ?? true,
    }
    
    if (effectiveTermConfig.useSegmentation) {
      const matches = await termDB.findMatchesInText(text, source, target, effectiveTermConfig)
      termMatchCount = matches.length
      
      if (matches.length > 0) {
        processedText = await applyTermReplacementsWithSegmentation(text, source, target, effectiveTermConfig)
      }
    } else {
      const terms = await termDB.search(text, source, target, undefined, effectiveTermConfig)
      termMatchCount = terms.length
      if (terms.length > 0) {
        processedText = applyTermReplacements(text, terms)
      }
    }
  }

  const result = await translateText(processedText, source, target, config)
  
  const enhancedResult: TranslationResult & {
    memoryMatch?: { type: string | null; similarity: number }
    termMatches?: number
  } = {
    ...result,
    memoryMatch: memoryMatchInfo,
    termMatches: termMatchCount,
  }

  if (saveToHistory) {
    await historyDB.add(enhancedResult)
  }

  if (saveToMemory && text.trim()) {
    const existingMemory = await translationMemoryDB.findExact(text, source, target)
    if (!existingMemory) {
      await translationMemoryDB.add({
        sourceText: text,
        translatedText: result.translatedText,
        sourceLang: source,
        targetLang: target,
        usageCount: 1,
        lastUsedAt: Date.now(),
        createdAt: Date.now(),
      })
    }
  }

  return enhancedResult
}

export const translateBatch = async (
  texts: string[],
  source: LanguageCode,
  target: LanguageCode,
  config: TranslateApiConfig,
  options?: {
    useTerms?: boolean
    useMemory?: boolean
    saveToHistory?: boolean
    saveToMemory?: boolean
    memoryConfig?: Partial<MemoryMatchConfig>
    termConfig?: Partial<TermMatchConfig>
  }
): Promise<Array<TranslationResult & {
  memoryMatch?: { type: string | null; similarity: number }
  termMatches?: number
}>> => {
  const results: Array<TranslationResult & {
    memoryMatch?: { type: string | null; similarity: number }
    termMatches?: number
  }> = []
  
  for (const text of texts) {
    const result = await translateWithEnhancements(text, source, target, config, options)
    results.push(result)
  }
  
  return results
}

export const getTranslationSuggestions = async (
  text: string,
  source: LanguageCode,
  target: LanguageCode,
  memoryConfig?: Partial<MemoryMatchConfig>
): Promise<{
  fromMemory: Array<{ text: string; score: number; source: 'memory' | 'term'; matchType: 'exact' | 'fuzzy' | 'contains' | 'exact-term' }>
}> => {
  const memoryResults = await translationMemoryDB.search(text, source, target, memoryConfig)
  const termResults = await termDB.search(text, source, target)
  
  const suggestions: Array<{ text: string; score: number; source: 'memory' | 'term'; matchType: 'exact' | 'fuzzy' | 'contains' | 'exact-term' }> = []
  
  memoryResults.forEach(entry => {
    const baseScore = entry.similarity
    const usageBoost = Math.min(0.15, entry.usageCount * 0.015)
    const finalScore = Math.min(1, baseScore + usageBoost)
    
    suggestions.push({
      text: entry.translatedText,
      score: finalScore,
      source: 'memory',
      matchType: entry.matchType,
    })
  })
  
  termResults.forEach(term => {
    suggestions.push({
      text: term.translatedText,
      score: 0.95,
      source: 'term',
      matchType: 'exact-term',
    })
  })
  
  return {
    fromMemory: suggestions.sort((a, b) => b.score - a.score).slice(0, 5),
  }
}
