import React from 'react';

const PARAM_TYPES = ['string', 'number', 'boolean', 'array', 'object'];

export default function ConfigPanel({ selectedNode, nodes, onNodeUpdate, onDeleteNode }) {
  if (!selectedNode) {
    return (
      <div className="config-panel">
        <div className="empty-state">
          <div className="empty-state-icon">⚙️</div>
          <div className="empty-state-text">
            点击画布上的节点<br />查看和编辑配置
          </div>
        </div>
      </div>
    );
  }

  const handleDataChange = (key, value) => {
    onNodeUpdate(selectedNode.id, {
      ...selectedNode,
      data: { ...selectedNode.data, [key]: value }
    });
  };

  const handleEnvChange = (index, type, value) => {
    const env = { ...(selectedNode.data.env || {}) };
    const keys = Object.keys(env);
    const currentKey = keys[index];
    
    if (type === 'key') {
      const newEnv = {};
      keys.forEach((k, i) => {
        if (i === index) {
          newEnv[value] = env[k];
        } else {
          newEnv[k] = env[k];
        }
      });
      handleDataChange('env', newEnv);
    } else {
      env[currentKey] = value;
      handleDataChange('env', env);
    }
  };

  const addEnv = () => {
    const env = { ...(selectedNode.data.env || {}) };
    env[`KEY_${Object.keys(env).length + 1}`] = 'value';
    handleDataChange('env', env);
  };

  const removeEnv = (key) => {
    const env = { ...(selectedNode.data.env || {}) };
    delete env[key];
    handleDataChange('env', env);
  };

  const getParamValue = (param) => {
    if (typeof param === 'object' && param !== null && 'value' in param) {
      if (param.type === 'array' || param.type === 'object') {
        return JSON.stringify(param.value);
      }
      return String(param.value);
    }
    return String(param);
  };

  const getParamType = (param) => {
    if (typeof param === 'object' && param !== null && 'type' in param) {
      return param.type;
    }
    return 'string';
  };

  const getParamDesc = (param) => {
    if (typeof param === 'object' && param !== null && 'description' in param) {
      return param.description;
    }
    return '';
  };

  const handleParamChange = (key, field, value) => {
    const params = { ...(selectedNode.data.parameters || {}) };
    const currentParam = params[key];
    
    let updatedParam;
    if (typeof currentParam === 'object' && currentParam !== null && 'type' in currentParam) {
      updatedParam = { ...currentParam };
    } else {
      updatedParam = {
        type: 'string',
        value: currentParam,
        description: ''
      };
    }

    if (field === 'key') {
      delete params[key];
      params[value] = updatedParam;
    } else if (field === 'value') {
      if (updatedParam.type === 'number') {
        updatedParam.value = value === '' ? '' : Number(value);
      } else if (updatedParam.type === 'boolean') {
        updatedParam.value = value === 'true';
      } else if (updatedParam.type === 'array' || updatedParam.type === 'object') {
        try {
          updatedParam.value = JSON.parse(value);
        } catch {
          updatedParam.value = value;
        }
      } else {
        updatedParam.value = value;
      }
      params[key] = updatedParam;
    } else if (field === 'type') {
      updatedParam.type = value;
      if (value === 'number' && typeof updatedParam.value === 'string') {
        const num = Number(updatedParam.value);
        updatedParam.value = isNaN(num) ? updatedParam.value : num;
      } else if (value === 'boolean') {
        updatedParam.value = updatedParam.value === 'true' || updatedParam.value === true;
      }
      params[key] = updatedParam;
    } else if (field === 'description') {
      updatedParam.description = value;
      params[key] = updatedParam;
    }

    handleDataChange('parameters', params);
  };

  const addParam = () => {
    const params = { ...(selectedNode.data.parameters || {}) };
    const newKey = `PARAM_${Object.keys(params).length + 1}`;
    params[newKey] = {
      type: 'string',
      value: 'value',
      description: ''
    };
    handleDataChange('parameters', params);
  };

  const removeParam = (key) => {
    const params = { ...(selectedNode.data.parameters || {}) };
    delete params[key];
    handleDataChange('parameters', params);
  };

  return (
    <div className="config-panel">
      <div className="config-panel-header">
        <div className="config-panel-title">📝 节点配置</div>
      </div>

      <div className="config-panel-body">
        <div className="config-section">
          <div className="config-section-title">基本信息</div>
          
          <div style={{ marginBottom: '12px' }}>
            <div className="config-label">节点名称</div>
            <input
              type="text"
              className="config-input"
              value={selectedNode.data.label || ''}
              onChange={(e) => handleDataChange('label', e.target.value)}
              placeholder="输入任务名称"
            />
          </div>

          <div className="config-row">
            <div>
              <div className="config-label">运行环境</div>
              <select
                className="config-select"
                value={selectedNode.data.runsOn || 'ubuntu-latest'}
                onChange={(e) => handleDataChange('runsOn', e.target.value)}
              >
                <option value="ubuntu-latest">Ubuntu Latest</option>
                <option value="ubuntu-22.04">Ubuntu 22.04</option>
                <option value="windows-latest">Windows Latest</option>
                <option value="macos-latest">macOS Latest</option>
              </select>
            </div>
            <div>
              <div className="config-label">超时(分钟)</div>
              <input
                type="number"
                className="config-input"
                value={selectedNode.data.timeout || ''}
                onChange={(e) => handleDataChange('timeout', e.target.value ? parseInt(e.target.value) : undefined)}
                placeholder="30"
                min="1"
              />
            </div>
          </div>
        </div>

        <div className="config-section">
          <div className="config-section-title">📜 执行脚本</div>
          <textarea
            className="config-textarea"
            value={(selectedNode.data.script || []).join('\n')}
            onChange={(e) => handleDataChange('script', e.target.value.split('\n').filter(line => line.trim()))}
            placeholder="npm install&#10;npm run build"
          />
          <div style={{ fontSize: '11px', color: '#94a3b8', marginTop: '4px' }}>
            每行一个命令
          </div>
        </div>

        <div className="config-section">
          <div className="config-section-title">🐳 容器镜像 (可选)</div>
          <input
            type="text"
            className="config-input"
            value={selectedNode.data.image || ''}
            onChange={(e) => handleDataChange('image', e.target.value)}
            placeholder="node:18-alpine"
          />
        </div>

        <div className="config-section">
          <div className="config-section-title">🌍 环境变量</div>
          {Object.entries(selectedNode.data.env || {}).map(([key, value], index) => (
            <div key={key} className="key-value-pair">
              <input
                type="text"
                className="config-input"
                value={key}
                onChange={(e) => handleEnvChange(index, 'key', e.target.value)}
                placeholder="KEY"
                style={{ flex: 1 }}
              />
              <input
                type="text"
                className="config-input"
                value={value}
                onChange={(e) => handleEnvChange(index, 'value', e.target.value)}
                placeholder="value"
                style={{ flex: 1 }}
              />
              <button className="remove-btn" onClick={() => removeEnv(key)}>×</button>
            </div>
          ))}
          <button className="add-btn" onClick={addEnv}>
            + 添加环境变量
          </button>
        </div>

        <div className="config-section">
          <div className="config-section-title">📋 任务参数</div>
          {Object.entries(selectedNode.data.parameters || {}).map(([key, param]) => (
            <div key={key} style={{ marginBottom: '12px', padding: '8px', background: '#f1f5f9', borderRadius: '6px' }}>
              <div style={{ marginBottom: '8px' }}>
                <div className="config-label">参数名</div>
                <input
                  type="text"
                  className="config-input"
                  value={key}
                  onChange={(e) => handleParamChange(key, 'key', e.target.value)}
                  placeholder="PARAM_NAME"
                />
              </div>
              <div className="config-row" style={{ marginBottom: '8px' }}>
                <div>
                  <div className="config-label">类型</div>
                  <select
                    className="config-select"
                    value={getParamType(param)}
                    onChange={(e) => handleParamChange(key, 'type', e.target.value)}
                  >
                    {PARAM_TYPES.map(type => (
                      <option key={type} value={type}>{type}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <div className="config-label">值</div>
                  <input
                    type="text"
                    className="config-input"
                    value={getParamValue(param)}
                    onChange={(e) => handleParamChange(key, 'value', e.target.value)}
                    placeholder={getParamType(param) === 'array' ? '[1,2,3]' : getParamType(param) === 'object' ? '{"key":"val"}' : 'value'}
                  />
                </div>
              </div>
              <div style={{ marginBottom: '8px' }}>
                <div className="config-label">描述</div>
                <input
                  type="text"
                  className="config-input"
                  value={getParamDesc(param)}
                  onChange={(e) => handleParamChange(key, 'description', e.target.value)}
                  placeholder="参数说明"
                />
              </div>
              <button className="remove-btn" onClick={() => removeParam(key)} style={{ width: '100%' }}>
                删除此参数
              </button>
            </div>
          ))}
          <button className="add-btn" onClick={addParam}>
            + 添加参数
          </button>
        </div>

        <div className="config-section">
          <div className="config-section-title">🔄 重试策略</div>
          <div className="config-row">
            <div>
              <div className="config-label">最大重试次数</div>
              <input
                type="number"
                className="config-input"
                value={selectedNode.data.retry?.max || ''}
                onChange={(e) => {
                  const retry = selectedNode.data.retry || {};
                  retry.max = e.target.value ? parseInt(e.target.value) : undefined;
                  handleDataChange('retry', Object.keys(retry).length ? retry : undefined);
                }}
                placeholder="3"
                min="1"
              />
            </div>
            <div>
              <div className="config-label">重试间隔(秒)</div>
              <input
                type="number"
                className="config-input"
                value={selectedNode.data.retry?.interval || ''}
                onChange={(e) => {
                  const retry = selectedNode.data.retry || {};
                  retry.interval = e.target.value ? parseInt(e.target.value) : undefined;
                  handleDataChange('retry', Object.keys(retry).length ? retry : undefined);
                }}
                placeholder="60"
                min="1"
              />
            </div>
          </div>
        </div>

        <div className="config-section">
          <div className="config-section-title">📦 产物归档</div>
          <input
            type="text"
            className="config-input"
            value={(selectedNode.data.artifacts?.paths || []).join(', ')}
            onChange={(e) => {
              const paths = e.target.value.split(',').map(p => p.trim()).filter(p => p);
              handleDataChange('artifacts', paths.length ? { paths } : undefined);
            }}
            placeholder="dist/, build/"
          />
          <div style={{ fontSize: '11px', color: '#94a3b8', marginTop: '4px' }}>
            用逗号分隔多个路径
          </div>
        </div>

        <button
          className="btn btn-danger"
          style={{ width: '100%', marginTop: '20px' }}
          onClick={() => onDeleteNode(selectedNode.id)}
        >
          🗑️ 删除节点
        </button>
      </div>
    </div>
  );
}
