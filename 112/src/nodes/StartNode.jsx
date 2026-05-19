import React from 'react'
import { Handle, Position } from 'reactflow'

const StartNode = ({ selected }) => {
  return (
    <div className="start-node">
      <Handle
        type="source"
        position={Position.Bottom}
        className="handle"
      />
      开始
    </div>
  )
}

export default StartNode
