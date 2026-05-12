import { useCollab } from './CollabManager';

function UserPresence() {
  const collab = useCollab();
  
  if (!collab || !collab.isConnected) {
    return (
      <div className="user-presence">
        <div className="presence-indicator status-offline" title="未连接协同">
          ○ 离线
        </div>
      </div>
    );
  }

  const usersArray = Array.from(collab.users.values());

  return (
    <div className="user-presence">
      <div className="presence-indicator status-online" title="已连接协同">
        ● 协同模式
      </div>
      
      {usersArray.length > 0 && (
        <div className="user-avatars">
          {usersArray.slice(0, 5).map((user) => (
            <div
              key={user.clientId}
              className="user-avatar"
              style={{ backgroundColor: user.color }}
              title={`${user.name}${user.id === collab.userName ? ' (你)' : ''}`}
            >
              {user.name.charAt(0)}
            </div>
          ))}
          
          {usersArray.length > 5 && (
            <div className="user-avatar user-avatar-more">
              +{usersArray.length - 5}
            </div>
          )}
        </div>
      )}
      
      <div className="user-count">
        {usersArray.length} 人在线
      </div>
    </div>
  );
}

export default UserPresence;
