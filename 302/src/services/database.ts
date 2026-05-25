import { openDB, IDBPDatabase } from 'idb'
import {
  DB_NAME,
  DB_VERSION,
  STORE_TERMS,
  STORE_TRANSLATION_MEMORY,
  STORE_DOCUMENTS,
  STORE_HISTORY,
} from '../constants'
import { TermEntry, TranslationMemory, DocumentTranslation, TranslationResult, LanguageCode, MemoryMatchConfig, TermMatchConfig } from '../types'

let db: IDBPDatabase | null = null

export const levenshteinDistance = (a: string, b: string): number => {
  const matrix: number[][] = []
  
  for (let i = 0; i <= b.length; i++) {
    matrix[i] = [i]
  }
  
  for (let j = 0; j <= a.length; j++) {
    matrix[0][j] = j
  }
  
  for (let i = 1; i <= b.length; i++) {
    for (let j = 1; j <= a.length; j++) {
      if (b.charAt(i - 1) === a.charAt(j - 1)) {
        matrix[i][j] = matrix[i - 1][j - 1]
      } else {
        matrix[i][j] = Math.min(
          matrix[i - 1][j - 1] + 1,
          matrix[i][j - 1] + 1,
          matrix[i - 1][j] + 1
        )
      }
    }
  }
  
  return matrix[b.length][a.length]
}

export const calculateSimilarity = (a: string, b: string): number => {
  if (!a || !b) return 0
  if (a === b) return 1
  
  const lowerA = a.toLowerCase()
  const lowerB = b.toLowerCase()
  
  if (lowerA === lowerB) return 0.95
  
  const maxLength = Math.max(lowerA.length, lowerB.length)
  if (maxLength === 0) return 0
  
  const distance = levenshteinDistance(lowerA, lowerB)
  const similarity = 1 - distance / maxLength
  
  const containsA = lowerB.includes(lowerA) ? 0.1 : 0
  const containsB = lowerA.includes(lowerB) ? 0.1 : 0
  
  return Math.min(1, similarity + containsA + containsB)
}

export const calculateJaccardSimilarity = (a: string, b: string): number => {
  const tokensA = new Set(tokenize(a.toLowerCase()))
  const tokensB = new Set(tokenize(b.toLowerCase()))
  
  const intersection = new Set([...tokensA].filter(x => tokensB.has(x)))
  const union = new Set([...tokensA, ...tokensB])
  
  if (union.size === 0) return 0
  return intersection.size / union.size
}

export const tokenize = (text: string, lang?: LanguageCode): string[] => {
  if (!text) return []
  
  const chinesePattern = /[\u4e00-\u9fa5]+/g
  const japanesePattern = /[\u3040-\u30ff\u31f0-\u31ff]+/g
  const koreanPattern = /[\uac00-\ud7af]+/g
  const englishPattern = /[a-zA-Z]+/g
  const numberPattern = /\d+/g
  
  const tokens: string[] = []
  
  const chineseMatches = text.match(chinesePattern)
  if (chineseMatches) {
    chineseMatches.forEach(match => {
      for (let i = 0; i < match.length; i++) {
        for (let j = i + 1; j <= Math.min(i + 5, match.length); j++) {
          tokens.push(match.slice(i, j))
        }
      }
    })
  }
  
  const japaneseMatches = text.match(japanesePattern)
  if (japaneseMatches) {
    japaneseMatches.forEach(match => {
      for (let i = 0; i < match.length; i++) {
        for (let j = i + 1; j <= Math.min(i + 4, match.length); j++) {
          tokens.push(match.slice(i, j))
        }
      }
    })
  }
  
  const koreanMatches = text.match(koreanPattern)
  if (koreanMatches) {
    tokens.push(...koreanMatches)
  }
  
  const englishMatches = text.match(englishPattern)
  if (englishMatches) {
    tokens.push(...englishMatches.map(w => w.toLowerCase()))
  }
  
  const numberMatches = text.match(numberPattern)
  if (numberMatches) {
    tokens.push(...numberMatches)
  }
  
  return [...new Set(tokens)]
}

