import React from 'react'
import { nodeTypesConfig } from '../config/nodeTypes'

const Sidebar = () => {
  const handleDragStart = (e, nodeType, config) => {
    e.dataTransfer.setData('application/reactflow', JSON.stringify({
      type: nodeType,
      config
    }))
    e.dataTransfer.effectAllowed = 'move'
  }

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        节点库
      </div>
      <div className="node-library">
        <div className="node-category">
          <div className="node-category-title">控制流节点</div>
          {nodeTypesConfig.controlFlow.map((node) => {
            const IconComponent = node.icon
            return (
              <div
                key={node.type}
                className="node-item"
                draggable
                onDragStart={(e) => handleDragStart(e, node.type, node.defaultData)}
              >
                <IconComponent className="node-item-icon" />
                <span className="node-item-label">{node.label}</span>
              </div>
            )
          })}
        </div>

        <div className="node-category">
          <div className="node-category-title">表单字段</div>
          {nodeTypesConfig.formFields.map((node) => {
            const IconComponent = node.icon
            return (
              <div
                key={node.type}
                className="node-item"
                draggable
                onDragStart={(e) => handleDragStart(e, 'formField', { ...node.defaultData, type: node.type, typeLabel: node.label })}
              >
                <IconComponent className="node-item-icon" />
                <span className="node-item-label">{node.label}</span>
              </div>
            )
          })}
        </div>
      </div>
    </aside>
  )
}

export default Sidebar
