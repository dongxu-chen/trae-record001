function UserList({ users, currentUserId }) {
  return (
    <div className="user-list">
      <div className="user-list-header">
        <h3>在线用户 ({users.length})</h3>
      </div>
      <div className="users">
        {users.map(user => (
          <div key={user.id} className={`user-item ${user.id === currentUserId ? 'current' : ''}`}>
            <div className="user-avatar-small">
              {user.username.charAt(0).toUpperCase()}
            </div>
            <span className="user-name">
              {user.username}
              {user.id === currentUserId && ' (我)'}
            </span>
            <span className="online-dot"></span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default UserList;