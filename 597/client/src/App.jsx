import React, { useState, useEffect, useRef, useCallback } from 'react';
import WordCloud from './utils/wordcloud.js';

const SHAPES = [
  { value: 'circle', label: '圆形', icon: '⭕' },
  { value: 'square', label: '方形', icon: '⬜' },
  { value: 'heart', label: '心形', icon: '❤️' }
];

const ENGINES = [
  { value: 'jieba', label: 'Jieba', desc: '基于词典，速度快' },
  { value: 'biobert', label: 'BioBERT', desc: '领域增强，精度高' },
  { value: 'combined', label: '双引擎融合', desc: 'Jieba+BioBERT' }
];

const MODES = [
  { value: 'normal', label: '标准', icon: '📊' },
  { value: 'sentiment', label: '情感', icon: '😊' },
  { value: 'timeseries', label: '时序', icon: '⏱️' }
];

const COLOR_SCHEMES = [
  { value: 'vibrant', label: '鲜艳', colors: ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4'] },
  { value: 'warm', label: '暖色', colors: ['#FF6B6B', '#FFA07A', '#FFD93D', '#FF8C42'] },
  { value: 'cool', label: '冷色', colors: ['#3498DB', '#2ECC71', '#1ABC9C', '#34495E'] },
  { value: 'pastel', label: '柔和', colors: ['#FFB3BA', '#BAFFC9', '#BAE1FF', '#FFFFBA'] },
  { value: 'monochrome', label: '单色', colors: ['#2C3E50', '#34495E', '#5D6D7E', '#7F8C8D'] }
];

const FONTS = [
  { value: 'Microsoft YaHei', label: '微软雅黑' },
  { value: 'SimHei', label: '黑体' },
  { value: 'SimSun', label: '宋体' },
  { value: 'KaiTi', label: '楷体' },
  { value: 'Arial', label: 'Arial' },
  { value: 'Georgia', label: 'Georgia' },
  { value: 'Times New Roman', label: 'Times New Roman' }
];

const SAMPLE_TEXT = `在项目开始的时候，团队面临了很多困难和挑战。我们遇到了无数的bug和问题，每个人都感到沮丧和焦虑。但是大家没有放弃，而是团结一心努力解决问题。渐渐地，我们看到了进步和成功的希望。现在，项目取得了出色的成果，每个人都感到高兴和自豪。

回顾这段旅程，有太多难忘的瞬间。初期的混乱和迷茫让我们几乎崩溃。一次次的失败和错误让我们怀疑自己。但每一次突破和进步都给我们带来惊喜和动力。那些美好的合作和交流让我们成为了更好的团队。

未来充满了光明和希望。我们将继续创新和突破，追求卓越和完美。感谢每一位成员的支持和付出，你们的勇敢和坚强是我们最大的财富。让我们一起创造更伟大的成就！

人工智能技术正在快速发展。机器学习和深度学习带来了突破性的进展。自然语言处理让计算机更好地理解人类。计算机视觉让机器能够看到世界。这些创新让我们对未来充满期待。

当然，技术发展也带来了新的问题和挑战。数据隐私和安全需要我们高度重视。算法偏见和歧视可能造成伤害。我们必须警惕风险，确保技术向善。但总体来说，进步和希望是主旋律。`;

function App() {
  const [text, setText] = useState(SAMPLE_TEXT);
  const [words, setWords] = useState([]);
  const [loading, setLoading] = useState(false);
  const [shape, setShape] = useState('circle');
  const [colorScheme, setColorScheme] = useState('vibrant');
  const [fontFamily, setFontFamily] = useState('Microsoft YaHei');
  const [minFontSize, setMinFontSize] = useState(12);
  const [maxFontSize, setMaxFontSize] = useState(80);
  const [customStopWords, setCustomStopWords] = useState([]);
  const [stopWordInput, setStopWordInput] = useState('');
  const [engine, setEngine] = useState('jieba');
  const [usedEngine, setUsedEngine] = useState('');
  const [renderTime, setRenderTime] = useState(null);
  const [placedCount, setPlacedCount] = useState(0);
  const [mode, setMode] = useState('normal');

  const [timeFrames, setTimeFrames] = useState([]);
  const [currentFrame, setCurrentFrame] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [frameRate, setFrameRate] = useState(1);
  const animationRef = useRef(null);

  const canvasRef = useRef(null);
  const wordCloudRef = useRef(null);
  const debounceTimerRef = useRef(null);

  const analyzeText = useCallback(async () => {
    if (!text.trim()) {
      setWords([]);
      setTimeFrames([]);
      return;
    }

    setLoading(true);
    const withSentiment = mode === 'sentiment' || mode === 'timeseries';

    try {
      if (mode === 'timeseries') {
        const response = await fetch('/api/timeseries', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text, stopWords: customStopWords, engine, segments: 8, withSentiment: true })
        });
        const data = await response.json();
        setTimeFrames(data.frames || []);
        if (data.frames && data.frames.length > 0) {
          setWords(data.frames[0].words);
        }
        setUsedEngine(data.engine || engine);
      } else {
        const response = await fetch('/api/analyze', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text, stopWords: customStopWords, engine, withSentiment })
        });
        const data = await response.json();
        setWords(data.words || []);
        setUsedEngine(data.engine || engine);
      }
    } catch (error) {
      console.error('分析失败:', error);
      const localWords = localAnalyze(text, withSentiment);
      setWords(localWords);
      setUsedEngine('local-fallback');
    } finally {
      setLoading(false);
    }
  }, [text, customStopWords, engine, mode]);

  const localAnalyze = (inputText, withSentiment = false) => {
    const stopWords = new Set([...customStopWords, '的', '是', '在', '我', '有', '和', '就', '不', 'the', 'a', 'an', 'is', 'are']);
    const positive = new Set(['好', '棒', '优秀', '成功', 'good', 'great', 'excellent']);
    const negative = new Set(['差', '坏', '问题', '困难', 'bad', 'terrible', 'worse']);

    const wordCount = new Map();
    const chineseWords = inputText.match(/[\u4e00-\u9fa5]{2,}/g) || [];
    const englishWords = inputText.toLowerCase().match(/[a-zA-Z]{2,}/g) || [];
    [...chineseWords, ...englishWords].forEach(word => {
      if (!stopWords.has(word.toLowerCase())) {
        wordCount.set(word, (wordCount.get(word) || 0) + 1);
      }
    });
    return Array.from(wordCount.entries())
      .map(([word, count]) => {
        const result = { word, count };
        if (withSentiment) {
          if (positive.has(word) || positive.has(word.toLowerCase())) result.sentiment = 'positive';
          else if (negative.has(word) || negative.has(word.toLowerCase())) result.sentiment = 'negative';
          else result.sentiment = 'neutral';
        }
        return result;
      })
      .sort((a, b) => b.count - a.count)
      .slice(0, 100);
  };

  useEffect(() => {
    if (debounceTimerRef.current) clearTimeout(debounceTimerRef.current);
    debounceTimerRef.current = setTimeout(() => { analyzeText(); }, 600);
    return () => { if (debounceTimerRef.current) clearTimeout(debounceTimerRef.current); };
  }, [analyzeText]);

  useEffect(() => {
    if (canvasRef.current && words.length > 0) {
      const t0 = performance.now();
      if (!wordCloudRef.current) {
        wordCloudRef.current = new WordCloud(canvasRef.current, {
          width: 700, height: 500, fontFamily, minFontSize, maxFontSize, colorScheme, shape,
          sentimentMode: mode === 'sentiment'
        });
      } else {
        wordCloudRef.current.updateOptions({
          fontFamily, minFontSize, maxFontSize, colorScheme, shape,
          sentimentMode: mode === 'sentiment'
        });
      }
      wordCloudRef.current.render(words);
      const elapsed = (performance.now() - t0).toFixed(1);
      setRenderTime(elapsed);
      setPlacedCount(wordCloudRef.current.placedWords.length);
    }
  }, [words, shape, colorScheme, fontFamily, minFontSize, maxFontSize, mode]);

  useEffect(() => {
    if (mode === 'timeseries' && timeFrames.length > 0 && isPlaying) {
      const animate = () => {
        setCurrentFrame(prev => {
          const next = (prev + 1) % timeFrames.length;
          const frameWords = timeFrames[next]?.words || [];
          if (wordCloudRef.current && frameWords.length > 0) {
            wordCloudRef.current.render(frameWords);
          }
          return next;
        });
      };
      animationRef.current = setInterval(animate, 1000 / frameRate);
      return () => clearInterval(animationRef.current);
    }
  }, [mode, timeFrames, isPlaying, frameRate]);

  useEffect(() => {
    if (mode === 'timeseries' && timeFrames.length > 0 && timeFrames[currentFrame]) {
      const frameWords = timeFrames[currentFrame]?.words || [];
      setWords(frameWords);
    }
  }, [currentFrame, mode, timeFrames]);

  const handleAddStopWord = () => {
    const word = stopWordInput.trim();
    if (word && !customStopWords.includes(word)) {
      setCustomStopWords([...customStopWords, word]);
      setStopWordInput('');
    }
  };

  const handleRemoveStopWord = (word) => {
    setCustomStopWords(customStopWords.filter(w => w !== word));
  };

  const handleDownloadPNG = () => {
    if (wordCloudRef.current) wordCloudRef.current.downloadPNG('wordcloud.png');
  };

  const handleDownloadSVG = () => {
    if (wordCloudRef.current) wordCloudRef.current.downloadSVG('wordcloud.svg');
  };

  const handleRegenerate = () => { analyzeText(); };

  const handleModeChange = (newMode) => {
    setMode(newMode);
    setCurrentFrame(0);
    setIsPlaying(false);
    setTimeFrames([]);
  };

  const togglePlay = () => {
    setIsPlaying(!isPlaying);
  };

  const handleFrameChange = (frame) => {
    setCurrentFrame(frame);
    setIsPlaying(false);
    if (wordCloudRef.current && timeFrames[frame]) {
      wordCloudRef.current.lastWordsData = null;
      wordCloudRef.current.render(timeFrames[frame].words);
    }
  };

  const totalWords = words.length;
  const totalCount = words.reduce((sum, w) => sum + w.count, 0);
  const topWord = words[0]?.word || '-';
  const topCount = words[0]?.count || 0;
  const positiveCount = words.filter(w => w.sentiment === 'positive').length;
  const negativeCount = words.filter(w => w.sentiment === 'negative').length;

  return (
    <div className="app">
      <header className="app-header">
        <h1>☁️ 词云生成工具</h1>
        <p>标准词云 · 情感词云 · 时序动画 · 支持SVG矢量导出</p>
      </header>

      <div className="main-container">
        <div className="config-panel">
          <div className="config-section">
            <h3>🎯 工作模式</h3>
            <div className="mode-selector">
              {MODES.map(m => (
                <div
                  key={m.value}
                  className={`mode-option ${mode === m.value ? 'active' : ''}`}
                  onClick={() => handleModeChange(m.value)}
                >
                  <span className="mode-icon">{m.icon}</span>
                  <span className="mode-label">{m.label}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="config-section">
            <h3>📝 文本输入</h3>
            <div className="input-group">
              <label>输入文本内容</label>
              <textarea
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder="请输入要生成词云的文本..."
                rows={6}
              />
            </div>
          </div>

          <div className="config-section">
            <h3>🧠 分词引擎</h3>
            <div className="engine-selector">
              {ENGINES.map(eng => (
                <div
                  key={eng.value}
                  className={`engine-option ${engine === eng.value ? 'active' : ''}`}
                  onClick={() => setEngine(eng.value)}
                >
                  <div className="engine-name">{eng.label}</div>
                  <div className="engine-desc">{eng.desc}</div>
                </div>
              ))}
            </div>
          </div>

          <div className="config-section">
            <h3>🎨 外观配置</h3>

            <div className="input-group">
              <label>形状掩膜</label>
              <div className="shape-selector">
                {SHAPES.map(s => (
                  <div
                    key={s.value}
                    className={`shape-option ${shape === s.value ? 'active' : ''}`}
                    onClick={() => setShape(s.value)}
                  >
                    <span className="shape-icon">{s.icon}</span>
                    <span className="shape-label">{s.label}</span>
                  </div>
                ))}
              </div>
            </div>

            {mode !== 'sentiment' && (
              <div className="input-group">
                <label>配色方案</label>
                <div className="color-picker">
                  {COLOR_SCHEMES.map(scheme => (
                    <div
                      key={scheme.value}
                      className={`color-option ${colorScheme === scheme.value ? 'active' : ''}`}
                      style={{ background: `linear-gradient(135deg, ${scheme.colors.join(', ')})` }}
                      onClick={() => setColorScheme(scheme.value)}
                      title={scheme.label}
                    />
                  ))}
                </div>
              </div>
            )}

            {mode === 'sentiment' && (
              <div className="input-group">
                <label>情感图例</label>
                <div className="sentiment-legend">
                  <div className="legend-item">
                    <span className="legend-color positive"></span>
                    <span className="legend-text">正面情感</span>
                  </div>
                  <div className="legend-item">
                    <span className="legend-color neutral"></span>
                    <span className="legend-text">中性情感</span>
                  </div>
                  <div className="legend-item">
                    <span className="legend-color negative"></span>
                    <span className="legend-text">负面情感</span>
                  </div>
                </div>
              </div>
            )}

            <div className="input-group">
              <label>字体</label>
              <select value={fontFamily} onChange={(e) => setFontFamily(e.target.value)}>
                {FONTS.map(f => (
                  <option key={f.value} value={f.value}>{f.label}</option>
                ))}
              </select>
            </div>

            <div className="input-group">
              <label>最小字号: {minFontSize}px</label>
              <input type="range" min="8" max="30" value={minFontSize} onChange={(e) => setMinFontSize(Number(e.target.value))} />
            </div>

            <div className="input-group">
              <label>最大字号: {maxFontSize}px</label>
              <input type="range" min="40" max="120" value={maxFontSize} onChange={(e) => setMaxFontSize(Number(e.target.value))} />
            </div>
          </div>

          <div className="config-section">
            <h3>🚫 停用词</h3>
            <div className="stopwords-input">
              <input
                type="text"
                value={stopWordInput}
                onChange={(e) => setStopWordInput(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleAddStopWord()}
                placeholder="输入停用词..."
              />
              <button onClick={handleAddStopWord}>添加</button>
            </div>
            <div className="stopwords-list">
              {customStopWords.map(word => (
                <span key={word} className="stopword-tag">
                  {word}
                  <button onClick={() => handleRemoveStopWord(word)}>×</button>
                </span>
              ))}
            </div>
          </div>
        </div>

        <div className="preview-panel">
          <div className="preview-header">
            <h2>词云预览</h2>
            <div className="preview-actions">
              <button className="btn btn-secondary" onClick={handleRegenerate} disabled={loading}>
                {loading ? <span className="loading"></span> : '🔄 重新生成'}
              </button>
              <button className="btn btn-secondary" onClick={handleDownloadPNG} disabled={words.length === 0}>
                📷 PNG
              </button>
              <button className="btn btn-primary" onClick={handleDownloadSVG} disabled={words.length === 0}>
                📐 导出 SVG
              </button>
            </div>
          </div>

          {mode === 'timeseries' && timeFrames.length > 0 && (
            <div className="timeline-controls">
              <button className="btn btn-small" onClick={togglePlay}>
                {isPlaying ? '⏸️ 暂停' : '▶️ 播放'}
              </button>
              <div className="timeline-slider">
                <input
                  type="range"
                  min={0}
                  max={timeFrames.length - 1}
                  value={currentFrame}
                  onChange={(e) => handleFrameChange(Number(e.target.value))}
                />
                <span className="frame-label">
                  时段 {currentFrame + 1} / {timeFrames.length}
                </span>
              </div>
              <select value={frameRate} onChange={(e) => setFrameRate(Number(e.target.value))}>
                <option value={0.5}>0.5x</option>
                <option value={1}>1x</option>
                <option value={2}>2x</option>
                <option value={3}>3x</option>
              </select>
            </div>
          )}

          <div className="wordcloud-container">
            {words.length > 0 ? (
              <canvas ref={canvasRef}></canvas>
            ) : (
              <div className="wordcloud-placeholder">
                <div className="icon">☁️</div>
                <p>{loading ? '正在分析文本...' : '输入文本后将在这里生成词云'}</p>
              </div>
            )}
          </div>

          <div className="stats-panel">
            <h4>📊 统计信息</h4>
            <div className="stats-grid">
              <div className="stat-item">
                <div className="stat-value">{totalWords}</div>
                <div className="stat-label">词汇数量</div>
              </div>
              <div className="stat-item">
                <div className="stat-value">{totalCount}</div>
                <div className="stat-label">总词频</div>
              </div>
              <div className="stat-item">
                <div className="stat-value" title={topWord}>{topWord.length > 6 ? topWord.slice(0, 6) + '...' : topWord}</div>
                <div className="stat-label">高频词汇</div>
              </div>
              <div className="stat-item">
                <div className="stat-value">{topCount}</div>
                <div className="stat-label">最高频次</div>
              </div>
              {mode === 'sentiment' && (
                <>
                  <div className="stat-item">
                    <div className="stat-value" style={{ color: '#22C55E' }}>{positiveCount}</div>
                    <div className="stat-label">正面词</div>
                  </div>
                  <div className="stat-item">
                    <div className="stat-value" style={{ color: '#EF4444' }}>{negativeCount}</div>
                    <div className="stat-label">负面词</div>
                  </div>
                </>
              )}
              {mode !== 'sentiment' && (
                <>
                  <div className="stat-item">
                    <div className="stat-value">{placedCount}</div>
                    <div className="stat-label">已放置</div>
                  </div>
                  <div className="stat-item">
                    <div className="stat-value">{renderTime ? `${renderTime}ms` : '-'}</div>
                    <div className="stat-label">渲染耗时</div>
                  </div>
                </>
              )}
            </div>
            {usedEngine && (
              <div className="engine-badge">
                分词引擎: <strong>{usedEngine}</strong>
                {mode !== 'normal' && ` · ${MODES.find(m => m.value === mode)?.label}模式`}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
