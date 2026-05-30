const PermissionSelector = ({ permissions, currentPermission, onPermissionChange, currentUser, onUserChange }) => {
  const users = [
    { id: 'admin_001', name: '系统管理员', role: 'admin' },
    { id: 'senior_001', name: '张经理', role: 'senior' },
    { id: 'normal_001', name: '李员工', role: 'normal' },
    { id: 'guest_001', name: '访客用户', role: 'guest' }
  ];

  const getRoleIcon = (role) => {
    const icons = {
      admin: '👑',
      senior: '💼',
      normal: '👤',
      guest: '👀'
    };
    return icons[role] || '👤';
  };

  return (
    <div className="permission-selector">
      <div className="permission-header">
        <h3>🔐 用户权限模拟</h3>
        <span className="permission-hint">选择不同权限查看脱敏效果</span>
      </div>

      <div className="user-selector">
        <label>模拟用户：</label>
        <select
          value={currentUser?.id || ''}
          onChange={(e) => {
            const user = users.find(u => u.id === e.target.value);
            if (user) {
              onUserChange(user);
              onPermissionChange(user.role);
            }
          }}
          className="user-select"
        >
          {users.map(user => (
            <option key={user.id} value={user.id}>
              {getRoleIcon(user.role)} {user.name} ({permissions.find(p => p.value === user.role)?.label || user.role})
            </option>
          ))}
        </select>
      </div>

      <div className="permission-levels">
        {permissions.map(perm => (
          <div 
            key={perm.value}
            className={`permission-level ${currentPermission === perm.value ? 'active' : ''}`}
            onClick={() => {
              onPermissionChange(perm.value);
              const user = users.find(u => u.role === perm.value);
              if (user) onUserChange(user);
            }}
          >
            <div className="perm-icon">{getRoleIcon(perm.value)}</div>
            <div className="perm-info">
              <div className="perm-label">{perm.label}</div>
              <div className="perm-desc">{perm.description}</div>
            </div>
            <div className="perm-level">
              级别 {perm.level + 1}
            </div>
          </div>
        ))}
      </div>

      <div className="permission-comparison">
        <h4>权限脱敏效果对比</h4>
        <table className="comparison-mini-table">
          <thead>
            <tr>
              <th>字段</th>
              {permissions.map(perm => (
                <th key={perm.value}>{perm.label}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>手机号</td>
              <td>13800138000</td>
              <td>13800****8000</td>
              <td>138****8000</td>
              <td>13*******0</td>
            </tr>
            <tr>
              <td>身份证</td>
              <td>110101199001011234</td>
              <td>110101********1234</td>
              <td>110101********1234</td>
              <td>11****************4</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default PermissionSelector;
