import React, { useCallback, useRef } from 'react'
import ReactFlow, {
  ReactFlowProvider,
  useNodesState,
  useEdgesState,
  Controls,
  MiniMap,
  Background,
  addEdge
} from 'reactflow'
import 'reactflow/dist/style.css'

import FormFieldNode from '../nodes/FormFieldNode'
import StartNode from '../nodes/StartNode'
import EndNode from '../nodes/EndNode'
import BranchNode from '../nodes/BranchNode'
import LoopNode from '../nodes/LoopNode'

const nodeTypes = {
  formField: FormFieldNode,
  start: StartNode,
  end: EndNode,
  branch: BranchNode,
  loop: LoopNode
}

const FlowCanvas = ({ nodes, edges, onNodesChange, onEdgesChange, onConnect, addNode, setSelectedNode }) => {
  const reactFlowWrapper = useRef(null)
  const [reactFlowInstance, setReactFlowInstance] = React.useState(null)

  const onInit = (instance) => {
    setReactFlowInstance(instance)
  }

  const onDragOver = useCallback((event) => {
    event.preventDefault()
    event.dataTransfer.dropEffect = 'move'
  }, [])

  const onDrop = useCallback(
    (event) => {
      event.preventDefault()

      const reactFlowBounds = reactFlowWrapper.current.getBoundingClientRect()
      const data = event.dataTransfer.getData('application/reactflow')

      if (typeof data === 'undefined' || !data) {
        return
      }

      const { type, config } = JSON.parse(data)
      const position = reactFlowInstance.project({
        x: event.clientX - reactFlowBounds.left,
        y: event.clientY - reactFlowBounds.top
      })

      addNode({ type, position, data: config || {} })
    },
    [reactFlowInstance, addNode]
  )

  const onNodeClick = (event, node) => {
    setSelectedNode(node)
  }

  const onPaneClick = () => {
    setSelectedNode(null)
  }

  return (
    <div className="flow-canvas" ref={reactFlowWrapper}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onInit={onInit}
        onDrop={onDrop}
        onDragOver={onDragOver}
        onNodeClick={onNodeClick}
        onPaneClick={onPaneClick}
        nodeTypes={nodeTypes}
        fitView
      >
        <Background variant="dots" gap={12} size={1} />
        <Controls />
        <MiniMap />
      </ReactFlow>
    </div>
  )
}

export default FlowCanvas
