import React, { useState } from 'react';

function SubtitlePanel({ apiBase, videoInfo, subtitles, onUpdateSubtitles }) {
  const [loading, setLoading] = useState(false);
  const [language, setLanguage] = useState('zh');
  const [editingCue, setEditingCue] = useState(null);
  const [editText, setEditText] = useState('');

  const generateSubtitles = async () => {
    if (!videoInfo) return;

    setLoading(true);
    
    setTimeout(() => {
      const mockSubtitles = {
        language: 'zh',
        cue_count: 8,
        cues: [
          { id: 1, start_time: 0, end_time: 3.5, text: '精彩片段开始', confidence: 0.9 },
          { id: 2, start_time: 3.5, end_time: 7.2, text: '画面切换中', confidence: 0.88 },
          { id: 3, start_time: 7.2, end_time: 11.5, text: '注意关键动作', confidence: 0.92 },
          { id: 4, start_time: 11.5, end_time: 15.0, text: '这是一个高光时刻', confidence: 0.95 },
          { id: 5, start_time: 15.0, end_time: 19.5, text: '场景转换', confidence: 0.85 },
          { id: 6, start_time: 19.5, end_time: 24.0, text: '音乐节奏变化', confidence: 0.87 },
          { id: 7, start_time: 24.0, end_time: 28.5, text: '情绪达到高潮', confidence: 0.91 },
          { id: 8, start_time: 28.5, end_time: 32.0, text: '完美结束', confidence: 0.89 }
        ]
      };
      onUpdateSubtitles(mockSubtitles);
      setLoading(false);
    }, 2000);
  };

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const startEdit = (cue) => {
    setEditingCue(cue.id);
    setEditText(cue.text);
  };

  const saveEdit = (cue) => {
    const updatedCues = subtitles.cues.map(c => 
      c.id === cue.id ? { ...c, text: editText } : c
    );
    onUpdateSubtitles({ ...subtitles, cues: updatedCues });
    setEditingCue(null);
    setEditText('');
  };

  const deleteCue = (cueId) => {
    const updatedCues = subtitles.cues.filter(c => c.id !== cueId);
    onUpdateSubtitles({ ...subtitles, cues: updatedCues, cue_count: updatedCues.length });
  };

  const addCue = () => {
    const lastCue = subtitles.cues[subtitles.cues.length - 1];
    const newId = Math.max(...subtitles.cues.map(c => c.id)) + 1;
    const newCue = {
      id: newId,
      start_time: lastCue ? lastCue.end_time : 0,
      end_time: lastCue ? lastCue.end_time + 3 : 3,
      text: '新字幕',
      confidence: 0.8
    };
    onUpdateSubtitles({
      ...subtitles,
      cues: [...subtitles.cues, newCue],
      cue_count: subtitles.cue_count + 1
    });
  };

  const exportSubtitles = (format) => {
    alert(`导出 ${format.toUpperCase()} 字幕文件`);
  };

  return (
    <div className="subtitle-panel">
      <div className="panel-section">
      <h3 className="panel-title">
        <span className="material-icons-round">subtitles</span>
        自动字幕生成
      </h3>

      {!subtitles ? (
        <div className="subtitle-empty">
          <span className="material-icons-round empty-icon">subtitles_off</span>
          <p>暂无字幕</p>
          <p className="empty-hint">点击下方按钮生成智能字幕</p>

          <div className="subtitle-options">
            <label>
              语言:
              <select value={language} onChange={(e) => setLanguage(e.target.value)}>
                <option value="zh">中文</option>
                <option value="en">English</option>
                <option value="ja">日本語</option>
              </select>
            </label>
          </div>

          <button 
            className="btn btn-primary"
            onClick={generateSubtitles}
            disabled={loading}
          >
            {loading ? (
              <>
                <span className="material-icons-round loading-icon spin">sync</span>
                正在生成...
              </>
            ) : (
              <>
                <span className="material-icons-round">auto_fix_high</span>
                生成智能字幕
              </>
            )}
          </button>
        </div>
      ) : (
        <>
          <div className="subtitle-header">
            <div className="subtitle-stats">
              <span>共 {subtitles.cue_count} 条字幕</span>
              <span>语言: {subtitles.language === 'zh' ? '中文' : subtitles.language}</span>
            </div>
            <div className="subtitle-actions">
              <button className="btn btn-small" onClick={generateSubtitles} disabled={loading}>
                <span className="material-icons-round">refresh</span>
                重新生成
              </button>
              <button className="btn btn-small" onClick={() => exportSubtitles('srt')}>
                <span className="material-icons-round">download</span>
                导出 SRT
              </button>
            </div>
          </div>

          <div className="subtitle-list">
            {subtitles.cues.map((cue) => (
              <div key={cue.id} className="subtitle-item">
                <div className="subtitle-time">
                  <span className="material-icons-round">schedule</span>
                  {formatTime(cue.start_time)} - {formatTime(cue.end_time)}
                </div>
                {editingCue === cue.id ? (
                  <div className="subtitle-edit">
                    <textarea
                      value={editText}
                      onChange={(e) => setEditText(e.target.value)}
                      autoFocus
                    />
                    <div className="edit-actions">
                      <button className="btn btn-small btn-primary" onClick={() => saveEdit(cue)}>
                        保存
                      </button>
                      <button className="btn btn-small" onClick={() => setEditingCue(null)}>
                        取消
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="subtitle-content">
                    <span className="subtitle-text">{cue.text}</span>
                    <div className="subtitle-item-actions">
                      <button 
                        className="icon-btn"
                        onClick={() => startEdit(cue)}
                        title="编辑"
                      >
                        <span className="material-icons-round">edit</span>
                      </button>
                      <button 
                        className="icon-btn"
                        onClick={() => deleteCue(cue.id)}
                        title="删除"
                      >
                        <span className="material-icons-round">delete</span>
                      </button>
                    </div>
                  </div>
                )}
                <div className="subtitle-confidence">
                  <span className="confidence-label">置信度</span>
                  <div className="confidence-bar">
                    <div 
                      className="confidence-fill" 
                      style={{ 
                        width: `${cue.confidence * 100}%`,
                        backgroundColor: cue.confidence > 0.85 ? '#22c55e' : cue.confidence > 0.7 ? '#eab308' : '#ef4444'
                      }}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>

          <button className="btn btn-secondary btn-full" onClick={addCue}>
            <span className="material-icons-round">add</span>
            添加新字幕
          </button>
        </>
      )}
      </div>
    </div>
  );
}

export default SubtitlePanel;
