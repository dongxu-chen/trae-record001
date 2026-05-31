function QueryHistory({ history }) {
  const getStatusClass = (status) => {
    const classes = {
      'completed': 'status-success',
      'failed': 'status-error',
      'rejected': 'status-warning',
      'timeout': 'status-error'
    }
    return classes[status] || 'status-info'
  }

  const getStatusText = (status) => {
    const texts = {
      'completed': '成功',
      'failed': '失败',
      'rejected': '被拒绝',
      'timeout': '超时'
    }
    return texts[status] || status
  }

  const getPriorityBadge = (priority) => {
    const badges = {
      'high': { bg: '#fee2e2', color: '#991b1b', text: '高' },
      'medium': { bg: '#fef3c7', color: '#92400e', text: '中' },
      'low': { bg: '#dbeafe', color: '#1d4ed8', text: '低' }
    }
    return badges[priority] || badges['medium']
  }

  const getResourceGroupLabel = (rg) => {
    if (!rg) return 'default'
    const labels = {
      'default': { icon: '📦', text: 'default' },
      'data_team': { icon: '🔬', text: 'data_team' },
      'reporting': { icon: '📊', text: 'reporting' },
      'realtime': { icon: '⚡', text: 'realtime' }
    }
    return labels[rg] || { icon: '👥', text: rg }
  }

  const formatDuration = (duration) => {
    if (!duration) return '-'
    if (typeof duration === 'number') {
      return (duration / 1000000).toFixed(2) + 'ms'
    }
    return duration.toString()
  }

  const formatDate = (dateStr) => {
    if (!dateStr) return '-'
    const date = new Date(dateStr)
    return date.toLocaleString('zh-CN')
  }

  if (!history || history.length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: '40px', color: '#999' }}>
        暂无查询历史
      </div>
    )
  }

  return (
    <div className="table-container">
      <table>
        <thead>
          <tr>
            <th>请求 ID</th>
            <th>用户 ID</th>
            <th>资源组</th>
            <th>查询内容</th>
            <th>优先级</th>
            <th>状态</th>
            <th>扫描行数</th>
            <th>内存使用</th>
            <th>耗时</th>
            <th>时间</th>
          </tr>
        </thead>
        <tbody>
          {history.map((item) => {
            const priorityBadge = getPriorityBadge(item.Priority)
            return (
              <tr key={item.ID}>
                <td style={{ fontFamily: 'monospace', fontSize: '11px' }}>
                  {item.ID?.slice(0, 8)}...
                </td>
                <td>{item.UserID}</td>
                <td>
                  {(() => {
                    const rgLabel = getResourceGroupLabel(item.ResourceGroup)
                    return (
                      <span style={{ fontSize: '11px' }}>
                        {rgLabel.icon} {rgLabel.text}
                      </span>
                    )
                  })()}
                </td>
                <td>
                  <div className="query-text" title={item.Query}>
                    {item.Query}
                  </div>
                </td>
                <td>
                  <span style={{
                    padding: '2px 8px',
                    borderRadius: '4px',
                    fontSize: '11px',
                    background: priorityBadge.bg,
                    color: priorityBadge.color
                  }}>
                    {priorityBadge.text}
                  </span>
                </td>
                <td>
                  <span className={`status-badge ${getStatusClass(item.Status)}`}>
                    {getStatusText(item.Status)}
                  </span>
                </td>
                <td>{item.ScanRows?.toLocaleString() || '-'}</td>
                <td>{item.MemoryUsed ? `${(item.MemoryUsed / 1024 / 1024).toFixed(2)} MB` : '-'}</td>
                <td>{formatDuration(item.Duration)}</td>
                <td>{formatDate(item.CreatedAt)}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

export default QueryHistory
