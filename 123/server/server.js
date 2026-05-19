const express = require('express');
const http = require('http');
const { Server } = require('socket.io');
const cors = require('cors');
const fs = require('fs');
const path = require('path');
require('dotenv').config();

const janusController = require('./janusController');

const app = express();
app.use(cors());
app.use(express.json({ limit: '500mb' }));

const server = http.createServer(app);
const io = new Server(server, {
  cors: {
    origin: '*',
    methods: ['GET', 'POST']
  },
  pingTimeout: 60000,
  pingInterval: 25000,
  maxHttpBufferSize: 1e8
});

const exams = new Map();
const examinees = new Map();
const proctors = new Map();
const recordings = new Map();
const examQuestions = new Map();
const userAnswers = new Map();

const recordingsDir = path.join(__dirname, 'recordings');
if (!fs.existsSync(recordingsDir)) {
  fs.mkdirSync(recordingsDir, { recursive: true });
}

const sampleExam = {
  examId: 'exam_001',
  title: '2024年度计算机基础考试',
  duration: 60,
  totalScore: 100,
  questions: [
    {
      id: 'q1',
      type: 'single',
      score: 10,
      question: 'JavaScript中，以下哪个方法用于向数组末尾添加元素？',
      options: ['push()', 'pop()', 'shift()', 'unshift()'],
      answer: 'A'
    },
    {
      id: 'q2',
      type: 'single',
      score: 10,
      question: 'CSS中，以下哪个属性用于设置元素的外边距？',
      options: ['padding', 'margin', 'border', 'outline'],
      answer: 'B'
    },
    {
      id: 'q3',
      type: 'single',
      score: 10,
      question: 'HTTP协议默认使用的端口号是？',
      options: ['21', '22', '80', '443'],
      answer: 'C'
    },
    {
      id: 'q4',
      type: 'single',
      score: 10,
      question: '在React中，以下哪个Hook用于管理组件状态？',
      options: ['useEffect', 'useState', 'useContext', 'useRef'],
      answer: 'B'
    },
    {
      id: 'q5',
      type: 'single',
      score: 10,
      question: '以下哪个不是JavaScript的数据类型？',
      options: ['string', 'boolean', 'float', 'undefined'],
      answer: 'C'
    },
    {
      id: 'q6',
      type: 'multiple',
      score: 15,
      question: '以下哪些是有效的CSS选择器？（多选）',
      options: ['.class', '#id', '*', '@media'],
      answer: ['A', 'B', 'C']
    },
    {
      id: 'q7',
      type: 'single',
      score: 10,
      question: 'Git中，以下哪个命令用于查看提交历史？',
      options: ['git status', 'git log', 'git diff', 'git show'],
      answer: 'B'
    },
    {
      id: 'q8',
      type: 'single',
      score: 10,
      question: 'Node.js中，以下哪个模块用于文件系统操作？',
      options: ['http', 'path', 'fs', 'url'],
      answer: 'C'
    },
    {
      id: 'q9',
      type: 'judge',
      score: 5,
      question: 'JavaScript是一种强类型编程语言。',
      answer: false
    },
    {
      id: 'q10',
      type: 'judge',
      score: 5,
      question: 'HTML5新增了<video>和<audio>标签。',
      answer: true
    }
  ]
};

examQuestions.set('exam_001', sampleExam);

const iceServers = [
  { urls: 'stun:stun.l.google.com:19302' },
  { urls: 'stun:stun1.l.google.com:19302' },
  { urls: 'stun:stun2.l.google.com:19302' },
  {
    urls: 'turn:openrelay.metered.ca:80',
    username: 'openrelayproject',
    credential: 'openrelayproject'
  },
  {
    urls: 'turn:openrelay.metered.ca:443',
    username: 'openrelayproject',
    credential: 'openrelayproject'
  }
];

app.use('/api/janus', janusController);

app.get('/api/ice-servers', (req, res) => {
  res.json({ iceServers });
});

app.get('/api/exams', (req, res) => {
  const examList = Array.from(examQuestions.values()).map(exam => ({
    examId: exam.examId,
    title: exam.title,
    duration: exam.duration,
    totalScore: exam.totalScore,
    questionCount: exam.questions.length
  }));
  res.json({ exams: examList });
});

