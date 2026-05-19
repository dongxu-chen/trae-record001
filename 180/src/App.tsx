import React from 'react'
import { useSelector } from 'react-redux'
import { RootState } from './store'
import ExamPage from './pages/ExamPage'
import ResultPage from './pages/ResultPage'
import './styles/index.css'

const App: React.FC = () => {
  const isSubmitted = useSelector((state: RootState) => state.exam.isSubmitted)
  
  return (
    <div className="app">
      {isSubmitted ? <ResultPage /> : <ExamPage />}
    </div>
  )
}

export default App
