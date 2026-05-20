import React from 'react';

export const UserList = ({ users, currentUserId }) => {
  return (
    <div className="user-list">
      <div className="user-list-header">
        <h3>👥 在线用户</h3>
        <span className="user-count">{users.length} 人在线</span>
      </div>
      <div className="users-container">
        {users.map(userId => (
          <div key={userId} className="user-item">
            <div
              className="user-avatar"
              style={{ backgroundColor: getClientColor(userId) }}
            >
              {userId.slice(0, 2).toUpperCase()}
            </div>
            <div className="user-info">
              <span className="user-name">
                用户 {userId.slice(0, 6)}
                {userId === currentUserId && ' (你)'}
              </span>
              <span className="user-status online">在线</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

function getClientColor(clientId) {
  const colors = [
    '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4',
    '#FFEAA7', '#DDA0DD', '#98D8C8', '#F7DC6F',
    '#BB8FCE', '#85C1E9',
  ];
  let hash = 0;
  for (let i = 0; i < clientId.length; i++) {
    hash = clientId.charCodeAt(i) + ((hash << 5) - hash);
  }
  return colors[Math.abs(hash) % colors.length];
}
