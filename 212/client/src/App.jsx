import { useState, useEffect } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { useWebSocket } from './hooks/useWebSocket';
import RoomList from './components/RoomList';
import ChatRoom from './components/ChatRoom';
import LoginModal from './components/LoginModal';
import SearchModal from './components/SearchModal';

function App() {
  const [user, setUser] = useState(null);
  const [rooms, setRooms] = useState([]);
  const [currentRoom, setCurrentRoom] = useState(null);
  const [unreadCounts, setUnreadCounts] = useState({});
  const [showSearch, setShowSearch] = useState(false);

  const {
    connect,
    sendMessage,
    sendVoice,
    sendTyping,
    markRead,
    sendReadReceipt,
    uploadVoice,
    messages,
    onlineUsers,
    typingUsers,
    isConnected,
    notifications,
    prependMessages
  } = useWebSocket(user, currentRoom);

  const loadOlderMessages = async () => {
    if (!currentRoom || messages.length === 0) return false;
    try {
      const oldestMessage = messages[0];
      const res = await fetch(`/api/rooms/${currentRoom.id}/messages?before=${oldestMessage.timestamp}&count=20&userId=${user?.id}`);
      const olderMessages = await res.json();
      if (olderMessages.length > 0) {
        prependMessages(olderMessages);
        return true;
      }
      return false;
    } catch (error) {
      console.error('Failed to load older messages:', error);
      return false;
    }
  };

  const handleSendVoice = async (blob, duration) => {
    if (!currentRoom) return;
    try {
      const result = await uploadVoice(blob, duration);
      if (result.url) {
        sendVoice(currentRoom.id, result.url, duration);
      }
    } catch (error) {
      console.error('Send voice failed:', error);
    }
  };

  const handleReadReceipt = (messageId) => {
    if (currentRoom) {
      sendReadReceipt(currentRoom.id, messageId);
    }
  };

  const searchMessages = async (params) => {
    if (!currentRoom) return [];
    try {
      const queryParams = new URLSearchParams();
      Object.entries(params).forEach(([key, value]) => {
        if (value) queryParams.append(key, value);
      });
      const res = await fetch(`/api/rooms/${currentRoom.id}/search?${queryParams.toString()}`);
      return await res.json();
    } catch (error) {
      console.error('Search failed:', error);
      return [];
    }
  };

  useEffect(() => {
    const savedUser = localStorage.getItem('chat_user');
    if (savedUser) {
      setUser(JSON.parse(savedUser));
    }
  }, []);

  useEffect(() => {
    if (user) {
      fetchRooms();
      fetchUnreadCounts();
    }
  }, [user]);

  const fetchRooms = async () => {
    try {
      const res = await fetch('/api/rooms');
      const data = await res.json();
      setRooms(data);
    } catch (error) {
      console.error('Failed to fetch rooms:', error);
    }
  };

  const fetchUnreadCounts = async () => {
    if (!user) return;
    try {
      const res = await fetch(`/api/users/${user.id}/unread`);
      const data = await res.json();
      setUnreadCounts(data);
    } catch (error) {
      console.error('Failed to fetch unread counts:', error);
    }
  };

  const handleLogin = (username) => {
    const newUser = {
      id: uuidv4(),
      username
    };
    localStorage.setItem('chat_user', JSON.stringify(newUser));
    setUser(newUser);
  };

  const createRoom = async (name) => {
    try {
      const res = await fetch('/api/rooms', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, createdBy: user.username })
      });
      const room = await res.json();
      setRooms(prev => [...prev, room]);
      return room;
    } catch (error) {
      console.error('Failed to create room:', error);
    }
  };

  const joinRoom = (room) => {
    setCurrentRoom(room);
    connect(room.id);
    markRead(room.id, user.id);
    setUnreadCounts(prev => ({ ...prev, [room.id]: 0 }));
  };

  const leaveRoom = () => {
    setCurrentRoom(null);
  };

  const handleSendMessage = (content, mentions) => {
    if (currentRoom) {
      sendMessage(currentRoom.id, content, mentions);
    }
  };

  if (!user) {
    return <LoginModal onLogin={handleLogin} />;
  }

  return (
    <div className="app-container">
      <div className="notification-container">
        {notifications.map(notif => (
          <div key={notif.id} className="notification">
            <div className="notification-title">{notif.title}</div>
            <div className="notification-content">{notif.content}</div>
          </div>
        ))}
      </div>
      <div className="sidebar">
        <div className="user-info">
          <div className="user-avatar">{user.username.charAt(0).toUpperCase()}</div>
          <span className="username">{user.username}</span>
          <span className={`status ${isConnected ? 'online' : 'offline'}`}></span>
        </div>
        <RoomList
          rooms={rooms}
          currentRoom={currentRoom}
          unreadCounts={unreadCounts}
          onCreateRoom={createRoom}
          onJoinRoom={joinRoom}
          userId={user.id}
        />
      </div>
      <div className="main-content">
        {currentRoom ? (
          <>
            <ChatRoom
              room={currentRoom}
              messages={messages}
              onlineUsers={onlineUsers}
              typingUsers={typingUsers}
              user={user}
              onSendMessage={handleSendMessage}
              onSendVoice={handleSendVoice}
              onTyping={sendTyping}
              onLeave={leaveRoom}
              onLoadOlder={loadOlderMessages}
              onReadReceipt={handleReadReceipt}
              onOpenSearch={() => setShowSearch(true)}
            />
            {showSearch && (
              <SearchModal
                room={currentRoom}
                onClose={() => setShowSearch(false)}
                onSearch={searchMessages}
              />
            )}
          </>
        ) : (
          <div className="welcome-screen">
            <h1>欢迎来到实时聊天室</h1>
            <p>选择一个聊天室或创建新的聊天室开始聊天</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;