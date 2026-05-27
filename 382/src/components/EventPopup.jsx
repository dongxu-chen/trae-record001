import React from 'react';
import moment from 'moment';

const EventPopup = ({ event, position, onClose, onViewDetails }) => {
  if (!event) return null;

  const formatTime = (timestamp) => moment(timestamp).format('YYYY-MM-DD HH:mm');

  const getPopupPosition = () => {
    const popupWidth = 320;
    const popupHeight = 200;
    let left = position.x + 20;
    let top = position.y - popupHeight / 2;

    if (left + popupWidth > window.innerWidth) {
      left = position.x - popupWidth - 20;
    }
    if (top < 10) top = 10;
    if (top + popupHeight > window.innerHeight) {
      top = window.innerHeight - popupHeight - 10;
    }

    return { left, top };
  };

  const popupStyle = getPopupPosition();

  return (
    <div className="event-popup" style={{ left: popupStyle.left, top: popupStyle.top }}>
      <div className="event-popup-header">
        <span className="event-popup-title">{event.title}</span>
        <button className="event-popup-close" onClick={onClose}>×</button>
      </div>
      <div className="event-popup-content">
        <div className="event-popup-row">
          <span className="event-popup-label">时间：</span>
          <span>{formatTime(event.startTime)} - {formatTime(event.endTime)}</span>
        </div>
        {event.details && (
          <>
            <div className="event-popup-row">
              <span className="event-popup-label">地点：</span>
              <span>{event.details.location}</span>
            </div>
            <div className="event-popup-row">
              <span className="event-popup-label">参与人数：</span>
              <span>{event.details.participants}人</span>
            </div>
            <div className="event-popup-row">
              <span className="event-popup-label">状态：</span>
              <span>{event.details.status}</span>
            </div>
            {event.details.organizer && (
              <div className="event-popup-row">
                <span className="event-popup-label">组织者：</span>
                <span>{event.details.organizer}</span>
              </div>
            )}
          </>
        )}
        {event.description && (
          <div className="event-popup-row" style={{ marginTop: 8 }}>
            <span>{event.description}</span>
          </div>
        )}
      </div>
      <div className="event-popup-actions">
        <button className="event-popup-btn primary" onClick={() => onViewDetails && onViewDetails(event)}>
          查看详情
        </button>
        <button className="event-popup-btn secondary" onClick={onClose}>
          关闭
        </button>
      </div>
    </div>
  );
};

export default EventPopup;
