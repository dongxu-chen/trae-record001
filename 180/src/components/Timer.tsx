import React, { useEffect, useRef, useState } from 'react'
import { useSelector, useDispatch } from 'react-redux'
import { ClockCircleOutlined } from '@ant-design/icons'
import { Button, Modal } from 'antd'
import { RootState } from '../store'
import { submitExam, setTimeRemaining } from '../store/examSlice'
import { formatTime } from '../utils/examUtils'
import { EXAM_DURATION } from '../data/questions'

const Timer: React.FC = () => {
  const dispatch = useDispatch()
  const timeRemaining = useSelector((state: RootState) => state.exam.timeRemaining)
  const isSubmitted = useSelector((state: RootState) => state.exam.isSubmitted)
  const startTime = useSelector((state: RootState) => state.exam.startTime)
  const workerRef = useRef<Worker | null>(null)
  const [workerReady, setWorkerReady] = useState(false)

  useEffect(() => {
    if (isSubmitted || !startTime) return

    try {
      workerRef.current = new Worker(
        new URL('../workers/timer.worker.ts', import.meta.url),
        { type: 'module' }
      )
      
      workerRef.current.onmessage = (e: MessageEvent) => {
        const { type, payload } = e.data
        
        switch (type) {
          case 'TICK':
            dispatch(setTimeRemaining(payload.remaining))
            break
          case 'TIME_UP':
            Modal.warning({
              title: '考试时间结束',
              content: '考试时间已到，系统将自动提交您的试卷。',
              okText: '确定',
              onOk: () => {
                dispatch(submitExam())
              }
            })
            break
        }
      }
      
      workerRef.current.onerror = (error) => {
        console.error('Timer Worker error:', error)
      }
      
      const endTime = startTime + EXAM_DURATION * 1000
      workerRef.current.postMessage({
        type: 'START',
        payload: { duration: EXAM_DURATION, endTime }
      })
      
      setWorkerReady(true)
      
      return () => {
        if (workerRef.current) {
          workerRef.current.postMessage({ type: 'STOP' })
          workerRef.current.terminate()
          workerRef.current = null
        }
      }
    } catch (error) {
      console.error('Failed to create timer worker:', error)
      
      const savedEndTime = startTime + EXAM_DURATION * 1000
      const checkTime = () => {
        const now = Date.now()
        const remaining = Math.max(0, Math.floor((savedEndTime - now) / 1000))
        dispatch(setTimeRemaining(remaining))
        
        if (remaining <= 0) {
          Modal.warning({
            title: '考试时间结束',
            content: '考试时间已到，系统将自动提交您的试卷。',
            okText: '确定',
            onOk: () => {
              dispatch(submitExam())
            }
          })
        }
      }
      
      checkTime()
      const timer = setInterval(checkTime, 1000)
      
      return () => clearInterval(timer)
    }
  }, [dispatch, isSubmitted, startTime])

  const isWarning = timeRemaining <= 60
  const isDanger = timeRemaining <= 30

  const handleManualSubmit = () => {
    if (workerRef.current) {
      workerRef.current.postMessage({ type: 'STOP' })
    }
    
    Modal.confirm({
      title: '确认提交',
      content: '您确定要提交试卷吗？提交后将无法修改答案。',
      okText: '确认提交',
      cancelText: '继续答题',
      onOk: () => {
        dispatch(submitExam())
      }
    })
  }

  if (!startTime) return null

  return (
    <div className="timer-container">
      <div className={`timer-display ${isDanger ? 'danger' : isWarning ? 'warning' : ''}`}>
        <ClockCircleOutlined className="timer-icon" />
        <span className="timer-label">剩余时间：</span>
        <span className="timer-value">{formatTime(timeRemaining)}</span>
      </div>
      <Button 
        type="primary" 
        danger 
        onClick={handleManualSubmit}
        className="submit-btn"
      >
        交卷
      </Button>
    </div>
  )
}

export default Timer
