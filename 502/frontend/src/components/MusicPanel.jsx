import React, { useState, useEffect } from 'react';

function MusicPanel({ apiBase, videoInfo, analysisResult, selectedMusic, onSelectMusic }) {
  const [recommendations, setRecommendations] = useState([]);
  const [loading, setLoading] = useState(false);
  const [videoRhythm, setVideoRhythm] = useState(null);
  const [genreFilter, setGenreFilter] = useState(null);
  const [moodFilter, setMoodFilter] = useState(null);

  const moodColors = {
    epic: { label: '史诗', color: '#8b5cf6' },
    happy: { label: '欢乐', color: '#22c55e' },
    calm: { label: '平静', color: '#06b6d4' },
    intense: { label: '激烈', color: '#ef4444' },
    romantic: { label: '浪漫', color: '#ec4899' },
    energetic: { label: '活力', color: '#f97316' },
    sad: { label: '伤感', color: '#64748b' },
    adventurous: { label: '冒险', color: '#14b8a6' }
  };

  useEffect(() => {
    loadRecommendations();
  }, [videoInfo, analysisResult, genreFilter, moodFilter]);

  const loadRecommendations = async () => {
    if (!videoInfo || !analysisResult) return;

    setLoading(true);
    setRecommendations([]);

    setTimeout(() => {
      const mockRecommendations = [
        {
          id: 'epic_001',
          name: 'Rise to Glory',
          artist: 'Cinematic Sounds',
          genre: 'Epic',
          mood: 'epic',
          bpm: 140,
          duration: 180,
          energy: 0.9,
          match_score: 0.92
        },
        {
          id: 'upbeat_001',
          name: 'Summer Vibes',
          artist: 'Happy Beats',
          genre: 'Pop',
          mood: 'happy',
          bpm: 120,
          duration: 165,
          energy: 0.75,
          match_score: 0.85
        },
        {
          id: 'relaxed_001',
          name: 'Morning Calm',
          artist: 'Ambient Dreams',
          genre: 'Ambient',
          mood: 'calm',
          bpm: 70,
          duration: 240,
          energy: 0.2,
          match_score: 0.78
        },
        {
          id: 'action_001',
          name: 'Pursuit',
          artist: 'Action Trailers',
          genre: 'Action',
          mood: 'intense',
          bpm: 160,
          duration: 120,
          energy: 0.95,
          match_score: 0.88
        },
        {
          id: 'romantic_001',
          name: 'Forever Yours',
          artist: 'Love Stories',
          genre: 'Romantic',
          mood: 'romantic',
          bpm: 90,
          duration: 200,
          energy: 0.4,
          match_score: 0.72
        }
      ];

      let filtered = mockRecommendations;
      if (genreFilter) {
        filtered = filtered.filter(t => t.genre.toLowerCase() === genreFilter);
      }
      if (moodFilter) {
        filtered = filtered.filter(t => t.mood === moodFilter);
      }

      setVideoRhythm({
        bpm: 110,
        avg_motion_intensity: 0.65,
        scene_change_rate: 0.3,
        dominant_mood: 'epic'
      });

      setRecommendations(filtered);
      setLoading(false);
    }, 1000);
  };

  const formatDuration = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="music-panel">
      <div className="panel-section">
      <h3 className="panel-title">
        <span className="material-icons-round">music_note</span>
        智能配乐推荐
      </h3>

      {videoRhythm && (
        <div className="rhythm-info">
          <div className="rhythm-grid">
            <div className="rhythm-item">
              <span className="rhythm-label">视频节奏</span>
              <span className="rhythm-value">{videoRhythm.bpm} BPM</span>
            </div>
            <div className="rhythm-item">
              <span className="rhythm-label">运动强度</span>
              <div className="progress-bar">
                <div 
                  className="progress-fill" style={{ width: `${videoRhythm.avg_motion_intensity * 100}%` }} />
              </div>
            </div>
            <div className="rhythm-item">
              <span className="rhythm-label">场景切换</span>
              <span className="rhythm-value">{Math.round(videoRhythm.scene_change_rate * 100)}%</span>
            </div>
            <div className="rhythm-item">
              <span className="rhythm-label">推荐情绪</span>
              <span 
                className="mood-tag" style={{ backgroundColor: moodColors[videoRhythm.dominant_mood]?.color || '#666' }}>
                {moodColors[videoRhythm.dominant_mood]?.label || '未知'}
              </span>
            </div>
            </div>
            </div>
      )}

      <div className="filter-row">
        <select 
          className="filter-select"
          value={genreFilter || ''}
          onChange={(e) => setGenreFilter(e.target.value || null)}
        >
          <option value="">所有流派</option>
          <option value="epic">Epic</option>
          <option value="pop">Pop</option>
          <option value="ambient">Ambient</option>
          <option value="action">Action</option>
          <option value="romantic">Romantic</option>
        </select>
        <select 
          className="filter-select"
          value={moodFilter || ''}
          onChange={(e) => setMoodFilter(e.target.value || null)}
        >
          <option value="">所有情绪</option>
          <option value="epic">史诗</option>
          <option value="happy">欢乐</option>
          <option value="calm">平静</option>
          <option value="intense">激烈</option>
          <option value="romantic">浪漫</option>
        </select>
      </div>

      {loading ? (
        <div className="loading-state">
          <span className="material-icons-round loading-icon">music_note</span>
          <p>正在分析视频节奏...</p>
        </div>
      ) : (
        <div className="music-list">
          {recommendations.map((track) => (
            <div 
              key={track.id}
              className={`music-card ${selectedMusic?.id === track.id ? 'selected' : ''}`}
              onClick={() => onSelectMusic(track)}
            >
              <div className="music-header">
                <div className="music-info">
                  <span className="music-title">{track.name}</span>
                  <span className="music-artist">{track.artist}</span>
                </div>
                <div className="match-badge" style={{ opacity: 0.3 + track.match_score * 0.7 }}>
                  {Math.round(track.match_score * 100)}%
                </div>
              </div>
              <div className="music-meta">
                <span className="music-genre">{track.genre}</span>
                <span className="music-bpm">{track.bpm} BPM</span>
                <span className="music-duration">{formatDuration(track.duration)}</span>
                <span 
                  className="music-mood" style={{ backgroundColor: moodColors[track.mood]?.color }}>
                  {moodColors[track.mood]?.label || track.mood}
                </span>
              </div>
              <div className="music-actions">
                <button className="btn btn-small">
                  <span className="material-icons-round">play_arrow</span>
                  试听
                </button>
                <button 
                  className={`btn btn-small ${selectedMusic?.id === track.id ? 'btn-primary' : ''}`}
                  onClick={(e) => {
                    e.stopPropagation();
                    onSelectMusic(track);
                  }}
                >
                  <span className="material-icons-round">
                    {selectedMusic?.id === track.id ? 'check' : 'add'}
                  </span>
                  {selectedMusic?.id === track.id ? '已选择' : '选择'}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {selectedMusic && (
        <div className="selected-music">
        <div className="selected-music-info">
          <span className="material-icons-round">check_circle</span>
          <span>已选: {selectedMusic.name}</span>
        </div>
        </div>
      )}
      </div>
    </div>
  );
}

export default MusicPanel;
