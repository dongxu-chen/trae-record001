import { ExamState, AntiCheatRecord } from '../types'

const STORAGE_KEY = 'online_exam_state'
const WRONG_QUESTIONS_KEY = 'wrong_questions_book'

export interface PersistedExamState {
  answers: ExamState['answers']
  currentIndex: number
  startTime: number | null
  endTime: number | null
  isSubmitted: boolean
  timeRemaining: number
  questionIds: number[]
  antiCheat: AntiCheatRecord
  isRandomMode: boolean
  savedAt: number
}

export function saveExamState(state: PersistedExamState): void {
  try {
    const data = {
      ...state,
      savedAt: Date.now()
    }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data))
  } catch (e) {
    console.error('Failed to save exam state to localStorage:', e)
  }
}

export function loadExamState(): PersistedExamState | null {
  try {
    const data = localStorage.getItem(STORAGE_KEY)
    if (!data) return null
    
    const parsed = JSON.parse(data) as PersistedExamState
    
    if (!parsed || typeof parsed !== 'object') return null
    
    return parsed
  } catch (e) {
    console.error('Failed to load exam state from localStorage:', e)
    return null
  }
}

export function clearExamState(): void {
  try {
    localStorage.removeItem(STORAGE_KEY)
  } catch (e) {
    console.error('Failed to clear exam state from localStorage:', e)
  }
}

export function hasSavedExam(): boolean {
  return loadExamState() !== null
}

export interface WrongQuestionRecord {
  questionId: number
  wrongCount: number
  lastWrongTime: number
  userAnswers: Array<{
    answer: number | number[] | boolean | null
    time: number
  }>
}

export function saveWrongQuestion(questionId: number, answer: number | number[] | boolean | null): void {
  try {
    const records = getWrongQuestions()
    const existing = records.find(r => r.questionId === questionId)
    
    if (existing) {
      existing.wrongCount += 1
      existing.lastWrongTime = Date.now()
      existing.userAnswers.push({ answer, time: Date.now() })
    } else {
      records.push({
        questionId,
        wrongCount: 1,
        lastWrongTime: Date.now(),
        userAnswers: [{ answer, time: Date.now() }]
      })
    }
    
    localStorage.setItem(WRONG_QUESTIONS_KEY, JSON.stringify(records))
  } catch (e) {
    console.error('Failed to save wrong question:', e)
  }
}

export function getWrongQuestions(): WrongQuestionRecord[] {
  try {
    const data = localStorage.getItem(WRONG_QUESTIONS_KEY)
    return data ? JSON.parse(data) : []
  } catch (e) {
    console.error('Failed to get wrong questions:', e)
    return []
  }
}

export function clearWrongQuestions(): void {
  try {
    localStorage.removeItem(WRONG_QUESTIONS_KEY)
  } catch (e) {
    console.error('Failed to clear wrong questions:', e)
  }
}
