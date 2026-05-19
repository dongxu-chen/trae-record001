import React from 'react'
import { Handle, Position } from 'reactflow'
import { RetweetOutlined } from '@ant-design/icons'

const LoopNode = ({ data, selected }) => {
  return (
    <div className={`loop-node ${selected ? 'selected' : ''}`}>
      <Handle
        type="target"
        position={Position.Top}
        className="handle"
      />
      <div className="node-header">
        <RetweetOutlined />
        <span>{data?.label || '循环'}</span>
      </div>
      <div className="node-body">
        <div style={{ fontSize: '12px', color: '#666', marginBottom: '8px' }}>
          条件: {data?.loopCondition || '未设置'}
        </div>
        <div style={{ fontSize: '12px', color: '#666' }}>
          最大次数: {data?.maxLoops || 10}
        </div>
      </div>
      <Handle
        type="source"
        position={Position.Bottom}
        className="handle"
        id="continue"
      />
      <Handle
        type="source"
        position={Position.Right}
        className="handle handle-false"
        id="exit"
        style={{ top: '50%', right: '-8px' }}
      />
    </div>
  )
}

export default LoopNode
