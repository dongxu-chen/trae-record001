import React from 'react';
import { Handle, Position } from '@xyflow/react';

const NODE_CONFIG = {
  compile: { color: '#3b82f6', icon: '⚙️', label: '编译' },
  test: { color: '#10b981', icon: '🧪', label: '测试' },
  build: { color: '#f59e0b', icon: '📦', label: '构建' },
  deploy: { color: '#ef4444', icon: '🚀', label: '部署' },
  parallel: { color: '#8b5cf6', icon: '⚡', label: '并发组' }
};

export default function CustomNode({ data, selected, type }) {
  const config = NODE_CONFIG[type] || NODE_CONFIG.build;
  const envCount = Object.keys(data.env || {}).length;
  const paramCount = Object.keys(data.parameters || {}).length;

  return (
    <div className={`custom-node ${selected ? 'selected' : ''}`}>
      <Handle
        type="target"
        position={Position.Left}
        className="handle"
        isConnectable={true}
      />
      
      <div className="custom-node-header" style={{ backgroundColor: config.color }}>
        <span className="node-icon">{config.icon}</span>
        <span>{data.label || config.label}</span>
      </div>
      
      <div className="custom-node-body">
        {data.script && (
          <div className="node-script">
            {Array.isArray(data.script) 
              ? data.script.join(' && ')
              : data.script}
          </div>
        )}
        
        {envCount > 0 && (
          <div>
            {Object.entries(data.env).slice(0, 3).map(([key]) => (
              <span key={key} className="node-env-badge">{key}</span>
            ))}
            {envCount > 3 && (
              <span className="node-env-badge">+{envCount - 3}</span>
            )}
          </div>
        )}
        
        {paramCount > 0 && (
          <div style={{ marginTop: '6px', fontSize: '11px', color: '#64748b' }}>
            📋 {paramCount} 个参数
          </div>
        )}
        
        {data.image && (
          <div style={{ marginTop: '6px', fontSize: '11px', color: '#64748b' }}>
            🐳 {data.image}
          </div>
        )}
      </div>
      
      <Handle
        type="source"
        position={Position.Right}
        className="handle"
        isConnectable={true}
      />
    </div>
  );
}
