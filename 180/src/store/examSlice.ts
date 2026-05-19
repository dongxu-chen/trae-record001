import { createSlice, PayloadAction } from '@reduxjs/toolkit'
import { ExamState, AntiCheatRecord, Question } from '../types'
import { mockQuestions, questionBank, getRandomQuestions, EXAM_DURATION } from '../data/questions'
import { loadExamState, clearExamState, PersistedExamState, saveWrongQuestion } from '../utils/storage'

const createInitialAntiCheat = (): AntiCheatRecord => ({
  tabSwitchCount: 0,
  tabSwitchTimestamps: [],
  fullscreenExitCount: 0,
  fullscreenExitTimestamps: [],
  copyCount: 0,
  pasteCount: 0,
  warnings: []
})

const getInitialAnswers = (questions: Question[]): Record<number, number | number[] | boolean | null> => {
  const answers: Record<number, number | number[] | boolean | null> = {}
  questions.forEach(q => {
    answers[q.id] = null
  })
  return answers
}

const getInitialState = (): ExamState => {
  const savedState = loadExamState()
  
  if (savedState && !savedState.isSubmitted && savedState.questionIds) {
    const now = Date.now()
    const elapsed = savedState.startTime ? Math.floor((now - savedState.startTime) / 1000) : 0
    const actualRemaining = Math.max(0, EXAM_DURATION - elapsed)
    
    const loadedQuestions = savedState.questionIds
      .map(id => questionBank.find(q => q.id === id))
      .filter((q): q is Question => q !== undefined)
    
    if (loadedQuestions.length > 0) {
      return {
        questions: loadedQuestions,
        originalQuestions: questionBank,
        currentIndex: savedState.currentIndex,
        answers: { ...getInitialAnswers(loadedQuestions), ...savedState.answers },
        timeRemaining: actualRemaining,
        isSubmitted: savedState.isSubmitted,
        startTime: savedState.startTime,
        endTime: savedState.endTime,
        antiCheat: savedState.antiCheat || createInitialAntiCheat(),
        isRandomMode: savedState.isRandomMode || false
      }
    }
  }
  
  return {
    questions: mockQuestions,
    originalQuestions: questionBank,
    currentIndex: 0,
    answers: getInitialAnswers(mockQuestions),
    timeRemaining: EXAM_DURATION,
    isSubmitted: false,
    startTime: null,
    endTime: null,
    antiCheat: createInitialAntiCheat(),
    isRandomMode: false
  }
}

const initialState: ExamState = getInitialState()

const examSlice = createSlice({
  name: 'exam',
  initialState,
  reducers: {
    setCurrentIndex: (state, action: PayloadAction<number>) => {
      state.currentIndex = action.payload
    },
    setAnswer: (state, action: PayloadAction<{ questionId: number; answer: number | number[] | boolean | null }>) => {
      state.answers[action.payload.questionId] = action.payload.answer
    },
    setTimeRemaining: (state, action: PayloadAction<number>) => {
      state.timeRemaining = action.payload
    },
    startExam: (state) => {
      if (!state.startTime) {
        state.startTime = Date.now()
      }
    },
    startRandomExam: (state, action: PayloadAction<number>) => {
      const randomQuestions = getRandomQuestions(action.payload)
      state.questions = randomQuestions
      state.answers = getInitialAnswers(randomQuestions)
      state.currentIndex = 0
      state.isSubmitted = false
      state.startTime = Date.now()
      state.endTime = null
      state.antiCheat = createInitialAntiCheat()
      state.isRandomMode = true
      clearExamState()
    },
    restoreExam: (state, action: PayloadAction<PersistedExamState>) => {
      const savedState = action.payload
      const now = Date.now()
      const elapsed = savedState.startTime ? Math.floor((now - savedState.startTime) / 1000) : 0
      const actualRemaining = Math.max(0, EXAM_DURATION - elapsed)
      
      const loadedQuestions = savedState.questionIds
        .map(id => questionBank.find(q => q.id === id))
        .filter((q): q is Question => q !== undefined)
      
      if (loadedQuestions.length > 0) {
        state.questions = loadedQuestions
        state.currentIndex = savedState.currentIndex
        state.answers = { ...getInitialAnswers(loadedQuestions), ...savedState.answers }
        state.timeRemaining = actualRemaining
        state.isSubmitted = savedState.isSubmitted
        state.startTime = savedState.startTime
        state.endTime = savedState.endTime
        state.antiCheat = savedState.antiCheat || createInitialAntiCheat()
        state.isRandomMode = savedState.isRandomMode || false
      }
    },
    recordTabSwitch: (state) => {
      state.antiCheat.tabSwitchCount += 1
      state.antiCheat.tabSwitchTimestamps.push(Date.now())
      if (state.antiCheat.tabSwitchCount >= 3) {
        state.antiCheat.warnings.push(`第${state.antiCheat.tabSwitchCount}次切屏，请注意考试纪律！`)
      }
    },
    recordFullscreenExit: (state) => {
      state.antiCheat.fullscreenExitCount += 1
      state.antiCheat.fullscreenExitTimestamps.push(Date.now())
      state.antiCheat.warnings.push(`退出全屏第${state.antiCheat.fullscreenExitCount}次`)
    },
    recordCopy: (state) => {
      state.antiCheat.copyCount += 1
    },
    recordPaste: (state) => {
      state.antiCheat.pasteCount += 1
    },
    submitExam: (state) => {
      state.isSubmitted = true
      state.endTime = Date.now()
      clearExamState()
      
      Object.entries(state.answers).forEach(([questionIdStr, userAnswer]) => {
        const questionId = parseInt(questionIdStr)
        const question = state.questions.find(q => q.id === questionId)
        if (!question) return
        
        let isCorrect = false
        if (userAnswer !== null) {
          if (question.type === 'multiple') {
            const correctAnswerIds = question.answer as number[]
            const userAnswerIds = userAnswer as number[]
            if (Array.isArray(userAnswerIds) && userAnswerIds.length === correctAnswerIds.length) {
              const sortedUserIds = [...userAnswerIds].sort((a, b) => a - b)
              const sortedCorrectIds = [...correctAnswerIds].sort((a, b) => a - b)
              isCorrect = sortedUserIds.every((id, idx) => id === sortedCorrectIds[idx])
            }
          } else {
            isCorrect = userAnswer === question.answer
          }
        }
        
        if (!isCorrect) {
          saveWrongQuestion(questionId, userAnswer)
        }
      })
    },
    resetExam: () => {
      clearExamState()
      return {
        questions: mockQuestions,
        originalQuestions: questionBank,
        currentIndex: 0,
        answers: getInitialAnswers(mockQuestions),
        timeRemaining: EXAM_DURATION,
        isSubmitted: false,
        startTime: null,
        endTime: null,
        antiCheat: createInitialAntiCheat(),
        isRandomMode: false
      }
    }
  }
})

export const {
  setCurrentIndex,
  setAnswer,
  setTimeRemaining,
  startExam,
  startRandomExam,
  restoreExam,
  recordTabSwitch,
  recordFullscreenExit,
  recordCopy,
  recordPaste,
  submitExam,
  resetExam
} = examSlice.actions

export default examSlice.reducer
