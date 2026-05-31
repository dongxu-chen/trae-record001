import { useState, useEffect, useRef, useCallback } from 'react';

const DEFAULT_STYLE = {
  fontFamily: "'Microsoft YaHei', 'PingFang SC', sans-serif",
  fontSize: 18,
  textColor: '#e0e0e0',
  bgColor: 'rgba(255, 255, 255, 0.05)',
  borderColor: '#00d4ff',
  translationColor: '#fbbf24',
  speakerLabelBg: 'rgba(124, 58, 237, 0.3)',
  speakerLabelColor: '#a78bfa'
};

const FONT_OPTIONS = [
  { value: "'Microsoft YaHei', 'PingFang SC', sans-serif", label: '微软雅黑' },
  { value: "'SimSun', 'Songti SC', serif", label: '宋体' },
  { value: "'KaiTi', 'STKaiti', serif", label: '楷体' },
  { value: "'SimHei', 'Heiti SC', sans-serif", label: '黑体' },
  { value: "'FangSong', 'STFangsong', serif", label: '仿宋' },
  { value: "'Arial', 'Helvetica', sans-serif", label: 'Arial' },
  { value: "'Georgia', serif", label: 'Georgia' },
  { value: "'Consolas', 'Courier New', monospace", label: 'Consolas' }
];

const COLOR_PRESETS = [
  { name: '经典白', text: '#e0e0e0', bg: 'rgba(255,255,255,0.05)', border: '#00d4ff' },
  { name: '暗夜蓝', text: '#93c5fd', bg: 'rgba(59,130,246,0.08)', border: '#3b82f6' },
  { name: '翡翠绿', text: '#6ee7b7', bg: 'rgba(16,185,129,0.08)', border: '#10b981' },
  { name: '琥珀橙', text: '#fcd34d', bg: 'rgba(245,158,11,0.08)', border: '#f59e0b' },
  { name: '玫瑰红', text: '#fda4af', bg: 'rgba(244,63,94,0.08)', border: '#f43f5e' },
  { name: '薰衣紫', text: '#c4b5fd', bg: 'rgba(139,92,246,0.08)', border: '#8b5cf6' }
];

