const fieldIcons = {
  phone: '📱',
  idCard: '🪪',
  email: '📧',
  name: '👤',
  address: '📍'
};

const FieldConfig = ({ fieldKey, rule, methods, patterns, onToggle, onUpdate }) => {
  const handleMethodChange = (e) => {
    const method = e.target.value;
    const updates = { method };
    
    if (method === 'replace') {
      updates.replacement = rule.replacement || '*';
    } else if (method === 'hash') {
      updates.hashAlgorithm = rule.hashAlgorithm || 'md5';
    } else if (method === 'truncate') {
      updates.maxLength = rule.maxLength || 10;
    }
    
    onUpdate(updates);
  };

  const renderMethodOptions = () => {
    switch (rule.method) {
      case 'replace':
        return (
          <div className="option-group">
            <label>替换字符</label>
            <input
              type="text"
              value={rule.replacement || '*'}
              onChange={(e) => onUpdate({ replacement: e.target.value })}
              maxLength={3}
              placeholder="输入替换字符"
            />
          </div>
        );
      case 'hash':
        return (
          <div className="option-group">
            <label>哈希算法</label>
            <select
              value={rule.hashAlgorithm || 'md5'}
              onChange={(e) => onUpdate({ hashAlgorithm: e.target.value })}
            >
              <option value="md5">MD5</option>
              <option value="sha1">SHA-1</option>
              <option value="sha256">SHA-256</option>
            </select>
          </div>
        );
      case 'truncate':
        return (
          <div className="option-group">
            <label>最大长度</label>
            <input
              type="number"
              value={rule.maxLength || 10}
              onChange={(e) => onUpdate({ maxLength: parseInt(e.target.value) || 10 })}
              min={1}
              max={100}
            />
          </div>
        );
      case 'mask':
        return (
          <div className="option-group">
            <label>掩码模式</label>
            <select
              value={rule.pattern || 'middle'}
              onChange={(e) => onUpdate({ pattern: e.target.value })}
            >
              {patterns.map(p => (
                <option key={p.value} value={p.value}>{p.label}</option>
              ))}
            </select>
          </div>
        );
      default:
        return null;
    }
  };

  const getMethodBadgeClass = () => {
    const methodClasses = {
      mask: 'mask',
      replace: 'replace',
      hash: 'hash',
      truncate: 'truncate',
      shuffle: 'shuffle'
    };
    return methodClasses[rule.method] || '';
  };

  return (
    <div className={`field-config ${rule.enabled ? 'enabled' : ''}`}>
      <div className="field-header">
        <div className="field-title">
          <span className={`field-icon ${fieldKey}`}>
            {fieldIcons[fieldKey] || '📄'}
          </span>
          <div>
            <span className="field-name">{rule.label}</span>
            {rule.enabled && (
              <div style={{ marginTop: '4px' }}>
                <span className={`method-badge ${getMethodBadgeClass()}`}>
                  {methods.find(m => m.value === rule.method)?.label || rule.method}
                </span>
              </div>
            )}
          </div>
        </div>
        <div
          className={`switch ${rule.enabled ? 'active' : ''}`}
          onClick={onToggle}
        />
      </div>

      {rule.enabled && (
        <div className="field-options">
          <div className="option-group">
            <label>脱敏方式</label>
            <select value={rule.method} onChange={handleMethodChange}>
              {methods.map(m => (
                <option key={m.value} value={m.value}>{m.label}</option>
              ))}
            </select>
          </div>
          {renderMethodOptions()}
        </div>
      )}
    </div>
  );
};

export default FieldConfig;
