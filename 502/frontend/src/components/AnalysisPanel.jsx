import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';

function AnalysisPanel({ apiBase, videoInfo, onAnalysisComplete, onBack }) {
  const [analyzing, setAnalyzing] = useState(false);
  const [status, setStatus] = useState('idle');
  const [progress, setProgress] = useState(0);
  const [message, setMessage] = useState('');
  const [error, setError] = useState(null);
  const [options, setOptions] = useState({
    sensitivity: 1.0,
    detect_motion: true,
    detect_color: true,
    detect_brightness: true,
    detect_audio: true,
    detect_laughter: true,
    audio_visual_fusion: true,
    min_duration: 2.0,
    max_duration: 30.0,
    merge_gap: 2.0
  });
  const eventSourceRef = useRef(null);

  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, []);

  const startAnalysis = async () => {
    setAnalyzing(true);
    setStatus('processing');
    setProgress(5);
    setMessage('启动分析...');
    setError(null);

    try {
      const response = await axios.post(`${apiBase}/analyze/${videoInfo.id}`, options);

      if (response.data.success) {
        listenToProgress();
      } else {
        setError(response.data.error || '启动分析失败');
        setAnalyzing(false);
        setStatus('error');
      }
    } catch (err) {
      setError(err.response?.data?.error || '启动分析失败');
      setAnalyzing(false);
      setStatus('error');
    }
  };

  const listenToProgress = () => {
    const es = new EventSource(`${apiBase}/analyze/${videoInfo.id}/events`);
    eventSourceRef.current = es;

    es.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        if (data.status === 'processing') {
          setProgress(Math.max(data.progress || 10, 10));
          setMessage(data.message || '正在分析...');
        } else if (data.status === 'completed') {
          setProgress(100);
          setMessage('分析完成！');
          setStatus('completed');
          setAnalyzing(false);
          es.close();
          eventSourceRef.current = null;

          setTimeout(() => {
            fetchResult();
          }, 500);
        } else if (data.status === 'error') {
          setError(data.error || '分析过程中出现错误');
          setStatus('error');
          setAnalyzing(false);
          es.close();
          eventSourceRef.current = null;
        }
      } catch (e) {
        // ignore parse errors
      }
    };

    es.onerror = () => {
      es.close();
      eventSourceRef.current = null;
      pollStatus();
    };
  };

  const pollStatus = async () => {
    const interval = setInterval(async () => {
      try {
        const response = await axios.get(`${apiBase}/analyze/${videoInfo.id}/status`);
        const data = response.data;

        if (data.status === 'completed') {
          clearInterval(interval);
          setProgress(100);
          setMessage('分析完成！');
          setStatus('completed');
          setAnalyzing(false);
          fetchResult();
        } else if (data.status === 'error') {
          clearInterval(interval);
          setError(data.error || '分析失败');
          setStatus('error');
          setAnalyzing(false);
        } else if (data.status === 'processing') {
          setProgress(prev => Math.min(prev + 5, 90));
        }
      } catch (err) {
        clearInterval(interval);
      }
    }, 3000);
  };

  const fetchResult = async () => {
    try {
      const response = await axios.get(`${apiBase}/analyze/${videoInfo.id}/result`);
      if (response.data.success) {
        onAnalysisComplete(response.data.result);
      } else {
        setError('获取分析结果失败');
      }
    } catch (err) {
      setError('获取分析结果失败');
    }
  };

  const updateOption = (key, value) => {
    setOptions(prev => ({ ...prev, [key]: value }));
  };

  const progressSteps = [
    { pct: 10, label: '提取视频帧' },
    { pct: 30, label: '分析画面内容' },
    { pct: 50, label: '检测运动高光' },
    { pct: 65, label: '分析音频特征' },
    { pct: 80, label: '合并检测结果' },
    { pct: 95, label: '生成分析报告' }
  ];

  return (
    <div className="analysis-panel">
      <div className="analysis-header">
        <button className="btn btn-ghost" onClick={onBack}>
          <span className="material-icons-round">arrow_back</span>
          返回
        </button>
        <div className="video-info-badge">
          <span className="material-icons-round">videocam</span>
          {videoInfo.originalName}
        </div>
      </div>

      <div className="analysis-content">
        <div className="analysis-options">
          <h3>
            <span className="material-icons-round">tune</span>
            分析参数设置
          </h3>

          <div className="option-group">
            <label>检测灵敏度</label>
            <div className="slider-group">
              <input
                type="range"
                min="0.5"
                max="2.0"
                step="0.1"
                value={options.sensitivity}
                onChange={e => updateOption('sensitivity', parseFloat(e.target.value))}
                disabled={analyzing}
              />
              <span className="slider-value">{options.sensitivity.toFixed(1)}</span>
            </div>
            <div className="slider-labels">
              <span>精确</span><span>平衡</span><span>宽松</span>
            </div>
          </div>

          <div className="option-group">
            <label>检测模块</label>
            <div className="checkbox-group">
              {[
                { key: 'detect_motion', label: '运动检测', icon: 'directions_run' },
                { key: 'detect_color', label: '色彩变化', icon: 'palette' },
                { key: 'detect_brightness', label: '亮度变化', icon: 'light_mode' },
                { key: 'detect_audio', label: '音频峰值', icon: 'graphic_eq' },
                { key: 'detect_laughter', label: '笑声检测', icon: 'sentiment_very_satisfied' },
                { key: 'audio_visual_fusion', label: '音视频融合', icon: 'hearing' }
              ].map(item => (
                <label key={item.key} className={`checkbox-item ${analyzing ? 'disabled' : ''}`}>
                  <input
                    type="checkbox"
                    checked={options[item.key]}
                    onChange={e => updateOption(item.key, e.target.checked)}
                    disabled={analyzing}
                  />
                  <span className="material-icons-round">{item.icon}</span>
                  {item.label}
                </label>
              ))}
            </div>
          </div>

          <div className="option-group">
            <label>片段最短时长 (秒)</label>
            <input
              type="number"
              min="1"
              max="10"
              value={options.min_duration}
              onChange={e => updateOption('min_duration', parseFloat(e.target.value))}
              disabled={analyzing}
              className="option-input"
            />
          </div>

          <div className="option-group">
            <label>片段最长时长 (秒)</label>
            <input
              type="number"
              min="5"
              max="60"
              value={options.max_duration}
              onChange={e => updateOption('max_duration', parseFloat(e.target.value))}
              disabled={analyzing}
              className="option-input"
            />
          </div>

          <button
            className="btn btn-primary btn-analyze"
            onClick={startAnalysis}
            disabled={analyzing}
          >
            <span className="material-icons-round">auto_awesome</span>
            {analyzing ? '分析中...' : '开始智能分析'}
          </button>
        </div>

        <div className="analysis-progress-section">
          {status === 'processing' && (
            <div className="progress-display">
              <div className="progress-bar-container">
                <div className="progress-bar" style={{ width: `${progress}%` }} />
              </div>
              <div className="progress-steps">
                {progressSteps.map((step, idx) => (
                  <div
                    key={idx}
                    className={`progress-step ${progress >= step.pct ? 'done' : ''}`}
                  >
                    <div className="step-dot" />
                    <span>{step.label}</span>
                  </div>
                ))}
              </div>
              <p className="progress-message">{message}</p>
            </div>
          )}

          {status === 'completed' && (
            <div className="analysis-success">
              <span className="material-icons-round success-icon">check_circle</span>
              <h3>分析完成</h3>
              <p>正在加载编辑界面...</p>
            </div>
          )}

          {error && (
            <div className="analysis-error">
              <span className="material-icons-round error-icon">error</span>
              <h3>分析失败</h3>
              <p>{error}</p>
              <button className="btn btn-secondary" onClick={startAnalysis}>
                重试
              </button>
            </div>
          )}

          {status === 'idle' && (
            <div className="analysis-preview">
              <div className="preview-icon-container">
                <span className="material-icons-round preview-icon">movie_filter</span>
              </div>
              <h3>准备就绪</h3>
              <p>调整分析参数后，点击"开始智能分析"按钮</p>
              <div className="preview-features">
                <div className="preview-feature">
                  <span className="material-icons-round">speed</span>
                  <span>快速采样分析</span>
                </div>
                <div className="preview-feature">
                  <span className="material-icons-round">psychology</span>
                  <span>多维度检测</span>
                </div>
                <div className="preview-feature">
                  <span className="material-icons-round">merge_type</span>
                  <span>智能合并片段</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default AnalysisPanel;
