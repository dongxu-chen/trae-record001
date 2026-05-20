import React, { useState } from 'react'
import { ReactFlowProvider } from 'reactflow'
import { ConfigProvider } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import Sidebar from './components/Sidebar'
import FlowCanvas from './components/FlowCanvas'
import PropertiesPanel from './components/PropertiesPanel'
import FormPreview from './components/FormPreview'
import Toolbar from './components/Toolbar'
import { useFlowStore } from './store/flowStore'

function App() {
  const {
    nodes,
    edges,
    onNodesChange,
    onEdgesChange,
    onConnect,
    addNode,
    setSelectedNode,
    selectedNode,
    setNodes,
    setEdges,
    clearFlow
  } = useFlowStore()

  const [showPreview, setShowPreview] = useState(false)

  const handleImport = (newNodes, newEdges) => {
    setNodes(newNodes)
    setEdges(newEdges)
    setSelectedNode(null)
  }

  return (
    <ConfigProvider locale={zhCN}>
      <ReactFlowProvider>
        <div className="app-container">
          <header className="header">
            <div className="header-title">React Flow 表单编排设计器</div>
            <div className="header-actions">
              <Toolbar
                nodes={nodes}
                edges={edges}
                onPreview={() => setShowPreview(true)}
                onClear={clearFlow}
                onImport={handleImport}
              />
            </div>
          </header>
          <div className="main-content">
            <Sidebar />
            <FlowCanvas
              nodes={nodes}
              edges={edges}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onConnect={onConnect}
              addNode={addNode}
              setSelectedNode={setSelectedNode}
            />
            <PropertiesPanel />
          </div>
          {showPreview && (
            <FormPreview
              nodes={nodes}
              onClose={() => setShowPreview(false)}
            />
          )}
        </div>
      </ReactFlowProvider>
    </ConfigProvider>
  )
}

export default App
