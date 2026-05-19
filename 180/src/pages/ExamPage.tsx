import React, { useState, useEffect } from 'react'
import { useSelector, useDispatch } from 'react-redux'
import { Layout, Button, Space, Drawer, Modal } from 'antd'
import { 
  MenuUnfoldOutlined, LeftOutlined, RightOutlined, FileTextOutlined,
  FullscreenOutlined, FullscreenExitOutlined
} from '@ant-design/icons'
import Timer from '../components/Timer'
import QuestionCard from '../components/QuestionCard'
import AnswerSheet from '../components/AnswerSheet'
import { RootState } from '../store'
import { setCurrentIndex, startExam, startRandomExam } from '../store/examSlice'
import { useAntiCheat } from '../hooks/useAntiCheat'

const { Header, Content } = Layout

const ExamPage: React.FC = () => {
  const dispatch = useDispatch()
  const questions = useSelector((state: RootState) => state.exam.questions)
  const currentIndex = useSelector((state: RootState) => state.exam.currentIndex)
  const startTime = useSelector((state: RootState) => state.exam.startTime)
  const isRandomMode = useSelector((state: RootState) => state.exam.isRandomMode)
  const [drawerVisible, setDrawerVisible] = useState(false)
  const [isMobile, setIsMobile] = useState(false)
  const [showStartModal, setShowStartModal] = useState(!startTime)

  const { isFullscreen, requestFullscreen, exitFullscreen, antiCheat } = useAntiCheat()

  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth <= 768)
    }
    checkMobile()
    window.addEventListener('resize', checkMobile)
    return () => window.removeEventListener('resize', checkMobile)
  }, [])

  const currentQuestion = questions[currentIndex]

  const handleStartExam = (random: boolean) => {
    setShowStartModal(false)
    if (random) {
      dispatch(startRandomExam(10))
    } else {
      dispatch(startExam())
    }
    requestFullscreen()
  }

  const handlePrev = () => {
    if (currentIndex > 0) {
      dispatch(setCurrentIndex(currentIndex - 1))
    }
  }

  const handleNext = () => {
    if (currentIndex < questions.length - 1) {
      dispatch(setCurrentIndex(currentIndex + 1))
    }
  }

  const toggleFullscreen = () => {
    if (isFullscreen) {
      exitFullscreen()
    } else {
      requestFullscreen()
    }
  }

  return (
    <Layout className="exam-layout">
      <Header className="exam-header">
        <div className="header-content">
          <div className="exam-title">
            <FileTextOutlined />
            <span>
              前端技术知识考试
              {isRandomMode && <span style={{ color: '#722ed1', marginLeft: 8, fontSize: 14 }}>（随机抽题）</span>}
            </span>
          </div>
          <Space>
            <Button
              icon={isFullscreen ? <FullscreenExitOutlined /> : <FullscreenOutlined />}
              onClick={toggleFullscreen}
            >
              {isFullscreen ? '退出全屏' : '全屏答题'}
            </Button>
            {antiCheat.tabSwitchCount > 0 && (
              <span style={{ color: '#ff4d4f', fontSize: 12 }}>
                切屏{antiCheat.tabSwitchCount}次
              </span>
            )}
            <Timer />
          </Space>
        </div>
      </Header>
      
      <Layout className="exam-body">
        <Content className="exam-content">
          <div className="question-container">
            <QuestionCard 
              question={currentQuestion} 
              questionNumber={currentIndex + 1}
            />
            
            <div className="question-navigation">
              <Space size="middle" className="nav-buttons">
                <Button 
                  onClick={handlePrev} 
                  disabled={currentIndex === 0}
                  icon={<LeftOutlined />}
                >
                  上一题
                </Button>
                <span className="progress-text">
                  {currentIndex + 1} / {questions.length}
                </span>
                <Button 
                  type="primary"
                  onClick={handleNext} 
                  disabled={currentIndex === questions.length - 1}
                >
                  下一题
                  <RightOutlined />
                </Button>
              </Space>
              
              {isMobile && (
                <Button 
                  className="mobile-sheet-btn"
                  type="primary"
                  icon={<MenuUnfoldOutlined />}
                  onClick={() => setDrawerVisible(true)}
                >
                  答题卡
                </Button>
              )}
            </div>
          </div>
        </Content>
        
        {!isMobile && (
          <div className="answer-sheet-sidebar">
            <AnswerSheet />
          </div>
        )}
      </Layout>
      
      <Drawer
        title="答题卡"
        placement="right"
        onClose={() => setDrawerVisible(false)}
        open={drawerVisible}
        width={320}
      >
        <AnswerSheet />
      </Drawer>

      <Modal
        title="开始考试"
        open={showStartModal}
        closable={false}
        maskClosable={false}
        footer={[
          <Button key="normal" type="primary" onClick={() => handleStartExam(false)}>
            标准试卷
          </Button>,
          <Button key="random" onClick={() => handleStartExam(true)}>
            随机抽题
          </Button>
        ]}
      >
        <p>欢迎参加前端技术知识考试！</p>
        <p>📋 考试说明：</p>
        <ul>
          <li>考试时长：10分钟</li>
          <li>题目数量：10道</li>
          <li>题型：单选、多选、判断</li>
          <li>满分：115分，60分及格</li>
        </ul>
        <p>⚠️ 考试纪律：</p>
        <ul>
          <li>考试期间请勿切换浏览器标签页</li>
          <li>请勿复制粘贴考试内容</li>
          <li>建议进入全屏模式答题</li>
          <li>切屏和退出全屏将被记录</li>
        </ul>
      </Modal>
    </Layout>
  )
}

export default ExamPage
