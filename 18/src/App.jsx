import { useState, useCallback, useEffect, useRef, useMemo } from 'react';
import { io } from 'socket.io-client';
import Editor from './client/Editor.jsx';
import Output from './client/Output.jsx';
import LanguageSelector, { LANGUAGES } from './client/LanguageSelector.jsx';
import UserPresence from './client/UserPresence.jsx';

const AUTO_RUN_DELAY = 800;
const SOCKET_URL = '/';

function generateRoomId() {
  return `room-${Math.random().toString(36).slice(2, 10)}`;
}

function generateUserId() {
  return `user-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
}

function generateUserName() {
  const adjectives = ['快速', '聪明', '勇敢', '友善', '创意', '热情', '冷静', '专注'];
  const nouns = ['狐狸', '熊猫', '狮子', '兔子', '老虎', '海豚', '猫头鹰', '蝴蝶'];
  const adj = adjectives[Math.floor(Math.random() * adjectives.length)];
  const noun = nouns[Math.floor(Math.random() * nouns.length)];
  return `${adj}${noun}`;
}

function App() {
  const [code, setCode] = useState('');
  const [language, setLanguage] = useState('javascript');
  const [output, setOutput] = useState([]);
  const [error, setError] = useState(null);
  const [isRunning, setIsRunning] = useState(false);
  const [duration, setDuration] = useState(null);
  const [autoRun, setAutoRun] = useState(true);
  const [isConnected, setIsConnected] = useState(false);

  const [isCollabMode, setIsCollabMode] = useState(false);
  const [roomId, setRoomId] = useState('');
  const [userId] = useState(() => generateUserId());
  const [userName] = useState(() => generateUserName());
  const [roomUsers, setRoomUsers] = useState([]);

  const autoRunTimerRef = useRef(null);
  const abortControllerRef = useRef(null);
  const socketRef = useRef(null);
  const codeRef = useRef(code);
  const startTimeRef = useRef(null);
  const outputRef = useRef([]);

  useEffect(() => {
    codeRef.current = code;
  }, [code]);

  useEffect(() => {
    outputRef.current = output;
  }, [output]);

  useEffect(() => {
    const langConfig = LANGUAGES.find(l => l.value === language);
    if (langConfig && !code) {
      setCode(langConfig.defaultCode);
      codeRef.current = langConfig.defaultCode;
    }
  }, [language, code]);

  useEffect(() => {
    const socket = io(SOCKET_URL, {
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000
    });

    socketRef.current = socket;

    socket.on('connect', () => {
      console.log('[Socket] 已连接');
      setIsConnected(true);
    });

    socket.on('disconnect', () => {
      console.log('[Socket] 已断开');
      setIsConnected(false);
      setIsRunning(false);
    });

    socket.on('connect_error', (error) => {
      console.error('[Socket] 连接错误:', error.message);
      setIsConnected(false);
    });

    socket.on('executionStart', ({ executionId, language: execLang }) => {
      console.log(`[执行] 开始: ${executionId.slice(0, 8)}`);
      startTimeRef.current = Date.now();
      setIsRunning(true);
      setOutput([]);
      setError(null);
      setDuration(null);
      outputRef.current = [];
    });

    socket.on('output', (data) => {
      const newOutput = [...outputRef.current, {
        level: data.level,
        message: data.message,
        timestamp: data.timestamp
      }];
      outputRef.current = newOutput;
      setOutput(newOutput);
    });

    socket.on('executionEnd', ({ executionId, exitCode, duration: execDuration, error: execError }) => {
      console.log(`[执行] 结束: ${executionId.slice(0, 8)}, 退出码: ${exitCode}`);
      setIsRunning(false);

      if (startTimeRef.current) {
        const durationMs = execDuration || (Date.now() - startTimeRef.current);
        setDuration(durationMs);
        startTimeRef.current = null;
      }

      if (execError) {
        setError(execError);
      }
    });

    socket.on('error', ({ error: socketError }) => {
      console.error('[Socket] 错误:', socketError);
      setError(socketError);
      setIsRunning(false);
    });

    socket.on('roomJoined', ({ roomId: rid, language: lang, users, userCount }) => {
      console.log(`[房间] 已加入 ${rid}`);
      setRoomId(rid);
      setRoomUsers(users);
      if (lang) {
        setLanguage(lang);
      }
    });

    socket.on('userJoined', ({ userId: uid, userName: uname }) => {
      console.log(`[房间] 用户加入: ${uname}`);
      setRoomUsers(prev => {
        if (!prev.find(u => u.userId === uid)) {
          return [...prev, { userId: uid, userName: uname }];
        }
        return prev;
      });
    });

    socket.on('userLeft', ({ userId: uid, userName: uname }) => {
      console.log(`[房间] 用户离开: ${uname}`);
      setRoomUsers(prev => prev.filter(u => u.userId !== uid));
    });

    socket.on('languageChanged', ({ language: newLang, userId: uid, userName: uname }) => {
      console.log(`[房间] 语言切换为 ${newLang} (用户: ${uname})`);
      setLanguage(newLang);
    });

    socket.on('codeRunning', ({ userId: uid, userName: uname, language: runLang }) => {
      if (uid !== userId) {
        console.log(`[房间] ${uname} 正在运行 ${runLang} 代码`);
      }
    });

    return () => {
      console.log('[Socket] 清理连接');
      socket.disconnect();
      socketRef.current = null;
    };
  }, [userId]);

  const handleLanguageChange = useCallback((newLang, defaultCode) => {
    setLanguage(newLang);
    
    const socket = socketRef.current;
    if (socket && socket.connected && roomId) {
      socket.emit('changeLanguage', { language: newLang });
    }
    
    if (defaultCode && defaultCode !== codeRef.current) {
      setCode(defaultCode);
      codeRef.current = defaultCode;
      
      if (autoRunTimerRef.current) {
        clearTimeout(autoRunTimerRef.current);
      }
      
      if (autoRun) {
        autoRunTimerRef.current = setTimeout(() => {
          executeCodeWebSocket(defaultCode, newLang);
        }, AUTO_RUN_DELAY);
      }
    }
  }, [roomId, autoRun]);

  const executeCodeWebSocket = useCallback((currentCode, currentLanguage = language) => {
    const socket = socketRef.current;

    if (!socket || !socket.connected) {
      setError('WebSocket 未连接，使用 HTTP 模式');
      executeCodeHTTP(currentCode, currentLanguage);
      return;
    }

    if (isRunning) {
      socket.emit('cancel');
    }

    setOutput([]);
    setError(null);
    setDuration(null);
    outputRef.current = [];

    socket.emit('execute', {
      code: currentCode,
      language: currentLanguage
    });
  }, [language, isRunning]);

  const executeCodeHTTP = useCallback(async (currentCode, currentLanguage = language) => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    setIsRunning(true);
    setOutput([]);
    setError(null);
    setDuration(null);

    try {
      const response = await fetch('/api/execute', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          code: currentCode,
          language: currentLanguage,
        }),
        signal: abortController.signal,
      });

      if (abortController.signal.aborted) {
        return;
      }

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || '执行失败');
      }

      setOutput(data.output || []);
      setDuration(data.duration);
      if (data.error) {
        setError(data.error);
      }
    } catch (err) {
      if (err.name === 'AbortError') {
        return;
      }
      setError(err.message || '网络错误');
    } finally {
      setIsRunning(false);
      if (abortControllerRef.current === abortController) {
        abortControllerRef.current = null;
      }
    }
  }, [language]);

  const handleRun = useCallback(() => {
    executeCodeWebSocket(codeRef.current, language);
  }, [executeCodeWebSocket, language]);

  const handleCodeChange = useCallback((newCode) => {
    setCode(newCode);
    codeRef.current = newCode;

    if (autoRunTimerRef.current) {
      clearTimeout(autoRunTimerRef.current);
    }

    if (autoRun) {
      autoRunTimerRef.current = setTimeout(() => {
        executeCodeWebSocket(newCode, language);
      }, AUTO_RUN_DELAY);
    }
  }, [autoRun, executeCodeWebSocket, language]);

  const handleClear = useCallback(() => {
    setOutput([]);
    setError(null);
    setDuration(null);
    outputRef.current = [];
  }, []);

  const toggleAutoRun = useCallback(() => {
    setAutoRun((prev) => {
      if (prev && autoRunTimerRef.current) {
        clearTimeout(autoRunTimerRef.current);
        autoRunTimerRef.current = null;
      }
      return !prev;
    });
  }, []);

  const handleCancel = useCallback(() => {
    const socket = socketRef.current;
    if (socket && socket.connected && isRunning) {
      socket.emit('cancel');
      setIsRunning(false);
      setError('执行已取消');
    }
  }, [isRunning]);

  const toggleCollabMode = useCallback(() => {
    const socket = socketRef.current;
    if (!socket) return;

    if (isCollabMode) {
      socket.emit('leaveRoom');
      setIsCollabMode(false);
      setRoomId('');
      setRoomUsers([]);
    } else {
      const newRoomId = generateRoomId();
      socket.emit('joinRoom', {
        roomId: newRoomId,
        userId,
        userName
      });
      setIsCollabMode(true);
    }
  }, [isCollabMode, userId, userName]);

  const joinRoom = useCallback((roomIdToJoin) => {
    const socket = socketRef.current;
    if (!socket) return;

    socket.emit('joinRoom', {
      roomId: roomIdToJoin,
      userId,
      userName
    });
    setIsCollabMode(true);
  }, [userId, userName]);

  const copyRoomLink = useCallback(() => {
    const link = `${window.location.origin}?room=${roomId}`;
    navigator.clipboard.writeText(link);
    alert(`房间链接已复制: ${link}`);
  }, [roomId]);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
        e.preventDefault();
        handleRun();
      }

      if ((e.metaKey || e.ctrlKey) && e.key === 's') {
        e.preventDefault();
        handleRun();
      }

      if ((e.metaKey || e.ctrlKey) && e.key === 'Escape') {
        e.preventDefault();
        handleCancel();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleRun, handleCancel]);

  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const roomFromUrl = urlParams.get('room');
    if (roomFromUrl) {
      const socket = socketRef.current;
      if (socket) {
        setTimeout(() => {
          joinRoom(roomFromUrl);
        }, 500);
      }
    }
  }, [joinRoom]);

  useEffect(() => {
    return () => {
      if (autoRunTimerRef.current) {
        clearTimeout(autoRunTimerRef.current);
      }
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  const currentLangConfig = useMemo(() => {
    return LANGUAGES.find(l => l.value === language) || LANGUAGES[0];
  }, [language]);

  return (
    <div className="app">
      <header className="header">
        <div className="header-left">
          <h1 className="title">在线代码沙箱</h1>
          
          <span className={`status-indicator ${isConnected ? 'status-connected' : 'status-disconnected'}`}>
            {isConnected ? '● 已连接' : '○ 未连接'}
          </span>

          {isCollabMode && (
            <div className="room-info">
              <span className="room-id">房间: {roomId.slice(0, 8)}...</span>
              <button className="btn btn-sm" onClick={copyRoomLink}>
                分享
              </button>
              {roomUsers.length > 0 && (
                <div className="user-avatars-small">
                  {roomUsers.slice(0, 3).map((user, idx) => (
                    <div
                      key={idx}
                      className="user-avatar-small"
                      title={user.userName}
                    >
                      {user.userName.charAt(0)}
                    </div>
                  ))}
                  {roomUsers.length > 3 && (
                    <span className="more-users">+{roomUsers.length - 3}</span>
                  )}
                </div>
              )}
            </div>
          )}
        </div>

        <div className="actions">
          <LanguageSelector
            value={language}
            onChange={handleLanguageChange}
            disabled={isRunning}
          />

          <button
            className={`btn btn-collab ${isCollabMode ? 'btn-collab-active' : ''}`}
            onClick={toggleCollabMode}
            title={isCollabMode ? '退出协同模式' : '开启协同模式'}
          >
            <span>{isCollabMode ? '👥' : '👤'}</span>
            <span>{isCollabMode ? '协同中' : '协同'}</span>
          </button>

          <button
            className={`btn btn-toggle ${autoRun ? 'btn-toggle-active' : ''}`}
            onClick={toggleAutoRun}
            title="自动运行 (代码变更后自动执行)"
          >
            <span className="toggle-icon">{autoRun ? '▶' : '⏸'}</span>
            <span>自动</span>
          </button>

          {isRunning ? (
            <button
              className="btn btn-cancel"
              onClick={handleCancel}
            >
              取消
              <span className="shortcut">Esc</span>
            </button>
          ) : (
            <>
              <button
                className="btn btn-clear"
                onClick={handleClear}
                disabled={isRunning}
              >
                清空
              </button>
              <button
                className="btn btn-run"
                onClick={handleRun}
                disabled={isRunning}
              >
                运行
                <span className="shortcut">Ctrl+Enter</span>
              </button>
            </>
          )}
        </div>
      </header>

      <main className="main">
        <div className="editor-section">
          <div className="section-header">
            <span className="section-title">代码编辑器</span>
            <span className="language-tag">
              {currentLangConfig.icon} {currentLangConfig.label}
            </span>
          </div>
          <Editor 
            code={code} 
            onChange={handleCodeChange} 
            onRun={handleRun}
            language={language}
          />
        </div>

        <div className="output-section">
          <div className="section-header">
            <span className="section-title">控制台输出</span>
            {duration && (
              <span className="duration">耗时: {duration}ms</span>
            )}
          </div>
          <Output
            output={output}
            error={error}
            isRunning={isRunning}
          />
        </div>
      </main>

      <footer className="footer">
        <p>
          支持语言: {LANGUAGES.map(l => `${l.icon}${l.label}`).join(' ')}
          {isCollabMode && ` | 协同模式已开启 | ${roomUsers.length + 1} 人在线`}
          {' | Ctrl+S/Ctrl+Enter 运行 | Esc 取消'}
        </p>
      </footer>
    </div>
  );
}

export default App;
