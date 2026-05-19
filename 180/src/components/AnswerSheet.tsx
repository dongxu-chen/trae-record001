import React from 'react'
import { useSelector, useDispatch } from 'react-redux'
import { Card, Space, Typography } from 'antd'
import { RootState } from '../store'
import { setCurrentIndex } from '../store/examSlice'
import { getQuestionTypeLabel } from '../utils/examUtils'

const { Text } = Typography

const AnswerSheet: React.FC = () => {
  const dispatch = useDispatch()
  const questions = useSelector((state: RootState) => state.exam.questions)
  const currentIndex = useSelector((state: RootState) => state.exam.currentIndex)
  const answers = useSelector((state: RootState) => state.exam.answers)

  const answeredCount = Object.values(answers).filter(a => a !== null).length
  const unansweredCount = questions.length - answeredCount

  const handleQuestionClick = (index: number) => {
    dispatch(setCurrentIndex(index))
  }

  const getQuestionTypeIcon = (type: string) => {
    const icons: Record<string, string> = {
      single: '单',
      multiple: '多',
      judge: '判'
    }
    return icons[type] || '?'
  }

  return (
    <Card title="答题卡" className="answer-sheet-card">
      <div className="answer-sheet-stats">
        <Space size="large" wrap>
          <span className="stat-item">
            <span className="stat-label">已答：</span>
            <Text type="success" strong>{answeredCount}</Text>
          </span>
          <span className="stat-item">
            <span className="stat-label">未答：</span>
            <Text type="danger" strong>{unansweredCount}</Text>
          </span>
          <span className="stat-item">
            <span className="stat-label">共：</span>
            <Text strong>{questions.length} 题</Text>
          </span>
        </Space>
      </div>
      
      <div className="answer-sheet-legend">
        <Space size="middle" wrap>
          <span className="legend-item">
            <span className="legend-dot answered"></span>
            <span>已答</span>
          </span>
          <span className="legend-item">
            <span className="legend-dot unanswered"></span>
            <span>未答</span>
          </span>
          <span className="legend-item">
            <span className="legend-dot current"></span>
            <span>当前</span>
          </span>
        </Space>
      </div>
      
      <div className="answer-sheet-grid">
        {questions.map((question, index) => {
          const isAnswered = answers[question.id] !== null
          const isCurrent = index === currentIndex
          
          return (
            <button
              key={question.id}
              className={`answer-sheet-item ${isAnswered ? 'answered' : 'unanswered'} ${isCurrent ? 'current' : ''}`}
              onClick={() => handleQuestionClick(index)}
              title={`${getQuestionTypeLabel(question.type)} - ${question.title.substring(0, 20)}...`}
            >
              <span className="item-type">{getQuestionTypeIcon(question.type)}</span>
              <span className="item-number">{index + 1}</span>
            </button>
          )
        })}
      </div>
    </Card>
  )
}

export default AnswerSheet
