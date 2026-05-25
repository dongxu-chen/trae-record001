export type LanguageCode = 'zh' | 'en' | 'ja' | 'ko' | 'fr' | 'de'

export interface Language {
  code: LanguageCode
  name: string
  nativeName: string
}

export interface TranslationResult {
  translatedText: string
  detectedLanguage?: LanguageCode
  source: LanguageCode
  target: LanguageCode
  originalText: string
  timestamp: number
}

export interface TermEntry {
  id?: number
  sourceText: string
  translatedText: string
  sourceLang: LanguageCode
  targetLang: LanguageCode
  domain?: string
  createdAt: number
  updatedAt: number
}

export interface TranslationMemory {
  id?: number
  sourceText: string
  translatedText: string
  sourceLang: LanguageCode
  targetLang: LanguageCode
  usageCount: number
  lastUsedAt: number
  createdAt: number
}

export interface TranslateApiConfig {
  provider: 'google' | 'deepl' | 'mock'
  apiKey?: string
  endpoint?: string
}

export type FileType = 'docx' | 'pdf' | 'txt'

export interface DocumentTranslation {
  id?: number
  fileName: string
  fileType: FileType
  sourceLang: LanguageCode
  targetLang: LanguageCode
  originalContent: string
  translatedContent: string
  translatedHtml?: string
  createdAt: number
}

export interface MemoryMatchConfig {
  enabled: boolean
  threshold: number
  useFuzzyMatch: boolean
  fuzzyMatchThreshold: number
}

export interface TermMatchConfig {
  enabled: boolean
  useSegmentation: boolean
  longTermFirst: boolean
}

export interface QualityScore {
  overall: number
  fluency: number
  fidelity: number
  terminology: number
  grammar: number
  style: number
}

export interface QualityIssue {
  id: string
  type: 'fluency' | 'fidelity' | 'terminology' | 'grammar' | 'style' | 'other'
  severity: 'low' | 'medium' | 'high'
  message: string
  suggestion?: string
  sourceText?: string
  targetText?: string
  startIndex?: number
  endIndex?: number
}

export interface QualityAssessment {
  score: QualityScore
  issues: QualityIssue[]
  needsHumanReview: boolean
  reviewReason: string[]
  confidence: number
  timestamp: number
}

export type TranslationStyle = 'formal' | 'friendly' | 'neutral' | 'technical' | 'casual'

export interface StyleAnalysis {
  detectedStyle: TranslationStyle
  confidence: number
  formalityScore: number
  friendlinessScore: number
  technicalityScore: number
  consistencyScore: number
  issues: Array<{
    id: string
    type: 'inconsistency' | 'formality_mismatch' | 'tone_mismatch' | 'terminology_mismatch'
    severity: 'low' | 'medium' | 'high'
    message: string
    location?: string
    suggestion?: string
  }>
  suggestions: string[]
  styleFeatures: {
    pronouns: number
    modalVerbs: number
    contractions: number
    honorifics: number
    sentenceLength: number
    vocabularyComplexity: number
  }
}

export interface Collaborator {
  id: string
  name: string
  avatar?: string
  color: string
  isOnline: boolean
  currentSegment?: string
  lastActive: number
}

export interface CollaborativeSegment {
  id: string
  sourceText: string
  translatedText: string
  status: 'pending' | 'in_progress' | 'translated' | 'reviewed' | 'conflict'
  assignee?: string
  lastModified: number
  modifiedBy?: string
  comments?: string[]
  versions: Array<{
    text: string
    by: string
    timestamp: number
  }>
}

export interface CollaborativeSession {
  id: string
  documentId?: number
  title: string
  sourceLang: LanguageCode
  targetLang: LanguageCode
  segments: CollaborativeSegment[]
  collaborators: Collaborator[]
  status: 'active' | 'completed' | 'archived'
  createdAt: number
  updatedAt: number
  createdBy: string
}

export interface MergeResult {
  merged: CollaborativeSegment[]
  conflicts: Array<{
    segmentId: string
    versions: Array<{ text: string; by: string; timestamp: number }>
    resolution?: string
  }>
  autoMerged: number
  manualRequired: number
}
