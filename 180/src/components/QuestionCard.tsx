import React from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { Radio, Checkbox, Card, Tag, Space } from 'antd'
import { CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons'
import { Question } from '../types'
import { RootState } from '../store'
import { setAnswer } from '../store/examSlice'
import { getQuestionTypeLabel, checkAnswer } from '../utils/examUtils'

interface QuestionCardProps {
  question: Question
  questionNumber: number
  showResult?: boolean
}

const QuestionCard: React.FC<QuestionCardProps> = ({ question, questionNumber, showResult = false }) => {
  const dispatch = useDispatch()
  const answers = useSelector((state: RootState) => state.exam.answers)
  const userAnswer = answers[question.id]
  
  const isAnswered = userAnswer !== null
  const isCorrect = showResult ? checkAnswer(question, userAnswer) : null

  const typeColor = {
    single: 'blue',
    multiple: 'purple',
    judge: 'green'
  }

  const handleSingleChange = (e: any) => {
    dispatch(setAnswer({ questionId: question.id, answer: e.target.value }))
  }

  const handleMultipleChange = (checkedValues: number[]) => {
    dispatch(setAnswer({ questionId: question.id, answer: checkedValues.length > 0 ? checkedValues : null }))
  }

  const handleJudgeChange = (e: any) => {
    dispatch(setAnswer({ questionId: question.id, answer: e.target.value }))
  }

  const getCorrectAnswerDisplay = () => {
    if (question.type === 'judge') {
      return question.answer ? '正确' : '错误'
    }
    if (question.type === 'multiple') {
      return (question.answer as number[]).map(idx => question.options[idx]).join('、')
    }
    return question.options[question.answer as number]
  }

  const getUserAnswerDisplay = () => {
    if (userAnswer === null) return '未作答'
    if (question.type === 'judge') {
      return userAnswer ? '正确' : '错误'
    }
    if (question.type === 'multiple') {
      if (!Array.isArray(userAnswer) || userAnswer.length === 0) return '未作答'
      return userAnswer.map(idx => question.options[idx]).join('、')
    }
    return question.options[userAnswer as number]
  }

  return (
    <Card 
      className={`question-card ${showResult && !isCorrect ? 'wrong-question' : ''}`}
      bordered={!showResult}
    >
      <div className="question-header">
        <Space size="middle">
          <span className="question-number">第 {questionNumber} 题</span>
          <Tag color={typeColor[question.type]}>{getQuestionTypeLabel(question.type)}</Tag>
          <Tag color="orange">{question.score} 分</Tag>
          {showResult && (
            isCorrect ? (
              <Tag icon={<CheckCircleOutlined />} color="success">回答正确</Tag>
            ) : (
              <Tag icon={<CloseCircleOutlined />} color="error">回答错误</Tag>
            )
          )}
        </Space>
      </div>
      
      <h3 className="question-title">{question.title}</h3>
      
      <div className="question-options">
        {question.type === 'single' && (
          <Radio.Group 
            value={userAnswer as number} 
            onChange={handleSingleChange}
            disabled={showResult}
          >
            <Space direction="vertical" className="options-space">
              {question.options.map((option, index) => (
                <Radio key={index} value={index} className="option-item">
                  <span className="option-label">{String.fromCharCode(65 + index)}.</span>
                  <span className="option-text">{option}</span>
                </Radio>
              ))}
            </Space>
          </Radio.Group>
        )}
        
        {question.type === 'multiple' && (
          <Checkbox.Group 
            value={userAnswer as number[] || []} 
            onChange={handleMultipleChange}
            disabled={showResult}
          >
            <Space direction="vertical" className="options-space">
              {question.options.map((option, index) => (
                <Checkbox key={index} value={index} className="option-item">
                  <span className="option-label">{String.fromCharCode(65 + index)}.</span>
                  <span className="option-text">{option}</span>
                </Checkbox>
              ))}
            </Space>
          </Checkbox.Group>
        )}
        
        {question.type === 'judge' && (
          <Radio.Group 
            value={userAnswer as boolean} 
            onChange={handleJudgeChange}
            disabled={showResult}
          >
            <Space className="options-space">
              <Radio value={true} className="option-item">正确</Radio>
              <Radio value={false} className="option-item">错误</Radio>
            </Space>
          </Radio.Group>
        )}
      </div>
      
      {showResult && (
        <div className="question-analysis">
          <div className="analysis-row">
            <span className="analysis-label">你的答案：</span>
            <span className={isCorrect ? 'correct-answer' : 'wrong-answer-text'}>
              {getUserAnswerDisplay()}
            </span>
          </div>
          {!isCorrect && (
            <div className="analysis-row">
              <span className="analysis-label">正确答案：</span>
              <span className="correct-answer">{getCorrectAnswerDisplay()}</span>
            </div>
          )}
          <div className="analysis-row">
            <span className="analysis-label">解析：</span>
            <span className="analysis-text">{question.analysis}</span>
          </div>
        </div>
      )}
    </Card>
  )
}

export default QuestionCard
