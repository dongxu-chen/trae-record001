import React from 'react'
import { Handle, Position } from 'reactflow'

const EndNode = ({ selected }) => {
  return (
    <div className="end-node">
      <Handle
        type="target"
        position={Position.Top}
        className="handle"
      />
      结束
    </div>
  )
}

export default EndNode