export const segmentText = (text: string, lang?: LanguageCode): string[] => {
  if (!text) return []
  
  const segments: string[] = []
  
  const sentences = text.split(/(?<=[.!?。！？])\s+|(?<=[\n])/)
  
  for (const sentence of sentences) {
    if (!sentence.trim()) continue
    
    segments.push(sentence.trim())
    
    const words = sentence.match(/[\u4e00-\u9fa5]+|[a-zA-Z]+|[\u3040-\u30ff]+|[\uac00-\ud7af]+|\d+/g) || []
    
    if (words.length > 2) {
      for (let i = 0; i < words.length; i++) {
        for (let j = i + 2; j <= Math.min(i + 8, words.length); j++) {
          const phrase = words.slice(i, j).join(' ')
          if (phrase.length >= 2) {
            segments.push(phrase)
          }
        }
      }
    }
  }
  
  return [...new Set(segments)]
}

export const initDB = async (): Promise<IDBPDatabase> => {
  if (db) return db

  db = await openDB(DB_NAME, DB_VERSION, {
    upgrade(db) {
      if (!db.objectStoreNames.contains(STORE_TERMS)) {
        const termStore = db.createObjectStore(STORE_TERMS, {
          keyPath: 'id',
          autoIncrement: true,
        })
        termStore.createIndex('sourceText', 'sourceText')
        termStore.createIndex('sourceLang_targetLang', ['sourceLang', 'targetLang'])
        termStore.createIndex('domain', 'domain')
        termStore.createIndex('sourceTextLength', 'sourceTextLength')
      }

      if (!db.objectStoreNames.contains(STORE_TRANSLATION_MEMORY)) {
        const tmStore = db.createObjectStore(STORE_TRANSLATION_MEMORY, {
          keyPath: 'id',
          autoIncrement: true,
        })
        tmStore.createIndex('sourceText', 'sourceText')
        tmStore.createIndex('sourceLang_targetLang', ['sourceLang', 'targetLang'])
        tmStore.createIndex('usageCount', 'usageCount')
        tmStore.createIndex('lastUsedAt', 'lastUsedAt')
      }

      if (!db.objectStoreNames.contains(STORE_DOCUMENTS)) {
        const docStore = db.createObjectStore(STORE_DOCUMENTS, {
          keyPath: 'id',
          autoIncrement: true,
        })
        docStore.createIndex('fileName', 'fileName')
        docStore.createIndex('createdAt', 'createdAt')
      }

      if (!db.objectStoreNames.contains(STORE_HISTORY)) {
        const historyStore = db.createObjectStore(STORE_HISTORY, {
          keyPath: 'id',
          autoIncrement: true,
        })
        historyStore.createIndex('timestamp', 'timestamp')
        historyStore.createIndex('source_target', ['source', 'target'])
      }
    },
  })

  return db
}

export const getDB = async (): Promise<IDBPDatabase> => {
  if (!db) {
    return initDB()
  }
  return db
}

