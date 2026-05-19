export type QuestionType = 'single' | 'multiple' | 'judge'

export interface KnowledgePoint {
  id: string
  name: string
  category: string
}

export interface Question {
  id: number
  type: QuestionType
  title: string
  options: string[]
  answer: number | number[] | boolean
  score: number
  analysis: string
  knowledgePoints: string[]
}

export interface AntiCheatRecord {
  tabSwitchCount: number
  tabSwitchTimestamps: number[]
  fullscreenExitCount: number
  fullscreenExitTimestamps: number[]
  copyCount: number
  pasteCount: number
  warnings: string[]
}

export interface ExamState {
  questions: Question[]
  originalQuestions: Question[]
  currentIndex: number
  answers: Record<number, number | number[] | boolean | null>
  timeRemaining: number
  isSubmitted: boolean
  startTime: number | null
  endTime: number | null
  antiCheat: AntiCheatRecord
  isRandomMode: boolean
}

export interface ExamResult {
  totalScore: number
  score: number
  correctCount: number
  wrongCount: number
  unansweredCount: number
  wrongQuestions: QuestionWithUserAnswer[]
  correctQuestions: QuestionWithUserAnswer[]
  timeUsed: number
  antiCheat: AntiCheatRecord
}

export interface QuestionWithUserAnswer extends Question {
  userAnswer: number | number[] | boolean | null
  isCorrect: boolean
}

export interface KnowledgeAnalysis {
  knowledgePoint: string
  category: string
  totalQuestions: number
  correctCount: number
  wrongCount: number
  accuracy: number
  isWeak: boolean
}

export interface ExamAnalysis {
  overallScore: number
  totalScore: number
  accuracy: number
  timeUsed: number
  knowledgeAnalysis: KnowledgeAnalysis[]
  weakPoints: KnowledgeAnalysis[]
  suggestions: string[]
}

export interface TranscriptData {
  examTitle: string
  studentName: string
  examDate: string
  score: number
  totalScore: number
  timeUsed: string
  correctCount: number
  wrongCount: number
  unansweredCount: number
  questions: QuestionWithUserAnswer[]
  analysis: ExamAnalysis
  antiCheat: AntiCheatRecord
}
