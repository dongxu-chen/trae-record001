import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import JanusClient from '../utils/janusClient';
import AntiCheatDetector from '../utils/antiCheatDetector';
import AIBehaviorDetector from '../utils/aiBehaviorDetector';

function ExamineePage() {
  const location = useLocation();
  const navigate = useNavigate();
  const { examId, userId, name } = location.state || {};
  
  const [isConnected, setIsConnected] = useState(false);
  const [isInExam, setIsInExam] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [currentQuestion, setCurrentQuestion] = useState(0);
  const [examQuestions, setExamQuestions] = useState([]);
  const [answers, setAnswers] = useState({});
  const [examStarted, setExamStarted] = useState(false);
  const [examSubmitted, setExamSubmitted] = useState(false);
  const [examResult, setExamResult] = useState(null);
  const [examTitle, setExamTitle] = useState('');
  const [elapsedTime, setElapsedTime] = useState(0);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [alerts, setAlerts] = useState([]);
  
  const webcamRef = useRef(null);
  const janusClientRef = useRef(null);
  const antiCheatRef = useRef(null);
  const aiBehaviorDetectorRef = useRef(null);
  const webcamStreamRef = useRef(null);
  const screenStreamRef = useRef(null);
  const timerRef = useRef(null);

  const addAlert = useCallback((alert) => {
    setAlerts(prev => [...prev.slice(-29), {
      ...alert,
      time: new Date().toLocaleTimeString()
    }]);
  }, []);

  useEffect(() => {
    fetch('http://localhost:3001/api/exams/exam_001')
      .then(res => res.json())
      .then(data => {
        setExamQuestions(data.questions);
        setExamTitle(data.title);
      })
      .catch(err => {
        console.error('获取试题失败:', err);
      });
  }, []);

  useEffect(() => {
    const detector = new AntiCheatDetector((alert) => {
      addAlert(alert);
    });
    antiCheatRef.current = detector;

    return () => {
      detector.stopMonitoring();
    };
  }, [addAlert]);

  useEffect(() => {
    const detector = new AIBehaviorDetector({
      onAlert: (alert) => {
        addAlert(alert);
      },
      detectionFrequency: 2000,
      phoneDetectionThreshold: 0.5,
      lookingDownThreshold: 0.4,
      lookingAsideThreshold: 0.4
    });
    
    aiBehaviorDetectorRef.current = detector;

    return () => {
      detector.stop();
    };
  }, [addAlert]);

  const initJanus = useCallback(async () => {
    try {
      const janus = new JanusClient({
        server: 'ws://localhost:8188',
        apiSecret: 'janus-exam-secret-2024',
        roomId: 1234567890,
        iceServers: [
          { urls: 'stun:stun.l.google.com:19302' }
        ]
      });

      janus.on('joined', (data) => {
        console.log('[Janus] Joined room:', data);
        setIsConnected(true);
        addAlert({
          type: 'janus-connected',
          severity: 'success',
          message: '已连接到SFU服务器'
        });
      });

      janus.on('error', (error) => {
        console.error('[Janus] Error:', error);
        addAlert({
          type: 'janus-error',
          severity: 'danger',
          message: 'SFU连接错误: ' + error.message
        });
      });

      janus.on('streamPublished', (data) => {
        console.log('[Janus] Stream published:', data);
        addAlert({
          type: 'stream-published',
          severity: 'info',
          message: '媒体流已发布到SFU服务器'
        });
      });

      janus.on('disconnected', () => {
        setIsConnected(false);
        addAlert({
          type: 'janus-disconnected',
          severity: 'warning',
          message: 'SFU连接已断开'
        });
      });

      await janus.connect();
      await janus.joinRoom(Number(userId), name, true);
      
      janusClientRef.current = janus;
    } catch (error) {
      console.error('Janus初始化失败:', error);
      addAlert({
        type: 'janus-init-error',
        severity: 'danger',
        message: 'SFU初始化失败: ' + error.message
      });
    }
  }, [userId, name, addAlert]);

  const startWebcam = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ 
        video: { width: 640, height: 480 },
        audio: true
      });
      webcamStreamRef.current = stream;
      
      if (webcamRef.current) {
        webcamRef.current.srcObject = stream;
      }
      
      if (aiBehaviorDetectorRef.current) {
        aiBehaviorDetectorRef.current.setVideoElement(webcamRef.current);
      }
      
      addAlert({
        type: 'webcam-started',
        severity: 'info',
        message: '摄像头已启动'
      });
    } catch (error) {
      console.error('摄像头启动失败:', error);
      addAlert({
        type: 'webcam-error',
        severity: 'danger',
        message: '摄像头启动失败: ' + error.message
      });
    }
  };

  const startScreenShare = async () => {
    try {
      const stream = await navigator.mediaDevices.getDisplayMedia({ 
        video: { width: 1280, height: 720 },
        audio: false
      });
      screenStreamRef.current = stream;
      
      stream.getVideoTracks()[0].onended = () => {
        addAlert({
          type: 'screen-stopped',
          severity: 'warning',
          message: '屏幕共享已停止'
        });
        screenStreamRef.current = null;
      };

      addAlert({
        type: 'screen-started',
        severity: 'info',
        message: '屏幕共享已启动'
      });
    } catch (error) {
      console.error('屏幕共享失败:', error);
      addAlert({
        type: 'screen-error',
        severity: 'danger',
        message: '屏幕共享失败: ' + error.message
      });
    }
  };

  const startExam = async () => {
    if (!webcamStreamRef.current) {
      alert('请先启动摄像头');
      return;
    }
    if (!screenStreamRef.current) {
      alert('请先启动屏幕共享');
      return;
    }

    try {
      if (!janusClientRef.current) {
        await initJanus();
      }

      const recordingFilename = `exam_${examId}_${userId}_${Date.now()}`;
      
      await janusClientRef.current.publish(webcamStreamRef.current, {
        streamId: `webcam_${userId}`,
        audio: true,
        video: true,
        record: true,
        filename: `${recordingFilename}_webcam`
      });

      await janusClientRef.current.publish(screenStreamRef.current, {
        streamId: `screen_${userId}`,
        audio: false,
        video: true,
        record: true,
        filename: `${recordingFilename}_screen`
      });

      setIsRecording(true);

      if (antiCheatRef.current) {
        antiCheatRef.current.startMonitoring();
        antiCheatRef.current.enterFullscreenMode();
        setIsFullscreen(true);
      }

      if (aiBehaviorDetectorRef.current) {
        aiBehaviorDetectorRef.current.start();
      }

      setExamStarted(true);
      setIsInExam(true);

      timerRef.current = setInterval(() => {
        setElapsedTime(prev => prev + 1);
      }, 1000);

      addAlert({
        type: 'exam-started',
        severity: 'success',
        message: '考试已开始，录制中...'
      });
    } catch (error) {
      console.error('开始考试失败:', error);
      addAlert({
        type: 'exam-start-error',
        severity: 'danger',
        message: '开始考试失败: ' + error.message
      });
    }
  };

  const submitAnswer = (questionId, answer, isMultiple = false) => {
    setAnswers(prev => {
      const newAnswers = { ...prev };
      if (isMultiple) {
        const currentAnswers = newAnswers[questionId] || [];
        if (currentAnswers.includes(answer)) {
          newAnswers[questionId] = currentAnswers.filter(a => a !== answer);
        } else {
          newAnswers[questionId] = [...currentAnswers, answer];
        }
      } else {
        newAnswers[questionId] = answer;
      }
      return newAnswers;
    });
  };

  const submitExam = async () => {
    const confirmed = window.confirm('确定要提交考试吗？提交后无法修改答案。');
    if (!confirmed) return;

    try {
      const answersArray = examQuestions.map((q, index) => ({
        questionId: q.id,
        answer: answers[q.id] || (q.type === 'multiple' ? [] : null)
      }));

      const response = await fetch('http://localhost:3001/api/exams/exam_001/submit', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          userId,
          answers: answersArray
        })
      });

      const result = await response.json();
      setExamResult(result);
      setExamSubmitted(true);
      setIsInExam(false);

      if (janusClientRef.current) {
        await janusClientRef.current.leave();
        janusClientRef.current.disconnect();
      }

      if (antiCheatRef.current) {
        antiCheatRef.current.stopMonitoring();
      }

      if (aiBehaviorDetectorRef.current) {
        aiBehaviorDetectorRef.current.stop();
      }

      if (timerRef.current) {
        clearInterval(timerRef.current);
      }

      if (webcamStreamRef.current) {
        webcamStreamRef.current.getTracks().forEach(track => track.stop());
      }
      if (screenStreamRef.current) {
        screenStreamRef.current.getTracks().forEach(track => track.stop());
      }

      setIsRecording(false);

      addAlert({
        type: 'exam-submitted',
        severity: 'success',
        message: `考试已提交，得分: ${result.score}/${result.totalScore}`
      });

    } catch (error) {
      console.error('提交考试失败:', error);
      addAlert({
        type: 'submit-error',
        severity: 'danger',
        message: '提交考试失败: ' + error.message
      });
    }
  };

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  useEffect(() => {
    startWebcam();
    
    return () => {
      if (webcamStreamRef.current) {
        webcamStreamRef.current.getTracks().forEach(track => track.stop());
      }
      if (screenStreamRef.current) {
        screenStreamRef.current.getTracks().forEach(track => track.stop());
      }
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
      if (janusClientRef.current) {
        janusClientRef.current.destroy();
      }
    };
  }, []);

  if (examSubmitted && examResult) {
    return (
      <div style={{ 
        padding: '40px', 
        maxWidth: '800px', 
        margin: '0 auto',
        minHeight: '100vh',
        backgroundColor: '#f5f7fa'
      }}>
        <div style={{
          background: 'white',
          borderRadius: '12px',
          padding: '40px',
          boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
          textAlign: 'center'
        }}>
          <h1 style={{ color: '#2c3e50', marginBottom: '20px' }}>考试提交成功！</h1>
          <div style={{ fontSize: '48px', fontWeight: 'bold', color: '#3498db', marginBottom: '20px' }}>
            {examResult.score} / {examResult.totalScore}
          </div>
          <p style={{ fontSize: '18px', color: '#7f8c8d', marginBottom: '30px' }}>
            考试时长: {formatTime(elapsedTime)}
          </p>
          
          <h2 style={{ color: '#2c3e50', marginBottom: '20px', textAlign: 'left' }}>答题详情</h2>
          <div style={{ textAlign: 'left' }}>
            {examResult.results && examResult.results.map((result, index) => (
              <div key={index} style={{
                padding: '15px',
                marginBottom: '10px',
                borderRadius: '8px',
                backgroundColor: result.isCorrect ? '#d5f4e6' : '#ffe6e6',
                borderLeft: `4px solid ${result.isCorrect ? '#27ae60' : '#e74c3c'}`
              }}>
                <p style={{ margin: '0 0 10px 0', fontWeight: 500 }}>
                  第 {index + 1} 题: {examQuestions[index]?.question}
                </p>
                <p style={{ margin: '5px 0', fontSize: '14px' }}>
                  <span style={{ color: '#e74c3c' }}>你的答案: {Array.isArray(result.userAnswer) ? result.userAnswer.join(', ') : (result.userAnswer ? String(result.userAnswer) : '未作答')}</span>
                </p>
                <p style={{ margin: '5px 0', fontSize: '14px' }}>
                  <span style={{ color: '#27ae60' }}>正确答案: {Array.isArray(result.correctAnswer) ? result.correctAnswer.join(', ') : String(result.correctAnswer)}</span>
                </p>
                <p style={{ margin: '5px 0', fontSize: '14px', fontWeight: 500 }}>
                  得分: {result.score} / {result.maxScore}
                </p>
              </div>
            ))}
          </div>

          <button
            onClick={() => navigate('/')}
            style={{
              marginTop: '30px',
              padding: '12px 40px',
              fontSize: '16px',
              backgroundColor: '#3498db',
              color: 'white',
              border: 'none',
              borderRadius: '8px',
              cursor: 'pointer'
            }}
          >
            返回首页
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="examinee-container" style={{ minHeight: '100vh', backgroundColor: '#f5f7fa' }}>
      <div className="header" style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: '15px 20px',
        background: 'white',
        marginBottom: '20px',
        boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
      }}>
        <div>
          <h2 style={{ margin: 0 }}>{examTitle || '在线考试'} - {name}</h2>
          <p style={{ margin: '5px 0 0 0', color: '#666', fontSize: '14px' }}>
            用户ID: {userId} | 考试ID: {examId}
          </p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
          {examStarted && (
            <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#e74c3c' }}>
              {formatTime(elapsedTime)}
            </div>
          )}
          <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
            <div style={{
              width: '12px',
              height: '12px',
              borderRadius: '50%',
              backgroundColor: webcamStreamRef.current ? '#28a745' : '#dc3545'
            }}></div>
            <span>摄像头: {webcamStreamRef.current ? '已开启' : '未开启'}</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
            <div style={{
              width: '12px',
              height: '12px',
              borderRadius: '50%',
              backgroundColor: screenStreamRef.current ? '#28a745' : '#dc3545'
            }}></div>
            <span>屏幕共享: {screenStreamRef.current ? '已开启' : '未开启'}</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
            <div style={{
              width: '12px',
              height: '12px',
              borderRadius: '50%',
              backgroundColor: isRecording ? '#e74c3c' : '#6c757d'
            }}></div>
            <span>录制: {isRecording ? '录制中' : '未录制'}</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
            <div style={{
              width: '12px',
              height: '12px',
              borderRadius: '50%',
              backgroundColor: isConnected ? '#28a745' : '#dc3545'
            }}></div>
            <span>SFU: {isConnected ? '已连接' : '未连接'}</span>
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 300px', gap: '20px', padding: '0 20px 20px' }}>
        <div>
          {!examStarted ? (
            <div style={{
              background: 'white',
              borderRadius: '12px',
              padding: '30px',
              boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
            }}>
              <h2 style={{ textAlign: 'center', marginBottom: '30px', color: '#2c3e50' }}>考前准备</h2>
              
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '30px' }}>
                <div style={{
                  border: `2px solid ${webcamStreamRef.current ? '#27ae60' : '#ddd'}`,
                  borderRadius: '12px',
                  padding: '20px',
                  textAlign: 'center',
                  backgroundColor: webcamStreamRef.current ? '#f0f9f4' : '#fafafa'
                }}>
                  <div style={{ fontSize: '40px', marginBottom: '10px' }}>📹</div>
                  <h3 style={{ margin: '0 0 10px 0', color: '#2c3e50' }}>摄像头</h3>
                  <p style={{ color: webcamStreamRef.current ? '#27ae60' : '#e74c3c', marginBottom: '15px' }}>
                    {webcamStreamRef.current ? '✓ 已开启' : '✗ 未开启'}
                  </p>
                  <video ref={webcamRef} autoPlay muted playsInline style={{ width: '100%', borderRadius: '8px', backgroundColor: '#000' }} />
                </div>

                <div style={{
                  border: `2px solid ${screenStreamRef.current ? '#27ae60' : '#ddd'}`,
                  borderRadius: '12px',
                  padding: '20px',
                  textAlign: 'center',
                  backgroundColor: screenStreamRef.current ? '#f0f9f4' : '#fafafa'
                }}>
                  <div style={{ fontSize: '40px', marginBottom: '10px' }}>🖥️</div>
                  <h3 style={{ margin: '0 0 10px 0', color: '#2c3e50' }}>屏幕共享</h3>
                  <p style={{ color: screenStreamRef.current ? '#27ae60' : '#e74c3c', marginBottom: '15px' }}>
                    {screenStreamRef.current ? '✓ 已开启' : '✗ 未开启'}
                  </p>
                  {!screenStreamRef.current && (
                    <button 
                      onClick={startScreenShare} 
                      style={{
                        padding: '10px 20px',
                        backgroundColor: '#3498db',
                        color: 'white',
                        border: 'none',
                        borderRadius: '8px',
                        cursor: 'pointer',
                        fontSize: '14px'
                      }}
                    >
                      开启屏幕共享
                    </button>
                  )}
                </div>
              </div>

              <div style={{ textAlign: 'center' }}>
                <button 
                  onClick={startExam} 
                  disabled={!webcamStreamRef.current || !screenStreamRef.current}
                  style={{
                    padding: '15px 60px',
                    fontSize: '18px',
                    fontWeight: 'bold',
                    backgroundColor: (webcamStreamRef.current && screenStreamRef.current) ? '#27ae60' : '#bdc3c7',
                    color: 'white',
                    border: 'none',
                    borderRadius: '8px',
                    cursor: (webcamStreamRef.current && screenStreamRef.current) ? 'pointer' : 'not-allowed'
                  }}
                >
                  开始考试
                </button>
                <p style={{ marginTop: '15px', color: '#95a5a6', fontSize: '14px' }}>
                  点击开始将自动进入全屏模式，考试全程将被录制并通过SFU转发
                </p>
              </div>
            </div>
          ) : (
            <div style={{
              background: 'white',
              borderRadius: '12px',
              padding: '30px',
              boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
            }}>
              <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: '20px',
                paddingBottom: '15px',
                borderBottom: '2px solid #eee'
              }}>
                <h2 style={{ margin: 0, color: '#2c3e50' }}>
                  第 {currentQuestion + 1} 题 / 共 {examQuestions.length} 题
                </h2>
                <button 
                  onClick={submitExam}
                  style={{
                    padding: '10px 25px',
                    backgroundColor: '#e74c3c',
                    color: 'white',
                    border: 'none',
                    borderRadius: '8px',
                    cursor: 'pointer',
                    fontSize: '14px',
                    fontWeight: 'bold'
                  }}
                >
                  提交考试
                </button>
              </div>

              {examQuestions[currentQuestion] && (
                <div>
                  <div style={{
                    padding: '20px',
                    backgroundColor: '#f8f9fa',
                    borderRadius: '8px',
                    marginBottom: '20px'
                  }}>
                    <div style={{
                      display: 'inline-block',
                      padding: '4px 12px',
                      backgroundColor: '#3498db',
                      color: 'white',
                      borderRadius: '20px',
                      fontSize: '12px',
                      marginBottom: '10px'
                    }}>
                      {examQuestions[currentQuestion].type === 'single' ? '单选题' :
                       examQuestions[currentQuestion].type === 'multiple' ? '多选题' :
                       examQuestions[currentQuestion].type === 'judge' ? '判断题' : '未知类型'}
                      · {examQuestions[currentQuestion].score}分
                    </div>
                    <h3 style={{ margin: '10px 0 0 0', color: '#2c3e50', fontSize: '18px' }}>
                      {examQuestions[currentQuestion].question}
                    </h3>
                  </div>

                  <div style={{ marginBottom: '30px' }}>
                    {examQuestions[currentQuestion].type === 'judge' ? (
                      <div style={{ display: 'flex', gap: '20px' }}>
                        <label style={{
                          flex: 1,
                          padding: '20px',
                          border: '2px solid #ddd',
                          borderRadius: '8px',
                          cursor: 'pointer',
                          backgroundColor: answers[examQuestions[currentQuestion].id] === true ? '#e3f2fd' : 'white',
                          borderColor: answers[examQuestions[currentQuestion].id] === true ? '#3498db' : '#ddd'
                        }}>
                          <input
                            type="radio"
                            name={`q-${currentQuestion}`}
                            checked={answers[examQuestions[currentQuestion].id] === true}
                            onChange={() => submitAnswer(examQuestions[currentQuestion].id, true)}
                            style={{ marginRight: '10px' }}
                          />
                          <span style={{ fontSize: '16px' }}>✓ 正确</span>
                        </label>
                        <label style={{
                          flex: 1,
                          padding: '20px',
                          border: '2px solid #ddd',
                          borderRadius: '8px',
                          cursor: 'pointer',
                          backgroundColor: answers[examQuestions[currentQuestion].id] === false ? '#e3f2fd' : 'white',
                          borderColor: answers[examQuestions[currentQuestion].id] === false ? '#3498db' : '#ddd'
                        }}>
                          <input
                            type="radio"
                            name={`q-${currentQuestion}`}
                            checked={answers[examQuestions[currentQuestion].id] === false}
                            onChange={() => submitAnswer(examQuestions[currentQuestion].id, false)}
                            style={{ marginRight: '10px' }}
                          />
                          <span style={{ fontSize: '16px' }}>✗ 错误</span>
                        </label>
                      </div>
                    ) : (
                      examQuestions[currentQuestion].options && examQuestions[currentQuestion].options.map((option, index) => {
                        const optionLabels = ['A', 'B', 'C', 'D', 'E', 'F'];
                        const isSelected = examQuestions[currentQuestion].type === 'multiple'
                          ? (answers[examQuestions[currentQuestion].id] || []).includes(optionLabels[index])
                          : answers[examQuestions[currentQuestion].id] === optionLabels[index];

                        return (
                          <label
                            key={index}
                            style={{
                              display: 'block',
                              padding: '15px 20px',
                              marginBottom: '10px',
                              border: '2px solid #ddd',
                              borderRadius: '8px',
                              cursor: 'pointer',
                              backgroundColor: isSelected ? '#e3f2fd' : 'white',
                              borderColor: isSelected ? '#3498db' : '#ddd',
                              transition: 'all 0.2s'
                            }}
                          >
                            <input
                              type={examQuestions[currentQuestion].type === 'multiple' ? 'checkbox' : 'radio'}
                              name={`q-${currentQuestion}`}
                              checked={isSelected}
                              onChange={() => submitAnswer(examQuestions[currentQuestion].id, optionLabels[index], examQuestions[currentQuestion].type === 'multiple')}
                              style={{ marginRight: '15px', transform: 'scale(1.2)' }}
                            />
                            <span style={{ fontSize: '16px' }}>
                              <strong>{optionLabels[index]}.</strong> {option}
                            </span>
                          </label>
                        );
                      })
                    )}
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <button
                      onClick={() => setCurrentQuestion(Math.max(0, currentQuestion - 1))}
                      disabled={currentQuestion === 0}
                      style={{
                        padding: '10px 25px',
                        backgroundColor: currentQuestion === 0 ? '#bdc3c7' : '#95a5a6',
                        color: 'white',
                        border: 'none',
                        borderRadius: '8px',
                        cursor: currentQuestion === 0 ? 'not-allowed' : 'pointer'
                      }}
                    >
                      ← 上一题
                    </button>
                    <button
                      onClick={() => setCurrentQuestion(Math.min(examQuestions.length - 1, currentQuestion + 1))}
                      disabled={currentQuestion === examQuestions.length - 1}
                      style={{
                        padding: '10px 25px',
                        backgroundColor: currentQuestion === examQuestions.length - 1 ? '#bdc3c7' : '#3498db',
                        color: 'white',
                        border: 'none',
                        borderRadius: '8px',
                        cursor: currentQuestion === examQuestions.length - 1 ? 'not-allowed' : 'pointer'
                      }}
                    >
                      下一题 →
                    </button>
                  </div>

                  <div style={{ marginTop: '30px', paddingTop: '20px', borderTop: '2px solid #eee' }}>
                    <p style={{ margin: '0 0 10px 0', color: '#666' }}>答题卡（已答：{Object.keys(answers).length}/{examQuestions.length}）</p>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                      {examQuestions.map((q, index) => (
                        <button
                          key={index}
                          onClick={() => setCurrentQuestion(index)}
                          style={{
                            width: '40px',
                            height: '40px',
                            borderRadius: '8px',
                            border: 'none',
                            backgroundColor: answers[q.id] ? '#27ae60' : '#ecf0f1',
                            color: answers[q.id] ? 'white' : '#7f8c8d',
                            fontWeight: currentQuestion === index ? 'bold' : 'normal',
                            cursor: 'pointer'
                          }}
                        >
                          {index + 1}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        <div>
          <div style={{
            background: 'white',
            borderRadius: '12px',
            padding: '15px',
            boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
            marginBottom: '20px'
          }}>
            <h3 style={{ margin: '0 0 10px 0', fontSize: '16px' }}>实时视频</h3>
            <video ref={webcamRef} autoPlay muted playsInline style={{ width: '100%', borderRadius: '8px', backgroundColor: '#000' }} />
          </div>

          <div style={{
            background: 'white',
            borderRadius: '12px',
            padding: '15px',
            boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
            maxHeight: '400px',
            overflowY: 'auto'
          }}>
            <h3 style={{ margin: '0 0 15px 0', fontSize: '16px' }}>监控日志</h3>
            {alerts.length === 0 ? (
              <p style={{ color: '#95a5a6', textAlign: 'center', padding: '20px' }}>暂无告警</p>
            ) : (
              [...alerts].reverse().map((alert, index) => (
                <div
                  key={index}
                  style={{
                    padding: '10px',
                    marginBottom: '8px',
                    borderRadius: '6px',
                    fontSize: '13px',
                    backgroundColor: 
                      alert.severity === 'danger' || alert.severity === 'critical' ? '#fee' :
                      alert.severity === 'warning' ? '#fff8e1' :
                      alert.severity === 'success' ? '#e8f5e9' : '#f5f5f5',
                    borderLeft: `4px solid ${
                      alert.severity === 'danger' || alert.severity === 'critical' ? '#e74c3c' :
                      alert.severity === 'warning' ? '#f39c12' :
                      alert.severity === 'success' ? '#27ae60' : '#3498db'
                    }`
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '3px' }}>
                    <strong style={{ color: '#2c3e50' }}>{alert.type}</strong>
                    <span style={{ color: '#95a5a6' }}>{alert.time}</span>
                  </div>
                  <div style={{ color: '#7f8c8d' }}>{alert.message}</div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default ExamineePage;
