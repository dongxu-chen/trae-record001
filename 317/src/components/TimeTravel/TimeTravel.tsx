import React, { useState, useCallback } from 'react';
import { TimeTravelState, HistorySnapshot } from '../../types';
import './TimeTravel.css';

interface TimeTravelProps {
  timeTravel: TimeTravelState;
  historySnapshots: HistorySnapshot[];
  onEnable: (enabled: boolean) => void;
  onJump: (index: number) => void;
  onPlay: () => void;
  onPause: () => void;
  onSpeedChange: (speed: number) => void;
}

const formatTime = (timestamp: number): string => {
  const date = new Date(timestamp);
  return date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  });
};

const getHealthColor = (score: number): string => {
  if (score >= 90) return '#22c55e';
  if (score >= 70) return '#84cc16';
  if (score >= 50) return '#f59e0b';
  if (score >= 30) return '#f97316';
  return '#ef4444';
};

export const TimeTravel: React.FC<TimeTravelProps> = ({
  timeTravel,
  historySnapshots,
  onEnable,
  onJump,
  onPlay,
  onPause,
  onSpeedChange,
}) => {
  const handleSliderChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const index = parseInt(e.target.value, 10);
    onJump(index);
  }, [onJump]);

  const handlePrev = useCallback(() => {
    if (timeTravel.currentIndex > 0) {
      onJump(timeTravel.currentIndex - 1);
    }
  }, [timeTravel.currentIndex, onJump]);

  const handleNext = useCallback(() => {
    if (timeTravel.currentIndex < historySnapshots.length - 1) {
      onJump(timeTravel.currentIndex + 1);
    }
  }, [timeTravel.currentIndex, historySnapshots.length, onJump]);

  const currentSnapshot = timeTravel.isEnabled && timeTravel.currentIndex >= 0
    ? historySnapshots[timeTravel.currentIndex]
    : null;

  return (
    <div className={`time-travel-container ${timeTravel.isEnabled ? 'active' : ''}`}>
      <div className="time-travel-header">
        <h3 className="time-travel-title">
          <span className="title-icon">⏰</span>
          时间旅行
        </h3>
        <label className="toggle-switch">
          <input
            type="checkbox"
            checked={timeTravel.isEnabled}
            onChange={(e) => onEnable(e.target.checked)}
          />
          <span className="toggle-slider" />
        </label>
      </div>

      {timeTravel.isEnabled && (
        <>
          <div className="time-timeline">
            <div className="timeline-track">
              {historySnapshots.map((snapshot, index) => (
                <div
                  key={index}
                  className={`timeline-point ${index === timeTravel.currentIndex ? 'current' : ''} ${index < timeTravel.currentIndex ? 'past' : ''}`}
                  style={{ left: `${(index / (historySnapshots.length - 1)) * 100}%` }}
                  title={`${formatTime(snapshot.timestamp)} - 健康分: ${snapshot.healthScore}`}
                >
                  <div 
                    className="point-dot"
                    style={{ backgroundColor: getHealthColor(snapshot.healthScore) }}
                  />
                </div>
              ))}
            </div>
            <input
              type="range"
              min="0"
              max={historySnapshots.length - 1}
              value={timeTravel.currentIndex}
              onChange={handleSliderChange}
              className="timeline-slider"
            />
          </div>

          <div className="time-controls">
            <button 
              className="control-btn" 
              onClick={handlePrev}
              disabled={timeTravel.currentIndex <= 0}
              title="上一帧"
            >
              ⏮
            </button>
            <button 
              className="control-btn play-btn" 
              onClick={timeTravel.isPlaying ? onPause : onPlay}
              title={timeTravel.isPlaying ? '暂停' : '播放'}
            >
              {timeTravel.isPlaying ? '⏸' : '▶'}
            </button>
            <button 
              className="control-btn" 
              onClick={handleNext}
              disabled={timeTravel.currentIndex >= historySnapshots.length - 1}
              title="下一帧"
            >
              ⏭
            </button>
          </div>

          <div className="time-info">
            <div className="info-row">
              <span className="info-label">当前时间</span>
              <span className="info-value">
                {currentSnapshot ? formatTime(currentSnapshot.timestamp) : '--:--:--'}
              </span>
            </div>
            <div className="info-row">
              <span className="info-label">健康评分</span>
              <span 
                className="info-value"
                style={{ color: currentSnapshot ? getHealthColor(currentSnapshot.healthScore) : 'inherit' }}
              >
                {currentSnapshot ? currentSnapshot.healthScore.toFixed(1) : '--'}
              </span>
            </div>
            <div className="info-row">
              <span className="info-label">进度</span>
              <span className="info-value">
                {timeTravel.currentIndex + 1} / {historySnapshots.length}
              </span>
            </div>
          </div>

          <div className="speed-control">
            <span className="speed-label">播放速度</span>
            <div className="speed-buttons">
              {[0.5, 1, 2, 4].map((speed) => (
                <button
                  key={speed}
                  className={`speed-btn ${timeTravel.playbackSpeed === speed ? 'active' : ''}`}
                  onClick={() => onSpeedChange(speed)}
                >
                  {speed}x
                </button>
              ))}
            </div>
          </div>

          {currentSnapshot && currentSnapshot.faultEvents.length > 0 && (
            <div className="fault-events">
              <h4 className="fault-title">故障事件</h4>
              {currentSnapshot.faultEvents.slice(-3).map((fault) => (
                <div key={fault.id} className={`fault-item severity-${fault.severity}`}>
                  <span className="fault-time">{formatTime(fault.timestamp)}</span>
                  <span className="fault-desc">{fault.description}</span>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {!timeTravel.isEnabled && (
        <div className="time-travel-hint">
          <p>开启时间旅行后可以回放历史拓扑状态</p>
          <p className="hint-sub">每5秒自动保存一次状态，最多保存60条记录</p>
        </div>
      )}
    </div>
  );
};