export const termDB = {
  async add(term: Omit<TermEntry, 'id'>): Promise<number> {
    const db = await getDB()
    const termWithLength = {
      ...term,
      sourceTextLength: term.sourceText.length,
    }
    return db.add(STORE_TERMS, termWithLength) as Promise<number>
  },

  async update(term: TermEntry & { sourceTextLength?: number }): Promise<IDBValidKey> {
    const db = await getDB()
    const termWithLength = {
      ...term,
      sourceTextLength: term.sourceText.length,
    }
    return db.put(STORE_TERMS, termWithLength)
  },

  async delete(id: number): Promise<void> {
    const db = await getDB()
    return db.delete(STORE_TERMS, id)
  },

  async get(id: number): Promise<TermEntry | undefined> {
    const db = await getDB()
    return db.get(STORE_TERMS, id)
  },

  async getAll(): Promise<TermEntry[]> {
    const db = await getDB()
    return db.getAll(STORE_TERMS)
  },

  async search(
    text: string,
    sourceLang?: LanguageCode,
    targetLang?: LanguageCode,
    domain?: string,
    config?: TermMatchConfig
  ): Promise<TermEntry[]> {
    const db = await getDB()
    const allTerms = await db.getAll(STORE_TERMS)
    
    const effectiveConfig: TermMatchConfig = config || {
      enabled: true,
      useSegmentation: true,
      longTermFirst: true,
    }
    
    let matchedTerms: TermEntry[] = []
    
    if (effectiveConfig.useSegmentation) {
      const segments = segmentText(text, sourceLang)
      
      for (const segment of segments) {
        for (const term of allTerms) {
          const matchesSource = !sourceLang || term.sourceLang === sourceLang
          const matchesTarget = !targetLang || term.targetLang === targetLang
          const matchesDomain = !domain || term.domain === domain
          
          if (!matchesSource || !matchesTarget || !matchesDomain) continue
          
          const similarity = calculateSimilarity(segment, term.sourceText)
          const containsMatch = term.sourceText.toLowerCase().includes(segment.toLowerCase()) ||
                               segment.toLowerCase().includes(term.sourceText.toLowerCase())
          
          if (similarity >= 0.85 || containsMatch) {
            if (!matchedTerms.find(t => t.id === term.id)) {
              matchedTerms.push({
                ...term,
                matchScore: similarity,
              } as any)
            }
          }
        }
      }
    } else {
      matchedTerms = allTerms.filter(term => {
        const matchesText = term.sourceText.toLowerCase().includes(text.toLowerCase()) ||
                           term.translatedText.toLowerCase().includes(text.toLowerCase())
        const matchesSource = !sourceLang || term.sourceLang === sourceLang
        const matchesTarget = !targetLang || term.targetLang === targetLang
        const matchesDomain = !domain || term.domain === domain
        return matchesText && matchesSource && matchesTarget && matchesDomain
      })
    }
    
    if (effectiveConfig.longTermFirst) {
      matchedTerms.sort((a, b) => {
        const lenDiff = b.sourceText.length - a.sourceText.length
        if (lenDiff !== 0) return lenDiff
        const scoreA = (a as any).matchScore || 0
        const scoreB = (b as any).matchScore || 0
        return scoreB - scoreA
      })
    }
    
    return matchedTerms
  },

  async findMatchesInText(
    text: string,
    sourceLang: LanguageCode,
    targetLang: LanguageCode,
    config?: TermMatchConfig
  ): Promise<Array<{ term: TermEntry; startIndex: number; endIndex: number }>> {
    const db = await getDB()
    const allTerms = await db.getAll(STORE_TERMS)
    
    const effectiveConfig: TermMatchConfig = config || {
      enabled: true,
      useSegmentation: true,
      longTermFirst: true,
    }
    
    const validTerms = allTerms.filter(
      term => term.sourceLang === sourceLang && term.targetLang === targetLang
    )
    
    if (effectiveConfig.longTermFirst) {
      validTerms.sort((a, b) => b.sourceText.length - a.sourceText.length)
    }
    
    const matches: Array<{ term: TermEntry; startIndex: number; endIndex: number }> = []
    const usedIndices = new Set<number>()
    
    const lowerText = text.toLowerCase()
    
    for (const term of validTerms) {
      const searchText = term.sourceText.toLowerCase()
      let startIndex = 0
      
      while (startIndex < lowerText.length) {
        const index = lowerText.indexOf(searchText, startIndex)
        if (index === -1) break
        
        const endIndex = index + term.sourceText.length
        const isOverlapping = Array.from(usedIndices).some(
          used => used >= index && used < endIndex
        )
        
        if (!isOverlapping) {
          matches.push({
            term,
            startIndex: index,
            endIndex,
          })
          
          for (let i = index; i < endIndex; i++) {
            usedIndices.add(i)
          }
        }
        
        startIndex = endIndex
      }
    }
    
    if (effectiveConfig.useSegmentation && matches.length === 0) {
      const tokens = tokenize(text, sourceLang)
      
      for (const token of tokens) {
        for (const term of validTerms) {
          const similarity = calculateSimilarity(token, term.sourceText)
          if (similarity >= 0.9) {
            const index = lowerText.indexOf(token.toLowerCase())
            if (index !== -1) {
              const isOverlapping = Array.from(usedIndices).some(
                used => used >= index && used < index + token.length
              )
              
              if (!isOverlapping) {
                matches.push({
                  term,
                  startIndex: index,
                  endIndex: index + token.length,
                })
                break
              }
            }
          }
        }
      }
    }
    
    matches.sort((a, b) => a.startIndex - b.startIndex)
    
    return matches
  },

  async findExact(
    text: string,
    sourceLang: LanguageCode,
    targetLang: LanguageCode
  ): Promise<TermEntry | undefined> {
    const db = await getDB()
    const allTerms = await db.getAll(STORE_TERMS)
    return allTerms.find(
      term =>
        term.sourceText.toLowerCase() === text.toLowerCase() &&
        term.sourceLang === sourceLang &&
        term.targetLang === targetLang
    )
  },

  async clear(): Promise<void> {
    const db = await getDB()
    return db.clear(STORE_TERMS)
  },
}