function App() {
  const [transcriptions, setTranscriptions] = useState([]);
  const [partialText, setPartialText] = useState('');
  const [currentLanguage, setCurrentLanguage] = useState('zh-CN');
  const [supportedLanguages, setSupportedLanguages] = useState({});
  const [hotwords, setHotwords] = useState([]);
  const [hotwordStats, setHotwordStats] = useState([]);
  const [newHotword, setNewHotword] = useState('');
  const [connectionStatus, setConnectionStatus] = useState('connecting');
  const [device, setDevice] = useState('cpu');
  const [avgLatency, setAvgLatency] = useState(0);
  const [latencyHistory, setLatencyHistory] = useState([]);
  const [speakers, setSpeakers] = useState({});
  const [diarizationEnabled, setDiarizationEnabled] = useState(true);
  const [translationEnabled, setTranslationEnabled] = useState(false);
  const [targetLang, setTargetLang] = useState('en');
  const [availableTargetLangs, setAvailableTargetLangs] = useState([]);
  const [editingSpeaker, setEditingSpeaker] = useState(null);
  const [speakerNameInput, setSpeakerNameInput] = useState('');
  const [subtitleStyle, setSubtitleStyle] = useState(() => {
    const saved = localStorage.getItem('subtitleStyle');
    return saved ? JSON.parse(saved) : DEFAULT_STYLE;
  });
  const [showStylePanel, setShowStylePanel] = useState(false);
  const wsRef = useRef(null);

  useEffect(() => {
    localStorage.setItem('subtitleStyle', JSON.stringify(subtitleStyle));
  }, [subtitleStyle]);

  const connectWebSocket = useCallback(() => {
    const ws = new WebSocket('ws://localhost:3001');
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('Connected to WebSocket server');
      setConnectionStatus('connected');
      ws.send(JSON.stringify({ action: 'get_config' }));
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      switch (data.type) {
        case 'transcription':
          if (data.partial) {
            setPartialText(data.text);
          } else {
            setTranscriptions((prev) => [
              {
                id: Date.now(),
                text: data.text,
                timestamp: data.timestamp,
                language: data.language,
                latency: data.latency,
                speaker_id: data.speaker_id,
                speaker_name: data.speaker_name,
                speaker_color: data.speaker_color,
                translation: data.translation,
                target_lang: data.target_lang
              },
              ...prev.slice(0, 99)
            ]);
            setPartialText('');
          }
          
          if (data.latency !== undefined) {
            setLatencyHistory((prev) => {
              const newHistory = [...prev, data.latency * 1000].slice(-20);
              const avg = newHistory.reduce((a, b) => a + b, 0) / newHistory.length;
              setAvgLatency(avg);
              return newHistory;
            });
          }

          if (data.speakers) {
            setSpeakers(data.speakers);
          }
          break;
          
        case 'partial_update':
          setPartialText(data.text);
          break;
          
        case 'config':
          setCurrentLanguage(data.language);
          setSupportedLanguages(data.supported_languages);
          setHotwords(data.hotwords);
          if (data.hotword_stats) setHotwordStats(data.hotword_stats);
          if (data.device) setDevice(data.device);
          if (data.diarization_enabled !== undefined) setDiarizationEnabled(data.diarization_enabled);
          if (data.speakers) setSpeakers(data.speakers);
          if (data.translation_enabled !== undefined) setTranslationEnabled(data.translation_enabled);
          if (data.target_lang) setTargetLang(data.target_lang);
          if (data.available_target_langs) setAvailableTargetLangs(data.available_target_langs);
          break;
          
        case 'language_changed':
          setCurrentLanguage(data.language);
          break;

        case 'diarization_toggled':
          setDiarizationEnabled(data.enabled);
          break;

        case 'speaker_name_changed':
          setSpeakers(data.speakers);
          break;

        case 'speakers_reset':
          setSpeakers(data.speakers);
          break;

        case 'translation_toggled':
          setTranslationEnabled(data.enabled);
          break;

        case 'target_lang_changed':
          setTargetLang(data.target_lang);
          break;
          
        case 'hotword_added':
        case 'hotword_removed':
          setHotwords(data.hotwords);
          if (data.hotword_stats) setHotwordStats(data.hotword_stats);
          break;
          
        case 'error':
          console.error('Server error:', data.message);
          break;
          
        default:
          break;
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      setConnectionStatus('disconnected');
    };

    ws.onclose = () => {
      console.log('Disconnected from WebSocket server');
      setConnectionStatus('disconnected');
      setTimeout(connectWebSocket, 3000);
    };
  }, []);

  useEffect(() => {
    connectWebSocket();
    return () => {
      if (wsRef.current) wsRef.current.close();
    };
  }, [connectWebSocket]);

  const sendAction = (action) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(action));
    }
  };

  const handleLanguageChange = (e) => {
    const newLang = e.target.value;
    setCurrentLanguage(newLang);
    sendAction({ action: 'set_language', language: newLang });
  };

  const handleAddHotword = () => {
    if (newHotword.trim() && !hotwords.includes(newHotword.trim())) {
      sendAction({ action: 'add_hotword', word: newHotword.trim() });
      setNewHotword('');
    }
  };

  const handleRemoveHotword = (word) => {
    sendAction({ action: 'remove_hotword', word });
  };

  const handleClearTranscriptions = () => setTranscriptions([]);

  const handleToggleDiarization = () => {
    const newVal = !diarizationEnabled;
    setDiarizationEnabled(newVal);
    sendAction({ action: 'toggle_diarization', enabled: newVal });
  };

  const handleSetSpeakerName = (speakerId, name) => {
    sendAction({ action: 'set_speaker_name', speaker_id: speakerId, name });
    setEditingSpeaker(null);
    setSpeakerNameInput('');
  };

  const handleResetSpeakers = () => {
    sendAction({ action: 'reset_speakers' });
  };

  const handleToggleTranslation = () => {
    const newVal = !translationEnabled;
    setTranslationEnabled(newVal);
    sendAction({ action: 'toggle_translation', enabled: newVal });
  };

  const handleSetTargetLang = (e) => {
    const lang = e.target.value;
    setTargetLang(lang);
    sendAction({ action: 'set_target_lang', target_lang: lang });
  };

  const applyColorPreset = (preset) => {
    setSubtitleStyle(prev => ({
      ...prev,
      textColor: preset.text,
      bgColor: preset.bg,
      borderColor: preset.border
    }));
  };

  const updateStyle = (key, value) => {
    setSubtitleStyle(prev => ({ ...prev, [key]: value }));
  };

  const resetStyle = () => setSubtitleStyle(DEFAULT_STYLE);

  const formatTimestamp = (timestamp) => {
    const date = new Date(timestamp * 1000);
    return date.toLocaleTimeString('zh-CN', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  };

  const getStatusText = () => {
    switch (connectionStatus) {
      case 'connected': return '已连接';
      case 'connecting': return '连接中...';
      case 'disconnected': return '已断开';
      default: return '未知';
    }
  };

  const targetLangNames = {
    'zh-CN': '中文', 'en': '英语', 'ja': '日语',
    'ko': '韩语', 'fr': '法语', 'de': '德语', 'es': '西班牙语', 'ru': '俄语'
  };

  return (
    <div className="app">
      <header className="header">
        <h1>实时语音转文字字幕系统</h1>
        <div className="status-bar">
          <span className="status-text">{getStatusText()}</span>
          <div className={`status-indicator ${connectionStatus}`}></div>
        </div>
      </header>

      <main className="main-content">
        <div className="subtitle-container">
          <div className="subtitle-header">
            <h2>实时字幕</h2>
            <div className="header-actions">
              <button className="style-toggle-btn" onClick={() => setShowStylePanel(!showStylePanel)}>
                样式
              </button>
              <button className="clear-btn" onClick={handleClearTranscriptions}>
                清空记录
              </button>
            </div>
          </div>

          {showStylePanel && (
            <div className="style-panel">
              <div className="style-section">
                <label>字体</label>
                <select value={subtitleStyle.fontFamily} onChange={(e) => updateStyle('fontFamily', e.target.value)}>
                  {FONT_OPTIONS.map(f => <option key={f.value} value={f.value}>{f.label}</option>)}
                </select>
              </div>
              <div className="style-section">
                <label>字号: {subtitleStyle.fontSize}px</label>
                <input type="range" min="12" max="32" value={subtitleStyle.fontSize}
                  onChange={(e) => updateStyle('fontSize', parseInt(e.target.value))} />
              </div>
              <div className="style-section">
                <label>文字颜色</label>
                <input type="color" value={subtitleStyle.textColor.startsWith('#') ? subtitleStyle.textColor : '#e0e0e0'}
                  onChange={(e) => updateStyle('textColor', e.target.value)} />
              </div>
              <div className="style-section">
                <label>背景颜色</label>
                <input type="color" value={subtitleStyle.bgColor.startsWith('rgba') ? '#1a1a2e' : subtitleStyle.bgColor}
                  onChange={(e) => updateStyle('bgColor', e.target.value + '1a')} />
              </div>
              <div className="style-section">
                <label>边框颜色</label>
                <input type="color" value={subtitleStyle.borderColor}
                  onChange={(e) => updateStyle('borderColor', e.target.value)} />
              </div>
              <div className="style-section">
                <label>翻译颜色</label>
                <input type="color" value={subtitleStyle.translationColor}
                  onChange={(e) => updateStyle('translationColor', e.target.value)} />
              </div>
              <div className="style-section">
                <label>配色方案</label>
                <div className="color-presets">
                  {COLOR_PRESETS.map(p => (
                    <button key={p.name} className="preset-btn" title={p.name}
                      style={{ background: p.border, color: p.text }}
                      onClick={() => applyColorPreset(p)}>
                      {p.name}
                    </button>
                  ))}
                </div>
              </div>
              <button className="reset-style-btn" onClick={resetStyle}>恢复默认</button>
            </div>
          )}

          <div className="subtitle-display">
            {partialText && (
              <div className="subtitle-item partial" style={{
                borderLeftColor: '#f59e0b',
                background: 'rgba(245, 158, 11, 0.05)',
                fontFamily: subtitleStyle.fontFamily,
                fontSize: `${subtitleStyle.fontSize}px`
              }}>
                <div className="timestamp">
                  实时识别中...
                  <span className="lang-badge">partial</span>
                </div>
                <div className="text" style={{ color: subtitleStyle.textColor }}>
                  {partialText}<span className="cursor">|</span>
                </div>
              </div>
            )}
            {transcriptions.length === 0 && !partialText ? (
              <div className="no-subtitle">
                等待语音输入...
                <br />
                <small>请确保麦克风已连接并授权</small>
              </div>
            ) : (
              transcriptions.map((item) => (
                <div key={item.id} className="subtitle-item" style={{
                  borderLeftColor: item.speaker_color || subtitleStyle.borderColor,
                  background: subtitleStyle.bgColor,
                  fontFamily: subtitleStyle.fontFamily,
                  fontSize: `${subtitleStyle.fontSize}px`
                }}>
                  <div className="timestamp">
                    {formatTimestamp(item.timestamp)}
                    <span className="lang-badge">{item.language}</span>
                    {item.latency !== undefined && (
                      <span className={`latency-badge ${item.latency < 0.5 ? 'good' : 'warning'}`}>
                        {(item.latency * 1000).toFixed(0)}ms
                      </span>
                    )}
                  </div>
                  {item.speaker_name && (
                    <div className="speaker-label" style={{
                      background: item.speaker_color ? `${item.speaker_color}33` : subtitleStyle.speakerLabelBg,
                      color: item.speaker_color || subtitleStyle.speakerLabelColor
                    }}>
                      {item.speaker_name}
                    </div>
                  )}
                  <div className="text" style={{ color: subtitleStyle.textColor }}>
                    {item.text}
                  </div>
                  {item.translation && (
                    <div className="translation-text" style={{ color: subtitleStyle.translationColor }}>
                      {item.translation}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </div>

        <aside className="sidebar">
          <div className="control-panel">
            <h3>语言选择</h3>
            <select className="language-select" value={currentLanguage} onChange={handleLanguageChange}>
              {Object.entries(supportedLanguages).map(([code, name]) => (
                <option key={code} value={code}>{name}</option>
              ))}
            </select>
          </div>

          <div className="control-panel">
            <h3>说话人分离</h3>
            <label className="toggle-row">
              <span>启用</span>
              <input type="checkbox" checked={diarizationEnabled} onChange={handleToggleDiarization} />
            </label>
            {diarizationEnabled && Object.keys(speakers).length > 0 && (
              <div className="speaker-list">
                {Object.entries(speakers).map(([id, info]) => (
                  <div key={id} className="speaker-item">
                    <span className="speaker-dot" style={{ background: info.color }}></span>
                    {editingSpeaker === id ? (
                      <input className="speaker-name-input" value={speakerNameInput}
                        onChange={(e) => setSpeakerNameInput(e.target.value)}
                        onBlur={() => handleSetSpeakerName(id, speakerNameInput)}
                        onKeyPress={(e) => e.key === 'Enter' && handleSetSpeakerName(id, speakerNameInput)}
                        autoFocus />
                    ) : (
                      <span className="speaker-name" onClick={() => { setEditingSpeaker(id); setSpeakerNameInput(info.name); }}>
                        {info.name}
                      </span>
                    )}
                    <span className="speaker-count">{info.segment_count}段</span>
                  </div>
                ))}
                <button className="reset-speakers-btn" onClick={handleResetSpeakers}>重置说话人</button>
              </div>
            )}
          </div>

          <div className="control-panel">
            <h3>实时翻译</h3>
            <label className="toggle-row">
              <span>启用翻译</span>
              <input type="checkbox" checked={translationEnabled} onChange={handleToggleTranslation} />
            </label>
            {translationEnabled && (
              <select className="language-select" value={targetLang} onChange={handleSetTargetLang}>
                {(availableTargetLangs.length > 0 ? availableTargetLangs : Object.keys(targetLangNames)).map(lang => (
                  <option key={lang} value={lang}>{targetLangNames[lang] || lang}</option>
                ))}
              </select>
            )}
          </div>

          <div className="hotword-manager">
            <h3>热词优化</h3>
            <div className="hotword-input">
              <input type="text" placeholder="输入热词..." value={newHotword}
                onChange={(e) => setNewHotword(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleAddHotword()} />
              <button className="add-btn" onClick={handleAddHotword}>添加</button>
            </div>
            <div className="hotword-list">
              {hotwords.map((word) => (
                <div key={word} className="hotword-tag">
                  {word}
                  <button onClick={() => handleRemoveHotword(word)}>×</button>
                </div>
              ))}
            </div>
          </div>

          <div className="connection-info">
            <h3>系统信息</h3>
            <p>服务器状态: <span className="status-text">{getStatusText()}</span></p>
            <p>推理设备: <span className="status-text">{device.toUpperCase()}</span></p>
            <p>当前语言: {supportedLanguages[currentLanguage] || currentLanguage}</p>
            <p>说话人数: {Object.keys(speakers).length}</p>
            <p>翻译: {translationEnabled ? targetLangNames[targetLang] || targetLang : '关闭'}</p>
            <p>平均延迟: <span className={`status-text ${avgLatency < 500 ? 'text-good' : 'text-warning'}`}>
              {avgLatency.toFixed(0)} ms
            </span></p>
          </div>

          {hotwordStats.length > 0 && (
            <div className="hotword-stats">
              <h3>热词统计</h3>
              <div className="hotword-stats-list">
                {hotwordStats.slice(0, 5).map((item) => (
                  <div key={item.word} className="hotword-stat-item">
                    <span className="hotword-name">{item.word}</span>
                    <span className="hotword-weight">权重: {item.weight.toFixed(2)}</span>
                    <span className="hotword-count">匹配: {item.match_count}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </aside>
      </main>
    </div>
  );
}

export default App;
