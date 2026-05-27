import React, { useState, useEffect } from 'react';
import axios from 'axios';

const NODE_TYPES_CLIENT = {
  compile: { label: '编译', color: '#3b82f6', icon: '⚙️' },
  test: { label: '测试', color: '#10b981', icon: '🧪' },
  build: { label: '构建', color: '#f59e0b', icon: '📦' },
  deploy: { label: '部署', color: '#ef4444', icon: '🚀' }
};

export default function Sidebar({ onDragStart, pipelineConfig, onPipelineConfigChange }) {
  const [nodeTypes, setNodeTypes] = useState(NODE_TYPES_CLIENT);

  useEffect(() => {
    axios.get('/api/node-types')
      .then(res => setNodeTypes(res.data))
      .catch(() => setNodeTypes(NODE_TYPES_CLIENT));
  }, []);

  const handleDragStart = (event, nodeType) => {
    event.dataTransfer.setData('application/reactflow/type', nodeType);
    event.dataTransfer.effectAllowed = 'move';
    if (onDragStart) {
      onDragStart(nodeType);
    }
  };

  return (
    <div className="sidebar">
      <div className="sidebar-section">
        <div className="sidebar-title">📋 任务节点</div>
        {Object.entries(nodeTypes).filter(([key]) => key !== 'parallel').map(([type, config]) => (
          <div
            key={type}
            className="node-palette-item"
            draggable
            onDragStart={(e) => handleDragStart(e, type)}
          >
            <span className="node-icon">{config.icon}</span>
            <span className="node-label">{config.label}</span>
          </div>
        ))}
      </div>

      <div className="sidebar-section">
        <div className="sidebar-title">⚙️ 流水线配置</div>
        
        <div style={{ marginBottom: '12px' }}>
          <div className="config-label">流水线名称</div>
          <input
            type="text"
            className="config-input"
            value={pipelineConfig.name || ''}
            onChange={(e) => onPipelineConfigChange({ ...pipelineConfig, name: e.target.value })}
            placeholder="my-pipeline"
          />
        </div>

        <div style={{ marginBottom: '12px' }}>
          <div className="config-label">版本</div>
          <input
            type="text"
            className="config-input"
            value={pipelineConfig.version || ''}
            onChange={(e) => onPipelineConfigChange({ ...pipelineConfig, version: e.target.value })}
            placeholder="1.0"
          />
        </div>

        <div style={{ marginBottom: '12px' }}>
          <div className="config-label">触发分支</div>
          <input
            type="text"
            className="config-input"
            value={(pipelineConfig.trigger?.push?.branches || []).join(', ')}
            onChange={(e) => {
              const branches = e.target.value.split(',').map(b => b.trim()).filter(b => b);
              onPipelineConfigChange({
                ...pipelineConfig,
                trigger: { push: { branches } }
              });
            }}
            placeholder="main, develop"
          />
        </div>

        <div style={{ marginBottom: '12px' }}>
          <div className="config-label">最大并发节点数</div>
          <input
            type="number"
            className="config-input"
            value={pipelineConfig.maxParallel || 5}
            onChange={(e) => onPipelineConfigChange({ 
              ...pipelineConfig, 
              maxParallel: parseInt(e.target.value) || 5 
            })}
            min="1"
            max="20"
            placeholder="5"
          />
          <div style={{ fontSize: '11px', color: '#94a3b8', marginTop: '4px' }}>
            超过限制的任务将排队执行
          </div>
        </div>
      </div>

      <div className="sidebar-section">
        <div className="sidebar-title">💡 操作提示</div>
        <div style={{ fontSize: '12px', color: '#64748b', lineHeight: '1.6' }}>
          <p style={{ marginBottom: '8px' }}>• 拖拽左侧节点到画布</p>
          <p style={{ marginBottom: '8px' }}>• 拖动节点右侧圆点到另一节点建立依赖</p>
          <p style={{ marginBottom: '8px' }}>• 点击节点进行配置</p>
          <p style={{ marginBottom: '8px' }}>• 同列多个节点自动并发执行</p>
          <p style={{ marginBottom: '8px' }}>• 循环依赖将被禁止保存</p>
          <p>• 支持导出/导入 YAML 文件</p>
        </div>
      </div>
    </div>
  );
}
