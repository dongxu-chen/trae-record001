import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react'
import { LanguageCode, TranslateApiConfig, MemoryMatchConfig, TermMatchConfig } from '../types'
import { initDB } from '../services/database'

interface AppContextType {
  sourceLang: LanguageCode
  setSourceLang: (lang: LanguageCode) => void
  targetLang: LanguageCode
  setTargetLang: (lang: LanguageCode) => void
  apiConfig: TranslateApiConfig
  setApiConfig: (config: TranslateApiConfig) => void
  useTerms: boolean
  setUseTerms: (value: boolean) => void
  useMemory: boolean
  setUseMemory: (value: boolean) => void
  memoryConfig: MemoryMatchConfig
  setMemoryConfig: (config: MemoryMatchConfig) => void
  termConfig: TermMatchConfig
  setTermConfig: (config: TermMatchConfig) => void
  dbReady: boolean
  swapLanguages: () => void
}

const AppContext = createContext<AppContextType | undefined>(undefined)

const STORAGE_KEYS = {
  SOURCE_LANG: 'translator_source_lang',
  TARGET_LANG: 'translator_target_lang',
  API_CONFIG: 'translator_api_config',
  USE_TERMS: 'translator_use_terms',
  USE_MEMORY: 'translator_use_memory',
  MEMORY_CONFIG: 'translator_memory_config',
  TERM_CONFIG: 'translator_term_config',
}

const defaultApiConfig: TranslateApiConfig = {
  provider: 'mock',
}

const defaultMemoryConfig: MemoryMatchConfig = {
  enabled: true,
  threshold: 0.7,
  useFuzzyMatch: true,
  fuzzyMatchThreshold: 0.8,
}

const defaultTermConfig: TermMatchConfig = {
  enabled: true,
  useSegmentation: true,
  longTermFirst: true,
}

export const AppProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [sourceLang, setSourceLang] = useState<LanguageCode>(() => {
    const saved = localStorage.getItem(STORAGE_KEYS.SOURCE_LANG)
    return (saved as LanguageCode) || 'zh'
  })
  
  const [targetLang, setTargetLang] = useState<LanguageCode>(() => {
    const saved = localStorage.getItem(STORAGE_KEYS.TARGET_LANG)
    return (saved as LanguageCode) || 'en'
  })
  
  const [apiConfig, setApiConfig] = useState<TranslateApiConfig>(() => {
    const saved = localStorage.getItem(STORAGE_KEYS.API_CONFIG)
    return saved ? JSON.parse(saved) : defaultApiConfig
  })
  
  const [useTerms, setUseTerms] = useState<boolean>(() => {
    const saved = localStorage.getItem(STORAGE_KEYS.USE_TERMS)
    return saved !== null ? JSON.parse(saved) : true
  })
  
  const [useMemory, setUseMemory] = useState<boolean>(() => {
    const saved = localStorage.getItem(STORAGE_KEYS.USE_MEMORY)
    return saved !== null ? JSON.parse(saved) : true
  })
  
  const [memoryConfig, setMemoryConfig] = useState<MemoryMatchConfig>(() => {
    const saved = localStorage.getItem(STORAGE_KEYS.MEMORY_CONFIG)
    return saved ? JSON.parse(saved) : defaultMemoryConfig
  })
  
  const [termConfig, setTermConfig] = useState<TermMatchConfig>(() => {
    const saved = localStorage.getItem(STORAGE_KEYS.TERM_CONFIG)
    return saved ? JSON.parse(saved) : defaultTermConfig
  })
  
  const [dbReady, setDbReady] = useState(false)

  useEffect(() => {
    localStorage.setItem(STORAGE_KEYS.SOURCE_LANG, sourceLang)
  }, [sourceLang])

  useEffect(() => {
    localStorage.setItem(STORAGE_KEYS.TARGET_LANG, targetLang)
  }, [targetLang])

  useEffect(() => {
    localStorage.setItem(STORAGE_KEYS.API_CONFIG, JSON.stringify(apiConfig))
  }, [apiConfig])

  useEffect(() => {
    localStorage.setItem(STORAGE_KEYS.USE_TERMS, JSON.stringify(useTerms))
  }, [useTerms])

  useEffect(() => {
    localStorage.setItem(STORAGE_KEYS.USE_MEMORY, JSON.stringify(useMemory))
  }, [useMemory])

  useEffect(() => {
    localStorage.setItem(STORAGE_KEYS.MEMORY_CONFIG, JSON.stringify(memoryConfig))
  }, [memoryConfig])

  useEffect(() => {
    localStorage.setItem(STORAGE_KEYS.TERM_CONFIG, JSON.stringify(termConfig))
  }, [termConfig])

  useEffect(() => {
    const init = async () => {
      try {
        await initDB()
        setDbReady(true)
      } catch (error) {
        console.error('Failed to initialize database:', error)
      }
    }
    init()
  }, [])

  const swapLanguages = useCallback(() => {
    setSourceLang(prev => {
      const newTarget = prev
      setTargetLang(newTarget)
      return targetLang
    })
  }, [targetLang])

  return (
    <AppContext.Provider
      value={{
        sourceLang,
        setSourceLang,
        targetLang,
        setTargetLang,
        apiConfig,
        setApiConfig,
        useTerms,
        setUseTerms,
        useMemory,
        setUseMemory,
        memoryConfig,
        setMemoryConfig,
        termConfig,
        setTermConfig,
        dbReady,
        swapLanguages,
      }}
    >
      {children}
    </AppContext.Provider>
  )
}

export const useApp = (): AppContextType => {
  const context = useContext(AppContext)
  if (context === undefined) {
    throw new Error('useApp must be used within an AppProvider')
  }
  return context
}