app.get('/api/exams/:examId', (req, res) => {
  const { examId } = req.params;
  const { userId } = req.query;
  
  const exam = examQuestions.get(examId);
  if (!exam) {
    return res.status(404).json({ error: '考试不存在' });
  }

  const shuffledQuestions = exam.questions.map(q => {
    let shuffledOptions = [...q.options];
    let optionMapping = {};
    
    if (q.type === 'single' || q.type === 'multiple') {
      const originalLabels = ['A', 'B', 'C', 'D'];
      const shuffledIndices = [...Array(q.options.length).keys()];
      
      for (let i = shuffledIndices.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [shuffledIndices[i], shuffledIndices[j]] = [shuffledIndices[j], shuffledIndices[i]];
      }
      
      shuffledOptions = shuffledIndices.map(i => q.options[i]);
      
      shuffledIndices.forEach((originalIndex, newIndex) => {
        optionMapping[originalLabels[newIndex]] = originalLabels[originalIndex];
      });
    }
    
    return {
      ...q,
      options: shuffledOptions,
      optionMapping,
      answer: undefined
    };
  });

  const userKey = `${examId}_${userId}`;
  userAnswers.set(userKey, {
    mapping: shuffledQuestions.map(q => ({
      questionId: q.id,
      optionMapping: q.optionMapping
    })),
    answers: {}
  });

  res.json({
    examId: exam.examId,
    title: exam.title,
    duration: exam.duration,
    totalScore: exam.totalScore,
    questions: shuffledQuestions.map(q => {
      const { optionMapping, ...rest } = q;
      return rest;
    })
  });
});

app.post('/api/exams/:examId/submit', (req, res) => {
  const { examId } = req.params;
  const { userId, answers } = req.body;
  
  const exam = examQuestions.get(examId);
  if (!exam) {
    return res.status(404).json({ error: '考试不存在' });
  }

  const userKey = `${examId}_${userId}`;
  const userAnswerData = userAnswers.get(userKey);
  
  if (!userAnswerData) {
    return res.status(400).json({ error: '请先获取试题' });
  }

  let score = 0;
  const results = [];

  answers.forEach((userAnswer, index) => {
    const question = exam.questions.find(q => q.id === userAnswer.questionId);
    if (!question) return;

    const mapping = userAnswerData.mapping.find(m => m.questionId === question.id);
    let actualAnswer = userAnswer.answer;
    
    if (mapping && (question.type === 'single' || question.type === 'multiple')) {
      if (Array.isArray(userAnswer.answer)) {
        actualAnswer = userAnswer.answer.map(a => {
          const original = Object.entries(mapping.optionMapping).find(([k, v]) => k === a);
          return original ? original[1] : a;
        });
      } else {
        const original = Object.entries(mapping.optionMapping).find(([k, v]) => k === userAnswer.answer);
        actualAnswer = original ? original[1] : userAnswer.answer;
      }
    }

    let isCorrect = false;
    if (question.type === 'multiple') {
      const sortedAnswer = Array.isArray(actualAnswer) ? actualAnswer.sort().join(',') : '';
      const sortedCorrect = question.answer.sort().join(',');
      isCorrect = sortedAnswer === sortedCorrect;
    } else if (question.type === 'judge') {
      isCorrect = actualAnswer === question.answer;
    } else {
      isCorrect = actualAnswer === question.answer;
    }

    if (isCorrect) {
      score += question.score;
    }

    results.push({
      questionId: question.id,
      question: question.question,
      userAnswer: userAnswer.answer,
      correctAnswer: question.answer,
      isCorrect,
      score: isCorrect ? question.score : 0,
      maxScore: question.score
    });
  });

  userAnswers.set(userKey, {
    ...userAnswerData,
    answers: answers,
    finalScore: score,
    results,
    submittedAt: new Date().toISOString()
  });

  res.json({
    success: true,
    score,
    totalScore: exam.totalScore,
    results
  });
});

app.get('/api/recordings', (req, res) => {
  const recordingList = Array.from(recordings.values()).map(r => ({
    recordingId: r.recordingId,
    examId: r.examId,
    userId: r.userId,
    userName: r.userName,
    startTime: r.startTime,
    duration: r.duration,
    hasVideo: r.hasVideo,
    hasScreen: r.hasScreen
  }));
  res.json({ recordings: recordingList });
});

app.get('/api/recordings/:recordingId', (req, res) => {
  const { recordingId } = req.params;
  const recording = recordings.get(recordingId);
  
  if (!recording) {
    return res.status(404).json({ error: '录制不存在' });
  }
  
  res.json(recording);
});

