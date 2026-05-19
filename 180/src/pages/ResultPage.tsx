import React, { useState, useMemo } from 'react'
import { useSelector, useDispatch } from 'react-redux'
import { Card, Statistic, Row, Col, Button, Space, Progress, Typography, Tabs, List, Tag, Modal, Input, message } from 'antd'
import { 
  TrophyOutlined, CheckCircleOutlined, CloseCircleOutlined, ClockCircleOutlined, 
  ReloadOutlined, FileTextOutlined, DownloadOutlined, PrinterOutlined,
  BookOutlined, BarChartOutlined, WarningOutlined
} from '@ant-design/icons'
import QuestionCard from '../components/QuestionCard'
import { RootState } from '../store'
import { resetExam, startRandomExam } from '../store/examSlice'
import { analyzeExam, generateTranscriptHTML, exportTranscript } from '../utils/examUtils'
import { getWrongQuestions, clearWrongQuestions } from '../utils/storage'
import { knowledgePoints } from '../data/questions'

const { Title, Text } = Typography
const { TabPane } = Tabs

const ResultPage: React.FC = () => {
  const dispatch = useDispatch()
  const { questions, answers, startTime, endTime, antiCheat, originalQuestions, isRandomMode } = useSelector((state: RootState) => state.exam)
  const [showNameModal, setShowNameModal] = useState(false)
  
  const calculateResult = () => {
    let score = 0
    let correctCount = 0
    let wrongCount = 0
    let unansweredCount = 0
    const details: any[] = []
    
    questions.forEach(question => {
      const userAnswer = answers[question.id]
      const isCorrect = checkAnswer(question, userAnswer)
      
      if (userAnswer === undefined || userAnswer === null) {
        unansweredCount++
      } else if (isCorrect) {
        correctCount++
        score += question.score
      } else {
        wrongCount++
      }
      
      details.push({
        questionId: question.id,
        userAnswer,
        isCorrect,
        score: isCorrect ? question.score : 0
      })
    })
    
    const totalScore = questions.reduce((sum, q) => sum + q.score, 0)
    const timeUsed = startTime && endTime ? Math.floor((endTime - startTime) / 1000) : 0
    
    return {
      score,
      totalScore,
      correctCount,
      wrongCount,
      unansweredCount,
      details,
      timeUsed,
      endTime: endTime || Date.now(),
      antiCheat
    }
  }
  
  const checkAnswer = (question: any, userAnswer: any): boolean => {
    if (question.type === 'multiple') {
      if (!Array.isArray(userAnswer) || !Array.isArray(question.answer)) {
        return false
      }
      const sortedUser = [...userAnswer].sort()
      const sortedCorrect = [...question.answer].sort()
      return JSON.stringify(sortedUser) === JSON.stringify(sortedCorrect)
    } else {
      return userAnswer === question.answer
    }
  }
  
  const result = useMemo(() => calculateResult(), [questions, answers, startTime, endTime, antiCheat])
  const analysis = useMemo(() => analyzeExam(result, originalQuestions), [result, originalQuestions])
  const wrongBookRecords = useMemo(() => getWrongQuestions(), [])
  
  const percentage = Math.round((result.score / result.totalScore) * 100)
  const isPassed = percentage >= 60
  
  const handleRestart = () => {
    dispatch(resetExam())
  }
  
  const handleRandomExam = () => {
    dispatch(startRandomExam(10))
  }
  
  const handleExport = () => {
    const examMode = isRandomMode ? '随机抽题' : '标准模式'
    const transcriptHTML = generateTranscriptHTML(result, analysis, originalQuestions, examMode)
    
    const newWindow = window.open('', '_blank')
    if (newWindow) {
      newWindow.document.write(transcriptHTML)
      newWindow.document.close()
      message.success('成绩单已打开，可直接打印或保存')
    } else {
      exportTranscript(transcriptHTML, '前端技术知识考试成绩单')
      message.success('成绩单下载成功')
    }
  }
  
  const handleClearWrongBook = () => {
    Modal.confirm({
      title: '确认清空错题本',
      content: '确定要清空所有错题记录吗？此操作不可恢复。',
      okText: '确认清空',
      cancelText: '取消',
      onOk: () => {
        clearWrongQuestions()
        message.success('错题本已清空')
        window.location.reload()
      }
    })
  }
  
  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}分${secs}秒`
  }

  return (
    <div className="result-page">
      <Card className="result-header-card">
        <div className="result-header">
          <div className="result-icon">
            <TrophyOutlined className={isPassed ? 'passed' : 'failed'} />
          </div>
          <div className="result-title">
            <Title level={2} className={isPassed ? 'passed-text' : 'failed-text'}>
              {isPassed ? '恭喜您，考试通过！' : '很遗憾，未能通过考试'}
            </Title>
            <Text type="secondary">继续努力，加油！</Text>
          </div>
        </div>
        
        <div className="score-section">
          <Progress 
            type="circle" 
            percent={percentage} 
            strokeColor={isPassed ? '#52c41a' : '#ff4d4f'}
            format={(percent) => (
              <span className="score-text">
                <span className="score-number">{result.score}</span>
                <span className="score-total">/{result.totalScore}</span>
              </span>
            )}
            width={140}
          />
        </div>
        
        <Row gutter={[16, 16]} className="stats-row">
          <Col xs={12} sm={6}>
            <Statistic 
              title="答对题数" 
              value={result.correctCount} 
              prefix={<CheckCircleOutlined style={{ color: '#52c41a' }} />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Col>
          <Col xs={12} sm={6}>
            <Statistic 
              title="答错题数" 
              value={result.wrongCount} 
              prefix={<CloseCircleOutlined style={{ color: '#ff4d4f' }} />}
              valueStyle={{ color: '#ff4d4f' }}
            />
          </Col>
          <Col xs={12} sm={6}>
            <Statistic 
              title="未答题数" 
              value={result.unansweredCount}
              prefix={<WarningOutlined style={{ color: '#faad14' }} />}
              valueStyle={{ color: '#faad14' }}
            />
          </Col>
          <Col xs={12} sm={6}>
            <Statistic 
              title="用时" 
              value={formatTime(result.timeUsed)} 
              prefix={<ClockCircleOutlined style={{ color: '#1890ff' }} />}
            />
          </Col>
        </Row>
        
        {antiCheat.tabSwitchCount > 0 && (
          <Card size="small" style={{ marginTop: 16, background: '#fff1f0', borderColor: '#ffa39e' }}>
            <Space>
              <WarningOutlined style={{ color: '#ff4d4f' }} />
              <Text type="danger">
                考试期间切屏 {antiCheat.tabSwitchCount} 次，退出全屏 {antiCheat.fullscreenExitCount} 次
              </Text>
            </Space>
          </Card>
        )}
        
        <div className="action-buttons">
          <Space wrap>
            <Button 
              type="primary" 
              size="large" 
              icon={<ReloadOutlined />}
              onClick={handleRestart}
            >
              重新考试
            </Button>
            <Button 
              size="large" 
              icon={<BarChartOutlined />}
              onClick={handleRandomExam}
            >
              随机抽题
            </Button>
            <Button 
              size="large" 
              icon={<DownloadOutlined />}
              onClick={handleExport}
            >
              导出/打印成绩单
            </Button>
          </Space>
        </div>
      </Card>
      
      <Card className="result-tabs-card">
        <Tabs defaultActiveKey="analysis">
          <TabPane 
            tab={<span><BarChartOutlined />试卷分析</span>} 
            key="analysis"
          >
            <Card 
              title="知识点掌握情况" 
              size="small"
              style={{ marginBottom: 16 }}
            >
              {analysis.knowledgeAnalysis.length > 0 ? (
                <List
                  dataSource={analysis.knowledgeAnalysis}
                  renderItem={(item) => (
                    <List.Item key={item.knowledgePoint}>
                      <List.Item.Meta
                        title={
                          <Space>
                            <span>{item.knowledgePoint}</span>
                            <Tag color="blue">{item.category}</Tag>
                            {item.isWeak && <Tag color="red">薄弱</Tag>}
                          </Space>
                        }
                        description={
                          <Space direction="vertical" style={{ width: '100%' }}>
                            <div>
                              <Text type="secondary">
                                共{item.totalQuestions}题，正确{item.correctCount}题，错误{item.wrongCount}题
                              </Text>
                            </div>
                            <Progress 
                              percent={item.accuracy} 
                              size="small"
                              strokeColor={item.isWeak ? '#ff4d4f' : '#52c41a'}
                              showInfo={false}
                              style={{ maxWidth: 200 }}
                            />
                            <Text strong className={item.isWeak ? 'wrong-answer-text' : 'correct-answer'}>
                              正确率 {item.accuracy}%
                            </Text>
                          </Space>
                        }
                      />
                    </List.Item>
                  )}
                />
              ) : (
                <Text type="secondary">暂无知识点分析数据</Text>
              )}
            </Card>
            
            {analysis.suggestions.length > 0 && (
              <Card 
                title="学习建议" 
                size="small"
                style={{ background: '#fffbe6', borderColor: '#ffe58f' }}
              >
                <List
                  dataSource={analysis.suggestions}
                  renderItem={(item, idx) => (
                    <List.Item>
                      <Space>
                        <CheckCircleOutlined style={{ color: '#faad14' }} />
                        <span>{item}</span>
                      </Space>
                    </List.Item>
                  )}
                />
              </Card>
            )}
          </TabPane>
          
          <TabPane 
            tab={<span><FileTextOutlined />答题详情</span>} 
            key="questions"
          >
            {result.wrongQuestions.length > 0 && (
              <Card 
                title={
                  <Space>
                    <CloseCircleOutlined style={{ color: '#ff4d4f' }} />
                    <span>错题解析（共 {result.wrongQuestions.length} 题）</span>
                  </Space>
                }
                size="small"
                style={{ marginBottom: 16 }}
              >
                <Space direction="vertical" size="large" style={{ width: '100%' }}>
                  {result.wrongQuestions.map((question, idx) => {
                    const originalIndex = questions.findIndex(q => q.id === question.id)
                    return (
                      <div key={question.id} className="wrong-question-item">
                        <QuestionCard 
                          question={question} 
                          questionNumber={originalIndex + 1}
                          showResult={true}
                        />
                      </div>
                    )
                  })}
                </Space>
              </Card>
            )}
            
            {result.correctQuestions.length > 0 && (
              <Card 
                title={
                  <Space>
                    <CheckCircleOutlined style={{ color: '#52c41a' }} />
                    <span>答对题目（共 {result.correctQuestions.length} 题）</span>
                  </Space>
                }
                size="small"
              >
                <Space direction="vertical" size="large" style={{ width: '100%' }}>
                  {result.correctQuestions.map((question, idx) => {
                    const originalIndex = questions.findIndex(q => q.id === question.id)
                    return (
                      <div key={question.id} className="correct-question-item">
                        <QuestionCard 
                          question={question} 
                          questionNumber={originalIndex + 1}
                          showResult={true}
                        />
                      </div>
                    )
                  })}
                </Space>
              </Card>
            )}
            
            {result.wrongQuestions.length === 0 && (
              <Card className="all-correct-card">
                <div className="all-correct-content">
                  <CheckCircleOutlined className="all-correct-icon" />
                  <Title level={4}>太棒了！全部答对！</Title>
                  <Text type="secondary">您已完全掌握这些知识</Text>
                </div>
              </Card>
            )}
          </TabPane>
          
          <TabPane 
            tab={<span><BookOutlined />错题本</span>} 
            key="wrongbook"
          >
            <Card 
              extra={
                <Button 
                  size="small" 
                  danger 
                  onClick={handleClearWrongBook}
                  disabled={wrongBookRecords.length === 0}
                >
                  清空错题本
                </Button>
              }
              size="small"
            >
              {getWrongBookQuestions().length > 0 ? (
                <List
                  dataSource={getWrongBookQuestions()}
                  renderItem={(item) => (
                    <List.Item key={item.questionId}>
                      <List.Item.Meta
                        title={
                          <Space>
                            <Tag color="red">错误{item.wrongCount}次</Tag>
                            <span>{item.question.title}</span>
                          </Space>
                        }
                        description={
                          <div>
                            <Text type="secondary">
                              知识点：{item.question.knowledgePoints
                                .map(kpId => knowledgePoints.find(kp => kp.id === kpId)?.name || kpId)
                                .join('、')}
                            </Text>
                            <br />
                            <Text type="secondary">
                              最近错误：{new Date(item.lastWrongTime).toLocaleString('zh-CN')}
                            </Text>
                          </div>
                        }
                      />
                    </List.Item>
                  )}
                />
              ) : (
                <div style={{ textAlign: 'center', padding: '40px 0' }}>
                  <Text type="secondary">暂无错题记录，继续保持！</Text>
                </div>
              )}
            </Card>
          </TabPane>
        </Tabs>
      </Card>
      
    </div>
  )
}

export default ResultPage
