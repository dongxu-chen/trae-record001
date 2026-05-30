import { useState } from 'react';

const fieldIcons = {
  phone: '📱',
  idCard: '🪪',
  email: '📧',
  name: '👤',
  address: '📍'
};

const RuleTable = ({ rules, methods, patterns, onToggle, onUpdate, onBatchUpdate }) => {
  const [selectedFields, setSelectedFields] = useState([]);
  const [batchMethod, setBatchMethod] = useState('mask');
  const [showBatchConfig, setShowBatchConfig] = useState(false);

  const handleSelectAll = () => {
    const allKeys = Object.keys(rules);
    if (selectedFields.length === allKeys.length) {
      setSelectedFields([]);
    } else {
      setSelectedFields(allKeys);
    }
  };

  const handleSelectField = (fieldKey) => {
    setSelectedFields(prev => 
      prev.includes(fieldKey)
        ? prev.filter(k => k !== fieldKey)
        : [...prev, fieldKey]
    );
  };

  const handleBatchApply = () => {
    if (selectedFields.length === 0) return;
    
    const updates = {
      method: batchMethod,
      enabled: true
    };

    if (batchMethod === 'replace') {
      updates.replacement = '*';
    } else if (batchMethod === 'hash') {
      updates.hashAlgorithm = 'md5';
      updates.hashSalt = 'default-salt';
    } else if (batchMethod === 'truncate') {
      updates.maxLength = 10;
    } else if (batchMethod === 'mask') {
      updates.pattern = 'adaptive';
      updates.keepStart = 2;
      updates.keepEnd = 2;
    }

    selectedFields.forEach(fieldKey => {
      onUpdate(fieldKey, updates);
    });

    setShowBatchConfig(false);
  };

  const handleBatchEnable = (enabled) => {
    selectedFields.forEach(fieldKey => {
      onUpdate(fieldKey, { enabled });
    });
  };

  const renderMethodOptions = (fieldKey, rule) => {
    if (!rule.enabled) return <span className="text-muted">未启用</span>;

    return (
      <div className="method-options-inline">
        <select
          value={rule.method}
          onChange={(e) => onUpdate(fieldKey, { method: e.target.value })}
          className="mini-select"
        >
          {methods.map(m => (
            <option key={m.value} value={m.value}>{m.label}</option>
          ))}
        </select>
        {rule.method === 'mask' && (
          <select
            value={rule.pattern || 'adaptive'}
            onChange={(e) => onUpdate(fieldKey, { pattern: e.target.value })}
            className="mini-select"
          >
            {patterns.map(p => (
              <option key={p.value} value={p.value}>{p.label}</option>
            ))}
          </select>
        )}
        {rule.method === 'mask' && rule.pattern === 'adaptive' && (
          <>
            <input
              type="number"
              value={rule.keepStart ?? 2}
              onChange={(e) => onUpdate(fieldKey, { keepStart: parseInt(e.target.value) || 0 })}
              className="mini-input"
              placeholder="首留"
              min="0"
              max="10"
              title="开头保留字符数"
            />
            <input
              type="number"
              value={rule.keepEnd ?? 2}
              onChange={(e) => onUpdate(fieldKey, { keepEnd: parseInt(e.target.value) || 0 })}
              className="mini-input"
              placeholder="尾留"
              min="0"
              max="10"
              title="结尾保留字符数"
            />
          </>
        )}
        {rule.method === 'replace' && (
          <input
            type="text"
            value={rule.replacement || '*'}
            onChange={(e) => onUpdate(fieldKey, { replacement: e.target.value })}
            className="mini-input"
            placeholder="替换符"
            maxLength={3}
          />
        )}
        {rule.method === 'hash' && (
          <>
            <select
              value={rule.hashAlgorithm || 'md5'}
              onChange={(e) => onUpdate(fieldKey, { hashAlgorithm: e.target.value })}
              className="mini-select"
            >
              <option value="md5">MD5</option>
              <option value="sha1">SHA-1</option>
              <option value="sha256">SHA-256</option>
            </select>
            <input
              type="text"
              value={rule.hashSalt || ''}
              onChange={(e) => onUpdate(fieldKey, { hashSalt: e.target.value })}
              className="mini-input wide"
              placeholder="盐值"
              title="哈希盐值，相同输入+相同盐值输出一致"
            />
          </>
        )}
        {rule.method === 'truncate' && (
          <input
            type="number"
            value={rule.maxLength || 10}
            onChange={(e) => onUpdate(fieldKey, { maxLength: parseInt(e.target.value) || 10 })}
            className="mini-input"
            placeholder="长度"
            min="1"
            max="100"
          />
        )}
      </div>
    );
  };

  const getMethodBadge = (method) => {
    const methodLabels = {
      mask: '掩码',
      replace: '替换',
      hash: '哈希',
      truncate: '截断',
      shuffle: '打乱'
    };
    return methodLabels[method] || method;
  };

  return (
    <div className="rule-table-container">
      <div className="batch-actions-bar">
        <div className="batch-left">
          <label className="select-all-label">
            <input
              type="checkbox"
              checked={selectedFields.length === Object.keys(rules).length && Object.keys(rules).length > 0}
              onChange={handleSelectAll}
              className="checkbox"
            />
            全选
          </label>
          <span className="selected-count">
            已选择 {selectedFields.length} 项
          </span>
        </div>
        <div className="batch-right">
          {selectedFields.length > 0 && (
            <>
              <button 
                className="btn btn-small btn-success"
                onClick={() => handleBatchEnable(true)}
              >
                ✓ 批量启用
              </button>
              <button 
                className="btn btn-small btn-warning"
                onClick={() => handleBatchEnable(false)}
              >
                ✗ 批量禁用
              </button>
              <button 
                className="btn btn-small btn-primary"
                onClick={() => setShowBatchConfig(!showBatchConfig)}
              >
                ⚙️ 批量配置
              </button>
            </>
          )}
        </div>
      </div>

      {showBatchConfig && selectedFields.length > 0 && (
        <div className="batch-config-panel">
          <h4>批量配置选中字段</h4>
          <div className="batch-config-row">
            <label>脱敏方式：</label>
            <select
              value={batchMethod}
              onChange={(e) => setBatchMethod(e.target.value)}
              className="mini-select"
            >
              {methods.map(m => (
                <option key={m.value} value={m.value}>{m.label}</option>
              ))}
            </select>
          </div>
          <div className="batch-config-row">
            <label>影响字段：</label>
            <span className="affected-fields">
              {selectedFields.map(k => rules[k].label).join('、')}
            </span>
          </div>
          <div className="batch-config-actions">
            <button className="btn btn-small btn-primary" onClick={handleBatchApply}>
              应用配置
            </button>
            <button className="btn btn-small btn-secondary" onClick={() => setShowBatchConfig(false)}>
              取消
            </button>
          </div>
        </div>
      )}

      <div className="table-wrapper">
        <table className="rule-table">
          <thead>
            <tr>
              <th style={{ width: '40px' }}>选择</th>
              <th style={{ width: '50px' }}></th>
              <th>字段名称</th>
              <th>状态</th>
              <th>脱敏方式</th>
              <th>配置参数</th>
              <th style={{ width: '80px' }}>操作</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(rules).map(([key, rule]) => (
              <tr key={key} className={selectedFields.includes(key) ? 'selected-row' : ''}>
                <td>
                  <input
                    type="checkbox"
                    checked={selectedFields.includes(key)}
                    onChange={() => handleSelectField(key)}
                    className="checkbox"
                  />
                </td>
                <td>
                  <span className="field-icon-inline">{fieldIcons[key] || '📄'}</span>
                </td>
                <td>
                  <strong>{rule.label}</strong>
                  <div className="field-key">{key}</div>
                </td>
                <td>
                  <div
                    className={`switch small ${rule.enabled ? 'active' : ''}`}
                    onClick={() => onToggle(key)}
                  />
                </td>
                <td>
                  {rule.enabled ? (
                    <span className={`method-badge ${rule.method}`}>
                      {getMethodBadge(rule.method)}
                    </span>
                  ) : (
                    <span className="text-muted">-</span>
                  )}
                </td>
                <td>
                  {renderMethodOptions(key, rule)}
                </td>
                <td>
                  <button
                    className="btn btn-icon"
                    onClick={() => onToggle(key)}
                    title={rule.enabled ? '禁用' : '启用'}
                  >
                    {rule.enabled ? '⏸️' : '▶️'}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default RuleTable;
