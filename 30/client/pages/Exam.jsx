import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Card,
  Radio,
  Button,
  Progress,
  Modal,
  message,
  Space,
  Typography,
  Steps,
  Divider,
  Alert,
} from 'antd';
import { 
  ClockCircleOutlined, 
  CheckCircleOutlined,
  WarningOutlined,
  ExclamationCircleOutlined
} from '@ant-design/icons';
import { 
  formatTime, 
  minutesToSeconds, 
  isTimeUp, 
  getTimeStatus,
  createAccurateTimer 
} from '../utils/timer';
import WebcamFeed from '../components/WebcamFeed';

const { Title, Text } = Typography;
const { Step } = Steps;

const API_BASE = 'http://localhost:5000/api/exam';
const PROCTOR_API_BASE = 'http://localhost:5000/api/proctor';

export default function Exam({ examId, studentName, onSubmit }) {
  const [exam, setExam] = useState(null);
  const [loading, setLoading] = useState(true);
  const [currentStep, setCurrentStep] = useState(0);
  const [answers, setAnswers] = useState({});
  const [timeLeft, setTimeLeft] = useState(0);
  const [totalTime, setTotalTime] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const [cameraActive, setCameraActive] = useState(false);
  const [antiCheatWarning, setAntiCheatWarning] = useState(null);
  const [violationCount, setViolationCount] = useState(0);

  const timerRef = useRef(null);
  const hasSubmittedRef = useRef(false);
  const tabSwitchCountRef = useRef(0);
  const copyPasteCountRef = useRef(0);
  const fullscreenExitCountRef = useRef(0);
  const maxViolations = 5;

  const sendEvent = useCallback(async (eventType, eventData, severity = 'info') => {
    try {
      await fetch(`${PROCTOR_API_BASE}/event`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          examId,
          studentName,
          eventType,
          eventData,
          severity,
          timestamp: new Date().toISOString()
        })
      });
    } catch (err) {
      console.error('事件发送失败:', err);
    }
  }, [examId, studentName]);

  const addViolation = useCallback((type, message) => {
    setViolationCount(prev => {
      const newCount = prev + 1;
      
      if (newCount >= maxViolations) {
        setAntiCheatWarning({
          type: 'danger',
          message: `已达到最大违规次数（${maxViolations}次），系统将自动提交考试`
        });
        handleSubmit(true);
      } else {
        setAntiCheatWarning({
          type: 'warning',
          message: `检测到违规行为（${type}），已记录。当前违规次数：${newCount}/${maxViolations}`
        });
        
        setTimeout(() => setAntiCheatWarning(null), 5000);
      }
      
      return newCount;
    });
  }, []);

  useEffect(() => {
    const fetchExam = async () => {
      try {
        const response = await fetch(`${API_BASE}/${examId}?studentName=${encodeURIComponent(studentName)}`);
        if (!response.ok) throw new Error('获取考试失败');
        const data = await response.json();
        setExam(data);
        const seconds = minutesToSeconds(data.duration_minutes);
        setTimeLeft(seconds);
        setTotalTime(seconds);
        sendEvent('exam_started', '考试开始');
      } catch (error) {
        message.error('加载考试失败');
      } finally {
        setLoading(false);
      }
    };

    fetchExam();
  }, [examId, studentName, sendEvent]);

  useEffect(() => {
    const requestFullscreen = async () => {
      try {
        if (!document.fullscreenElement && document.documentElement.requestFullscreen) {
          await document.documentElement.requestFullscreen();
        }
      } catch (err) {
        console.log('全屏请求被拒绝:', err);
      }
    };

    const handleVisibilityChange = () => {
      if (document.hidden) {
        tabSwitchCountRef.current++;
        addViolation('tab_switch', '切换标签页或最小化窗口');
        sendEvent('tab_switch', { count: tabSwitchCountRef.current }, 'warning');
      }
    };

    const handleFullscreenChange = () => {
      if (!document.fullscreenElement && !document.webkitFullscreenElement) {
        fullscreenExitCountRef.current++;
        addViolation('fullscreen_exit', '退出全屏模式');
        sendEvent('fullscreen_exit', { count: fullscreenExitCountRef.current }, 'warning');
      }
    };

    const handleCopy = (e) => {
      e.preventDefault();
      copyPasteCountRef.current++;
      addViolation('copy', '尝试复制内容');
      sendEvent('copy_attempt', { count: copyPasteCountRef.current }, 'warning');
      message.warning('考试期间禁止复制');
    };

    const handlePaste = (e) => {
      e.preventDefault();
      copyPasteCountRef.current++;
      addViolation('paste', '尝试粘贴内容');
      sendEvent('paste_attempt', { count: copyPasteCountRef.current }, 'warning');
      message.warning('考试期间禁止粘贴');
    };

    const handleContextMenu = (e) => {
      e.preventDefault();
      addViolation('context_menu', '尝试打开右键菜单');
      sendEvent('context_menu', '右键菜单被阻止', 'warning');
    };

    const handleBeforeUnload = (e) => {
      if (!hasSubmittedRef.current) {
        sendEvent('before_unload', '尝试关闭页面', 'danger');
        e.preventDefault();
        e.returnValue = '确定要离开考试页面吗？';
        return e.returnValue;
      }
    };

    const handleKeyDown = (e) => {
      const blockedKeys = {
        'F12': 'DevTools',
        'F5': '刷新',
        'r': '刷新 (Ctrl+R)'
      };

      if (e.key === 'F12') {
        e.preventDefault();
        addViolation('devtools', '尝试打开开发者工具');
        sendEvent('devtools_attempt', 'F12 被阻止', 'warning');
      }

      if ((e.ctrlKey || e.metaKey) && e.key === 'r') {
        e.preventDefault();
        addViolation('refresh', '尝试刷新页面');
        sendEvent('refresh_attempt', 'Ctrl+R 被阻止', 'warning');
      }

      if ((e.ctrlKey || e.metaKey) && e.key === 'u') {
        e.preventDefault();
        addViolation('view_source', '尝试查看源代码');
        sendEvent('view_source', 'Ctrl+U 被阻止', 'warning');
      }

      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault();
        addViolation('save_page', '尝试保存页面');
        sendEvent('save_page', 'Ctrl+S 被阻止', 'warning');
      }

      if ((e.ctrlKey || e.metaKey) && e.key === 'c') {
        e.preventDefault();
        addViolation('copy', '尝试复制内容');
        sendEvent('copy_attempt', 'Ctrl+C 被阻止', 'warning');
        message.warning('考试期间禁止复制');
      }

      if ((e.ctrlKey || e.metaKey) && e.key === 'v') {
        e.preventDefault();
        addViolation('paste', '尝试粘贴内容');
        sendEvent('paste_attempt', 'Ctrl+V 被阻止', 'warning');
        message.warning('考试期间禁止粘贴');
      }
    };

    requestFullscreen();

    document.addEventListener('visibilitychange', handleVisibilityChange);
    document.addEventListener('fullscreenchange', handleFullscreenChange);
    document.addEventListener('webkitfullscreenchange', handleFullscreenChange);
    document.addEventListener('copy', handleCopy);
    document.addEventListener('paste', handlePaste);
    document.addEventListener('contextmenu', handleContextMenu);
    document.addEventListener('keydown', handleKeyDown);
    window.addEventListener('beforeunload', handleBeforeUnload);

    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      document.removeEventListener('fullscreenchange', handleFullscreenChange);
      document.removeEventListener('webkitfullscreenchange', handleFullscreenChange);
      document.removeEventListener('copy', handleCopy);
      document.removeEventListener('paste', handlePaste);
      document.removeEventListener('contextmenu', handleContextMenu);
      document.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('beforeunload', handleBeforeUnload);

      if (document.fullscreenElement && document.exitFullscreen) {
        document.exitFullscreen().catch(console.error);
      }
    };
  }, [addViolation, sendEvent]);

  useEffect(() => {
    if (loading || timeLeft <= 0 || submitting) return;

    timerRef.current = createAccurateTimer(
      timeLeft,
      (remaining) => {
        setTimeLeft(remaining);
      },
      () => {
        if (!hasSubmittedRef.current) {
          handleSubmit(true);
        }
      }
    );

    return () => {
      if (timerRef.current) {
        timerRef.current.stop();
        timerRef.current = null;
      }
    };
  }, [loading, timeLeft, submitting]);

  const handleAnswer = (questionId, value) => {
    if (submitting) return;
    setAnswers(prev => ({
      ...prev,
      [questionId]: value,
    }));
  };

  const handleSubmit = useCallback(async (autoSubmit = false) => {
    if (submitting || hasSubmittedRef.current) return;
    hasSubmittedRef.current = true;

    if (timerRef.current) {
      timerRef.current.stop();
      timerRef.current = null;
    }

    sendEvent('submit_attempt', { autoSubmit, violationCount });

    if (!autoSubmit && !isTimeUp(timeLeft)) {
      Modal.confirm({
        title: '确认提交考试？',
        content: `您已完成 ${Object.keys(answers).length}/${exam?.questions.length || 0} 道题目，确定要提交吗？`,
        okText: '确认提交',
        cancelText: '继续答题',
        onOk: () => doSubmit(),
        onCancel: () => {
          hasSubmittedRef.current = false;
          const remaining = totalTime;
          timerRef.current = createAccurateTimer(
            remaining,
            (r) => setTimeLeft(r),
            () => handleSubmit(true)
          );
        },
      });
      return;
    }

    doSubmit();

    async function doSubmit() {
      setSubmitting(true);
      try {
        const response = await fetch(`${API_BASE}/submit`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            examId,
            studentName,
            answers,
            violationCount,
            tabSwitchCount: tabSwitchCountRef.current,
            copyPasteCount: copyPasteCountRef.current,
          }),
        });

        if (!response.ok) {
          if (response.status === 409) {
            const errorData = await response.json();
            message.warning('考试已提交');
            if (errorData.resultId) {
              onSubmit(errorData.resultId);
            }
            return;
          }
          throw new Error('提交失败');
        }

        const result = await response.json();

        sendEvent('exam_submitted', {
          score: result.score,
          passed: result.passed,
          autoSubmit
        });

        if (autoSubmit) {
          message.warning('时间已到，自动提交考试');
        } else {
          message.success('考试提交成功');
        }

        onSubmit(result.resultId);
      } catch (error) {
        message.error('提交考试失败');
        setSubmitting(false);
        hasSubmittedRef.current = false;
      }
    }
  }, [submitting, timeLeft, totalTime, answers, exam, examId, studentName, onSubmit, sendEvent, violationCount]);

  const getTimerColor = () => {
    const status = getTimeStatus(timeLeft, totalTime);
    switch (status) {
      case 'danger':
        return 'red';
      case 'warning':
        return 'orange';
      default:
        return 'green';
    }
  };

  if (loading) {
    return (
      <Card loading={true} style={{ maxWidth: 1200, margin: '20px auto' }}>
        加载中...
      </Card>
    );
  }

  if (!exam) {
    return (
      <Card style={{ maxWidth: 1200, margin: '20px auto' }}>
        <Text type="danger">考试加载失败</Text>
      </Card>
    );
  }

  const currentQuestion = exam.questions[currentStep];
  const answeredCount = Object.keys(answers).length;
  const progress = (answeredCount / exam.questions.length) * 100;

  return (
    <div style={{ maxWidth: 1200, margin: '20px auto', padding: '0 16px' }}>
      <Card>
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 16 }}>
            <Title level={3} style={{ margin: 0 }}>{exam.title}</Title>
            <Space>
              {violationCount > 0 && (
                <Space>
                  <ExclamationCircleOutlined style={{ color: '#faad14' }} />
                  <Text type="warning">违规次数: {violationCount}/{maxViolations}</Text>
                </Space>
              )}
              <Space>
                <ClockCircleOutlined style={{ color: getTimerColor(), fontSize: 20 }} />
                <Text strong style={{ color: getTimerColor(), fontSize: 18 }}>
                  {formatTime(timeLeft)}
                </Text>
              </Space>
            </Space>
          </div>

          <Alert
            message="考试环境要求"
            description="请保持摄像头开启，全屏作答，禁止切换标签页、复制粘贴或使用开发者工具。违规行为将被记录。"
            type="info"
            showIcon
          />

          {antiCheatWarning && (
            <Alert
              message="系统警告"
              description={antiCheatWarning.message}
              type={antiCheatWarning.type === 'danger' ? 'error' : 'warning'}
              showIcon
              icon={<WarningOutlined />}
              closable
            />
          )}

          <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
            <div style={{ flex: 1, minWidth: 300 }}>
              <Text type="secondary">{exam.description}</Text>

              <div style={{ marginTop: 16 }}>
                <Text strong>答题进度：</Text>
                <Progress
                  percent={Math.round(progress)}
                  format={percent => `${Object.keys(answers).length}/${exam.questions.length}`}
                  status={progress === 100 ? 'success' : 'active'}
                />
              </div>

              <Steps
                current={currentStep}
                direction="horizontal"
                size="small"
                items={exam.questions.map((q, index) => ({
                  title: index + 1,
                  status: answers[q.id] ? 'finish' : undefined,
                }))}
                onChange={setCurrentStep}
                style={{ marginTop: 16 }}
              />

              <Divider />

              <Card
                title={`第 ${currentStep + 1} 题 / 共 ${exam.questions.length} 题`}
                extra={
                  <Space>
                    {answers[currentQuestion.id] && (
                      <CheckCircleOutlined style={{ color: '#52c41a' }} />
                    )}
                  </Space>
                }
              >
                <div style={{ marginBottom: 24 }}>
                  <Text style={{ fontSize: 16 }}>{currentQuestion.questionText}</Text>
                </div>

                <Radio.Group
                  value={answers[currentQuestion.id]}
                  onChange={e => handleAnswer(currentQuestion.id, e.target.value)}
                >
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 12, width: '100%' }}>
                    {Object.entries(currentQuestion.options).map(([key, value]) => (
                      <Radio key={key} value={key} style={{ fontSize: 15, marginRight: 0 }}>
                        <Text strong>{key}.</Text> {value}
                      </Radio>
                    ))}
                  </div>
                </Radio.Group>
              </Card>

              <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 16 }}>
                <Button
                  onClick={() => setCurrentStep(prev => Math.max(0, prev - 1))}
                  disabled={currentStep === 0}
                >
                  上一题
                </Button>

                {currentStep < exam.questions.length - 1 ? (
                  <Button
                    type="primary"
                    onClick={() => setCurrentStep(prev => prev + 1)}
                  >
                    下一题
                  </Button>
                ) : (
                  <Button
                    type="primary"
                    onClick={() => handleSubmit(false)}
                    loading={submitting}
                  >
                    提交考试
                  </Button>
                )}
              </div>
            </div>

            <div style={{ width: 320, flexShrink: 0 }}>
              <WebcamFeed
                examId={examId}
                studentName={studentName}
                snapshotInterval={15000}
                onCameraStatusChange={setCameraActive}
              />

              <Card size="small" style={{ marginTop: 16 }}>
                <Space direction="vertical" size="small" style={{ width: '100%' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Text>考生：</Text>
                    <Text strong>{studentName}</Text>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Text>摄像头：</Text>
                    <Text type={cameraActive ? 'success' : 'danger'}>
                      {cameraActive ? '已开启' : '未开启'}
                    </Text>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Text>考试时长：</Text>
                    <Text strong>{exam.duration_minutes} 分钟</Text>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Text>题目数量：</Text>
                    <Text strong>{exam.questions.length} 题</Text>
                  </div>
                </Space>
              </Card>
            </div>
          </div>
        </Space>
      </Card>
    </div>
  );
}