app.post('/api/recordings/chunk', (req, res) => {
  const { recordingId, chunkIndex, chunkType, data, userId, examId, userName } = req.body;
  
  const examDir = path.join(recordingsDir, examId);
  if (!fs.existsSync(examDir)) {
    fs.mkdirSync(examDir, { recursive: true });
  }
  
  const userDir = path.join(examDir, userId);
  if (!fs.existsSync(userDir)) {
    fs.mkdirSync(userDir, { recursive: true });
  }
  
  const filename = `${chunkType}_${chunkIndex}.webm`;
  const filepath = path.join(userDir, filename);
  
  const buffer = Buffer.from(data.split(',')[1], 'base64');
  fs.appendFileSync(filepath, buffer);
  
  if (!recordings.has(recordingId)) {
    recordings.set(recordingId, {
      recordingId,
      examId,
      userId,
      userName,
      startTime: new Date().toISOString(),
      chunks: { video: [], screen: [] },
      duration: 0
    });
  }
  
  const recording = recordings.get(recordingId);
  recording.chunks[chunkType].push({ index: chunkIndex, filename, timestamp: Date.now() });
  recording.hasVideo = recording.chunks.video.length > 0;
  recording.hasScreen = recording.chunks.screen.length > 0;
  
  res.json({ success: true, chunkIndex, chunkType });
});

app.post('/api/recordings/finish', (req, res) => {
  const { recordingId, duration } = req.body;
  const recording = recordings.get(recordingId);
  
  if (recording) {
    recording.duration = duration;
    recording.endTime = new Date().toISOString();
    res.json({ success: true, recordingId });
  } else {
    res.status(404).json({ error: '录制不存在' });
  }
});

io.on('connection', (socket) => {
  console.log('客户端连接:', socket.id);

  socket.on('join-exam', (data) => {
    const { examId, userId, role, name } = data;
    socket.join(examId);
    
    if (role === 'examinee') {
      examinees.set(socket.id, { examId, userId, name, socketId: socket.id, connected: true, joinedAt: new Date().toISOString() });
    } else if (role === 'proctor') {
      proctors.set(socket.id, { examId, userId, name, socketId: socket.id, connected: true });
    }

    io.to(examId).emit('user-joined', { userId, role, name, socketId: socket.id });
    
    const examineesInExam = Array.from(examinees.values())
      .filter(e => e.examId === examId);
    io.to(examId).emit('examinees-list', examineesInExam);
  });

  socket.on('reconnect-request', (data) => {
    const { targetId, streamType } = data;
    io.to(targetId).emit('reconnect-offer', {
      senderId: socket.id,
      streamType
    });
  });

  socket.on('offer', (data) => {
    const { targetId, offer, streamType, reconnectAttempt = 0 } = data;
    io.to(targetId).emit('offer', {
      senderId: socket.id,
      offer,
      streamType,
      reconnectAttempt
    });
  });

  socket.on('answer', (data) => {
    const { targetId, answer, reconnectAttempt = 0 } = data;
    io.to(targetId).emit('answer', {
      senderId: socket.id,
      answer,
      reconnectAttempt
    });
  });

  socket.on('ice-candidate', (data) => {
    const { targetId, candidate } = data;
    io.to(targetId).emit('ice-candidate', {
      senderId: socket.id,
      candidate
    });
  });

  socket.on('connection-state-change', (data) => {
    const { targetId, state } = data;
    io.to(targetId).emit('peer-connection-state', {
      senderId: socket.id,
      state
    });
  });

  socket.on('cheating-alert', (data) => {
    const { examId, type, message, timestamp, details, severity } = data;
    io.to(examId).emit('cheating-alert', {
      examineeId: socket.id,
      type,
      message,
      timestamp,
      details,
      severity: severity || 'warning'
    });
  });

  socket.on('exam-status', (data) => {
    const { examId, status, currentQuestion, elapsedTime } = data;
    io.to(examId).emit('exam-status-update', {
      examineeId: socket.id,
      status,
      currentQuestion,
      elapsedTime
    });
  });

  socket.on('disconnect', () => {
    const examinee = examinees.get(socket.id);
    const proctor = proctors.get(socket.id);

    if (examinee) {
      io.to(examinee.examId).emit('user-left', { userId: examinee.userId, role: 'examinee' });
      examinees.delete(socket.id);
      const remainingExaminees = Array.from(examinees.values())
        .filter(e => e.examId === examinee.examId);
      io.to(examinee.examId).emit('examinees-list', remainingExaminees);
    }

    if (proctor) {
      proctors.delete(socket.id);
    }

    console.log('客户端断开:', socket.id);
  });
});

const PORT = process.env.PORT || 3001;
server.listen(PORT, () => {
  console.log(`服务器运行在端口 ${PORT}`);
  console.log('ICE服务器配置已就绪');
  console.log('试题管理API已就绪');
  console.log('录制存储API已就绪');
  console.log('示例考试 exam_001 已加载');
});
