import React, { useState, useEffect } from 'react';
import axios from 'axios';

function ExportPanel({ apiBase, videoInfo, selectedHighlights, onBack }) {
  const [format, setFormat] = useState('mp4');
  const [resolution, setResolution] = useState('original');
  const [quality, setQuality] = useState('balanced');
  const [clipDuration, setClipDuration] = useState('');
  const [transition, setTransition] = useState('none');
  const [transitionDuration, setTransitionDuration] = useState(0.5);
  const [exporting, setExporting] = useState(false);
  const [compiling, setCompiling] = useState(false);
  const [progress, setProgress] = useState('');
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [compileId, setCompileId] = useState(null);
  const [apiPresets, setApiPresets] = useState(null);

  const totalDuration = selectedHighlights.reduce(
    (sum, h) => sum + (h.end_time - h.start_time), 0
  );

  useEffect(() => {
    axios.get(`${apiBase}/formats`).then(res => {
      if (res.data) setApiPresets(res.data);
    }).catch(() => {});
  }, [apiBase]);

  const formats = [
    { id: 'mp4', name: 'MP4', desc: 'H.264 + AAC', icon: 'movie' },
    { id: 'webm', name: 'WebM', desc: 'VP9 + Opus', icon: 'web' },
    { id: 'avi', name: 'AVI', desc: 'H.264 + MP3', icon: 'theaters' },
    { id: 'mov', name: 'MOV', desc: 'QuickTime', icon: 'apple' },
    { id: 'gif', name: 'GIF', desc: '动图 (无音频)', icon: 'gif_box' }
  ];

  const resolutions = [
    { id: 'original', name: '原始分辨率' },
    { id: '1080p', name: '1080p (1920×1080)' },
    { id: '720p', name: '720p (1280×720)' },
    { id: '480p', name: '480p (854×480)' }
  ];

  const qualityPresets = [
    { id: 'ultra', name: '超高品质', desc: 'CRF 15 · 最大画质', icon: 'diamond', size: '大', color: '#f59e0b' },
    { id: 'high', name: '高品质', desc: 'CRF 18 · 画质优先', icon: 'workspace_premium', size: '中大', color: '#3fb950' },
    { id: 'balanced', name: '均衡', desc: 'CRF 23 · 推荐设置', icon: 'balance', size: '中', color: '#58a6ff' },
    { id: 'compact', name: '紧凑', desc: 'CRF 28 · 体积优先', icon: 'compress', size: '小', color: '#8b5cf6' },
    { id: 'minimal', name: '最小体积', desc: 'CRF 32 · 极致压缩', icon: 'data_saver_on', size: '极小', color: '#6e7681' }
  ];

  const transitions = [
    { id: 'none', name: '无过渡', desc: '直接拼接', icon: 'close' },
    { id: 'fade', name: '淡入淡出', desc: '首尾渐变', icon: 'gradient' },
    { id: 'crossfade', name: '交叉溶解', desc: '相邻交叉过渡', icon: 'blur_on' },
    { id: 'zoom', name: '缩放过渡', desc: '缩放效果衔接', icon: 'zoom_in' }
  ];

  const estimatedSizeMB = (() => {
    const bitrateMap = {
      '4k': { ultra: 15000, high: 10000, balanced: 6000, compact: 3000, minimal: 1500 },
      '1080p': { ultra: 12000, high: 7000, balanced: 4000, compact: 2000, minimal: 800 },
      '720p': { ultra: 6000, high: 4000, balanced: 2500, compact: 1200, minimal: 500 },
      '480p': { ultra: 3000, high: 2000, balanced: 1500, compact: 800, minimal: 400 },
      'original': { ultra: 12000, high: 7000, balanced: 4000, compact: 2000, minimal: 800 }
    };
    const res = bitrateMap[resolution] || bitrateMap['1080p'];
    const bitrate = res[quality] || res['balanced'];
    return ((bitrate * 1000 / 8) * totalDuration / (1024 * 1024)).toFixed(1);
  })();

  const handleCompile = async () => {
    setCompiling(true);
    setProgress('正在合成高光合集...');
    setError(null);

    try {
      const response = await axios.post(`${apiBase}/compile`, {
        videoId: videoInfo.id,
        highlights: selectedHighlights,
        options: {
          clip_duration: clipDuration ? parseFloat(clipDuration) : null,
          transition,
          transition_duration: transitionDuration
        }
      });

      if (response.data.success) {
        setCompileId(response.data.compileId);
        setProgress('合成完成！准备导出...');
        setResult(response.data);
      } else {
        setError(response.data.error || '合成失败');
      }
    } catch (err) {
      setError(err.response?.data?.error || '合成失败，请重试');
    } finally {
      setCompiling(false);
    }
  };

  const handleExport = async () => {
    setExporting(true);
    setProgress('正在导出视频...');
    setError(null);

    try {
      const response = await axios.post(`${apiBase}/export`, {
        videoId: compileId || videoInfo.id,
        format,
        resolution,
        quality
      });

      if (response.data.success) {
        setProgress('导出完成！');
        setResult(prev => ({ ...prev, ...response.data }));
      } else {
        setError(response.data.error || '导出失败');
      }
    } catch (err) {
      setError(err.response?.data?.error || '导出失败，请重试');
    } finally {
      setExporting(false);
    }
  };

  const handleDownload = () => {
    if (result?.downloadUrl) {
      window.open(`${apiBase.replace('/api', '')}${result.downloadUrl}`, '_blank');
    } else if (compileId) {
      window.open(`${apiBase}/export/${compileId}/download`, '_blank');
    }
  };

  return (
    <div className="export-panel">
      <div className="export-header">
        <button className="btn btn-ghost" onClick={onBack}>
          <span className="material-icons-round">arrow_back</span>
          返回编辑
        </button>
        <h2>导出设置</h2>
      </div>

      <div className="export-content">
        <div className="export-settings">
          <section className="settings-section">
            <h3>
              <span className="material-icons-round">video_settings</span>
              输出格式
            </h3>
            <div className="format-grid">
              {formats.map(f => (
                <div
                  key={f.id}
                  className={`format-card ${format === f.id ? 'selected' : ''}`}
                  onClick={() => setFormat(f.id)}
                >
                  <span className="material-icons-round">{f.icon}</span>
                  <div className="format-info">
                    <span className="format-name">{f.name}</span>
                    <span className="format-desc">{f.desc}</span>
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section className="settings-section">
            <h3>
              <span className="material-icons-round">aspect_ratio</span>
              分辨率
            </h3>
            <div className="resolution-options">
              {resolutions.map(r => (
                <label key={r.id} className={`radio-card ${resolution === r.id ? 'selected' : ''}`}>
                  <input
                    type="radio"
                    name="resolution"
                    value={r.id}
                    checked={resolution === r.id}
                    onChange={() => setResolution(r.id)}
                  />
                  <span>{r.name}</span>
                </label>
              ))}
            </div>
          </section>

          <section className="settings-section quality-section">
            <h3>
              <span className="material-icons-round">high_quality</span>
              画质预设
            </h3>
            <div className="quality-preset-grid">
              {qualityPresets.map(q => (
                <div
                  key={q.id}
                  className={`quality-preset-card ${quality === q.id ? 'selected' : ''}`}
                  onClick={() => setQuality(q.id)}
                  style={quality === q.id ? { borderColor: q.color, background: `${q.color}10` } : {}}
                >
                  <span className="material-icons-round preset-icon" style={{ color: q.color }}>{q.icon}</span>
                  <div className="preset-info">
                    <span className="preset-name" style={quality === q.id ? { color: q.color } : {}}>{q.name}</span>
                    <span className="preset-desc">{q.desc}</span>
                  </div>
                  <span className="preset-size-badge" style={{ background: `${q.color}20`, color: q.color }}>
                    {q.size}
                  </span>
                </div>
              ))}
            </div>
            <div className="size-estimate">
              <span className="material-icons-round">sd_card</span>
              预估文件大小：<strong>{estimatedSizeMB} MB</strong>
              <span className="size-hint">（实际大小取决于视频内容复杂度）</span>
            </div>
          </section>

          <section className="settings-section">
            <h3>
              <span className="material-icons-round">content_cut</span>
              剪辑选项
            </h3>
            <div className="clip-options">
              <div className="option-row">
                <label>单段最大时长 (秒)</label>
                <input
                  type="number"
                  min="2"
                  max="60"
                  value={clipDuration}
                  onChange={e => setClipDuration(e.target.value)}
                  placeholder="不限制"
                  className="option-input"
                />
              </div>
              <div className="option-row transition-row">
                <label>场景过渡效果</label>
                <div className="transition-grid">
                  {transitions.map(t => (
                    <div
                      key={t.id}
                      className={`transition-card ${transition === t.id ? 'selected' : ''}`}
                      onClick={() => setTransition(t.id)}
                    >
                      <span className="material-icons-round">{t.icon}</span>
                      <span className="transition-name">{t.name}</span>
                      <span className="transition-desc">{t.desc}</span>
                    </div>
                  ))}
                </div>
              </div>
              {transition !== 'none' && (
                <div className="option-row">
                  <label>过渡时长 (秒)</label>
                  <div className="slider-group">
                    <input
                      type="range"
                      min="0.2"
                      max="2.0"
                      step="0.1"
                      value={transitionDuration}
                      onChange={e => setTransitionDuration(parseFloat(e.target.value))}
                      className="transition-slider"
                    />
                    <span className="slider-value">{transitionDuration.toFixed(1)}s</span>
                  </div>
                </div>
              )}
            </div>
          </section>
        </div>

        <div className="export-summary">
          <div className="summary-card">
            <h3>
              <span className="material-icons-round">summarize</span>
              导出摘要
            </h3>
            <div className="summary-details">
              <div className="detail-row">
                <span>片段数量</span>
                <strong>{selectedHighlights.length}</strong>
              </div>
              <div className="detail-row">
                <span>总时长</span>
                <strong>{totalDuration.toFixed(1)} 秒</strong>
              </div>
              <div className="detail-row">
                <span>输出格式</span>
                <strong>{format.toUpperCase()}</strong>
              </div>
              <div className="detail-row">
                <span>分辨率</span>
                <strong>{resolution === 'original' ? '原始' : resolution}</strong>
              </div>
              <div className="detail-row">
                <span>画质</span>
                <strong>{qualityPresets.find(q => q.id === quality)?.name}</strong>
              </div>
              <div className="detail-row">
                <span>过渡效果</span>
                <strong>{transitions.find(t => t.id === transition)?.name}</strong>
              </div>
              {transition !== 'none' && (
                <div className="detail-row">
                  <span>过渡时长</span>
                  <strong>{transitionDuration.toFixed(1)}s</strong>
                </div>
              )}
              <div className="detail-row highlight-row">
                <span>预估大小</span>
                <strong className="size-highlight">{estimatedSizeMB} MB</strong>
              </div>
            </div>

            <div className="export-actions">
              {!compileId ? (
                <button
                  className="btn btn-primary btn-compile"
                  onClick={handleCompile}
                  disabled={compiling || selectedHighlights.length === 0}
                >
                  <span className="material-icons-round">merge_type</span>
                  {compiling ? '合成中...' : '合成高光合集'}
                </button>
              ) : (
                <>
                  <button
                    className="btn btn-primary btn-export"
                    onClick={handleExport}
                    disabled={exporting}
                  >
                    <span className="material-icons-round">file_download</span>
                    {exporting ? '导出中...' : '导出视频'}
                  </button>
                  <button
                    className="btn btn-secondary btn-download"
                    onClick={handleDownload}
                    disabled={!result?.downloadUrl && !compileId}
                  >
                    <span className="material-icons-round">download</span>
                    下载文件
                  </button>
                </>
              )}
            </div>

            {progress && (
              <div className="export-progress">
                <span className="material-icons-round rotating">sync</span>
                {progress}
              </div>
            )}

            {error && (
              <div className="export-error">
                <span className="material-icons-round">error</span>
                {error}
              </div>
            )}

            {result?.success && (
              <div className="export-success">
                <span className="material-icons-round">check_circle</span>
                导出成功！
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default ExportPanel;
