function ResultDisplay({ result }) {
  const getStatusClass = (status) => {
    const classes = {
      'completed': 'status-success',
      'failed': 'status-error',
      'rejected': 'status-warning',
      'timeout': 'status-error',
      'error': 'status-error'
    }
    return classes[status] || 'status-info'
  }

  const getStatusText = (status) => {
    const texts = {
      'completed': '执行成功',
      'failed': '执行失败',
      'rejected': '被限流拒绝',
      'timeout': '查询超时',
      'error': '错误'
    }
    return texts[status] || status
  }

  const getRiskClass = (level) => {
    const classes = {
      'CRITICAL': 'risk-critical',
      'HIGH': 'risk-high',
      'MEDIUM': 'risk-medium',
      'LOW': 'risk-low'
    }
    return classes[level] || 'risk-low'
  }

  return (
    <div>
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '16px'
      }}>
        <div>
          <span className={`status-badge ${getStatusClass(result.Status)}`} style={{ marginRight: '12px' }}>
            {getStatusText(result.Status)}
          </span>
          <span style={{ fontSize: '13px', color: '#666', marginRight: '16px' }}>
            请求ID: {result.RequestID}
          </span>
          {result.ResourceGroup && (
            <span style={{ fontSize: '13px', color: '#666' }}>
              资源组: {result.ResourceGroup}
            </span>
          )}
        </div>
        {result.Duration && (
          <span style={{ fontSize: '13px', color: '#666' }}>
            耗时: {result.Duration}
          </span>
        )}
      </div>

      {result.Error && (
        <div style={{
          background: '#fef2f2',
          border: '1px solid #fecaca',
          padding: '12px 16px',
          borderRadius: '8px',
          marginBottom: '16px',
          color: '#991b1b',
          fontSize: '14px'
        }}>
          <strong>错误信息：</strong>{result.Error}
        </div>
      )}

      {result.Complexity && (
        <div style={{
          background: '#f0f9ff',
          border: '1px solid #bae6fd',
          padding: '16px',
          borderRadius: '8px',
          marginBottom: '16px'
        }}>
          <div style={{ display: 'flex', gap: '24px', alignItems: 'center', flexWrap: 'wrap' }}>
            <span style={{ fontSize: '13px', color: '#0369a1' }}>
              <strong>Cost估值：</strong>{result.Complexity.EstimatedCost?.toLocaleString()}
            </span>
            <span style={{ fontSize: '13px', color: '#0369a1' }}>
              <strong>复杂度分数：</strong>{result.Complexity.ComplexityScore?.toFixed(1)}
            </span>
            <span className={`complexity-badge ${getRiskClass(result.Complexity.RiskLevel)}`}>
              风险等级：{result.Complexity.RiskLevel}
            </span>
            <span style={{ fontSize: '13px', color: '#0369a1' }}>
              <strong>预估扫描：</strong>{result.Complexity.EstimatedRows?.toLocaleString()} 行
            </span>
            <span style={{ fontSize: '13px', color: '#0369a1' }}>
              <strong>预估内存：</strong>{(result.Complexity.EstimatedMemory / 1024 / 1024).toFixed(2)} MB
            </span>
          </div>
          {result.Complexity.CostBreakdown && Object.keys(result.Complexity.CostBreakdown).length > 0 && (
            <div style={{ marginTop: '12px', paddingTop: '12px', borderTop: '1px solid #bae6fd' }}>
              <span style={{ fontSize: '12px', color: '#0369a1', marginRight: '12px' }}><strong>Cost构成：</strong></span>
              {Object.entries(result.Complexity.CostBreakdown).map(([key, value]) => (
                <span key={key} style={{
                  padding: '2px 8px',
                  background: '#e0f2fe',
                  borderRadius: '12px',
                  fontSize: '11px',
                  color: '#0369a1',
                  marginRight: '6px'
                }}>
                  {key}: {value.toFixed(1)}%
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      {result.Status === 'completed' && result.Data && result.Data.length > 0 && (
        <div>
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '12px'
          }}>
            <h4 style={{ fontSize: '14px', fontWeight: '600' }}>查询结果</h4>
            <span style={{ fontSize: '12px', color: '#666' }}>
              共 {result.Data.length} 行，扫描 {result.ScanRows?.toLocaleString()} 行，
              内存使用 {result.MemoryUsed ? (result.MemoryUsed / 1024 / 1024).toFixed(2) : 0} MB
            </span>
          </div>
          <div className="result-data">
            <pre>{JSON.stringify(result.Data, null, 2)}</pre>
          </div>
        </div>
      )}

      {result.Status === 'completed' && (!result.Data || result.Data.length === 0) && (
        <div style={{
          textAlign: 'center',
          padding: '24px',
          color: '#999',
          background: '#f8f9fa',
          borderRadius: '8px'
        }}>
          查询执行成功，但无返回数据
        </div>
      )}
    </div>
  )
}

export default ResultDisplay
