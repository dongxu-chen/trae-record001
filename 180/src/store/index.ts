import { configureStore } from '@reduxjs/toolkit'
import examReducer from './examSlice'
import persistMiddleware from './middleware/persistMiddleware'

export const store = configureStore({
  reducer: {
    exam: examReducer
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        ignoredPaths: ['exam']
      }
    }).concat(persistMiddleware)
})

export type RootState = ReturnType<typeof store.getState>
export type AppDispatch = typeof store.dispatch
