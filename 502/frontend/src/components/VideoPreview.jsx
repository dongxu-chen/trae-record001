import React, { useRef, useEffect, useState, useCallback } from 'react';

function VideoPreview({ apiBase, videoInfo, highlights, currentTime, onTimeSeek }) {
  const videoRef = useRef(null);
  const [playing, setPlaying] = useState(false);
  const [duration, setDuration] = useState(0);
  const [videoCurrentTime, setVideoCurrentTime] = useState(0);
  const [volume, setVolume] = useState(0.8);

  const videoUrl = `${apiBase}/videos/${videoInfo.id}/stream`;

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const handleTimeUpdate = () => {
      setVideoCurrentTime(video.currentTime);
    };

    const handleLoadedMetadata = () => {
      setDuration(video.duration);
    };

    video.addEventListener('timeupdate', handleTimeUpdate);
    video.addEventListener('loadedmetadata', handleLoadedMetadata);

    return () => {
      video.removeEventListener('timeupdate', handleTimeUpdate);
      video.removeEventListener('loadedmetadata', handleLoadedMetadata);
    };
  }, []);

  useEffect(() => {
    const video = videoRef.current;
    if (!video || Math.abs(currentTime - video.currentTime) > 1) {
      video.currentTime = currentTime;
    }
  }, [currentTime]);

  const togglePlay = useCallback(() => {
    const video = videoRef.current;
    if (!video) return;
    if (playing) {
      video.pause();
    } else {
      video.play();
    }
    setPlaying(!playing);
  }, [playing]);

  const handleSeek = (e) => {
    const video = videoRef.current;
    if (!video || !duration) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const pct = (e.clientX - rect.left) / rect.width;
    video.currentTime = pct * duration;
    onTimeSeek(pct * duration);
  };

  const handleVolumeChange = (e) => {
    const video = videoRef.current;
    if (!video) return;
    video.volume = parseFloat(e.target.value);
    setVolume(parseFloat(e.target.value));
  };

  const skipTime = (delta) => {
    const video = videoRef.current;
    if (!video) return;
    video.currentTime = Math.max(0, Math.min(video.duration, video.currentTime + delta));
  };

  const formatTime = (seconds) => {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  const activeHighlight = highlights.find(
    h => videoCurrentTime >= h.start_time && videoCurrentTime <= h.end_time
  );

  return (
    <div className="video-preview">
      <div className="video-container">
        <video
          ref={videoRef}
          src={videoUrl}
          onClick={togglePlay}
          onPlay={() => setPlaying(true)}
          onPause={() => setPlaying(false)}
        />

        {activeHighlight && (
          <div className="highlight-indicator">
            <span className="material-icons-round">auto_awesome</span>
            高光片段
            <span className="highlight-type">{activeHighlight.type}</span>
          </div>
        )}

        {!playing && (
          <button className="play-overlay" onClick={togglePlay}>
            <span className="material-icons-round">play_arrow</span>
          </button>
        )}
      </div>

      <div className="video-controls">
        <div className="seek-bar" onClick={handleSeek}>
          <div
            className="seek-progress"
            style={{ width: duration ? `${(videoCurrentTime / duration) * 100}%` : '0%' }}
          />
          {highlights.map(h => (
            <div
              key={h.id}
              className="seek-highlight"
              style={{
                left: `${(h.start_time / duration) * 100}%`,
                width: `${((h.end_time - h.start_time) / duration) * 100}%`
              }}
              title={`高光 #${h.id}`}
            />
          ))}
        </div>

        <div className="control-buttons">
          <div className="controls-left">
            <button className="ctrl-btn" onClick={() => skipTime(-5)} title="后退5秒">
              <span className="material-icons-round">replay_5</span>
            </button>
            <button className="ctrl-btn ctrl-play" onClick={togglePlay}>
              <span className="material-icons-round">
                {playing ? 'pause' : 'play_arrow'}
              </span>
            </button>
            <button className="ctrl-btn" onClick={() => skipTime(5)} title="前进5秒">
              <span className="material-icons-round">forward_5</span>
            </button>
            <span className="time-display">
              {formatTime(videoCurrentTime)} / {formatTime(duration)}
            </span>
          </div>

          <div className="controls-right">
            <span className="material-icons-round volume-icon">
              {volume === 0 ? 'volume_off' : volume < 0.5 ? 'volume_down' : 'volume_up'}
            </span>
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={volume}
              onChange={handleVolumeChange}
              className="volume-slider"
            />
          </div>
        </div>
      </div>
    </div>
  );
}

export default VideoPreview;
