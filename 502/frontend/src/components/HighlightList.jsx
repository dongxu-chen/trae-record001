import React, { useState } from 'react';

function HighlightList({ highlights, selectedHighlights, onToggle, onTimeSeek, scenes }) {
  const [filter, setFilter] = useState('all');
  const [sortBy, setSortBy] = useState('confidence');

  const typeLabels = {
    motion: '运动高光',
    color: '色彩变化',
    brightness: '亮度变化',
    audio_peak: '音频峰值',
    laughter: '笑声检测',
    spectral_change: '频谱变化',
    multi: '综合高光'
  };

  const typeIcons = {
    motion: 'directions_run',
    color: 'palette',
    brightness: 'light_mode',
    audio_peak: 'graphic_eq',
    laughter: 'sentiment_very_satisfied',
    spectral_change: 'graphic_eq',
    multi: 'auto_awesome'
  };

  const typeColors = {
    motion: '#f97316',
    color: '#8b5cf6',
    brightness: '#eab308',
    audio_peak: '#06b6d4',
    laughter: '#22c55e',
    spectral_change: '#e879f9',
    multi: '#ec4899'
  };

  const filteredHighlights = highlights
    .filter(h => filter === 'all' || h.type === filter)
    .sort((a, b) => {
      if (sortBy === 'confidence') return (b.confidence || 0) - (a.confidence || 0);
      if (sortBy === 'time') return a.start_time - b.start_time;
      if (sortBy === 'duration') return b.duration - a.duration;
      return 0;
    });

  const isSelected = (h) => selectedHighlights.some(sh => sh.id === h.id);

  const selectAll = () => {
    const unselected = filteredHighlights.filter(h => !isSelected(h));
    unselected.forEach(h => onToggle(h));
  };

  const deselectAll = () => {
    selectedHighlights.forEach(h => onToggle(h));
  };

  const formatTime = (seconds) => {
    const m = Math.floor(seconds / 60);
    const s = (seconds % 60).toFixed(1);
    return `${m}:${s.padStart(4, '0')}`;
  };

  const types = [...new Set(highlights.map(h => h.type))];

  const totalSelectedDuration = selectedHighlights.reduce(
    (sum, h) => sum + (h.end_time - h.start_time), 0
  );

  return (
    <div className="highlight-list">
      <div className="highlight-header">
        <h3>
          <span className="material-icons-round">auto_awesome</span>
          高光片段 ({highlights.length})
        </h3>
        <div className="highlight-actions">
          <button className="btn-sm" onClick={selectAll}>全选</button>
          <button className="btn-sm" onClick={deselectAll}>清空</button>
        </div>
      </div>

      <div className="highlight-summary">
        <div className="summary-stat">
          <span className="stat-value">{selectedHighlights.length}</span>
          <span className="stat-label">已选</span>
        </div>
        <div className="summary-stat">
          <span className="stat-value">{totalSelectedDuration.toFixed(1)}s</span>
          <span className="stat-label">总时长</span>
        </div>
      </div>

      <div className="highlight-filters">
        <select value={filter} onChange={e => setFilter(e.target.value)} className="filter-select">
          <option value="all">全部类型</option>
          {types.map(t => (
            <option key={t} value={t}>{typeLabels[t] || t}</option>
          ))}
        </select>
        <select value={sortBy} onChange={e => setSortBy(e.target.value)} className="filter-select">
          <option value="confidence">按置信度</option>
          <option value="time">按时间</option>
          <option value="duration">按时长</option>
        </select>
      </div>

      <div className="highlight-items">
        {filteredHighlights.map(h => {
          const selected = isSelected(h);
          const color = typeColors[h.type] || '#6366f1';

          return (
            <div
              key={h.id}
              className={`highlight-item ${selected ? 'selected' : ''}`}
              style={{ borderLeftColor: color }}
            >
              <div className="highlight-item-header">
                <label className="highlight-checkbox">
                  <input
                    type="checkbox"
                    checked={selected}
                    onChange={() => onToggle(h)}
                  />
                  <span className="checkmark" style={{ backgroundColor: selected ? color : 'transparent' }} />
                </label>
                <span className="highlight-badge" style={{ backgroundColor: color + '20', color }}>
                  <span className="material-icons-round badge-icon">{typeIcons[h.type] || 'star'}</span>
                  {typeLabels[h.type] || h.type}
                </span>
                <span className="highlight-id">#{h.id}</span>
              </div>

              <div className="highlight-item-body">
                <div className="highlight-time">
                  <span className="material-icons-round">schedule</span>
                  {formatTime(h.start_time)} → {formatTime(h.end_time)}
                </div>
                <div className="highlight-duration">
                  {h.duration?.toFixed(1) || ((h.end_time - h.start_time).toFixed(1))}s
                </div>
              </div>

              <div className="highlight-confidence">
                <div className="confidence-bar">
                  <div
                    className="confidence-fill"
                    style={{
                      width: `${(h.confidence || 0) * 100}%`,
                      backgroundColor: color
                    }}
                  />
                </div>
                <span className="confidence-text">
                  {Math.round((h.confidence || 0) * 100)}%
                </span>
              </div>

              <button
                className="btn-preview"
                onClick={() => onTimeSeek(h.start_time)}
                title="跳转到此片段"
              >
                <span className="material-icons-round">play_arrow</span>
                预览
              </button>
            </div>
          );
        })}
      </div>

      {scenes && scenes.length > 0 && (
        <div className="scenes-section">
          <h4>
            <span className="material-icons-round">view_comfy</span>
            场景列表 ({scenes.length})
          </h4>
          <div className="scene-items">
            {scenes.map(scene => (
              <div
                key={scene.scene_idx}
                className="scene-item"
                onClick={() => onTimeSeek(scene.start_time)}
              >
                <span className="scene-idx">S{scene.scene_idx + 1}</span>
                <span className="scene-type">{scene.type}</span>
                <span className="scene-time">
                  {formatTime(scene.start_time)} - {formatTime(scene.end_time)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default HighlightList;
