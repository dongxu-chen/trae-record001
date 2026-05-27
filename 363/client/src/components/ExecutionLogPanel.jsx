import React, { useState, useEffect, useRef } from 'react';

const LOG_LEVELS = {
  info: { color: '#94a3b8', bg: 'transparent' },
  command: { color: '#6366f1', bg: 'rgba(99, 102, 241, 0.1)' },
  output: { color: '#e2e8f0', bg: 'transparent' },
  success: { color: '#10b981', bg: 'rgba(16, 185, 129, 0.1)' },
  error: { color: '#ef4444', bg: 'rgba(239, 68, 68, 0.1)' }
};

export default function ExecutionLogPanel({
  isOpen,
  onClose,
  wsUrl = 'ws://localhost:3001/ws',
  currentExecutionId
}) {
  const [logs, setLogs] = useState([]);
  const [executionStatus, setExecutionStatus] = useState(null);
  const [currentStage, setCurrentStage] = useState(0);
  const [totalStages, setTotalStages] = useState(0);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef(null);
  const logsEndRef = useRef(null);

  useEffect(() => {
    if (!isOpen) return;

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      setLogs(prev => [...prev, {
        timestamp: Date.now(),
        message: '✅ 已连接到日志服务器',
        level: 'success',
        job: 'System'
      }]);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        if (currentExecutionId && data.executionId !== currentExecutionId) {
          return;
        }

        switch (data.type) {
          case 'log':
            setLogs(prev => [...prev, {
              timestamp: data.timestamp,
              message: data.message,
              level: data.level,
              job: data.job,
              stage: data.stage
            }]);
            break;
          case 'execution-started':
            setTotalStages(data.totalStages);
            setCurrentStage(0);
            setExecutionStatus('running');
            setLogs(prev => [...prev, {
              timestamp: Date.now(),
              message: `🚀 流水线执行开始，共 ${data.totalStages} 个阶段`,
              level: 'info',
              job: 'System'
            }]);
            break;
          case 'stage-started':
            setCurrentStage(data.stageIndex);
            setLogs(prev => [...prev, {
              timestamp: Date.now(),
              message: `📍 阶段 ${data.stageIndex + 1} 开始 (${data.jobCount} 个任务)`,
              level: 'info',
              job: 'System'
            }]);
            break;
          case 'stage-completed':
            setLogs(prev => [...prev, {
              timestamp: Date.now(),
              message: `✅ 阶段 ${data.stageIndex + 1} ${data.status === 'success' ? '完成' : '失败'}`,
              level: data.status === 'success' ? 'success' : 'error',
              job: 'System'
            }]);
            break;
          case 'execution-completed':
            setExecutionStatus(data.status);
            setLogs(prev => [...prev, {
              timestamp: Date.now(),
              message: `🎉 流水线执行${data.status === 'success' ? '成功' : '失败'}，总用时 ${data.totalDuration}s`,
              level: data.status === 'success' ? 'success' : 'error',
              job: 'System'
            }]);
            break;
        }
      } catch (e) {
        console.error('解析WebSocket消息失败:', e);
      }
    };

    ws.onclose = () => {
      setConnected(false);
      setLogs(prev => [...prev, {
        timestamp: Date.now(),
        message: '❌ 连接已断开',
        level: 'error',
        job: 'System'
      }]);
    };

    ws.onerror = () => {
      setLogs(prev => [...prev, {
        timestamp: Date.now(),
        message: '❌ 连接错误',
        level: 'error',
        job: 'System'
      }]);
    };

    return () => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.close();
      }
    };
  }, [isOpen, wsUrl, currentExecutionId]);

  useEffect(() => {
    if (logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs]);

  const clearLogs = () => {
    setLogs([]);
  };

  if (!isOpen) return null;

  return (
    <div className="execution-log-panel">
      <div className="execution-log-header">
        <div>
          <div className="execution-log-title">📋 执行日志</div>
          <div style={{ fontSize: '12px', color: '#94a3b8' }}>
            {connected ? '🟢 已连接' : '🔴 已断开'}
            {executionStatus && (
              <span style={{ marginLeft: '12px' }}>
                状态: {executionStatus === 'running' ? '执行中' : executionStatus === 'success' ? '成功' : '失败'}
              </span>
            )}
            {totalStages > 0 && (
              <span style={{ marginLeft: '12px' }}>
                阶段: {currentStage + 1}/{totalStages}
              </span>
            )}
          </div>
        </div>
        <div>
          <button className="btn btn-secondary" onClick={clearLogs} style={{ marginRight: '8px' }}>
            清空
          </button>
          <button className="btn btn-secondary" onClick={onClose}>
            关闭
          </button>
        </div>
      </div>

      <div className="execution-log-content">
        {logs.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '60px', color: '#64748b' }}>
            暂无日志，点击"执行流水线"开始
          </div>
        ) : (
          logs.map((log, index) => (
            <div
              key={index}
              className="log-line"
              style={{
                color: LOG_LEVELS[log.level]?.color,
                backgroundColor: LOG_LEVELS[log.level]?.bg,
                padding: '4px 8px',
                borderRadius: '4px',
                marginBottom: '2px'
              }}
            >
              <span style={{ color: '#64748b', fontSize: '11px', marginRight: '8px' }}>
                {new Date(log.timestamp).toLocaleTimeString()}
              </span>
              <span style={{ color: '#6366f1', marginRight: '8px', fontWeight: '500' }}>
                [{log.job}]
              </span>
              {log.message}
            </div>
          ))
        )}
        <div ref={logsEndRef} />
      </div>
    </div>
  );
}
