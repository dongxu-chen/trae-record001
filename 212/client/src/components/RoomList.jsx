import { useState } from 'react';

function RoomList({ rooms, currentRoom, unreadCounts, onCreateRoom, onJoinRoom, userId }) {
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newRoomName, setNewRoomName] = useState('');

  const handleCreateRoom = async () => {
    if (newRoomName.trim()) {
      const room = await onCreateRoom(newRoomName.trim());
      if (room) {
        setShowCreateModal(false);
        setNewRoomName('');
        onJoinRoom(room);
      }
    }
  };

  return (
    <div className="room-list">
      <div className="room-list-header">
        <h3>聊天室</h3>
        <button className="create-btn" onClick={() => setShowCreateModal(true)}>
          +
        </button>
      </div>
      
      <div className="rooms">
        {rooms.length === 0 ? (
          <p className="no-rooms">暂无聊天室</p>
        ) : (
          rooms.map(room => (
            <div
              key={room.id}
              className={`room-item ${currentRoom?.id === room.id ? 'active' : ''}`}
              onClick={() => onJoinRoom(room)}
            >
              <div className="room-icon">#</div>
              <div className="room-info">
                <span className="room-name">{room.name}</span>
                <span className="room-meta">{room.users?.length || 0} 人在线</span>
              </div>
              {(unreadCounts[room.id] || 0) > 0 && currentRoom?.id !== room.id && (
                <span className="unread-badge">
                  {unreadCounts[room.id] > 99 ? '99+' : unreadCounts[room.id]}
                </span>
              )}
            </div>
          ))
        )}
      </div>

      {showCreateModal && (
        <div className="modal-overlay" onClick={() => setShowCreateModal(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <h3>创建新聊天室</h3>
            <input
              type="text"
              value={newRoomName}
              onChange={(e) => setNewRoomName(e.target.value)}
              placeholder="输入聊天室名称..."
              maxLength={30}
              autoFocus
              onKeyPress={(e) => e.key === 'Enter' && handleCreateRoom()}
            />
            <div className="modal-actions">
              <button className="cancel-btn" onClick={() => setShowCreateModal(false)}>
                取消
              </button>
              <button 
                className="confirm-btn" 
                onClick={handleCreateRoom}
                disabled={!newRoomName.trim()}
              >
                创建
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default RoomList;