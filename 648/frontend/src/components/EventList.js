import React from 'react';

function EventList({ events }) {
  if (!events || events.length === 0) {
    return (
      <div className="empty">
        暂无事件
      </div>
    );
  }

  const getStatusClass = (event) => {
    if (event.Processed) return 'success';
    if (event.Error) return 'error';
    return 'pending';
  };

  const formatTime = (timestamp) => {
    if (!timestamp) return '';
    return new Date(timestamp).toLocaleTimeString();
  };

  return (
    <div className="event-list">
      {events.slice().reverse().map((event) => (
        <div key={event.ID} className="event-item">
          <div className="event-info">
            <div className="event-key">{event.Key}</div>
            <div className="event-meta">
              DB: {event.DB} | {formatTime(event.Timestamp)}
              {event.RetryCount > 0 && ` | 重试: ${event.RetryCount}次`}
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <span className={`event-type ${event.EventType}`}>
              {event.EventType}
            </span>
            <div className="event-status">
              <span className={`status-badge ${getStatusClass(event)}`}></span>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

export default EventList;
