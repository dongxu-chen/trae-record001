import React from 'react'
import { Handle, Position } from 'reactflow'
import { ForkOutlined } from '@ant-design/icons'

const BranchNode = ({ data, selected }) => {
  return (
    <div className={`branch-node ${selected ? 'selected' : ''}`}>
      <Handle
        type="target"
        position={Position.Top}
        className="handle"
      />
      <div className="node-header">
        <ForkOutlined />
        <span>{data?.label || '条件分支'}</span>
      </div>
      <div className="node-body">
        <div style={{ fontSize: '12px', color: '#666', marginBottom: '12px' }}>
          {data?.condition || '未设置条件'}
        </div>
        <div className="branch-outputs">
          <div className="branch-output-item">
            <span style={{ color: '#52c41a' }}>✓ {data?.trueLabel || '是'}</span>
            <Handle
              type="source"
              position={Position.Right}
              className="handle handle-true"
              id="true"
              style={{ top: '50%', right: '-8px' }}
            />
          </div>
          <div className="branch-output-item">
            <span style={{ color: '#ff4d4f' }}>✗ {data?.falseLabel || '否'}</span>
            <Handle
              type="source"
              position={Position.Bottom}
              className="handle handle-false"
              id="false"
            />
          </div>
        </div>
      </div>
    </div>
  )
}

export default BranchNode
