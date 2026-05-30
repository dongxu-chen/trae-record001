function RuleConfigPanel({ rule, config, onConfigChange }) {
  if (!rule?.configFields) return null

  const renderField = (field) => {
    const value = config[field.key]

    switch (field.type) {
      case 'number':
        return (
          <input
            type="number"
            value={value ?? ''}
            onChange={(e) => onConfigChange(field.key, Number(e.target.value))}
          />
        )

      case 'text':
        return (
          <input
            type="text"
            value={value ?? ''}
            onChange={(e) => onConfigChange(field.key, e.target.value)}
          />
        )

      case 'textarea':
        return (
          <textarea
            value={value ?? ''}
            onChange={(e) => onConfigChange(field.key, e.target.value)}
            style={{ width: '100%', minHeight: '80px', padding: '8px 12px' }}
          />
        )

      case 'select':
        return (
          <select
            value={value ?? ''}
            onChange={(e) => onConfigChange(field.key, e.target.value)}
          >
            {field.options?.map((opt) => (
              <option key={opt} value={opt}>{opt}</option>
            ))}
          </select>
        )

      case 'boolean':
        return (
          <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={value ?? false}
              onChange={(e) => onConfigChange(field.key, e.target.checked)}
            />
            <span style={{ fontSize: '14px', color: '#374151' }}>启用</span>
          </label>
        )

      case 'mappings':
        return (
          <div>
            <textarea
              placeholder="每行一个值，用于循环填充"
              value={Array.isArray(value) ? value.join('\n') : ''}
              onChange={(e) => onConfigChange(field.key, e.target.value.split('\n').filter(v => v.trim()))}
              style={{ width: '100%', minHeight: '80px', padding: '8px 12px' }}
            />
            <div style={{ fontSize: '12px', color: '#6b7280', marginTop: '4px' }}>
              每行输入一个值
            </div>
          </div>
        )

      default:
        return (
          <input
            type="text"
            value={value ?? ''}
            onChange={(e) => onConfigChange(field.key, e.target.value)}
          />
        )
    }
  }

  return (
    <div className="rule-config">
      <div style={{ fontSize: '14px', fontWeight: '500', color: '#374151', marginBottom: '12px' }}>
        规则配置
      </div>
      {rule.configFields.map((field) => (
        <div key={field.key} className="form-group">
          <label>{field.label}</label>
          {renderField(field)}
        </div>
      ))}
    </div>
  )
}

export default RuleConfigPanel