export const translationMemoryDB = {
  async add(entry: Omit<TranslationMemory, 'id'>): Promise<number> {
    const db = await getDB()
    return db.add(STORE_TRANSLATION_MEMORY, entry) as Promise<number>
  },

  async update(entry: TranslationMemory): Promise<IDBValidKey> {
    const db = await getDB()
    return db.put(STORE_TRANSLATION_MEMORY, entry)
  },

  async delete(id: number): Promise<void> {
    const db = await getDB()
    return db.delete(STORE_TRANSLATION_MEMORY, id)
  },

  async get(id: number): Promise<TranslationMemory | undefined> {
    const db = await getDB()
    return db.get(STORE_TRANSLATION_MEMORY, id)
  },

  async getAll(): Promise<TranslationMemory[]> {
    const db = await getDB()
    return db.getAll(STORE_TRANSLATION_MEMORY)
  },

  async search(
    text: string,
    sourceLang: LanguageCode,
    targetLang: LanguageCode,
    config?: Partial<MemoryMatchConfig>
  ): Promise<Array<TranslationMemory & { similarity: number; matchType: 'exact' | 'fuzzy' | 'contains' }>> {
    const db = await getDB()
    const allEntries = await db.getAll(STORE_TRANSLATION_MEMORY)
    
    const effectiveConfig: MemoryMatchConfig = {
      enabled: true,
      threshold: config?.threshold ?? 0.7,
      useFuzzyMatch: config?.useFuzzyMatch ?? true,
      fuzzyMatchThreshold: config?.fuzzyMatchThreshold ?? 0.8,
    }
    
    const lowerText = text.toLowerCase().trim()
    const results: Array<TranslationMemory & { similarity: number; matchType: 'exact' | 'fuzzy' | 'contains' }> = []
    
    for (const entry of allEntries) {
      if (entry.sourceLang !== sourceLang || entry.targetLang !== targetLang) {
        continue
      }
      
      const lowerSource = entry.sourceText.toLowerCase()
      
      let similarity = 0
      let matchType: 'exact' | 'fuzzy' | 'contains' | null = null
      
      if (lowerSource === lowerText) {
        similarity = 1.0
        matchType = 'exact'
      } else if (lowerSource.includes(lowerText) || lowerText.includes(lowerSource)) {
        similarity = Math.max(0.75, calculateJaccardSimilarity(text, entry.sourceText))
        matchType = 'contains'
      } else if (effectiveConfig.useFuzzyMatch) {
        const levenshteinSim = calculateSimilarity(text, entry.sourceText)
        const jaccardSim = calculateJaccardSimilarity(text, entry.sourceText)
        similarity = (levenshteinSim * 0.6 + jaccardSim * 0.4)
        
        if (similarity >= effectiveConfig.fuzzyMatchThreshold) {
          matchType = 'fuzzy'
        }
      }
      
      if (matchType && similarity >= effectiveConfig.threshold) {
        const usageBoost = Math.min(0.1, entry.usageCount * 0.01)
        const finalScore = Math.min(1, similarity + usageBoost)
        
        results.push({
          ...entry,
          similarity: finalScore,
          matchType,
        })
      }
    }
    
    results.sort((a, b) => {
      if (a.matchType !== b.matchType) {
        const typeOrder = { exact: 0, contains: 1, fuzzy: 2 }
        return typeOrder[a.matchType] - typeOrder[b.matchType]
      }
      if (b.similarity !== a.similarity) {
        return b.similarity - a.similarity
      }
      if (b.usageCount !== a.usageCount) {
        return b.usageCount - a.usageCount
      }
      return b.lastUsedAt - a.lastUsedAt
    })
    
    return results
  },

  async findBestMatch(
    text: string,
    sourceLang: LanguageCode,
    targetLang: LanguageCode,
    config?: Partial<MemoryMatchConfig>
  ): Promise<(TranslationMemory & { similarity: number; matchType: string }) | null> {
    const results = await this.search(text, sourceLang, targetLang, config)
    return results.length > 0 ? results[0] : null
  },

  async findExact(
    text: string,
    sourceLang: LanguageCode,
    targetLang: LanguageCode
  ): Promise<TranslationMemory | undefined> {
    const db = await getDB()
    const allEntries = await db.getAll(STORE_TRANSLATION_MEMORY)
    return allEntries.find(
      entry =>
        entry.sourceText.toLowerCase() === text.toLowerCase() &&
        entry.sourceLang === sourceLang &&
        entry.targetLang === targetLang
    )
  },

  async recordUsage(id: number): Promise<void> {
    const db = await getDB()
    const entry = await db.get(STORE_TRANSLATION_MEMORY, id)
    if (entry) {
      entry.usageCount += 1
      entry.lastUsedAt = Date.now()
      await db.put(STORE_TRANSLATION_MEMORY, entry)
    }
  },

  async clear(): Promise<void> {
    const db = await getDB()
    return db.clear(STORE_TRANSLATION_MEMORY)
  },
}

