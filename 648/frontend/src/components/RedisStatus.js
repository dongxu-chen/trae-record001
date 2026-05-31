import React from 'react';

function RedisStatus({ status }) {
  if (!status) return null;

  const databases = Object.entries(status.databases || {});

  return (
    <div className="redis-status">
      <div className="status-item">
        <span className="status-dot"></span>
        <span>{status.address}</span>
      </div>
      {databases.map(([db, info]) => (
        <div key={db} className="status-item">
          <span className={`status-dot ${info.status === 'connected' ? '' : 'disconnected'}`}></span>
          <span>DB {db}</span>
          {info.pending > 0 && (
            <span style={{ fontSize: '11px', color: '#faad14' }}>
              ({info.pending} 等待)
            </span>
          )}
        </div>
      ))}
    </div>
  );
}

export default RedisStatus;
