import { load, cut, cutForSearch } from '@node-rs/jieba'

let isLoaded = false

export async function initJieba() {
  if (!isLoaded) {
    await load()
    isLoaded = true
  }
}

export function tokenize(text: string, forSearch: boolean = false): string[] {
  if (!text) return []
  
  const words = forSearch ? cutForSearch(text) : cut(text)
  
  return words.filter(word => {
    if (word.length < 2) return false
    if (/^\d+$/.test(word)) return false
    if (/^[a-zA-Z]$/.test(word)) return false
    return true
  })
}

export function tokenizeWithWeight(text: string): Map<string, number> {
  const tokens = tokenize(text, true)
  const tokenMap = new Map<string, number>()
  
  for (const token of tokens) {
    const count = tokenMap.get(token) || 0
    tokenMap.set(token, count + 1)
  }
  
  return tokenMap
}

export function extractKeywords(text: string, topN: number = 10): string[] {
  const tokenMap = tokenizeWithWeight(text)
  const sortedTokens = Array.from(tokenMap.entries())
    .sort((a, b) => b[1] - a[1])
    .slice(0, topN)
    .map(([token]) => token)
  
  return sortedTokens
}