export const historyDB = {
  async add(result: TranslationResult): Promise<number> {
    const db = await getDB()
    return db.add(STORE_HISTORY, { ...result, id: undefined }) as Promise<number>
  },

  async getAll(limit?: number): Promise<TranslationResult[]> {
    const db = await getDB()
    let results = await db.getAll(STORE_HISTORY)
    results = results.sort((a, b) => b.timestamp - a.timestamp)
    return limit ? results.slice(0, limit) : results
  },

  async delete(id: number): Promise<void> {
    const db = await getDB()
    return db.delete(STORE_HISTORY, id)
  },

  async clear(): Promise<void> {
    const db = await getDB()
    return db.clear(STORE_HISTORY)
  },
}

export const documentDB = {
  async add(doc: Omit<DocumentTranslation, 'id'>): Promise<number> {
    const db = await getDB()
    return db.add(STORE_DOCUMENTS, doc) as Promise<number>
  },

  async get(id: number): Promise<DocumentTranslation | undefined> {
    const db = await getDB()
    return db.get(STORE_DOCUMENTS, id)
  },

  async getAll(): Promise<DocumentTranslation[]> {
    const db = await getDB()
    const docs = await db.getAll(STORE_DOCUMENTS)
    return docs.sort((a, b) => b.createdAt - a.createdAt)
  },

  async delete(id: number): Promise<void> {
    const db = await getDB()
    return db.delete(STORE_DOCUMENTS, id)
  },

  async clear(): Promise<void> {
    const db = await getDB()
    return db.clear(STORE_DOCUMENTS)
  },
}

export const applyTermReplacements = (
  text: string,
  terms: TermEntry[]
): string => {
  let result = text
  const sortedTerms = [...terms].sort((a, b) => b.sourceText.length - a.sourceText.length)
  
  const usedRanges: Array<{ start: number; end: number }> = []
  
  for (const term of sortedTerms) {
    const escapedText = term.sourceText.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    const regex = new RegExp(escapedText, 'gi')
    
    result = result.replace(regex, (match, offset) => {
      const isOverlapping = usedRanges.some(
        range => offset < range.end && offset + match.length > range.start
      )
      
      if (isOverlapping) {
        return match
      }
      
      usedRanges.push({ start: offset, end: offset + match.length })
      return term.translatedText
    })
  }
  
  return result
}

export const applyTermReplacementsWithSegmentation = async (
  text: string,
  sourceLang: LanguageCode,
  targetLang: LanguageCode,
  config?: TermMatchConfig
): Promise<string> => {
  const matches = await termDB.findMatchesInText(text, sourceLang, targetLang, config)
  
  if (matches.length === 0) {
    return text
  }
  
  let result = text
  let offset = 0
  
  for (const match of matches) {
    const start = match.startIndex + offset
    const end = match.endIndex + offset
    const original = result.slice(start, end)
    const replacement = match.term.translatedText
    
    result = result.slice(0, start) + replacement + result.slice(end)
    offset += replacement.length - original.length
  }
  
  return result
}
