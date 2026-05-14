import { useState, useEffect } from 'react';

const AlarmList = ({ alarms, onDismiss, maxItems = 10 }) => {
  const [currentIndex, setCurrentIndex] = useState(0);
  const displayAlarms = alarms.slice(0, maxItems);

  useEffect(() => {
    if (displayAlarms.length > 0) {
      const interval = setInterval(() => {
        setCurrentIndex((prev) => (prev + 1) % Math.max(displayAlarms.length, 1));
      }, 3000);
      return () => clearInterval(interval);
    }
  }, [displayAlarms.length]);

  const formatTime = (timestamp) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('zh-CN', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  };

  const getLevelStyle = (level) => {
    const styles = {
      error: {
        bg: 'rgba(255, 68, 68, 0.2)',
        border: 'rgba(255, 68, 68, 0.5)',
        color: '#ff4444',
        icon: '🚨'
      },
      warning: {
        bg: 'rgba(255, 193, 7, 0.2)',
        border: 'rgba(255, 193, 7, 0.5)',
        color: '#ffc107',
        icon: '⚠️'
      },
      info: {
        bg: 'rgba(0, 179, 255, 0.2)',
        border: 'rgba(0, 179, 255, 0.5)',
        color: '#00b3ff',
        icon: 'ℹ️'
      }
    };
    return styles[level] || styles.info;
  };

  const activeAlarm = displayAlarms[currentIndex];

  if (displayAlarms.length === 0) {
    return (
      <div className="alarm-container">
        <div className="alarm-header">
          <span className="alarm-title">实时告警</span>
          <span className="alarm-count">0 条</span>
        </div>
        <div className="no-alarm">
          <span className="no-alarm-icon">✅</span>
          <span className="no-alarm-text">系统运行正常，暂无告警</span>
        </div>
        <style>{`
          .alarm-container {
            width: 100%;
            height: 100%;
            display: flex;
            flex-direction: column;
            padding: 15px;
            background: rgba(0, 179, 255, 0.1);
            border: 1px solid rgba(0, 179, 255, 0.3);
            border-radius: 10px;
            overflow: hidden;
          }
          .alarm-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 1px solid rgba(0, 179, 255, 0.3);
          }
          .alarm-title {
            color: #00b3ff;
            font-size: 18px;
            font-weight: bold;
          }
          .alarm-count {
            color: #00ff88;
            font-size: 14px;
          }
          .no-alarm {
            flex: 1;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
          }
          .no-alarm-icon {
            font-size: 24px;
          }
          .no-alarm-text {
            color: rgba(255, 255, 255, 0.7);
            font-size: 16px;
          }
        `}</style>
      </div>
    );
  }

  return (
    <div className="alarm-container">
      <div className="alarm-header">
        <span className="alarm-title">实时告警</span>
        <span className="alarm-count">
          {displayAlarms.length} 条 {currentIndex + 1}/{displayAlarms.length}
        </span>
      </div>
      
      <div className="alarm-scroll">
        {activeAlarm && (
          <div 
            className="alarm-item active"
            style={{
              backgroundColor: getLevelStyle(activeAlarm.level).bg,
              borderColor: getLevelStyle(activeAlarm.level).border
            }}
          >
            <div className="alarm-left">
              <span className="alarm-icon">
                {getLevelStyle(activeAlarm.level).icon}
              </span>
              <span className="alarm-level" style={{ color: getLevelStyle(activeAlarm.level).color }}>
                [{activeAlarm.level.toUpperCase()}]
              </span>
            </div>
            <div className="alarm-content">
              <div className="alarm-title-text">
                {activeAlarm.title}
              </div>
              <div className="alarm-message">
                {activeAlarm.message}
              </div>
              <div className="alarm-meta">
                <span className="alarm-region">📍 {activeAlarm.region}</span>
                <span className="alarm-time">🕐 {formatTime(activeAlarm.timestamp)}</span>
              </div>
            </div>
            <button 
              className="alarm-dismiss"
              onClick={() => onDismiss && onDismiss(activeAlarm.id)}
            >
              ✕
            </button>
          </div>
        )}
      </div>

      <div className="alarm-dots">
        {displayAlarms.map((_, index) => (
          <span 
            key={index} 
            className={`alarm-dot ${index === currentIndex ? 'active' : ''}`}
          />
        ))}
      </div>

      <style>{`
        .alarm-container {
          width: 100%;
          height: 100%;
          display: flex;
          flex-direction: column;
          padding: 15px;
          background: rgba(0, 179, 255, 0.1);
          border: 1px solid rgba(0, 179, 255, 0.3);
          border-radius: 10px;
          overflow: hidden;
        }
        .alarm-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 10px;
          padding-bottom: 10px;
          border-bottom: 1px solid rgba(0, 179, 255, 0.3);
        }
        .alarm-title {
          color: #00b3ff;
          font-size: 18px;
          font-weight: bold;
        }
        .alarm-count {
          color: #00ff88;
          font-size: 14px;
        }
        .alarm-scroll {
          flex: 1;
          overflow: hidden;
          display: flex;
          align-items: center;
        }
        .alarm-item {
          display: flex;
          align-items: center;
          gap: 15px;
          padding: 15px;
          border-radius: 8px;
          border: 1px solid;
          width: 100%;
          transition: all 0.3s ease;
          position: relative;
        }
        .alarm-item.active {
          animation: pulse 2s infinite;
        }
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.8; }
        }
        .alarm-left {
          display: flex;
          align-items: center;
          gap: 10px;
          flex-shrink: 0;
        }
        .alarm-icon {
          font-size: 28px;
        }
        .alarm-level {
          font-weight: bold;
          font-size: 12px;
        }
        .alarm-content {
          flex: 1;
          min-width: 0;
        }
        .alarm-title-text {
          color: #fff;
          font-weight: bold;
          font-size: 16px;
          margin-bottom: 5px;
        }
        .alarm-message {
          color: rgba(255, 255, 255, 0.9);
          font-size: 14px;
          margin-bottom: 5px;
        }
        .alarm-meta {
          display: flex;
          gap: 15px;
          color: rgba(255, 255, 255, 0.6);
          font-size: 12px;
        }
        .alarm-dismiss {
          background: none;
          border: none;
          color: rgba(255, 255, 255, 0.6);
          font-size: 20px;
          cursor: pointer;
          padding: 5px;
          border-radius: 50%;
          transition: all 0.2s ease;
          flex-shrink: 0;
        }
        .alarm-dismiss:hover {
          background: rgba(255, 255, 255, 0.1);
          color: #fff;
        }
        .alarm-dots {
          display: flex;
          justify-content: center;
          gap: 8px;
          margin-top: 10px;
        }
        .alarm-dot {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          background: rgba(255, 255, 255, 0.3);
          transition: all 0.3s ease;
        }
        .alarm-dot.active {
          background: #00ff88;
          transform: scale(1.2);
        }
      `}</style>
    </div>
  );
};

export default AlarmList;
