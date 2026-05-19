import { Middleware } from '@reduxjs/toolkit'
import { RootState } from '../index'
import { saveExamState } from '../../utils/storage'

const persistMiddleware: Middleware<{}, RootState> = (store) => (next) => (action) => {
  const result = next(action)
  
  const state = store.getState()
  const { exam } = state
  
  if (!exam.isSubmitted && exam.startTime) {
    saveExamState({
      answers: exam.answers,
      currentIndex: exam.currentIndex,
      startTime: exam.startTime,
      endTime: exam.endTime,
      isSubmitted: exam.isSubmitted,
      timeRemaining: exam.timeRemaining,
      questionIds: exam.questions.map(q => q.id),
      antiCheat: exam.antiCheat,
      isRandomMode: exam.isRandomMode,
      savedAt: Date.now()
    })
  }
  
  return result
}

export default persistMiddleware
