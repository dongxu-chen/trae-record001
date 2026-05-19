import { Question, ExamResult, ExamAnalysis, KnowledgeAnalysis, QuestionType } from '../types'

export function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
}

export function getQuestionTypeLabel(type: QuestionType): string {
  const labels: Record<QuestionType, string> = {
    single: '单选题',
    multiple: '多选题',
    judge: '判断题'
  }
  return labels[type] || type
}

export function checkAnswer(question: Question, userAnswer: number | number[] | boolean | null): boolean {
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

export function calculateScore(question: Question, userAnswer: string | string[]): number {
  const isCorrect = checkAnswer(question, userAnswer)
  return isCorrect ? question.score : 0
}

export function analyzeExam(result: any, allQuestions: Question[]): ExamAnalysis {
  const knowledgeStats: Record<string, { total: number; correct: number; wrong: number; category: string }> = {}
  
  result.details.forEach((detail: any) => {
    const question = allQuestions.find(q => q.id === detail.questionId)
    if (question) {
      question.knowledgePoints.forEach(kpId => {
        if (!knowledgeStats[kpId]) {
          knowledgeStats[kpId] = {
            total: 0,
            correct: 0,
            wrong: 0,
            category: '其他'
          }
        }
        knowledgeStats[kpId].total++
        if (detail.isCorrect) {
          knowledgeStats[kpId].correct++
        } else {
          knowledgeStats[kpId].wrong++
        }
      })
    }
  })
  
  const knowledgeAnalysis: KnowledgeAnalysis[] = Object.entries(knowledgeStats).map(([knowledgePoint, stats]) => ({
    knowledgePoint,
    category: stats.category,
    totalQuestions: stats.total,
    correctCount: stats.correct,
    wrongCount: stats.wrong,
    accuracy: stats.total > 0 ? Math.round((stats.correct / stats.total) * 100) : 0,
    isWeak: stats.total > 0 ? stats.correct / stats.total < 0.6 : false
  }))
  
  const weakPoints = knowledgeAnalysis.filter(k => k.isWeak)
  const overallAccuracy = result.details.length > 0 
    ? Math.round((result.details.filter((d: any) => d.isCorrect).length / result.details.length) * 100) 
    : 0
  
  const suggestions: string[] = []
  
  if (overallAccuracy < 60) {
    suggestions.push('整体掌握程度较低，建议系统性复习基础知识')
  } else if (overallAccuracy < 80) {
    suggestions.push('整体掌握程度中等，重点攻克薄弱知识点')
  } else {
    suggestions.push('整体掌握良好，可以挑战更高难度题目')
  }
  
  if (weakPoints.length > 0) {
    suggestions.push(`以下知识点需要加强：${weakPoints.map(w => w.knowledgePoint).join('、')}`)
  }
  
  return {
    overallScore: result.score,
    totalScore: result.totalScore,
    accuracy: overallAccuracy,
    timeUsed: result.timeUsed,
    knowledgeAnalysis,
    weakPoints,
    suggestions
  }
}

export function generateTranscriptHTML(
  result: any, 
  analysis: ExamAnalysis, 
  allQuestions: Question[],
  examMode: string = '标准模式'
): string {
  const examTime = new Date(result.endTime).toLocaleString('zh-CN')
  
  const getScoreLevel = (score: number, total: number): string => {
    const percentage = (score / total) * 100
    if (percentage >= 90) return '优秀'
    if (percentage >= 80) return '良好'
    if (percentage >= 60) return '及格'
    return '不及格'
  }
  
  const level = getScoreLevel(result.score, result.totalScore)
  const levelColor = result.score >= 60 ? '#52c41a' : '#ff4d4f'
  
  return `
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>考试成绩单</title>
  <style>
    * {
      margin: 0;
      padding: 0;
      box-sizing: border-box;
    }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
      background: #f5f5f5;
      padding: 20px;
      color: #333;
    }
    .transcript-container {
      max-width: 800px;
      margin: 0 auto;
      background: white;
      border-radius: 12px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.1);
      overflow: hidden;
    }
    .transcript-header {
      background: linear-gradient(135deg, #1890ff 0%, #096dd9 100%);
      color: white;
      padding: 30px;
      text-align: center;
    }
    .transcript-title {
      font-size: 24px;
      font-weight: bold;
      margin-bottom: 8px;
    }
    .transcript-subtitle {
      font-size: 14px;
      opacity: 0.9;
    }
    .transcript-body {
      padding: 30px;
    }
    .score-section {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 40px;
      padding: 30px;
      background: #f8f9fa;
      border-radius: 8px;
      margin-bottom: 24px;
    }
    .score-display {
      text-align: center;
    }
    .score-number {
      font-size: 48px;
      font-weight: bold;
      color: ${levelColor};
    }
    .score-total {
      font-size: 14px;
      color: #999;
      margin-top: 4px;
    }
    .score-info {
      flex: 1;
    }
    .info-row {
      display: flex;
      padding: 8px 0;
      border-bottom: 1px dashed #eee;
    }
    .info-row:last-child {
      border-bottom: none;
    }
    .info-label {
      width: 100px;
      color: #666;
      font-size: 14px;
    }
    .info-value {
      flex: 1;
      font-weight: 500;
      color: #333;
    }
    .level-badge {
      display: inline-block;
      padding: 4px 12px;
      background: ${levelColor}15;
      color: ${levelColor};
      border-radius: 4px;
      font-size: 14px;
      font-weight: 500;
    }
    .section-title {
      font-size: 16px;
      font-weight: 600;
      margin: 24px 0 16px;
      padding-left: 12px;
      border-left: 4px solid #1890ff;
    }
    .stats-grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 12px;
      margin-bottom: 16px;
    }
    .stat-card {
      padding: 16px;
      background: #f8f9fa;
      border-radius: 8px;
      text-align: center;
    }
    .stat-value {
      font-size: 24px;
      font-weight: bold;
      color: #1890ff;
    }
    .stat-label {
      font-size: 13px;
      color: #999;
      margin-top: 4px;
    }
    .knowledge-list {
      margin-bottom: 16px;
    }
    .knowledge-item {
      display: flex;
      align-items: center;
      padding: 12px;
      background: #f8f9fa;
      border-radius: 8px;
      margin-bottom: 8px;
    }
    .knowledge-name {
      flex: 1;
      font-weight: 500;
    }
    .knowledge-category {
      padding: 2px 8px;
      background: #e6f7ff;
      color: #1890ff;
      border-radius: 4px;
      font-size: 12px;
      margin-right: 12px;
    }
    .progress-bar {
      width: 120px;
      height: 8px;
      background: #eee;
      border-radius: 4px;
      overflow: hidden;
      margin: 0 12px;
    }
    .progress-fill {
      height: 100%;
      background: linear-gradient(90deg, #52c41a, #73d13d);
      transition: width 0.3s;
    }
    .progress-fill.medium {
      background: linear-gradient(90deg, #faad14, #ffc53d);
    }
    .progress-fill.weak {
      background: linear-gradient(90deg, #ff4d4f, #ff7875);
    }
    .accuracy-text {
      width: 50px;
      text-align: right;
      font-weight: 500;
    }
    .suggestion-item {
      padding: 12px 16px;
      background: #fffbe6;
      border-left: 4px solid #faad14;
      border-radius: 4px;
      margin-bottom: 8px;
      font-size: 14px;
    }
    .questions-section {
      margin-top: 24px;
    }
    .question-item {
      padding: 16px;
      border: 1px solid #eee;
      border-radius: 8px;
      margin-bottom: 16px;
    }
    .question-header {
      display: flex;
      align-items: flex-start;
      gap: 12px;
      margin-bottom: 12px;
    }
    .question-number {
      flex-shrink: 0;
      width: 32px;
      height: 32px;
      background: #1890ff;
      color: white;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: bold;
      font-size: 14px;
    }
    .question-number.wrong {
      background: #ff4d4f;
    }
    .question-content {
      flex: 1;
    }
    .question-type-tag {
      display: inline-block;
      padding: 2px 8px;
      background: #f0f0f0;
      border-radius: 4px;
      font-size: 12px;
      margin-left: 8px;
    }
    .question-text {
      margin-top: 8px;
      line-height: 1.6;
    }
    .options-list {
      margin: 12px 0;
    }
    .option-item {
      padding: 8px 12px;
      margin-bottom: 4px;
      border-radius: 4px;
      font-size: 14px;
    }
    .option-item.correct {
      background: #f6ffed;
      color: #389e0d;
    }
    .option-item.wrong {
      background: #fff1f0;
      color: #cf1322;
    }
    .answer-section {
      padding-top: 12px;
      border-top: 1px dashed #eee;
    }
    .answer-row {
      display: flex;
      gap: 8px;
      margin-bottom: 8px;
      font-size: 14px;
    }
    .answer-label {
      color: #666;
      min-width: 80px;
    }
    .answer-value {
      flex: 1;
    }
    .explanation-section {
      margin-top: 12px;
      padding: 12px;
      background: #f8f9fa;
      border-radius: 4px;
    }
    .explanation-title {
      font-weight: 600;
      margin-bottom: 8px;
      color: #1890ff;
    }
    .explanation-text {
      font-size: 14px;
      line-height: 1.6;
      color: #666;
    }
    .transcript-footer {
      text-align: center;
      padding: 24px;
      color: #999;
      font-size: 12px;
      border-top: 1px solid #eee;
    }
    @media print {
      body {
        background: white;
        padding: 0;
      }
      .transcript-container {
        box-shadow: none;
      }
    }
  </style>
</head>
<body>
  <div class="transcript-container">
    <div class="transcript-header">
      <div class="transcript-title">前端技术知识考试成绩单</div>
      <div class="transcript-subtitle">Frontend Technical Exam Transcript</div>
    </div>
    
    <div class="transcript-body">
      <div class="score-section">
        <div class="score-display">
          <div class="score-number">${result.score}</div>
          <div class="score-total">/ ${result.totalScore} 分</div>
        </div>
        <div class="score-info">
          <div class="info-row">
            <span class="info-label">考试模式</span>
            <span class="info-value">${examMode}</span>
          </div>
          <div class="info-row">
            <span class="info-label">成绩等级</span>
            <span class="info-value"><span class="level-badge">${level}</span></span>
          </div>
          <div class="info-row">
            <span class="info-label">正确率</span>
            <span class="info-value">${analysis.accuracy}%</span>
          </div>
          <div class="info-row">
            <span class="info-label">答题用时</span>
            <span class="info-value">${Math.floor(result.timeUsed / 60)}分${result.timeUsed % 60}秒</span>
          </div>
          <div class="info-row">
            <span class="info-label">考试时间</span>
            <span class="info-value">${examTime}</span>
          </div>
        </div>
      </div>
      
      <div class="section-title">答题统计</div>
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-value">${result.details.length}</div>
          <div class="stat-label">总题数</div>
        </div>
        <div class="stat-card">
          <div class="stat-value" style="color: #52c41a;">${result.details.filter(d => d.isCorrect).length}</div>
          <div class="stat-label">答对题数</div>
        </div>
        <div class="stat-card">
          <div class="stat-value" style="color: #ff4d4f;">${result.details.filter(d => !d.isCorrect).length}</div>
          <div class="stat-label">答错题数</div>
        </div>
        <div class="stat-card">
          <div class="stat-value" style="color: #faad14;">${analysis.weakPoints.length}</div>
          <div class="stat-label">薄弱知识点</div>
        </div>
      </div>
      
      <div class="section-title">知识点掌握情况</div>
      <div class="knowledge-list">
        ${analysis.knowledgeAnalysis.map(k => `
          <div class="knowledge-item">
            <span class="knowledge-name">${k.knowledgePoint}</span>
            <span class="knowledge-category">${k.category}</span>
            <div class="progress-bar">
              <div class="progress-fill ${k.isWeak ? 'weak' : k.accuracy >= 80 ? 'good' : 'medium'}" style="width: ${k.accuracy}%;"></div>
            </div>
            <span class="accuracy-text" style="color: ${k.isWeak ? '#ff4d4f' : k.accuracy >= 80 ? '#52c41a' : '#faad14'}">${k.accuracy}%</span>
          </div>
        `).join('')}
      </div>
      
      <div class="section-title">学习建议</div>
      <div>
        ${analysis.suggestions.map(s => `<div class="suggestion-item">💡 ${s}</div>`).join('')}
      </div>
      
      <div class="section-title">答题详情</div>
      <div class="questions-section">
        ${result.details.map((detail: any, index: number) => {
          const question = allQuestions.find(q => q.id === detail.questionId)
          if (!question) return ''
          const typeName = question.type === 'single' ? '单选题' : question.type === 'multiple' ? '多选题' : '判断题'
          const options = question.options.map((opt: string, optIdx: number) => {
            const isCorrect = Array.isArray(question.answer) 
              ? question.answer.includes(optIdx)
              : optIdx === question.answer
            const isUserSelected = Array.isArray(detail.userAnswer)
              ? detail.userAnswer.includes(optIdx)
              : optIdx === detail.userAnswer
            let className = 'option-item'
            if (isCorrect) className += ' correct'
            else if (isUserSelected) className += ' wrong'
            const label = String.fromCharCode(65 + optIdx)
            return `<div class="${className}">${label}. ${opt} ${isCorrect ? ' ✓' : (isUserSelected ? ' ✗' : '')}</div>`
          }).join('')
          
          const getAnswerLabel = (answer: any) => {
            if (answer === null || answer === undefined) return '未作答'
            if (Array.isArray(answer)) {
              return answer.map((a: number) => String.fromCharCode(65 + a)).join('、')
            }
            if (typeof answer === 'boolean') {
              return answer ? '正确' : '错误'
            }
            return String.fromCharCode(65 + answer)
          }
          
          const userAnswerText = getAnswerLabel(detail.userAnswer)
          const correctAnswerText = getAnswerLabel(question.answer)
          
          return `
            <div class="question-item">
              <div class="question-header">
                <div class="question-number ${detail.isCorrect ? '' : 'wrong'}">${index + 1}</div>
                <div class="question-content">
                  <span class="question-type-tag">${typeName}</span>
                  <span style="color: ${detail.isCorrect ? '#52c41a' : '#ff4d4f'}; font-weight: 500;">
                    ${detail.isCorrect ? '正确' : '错误'}
                  </span>
                  <div class="question-text">${question.title}</div>
                </div>
              </div>
              <div class="options-list">
                ${options}
              </div>
              <div class="answer-section">
                <div class="answer-row">
                  <span class="answer-label">你的答案</span>
                  <span class="answer-value" style="color: ${detail.isCorrect ? '#52c41a' : '#ff4d4f'}; font-weight: 500;">${userAnswerText}</span>
                </div>
                <div class="answer-row">
                  <span class="answer-label">正确答案</span>
                  <span class="answer-value" style="color: #52c41a; font-weight: 500;">${correctAnswerText}</span>
                </div>
              </div>
              <div class="explanation-section">
                <div class="explanation-title">📝 解析</div>
                <div class="explanation-text">${question.analysis}</div>
              </div>
            </div>
          `
        }).join('')}
      </div>
    </div>
    
    <div class="transcript-footer">
      <p>本成绩单由在线考试系统自动生成</p>
      <p>Generated by Online Exam System</p>
    </div>
  </div>
</body>
</html>
  `
}

export function exportTranscript(transcriptHTML: string, filename: string = '成绩单') {
  const blob = new Blob([transcriptHTML], { type: 'text/html;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `${filename}_${new Date().toLocaleDateString('zh-CN').replace(/\//g, '-')}.html`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}
