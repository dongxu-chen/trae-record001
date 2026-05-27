import React, { useState, useCallback, useRef, useMemo } from 'react';
import {
  ReactFlow,
  ReactFlowProvider,
  Background,
  Controls,
  MiniMap,
  addEdge,
  useNodesState,
  useEdgesState,
  MarkerType,
  useReactFlow
} from '@xyflow/react';
import { v4 as uuidv4 } from 'uuid';
import axios from 'axios';
import yaml from 'js-yaml';

import CustomNode from './nodes/CustomNode';
import Sidebar from './components/Sidebar';
import ConfigPanel from './components/ConfigPanel';
import YamlModal from './components/YamlModal';
import Toast from './components/Toast';

const nodeTypes = {
  compile: CustomNode,
  test: CustomNode,
  build: CustomNode,
  deploy: CustomNode,
  parallel: CustomNode
};

const NODE_DEFAULTS = {
  compile: {
    label: '编译代码',
    script: ['npm install', 'npm run build'],
    runsOn: 'ubuntu-latest',
    image: 'node:18-alpine',
    env: {},
    parameters: {}
  },
  test: {
    label: '运行测试',
    script: ['npm install', 'npm test'],
    runsOn: 'ubuntu-latest',
    image: 'node:18-alpine',
    env: { CI: 'true' },
    parameters: {}
  },
  build: {
    label: '构建产物',
    script: ['npm install', 'npm run build'],
    runsOn: 'ubuntu-latest',
    image: 'node:18-alpine',
    env: {},
    parameters: {},
    artifacts: { paths: ['dist/'] }
  },
  deploy: {
    label: '部署应用',
    script: ['kubectl apply -f k8s/'],
    runsOn: 'ubuntu-latest',
    env: {},
    parameters: { ENV: 'production' }
  }
};

const initialNodes = [
  {
    id: 'node-1',
    type: 'compile',
    position: { x: 100, y: 100 },
    data: { ...NODE_DEFAULTS.compile, label: '代码编译' }
  },
  {
    id: 'node-2',
    type: 'test',
    position: { x: 350, y: 50 },
    data: { ...NODE_DEFAULTS.test, label: '单元测试' }
  },
  {
    id: 'node-3',
    type: 'test',
    position: { x: 350, y: 250 },
    data: { ...NODE_DEFAULTS.test, label: '集成测试' }
  },
  {
    id: 'node-4',
    type: 'build',
    position: { x: 600, y: 100 },
    data: { ...NODE_DEFAULTS.build, label: '镜像构建' }
  },
  {
    id: 'node-5',
    type: 'deploy',
    position: { x: 850, y: 100 },
    data: { ...NODE_DEFAULTS.deploy, label: '生产部署' }
  }
];

const initialEdges = [
  {
    id: 'edge-1',
    source: 'node-1',
    target: 'node-2',
    animated: true,
    style: { stroke: '#6366f1', strokeWidth: 2 },
    markerEnd: { type: MarkerType.ArrowClosed, color: '#6366f1' }
  },
  {
    id: 'edge-2',
    source: 'node-1',
    target: 'node-3',
    animated: true,
    style: { stroke: '#6366f1', strokeWidth: 2 },
    markerEnd: { type: MarkerType.ArrowClosed, color: '#6366f1' }
  },
  {
    id: 'edge-3',
    source: 'node-2',
    target: 'node-4',
    animated: true,
    style: { stroke: '#6366f1', strokeWidth: 2 },
    markerEnd: { type: MarkerType.ArrowClosed, color: '#6366f1' }
  },
  {
    id: 'edge-4',
    source: 'node-3',
    target: 'node-4',
    animated: true,
    style: { stroke: '#6366f1', strokeWidth: 2 },
    markerEnd: { type: MarkerType.ArrowClosed, color: '#6366f1' }
  },
  {
    id: 'edge-5',
    source: 'node-4',
    target: 'node-5',
    animated: true,
    style: { stroke: '#6366f1', strokeWidth: 2 },
    markerEnd: { type: MarkerType.ArrowClosed, color: '#6366f1' }
  }
];

const defaultEdgeOptions = {
  animated: true,
  style: { stroke: '#6366f1', strokeWidth: 2 },
  markerEnd: { type: MarkerType.ArrowClosed, color: '#6366f1' }
};

function FlowCanvas({
  nodes,
  edges,
  onNodesChange,
  onEdgesChange,
  onConnect,
  onNodeClick,
  onPaneClick,
  onAddNode,
  pipelineStats,
  selectedNode
}) {
  const reactFlowWrapper = useRef(null);
  const { screenToFlowPosition } = useReactFlow();

  const onDragOver = useCallback((event) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  const onDrop = useCallback((event) => {
    event.preventDefault();

    const type = event.dataTransfer.getData('application/reactflow/type');
    if (!type) return;

    const position = screenToFlowPosition({
      x: event.clientX,
      y: event.clientY,
    });

    onAddNode(type, position);
  }, [screenToFlowPosition, onAddNode]);

  return (
    <div className="flow-container" ref={reactFlowWrapper}>
      {pipelineStats && (
        <div className="pipeline-info" style={{
          position: 'absolute',
          top: '16px',
          left: '50%',
          transform: 'translateX(-50%)',
          zIndex: 10,
          minWidth: '300px'
        }}>
          <div className="pipeline-info-row">
            <span>状态:</span>
            <span style={{ fontWeight: '600' }}>
              {pipelineStats.valid ? '✅ 有效' : '❌ 无效'}
            </span>
          </div>
          <div className="pipeline-info-row">
            <span>阶段数:</span>
            <span>{pipelineStats.stages}</span>
          </div>
          <div className="pipeline-info-row">
            <span>任务数:</span>
            <span>{pipelineStats.totalJobs}</span>
          </div>
          {pipelineStats.warnings.length > 0 && (
            <div style={{ marginTop: '8px', paddingTop: '8px', borderTop: '1px solid #86efac', fontSize: '11px', color: '#92400e' }}>
              ⚠️ {pipelineStats.warnings.length} 个警告
            </div>
          )}
        </div>
      )}
      
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onNodeClick={onNodeClick}
        onPaneClick={onPaneClick}
        onDrop={onDrop}
        onDragOver={onDragOver}
        nodeTypes={nodeTypes}
        defaultEdgeOptions={defaultEdgeOptions}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        className="react-flow-wrapper"
      >
        <Background variant="dots" gap={20} size={1} color="#e2e8f0" />
        <Controls position="bottom-left" />
        <MiniMap
          position="bottom-right"
          nodeStrokeColor={(n) => {
            const colors = {
              compile: '#3b82f6',
              test: '#10b981',
              build: '#f59e0b',
              deploy: '#ef4444'
            };
            return colors[n.type] || '#666';
          }}
          nodeColor={(n) => {
            const colors = {
              compile: '#dbeafe',
              test: '#d1fae5',
              build: '#fef3c7',
              deploy: '#fee2e2'
            };
            return colors[n.type] || '#f1f5f9';
          }}
          style={{
            backgroundColor: '#f8fafc',
            border: '1px solid #e2e8f0',
            borderRadius: '8px'
          }}
        />
      </ReactFlow>
    </div>
  );
}

function AppContent() {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const [selectedNodeId, setSelectedNodeId] = useState(null);
  const [pipelineConfig, setPipelineConfig] = useState({
    name: 'my-cicd-pipeline',
    version: '1.0',
    trigger: {
      push: { branches: ['main', 'develop'] }
    },
    globalEnv: {},
    notifications: {},
    maxParallel: 5
  });
  
  const [showYamlModal, setShowYamlModal] = useState(false);
  const [yamlContent, setYamlContent] = useState('');
  const [toast, setToast] = useState({ message: '', type: 'info' });
  const [pipelineStats, setPipelineStats] = useState(null);

  const selectedNode = useMemo(() => {
    return nodes.find(n => n.id === selectedNodeId) || null;
  }, [nodes, selectedNodeId]);

  const showToast = (message, type = 'info') => {
    setToast({ message, type });
  };

  const handleAddNode = useCallback((type, position) => {
    const newNode = {
      id: uuidv4(),
      type,
      position,
      data: {
        ...(NODE_DEFAULTS[type] || { label: type }),
        label: `${NODE_DEFAULTS[type]?.label || type} ${nodes.filter(n => n.type === type).length + 1}`
      }
    };

    setNodes((nds) => nds.concat(newNode));
    showToast(`已添加 ${type} 节点`, 'success');
  }, [nodes, setNodes]);

  const detectCycle = (newEdges, source, target) => {
    const adjacencyList = new Map();
    const nodeIds = new Set();
    
    newEdges.forEach(edge => {
      nodeIds.add(edge.source);
      nodeIds.add(edge.target);
      if (!adjacencyList.has(edge.source)) {
        adjacencyList.set(edge.source, []);
      }
      adjacencyList.get(edge.source).push(edge.target);
    });
    
    nodeIds.forEach(id => {
      if (!adjacencyList.has(id)) {
        adjacencyList.set(id, []);
      }
    });
    
    const visited = new Set();
    const recStack = new Set();
    
    const dfs = (nodeId) => {
      visited.add(nodeId);
      recStack.add(nodeId);
      
      const neighbors = adjacencyList.get(nodeId) || [];
      for (const neighbor of neighbors) {
        if (!visited.has(neighbor)) {
          if (dfs(neighbor)) return true;
        } else if (recStack.has(neighbor)) {
          return true;
        }
      }
      
      recStack.delete(nodeId);
      return false;
    };
    
    for (const nodeId of nodeIds) {
      if (!visited.has(nodeId)) {
        if (dfs(nodeId)) return true;
      }
    }
    
    return false;
  };

  const onConnect = useCallback((params) => {
    if (params.source === params.target) {
      showToast('不能连接到自己', 'error');
      return;
    }
    
    const exists = edges.some(
      e => e.source === params.source && e.target === params.target
    );
    
    if (exists) {
      showToast('连接已存在', 'error');
      return;
    }
    
    const newEdges = [...edges, { source: params.source, target: params.target }];
    if (detectCycle(newEdges, params.source, params.target)) {
      showToast('❌ 检测到循环依赖，禁止创建此连接', 'error');
      return;
    }
    
    setEdges((eds) => addEdge({ ...params, ...defaultEdgeOptions }, eds));
  }, [edges, setEdges]);

  const onNodeClick = useCallback((event, node) => {
    setSelectedNodeId(node.id);
  }, []);

  const onPaneClick = useCallback(() => {
    setSelectedNodeId(null);
  }, []);

  const handleNodeUpdate = useCallback((nodeId, updatedNode) => {
    setNodes((nds) =>
      nds.map((n) => (n.id === nodeId ? updatedNode : n))
    );
  }, [setNodes]);

  const handleDeleteNode = useCallback((nodeId) => {
    setNodes((nds) => nds.filter((n) => n.id !== nodeId));
    setEdges((eds) => eds.filter((e) => e.source !== nodeId && e.target !== nodeId));
    setSelectedNodeId(null);
    showToast('节点已删除', 'success');
  }, [setNodes, setEdges]);

  const handleGenerateYaml = async () => {
    try {
      const res = await axios.post('/api/generate-yaml', {
        nodes,
        edges,
        pipelineConfig
      });
      setYamlContent(res.data.yaml);
      setShowYamlModal(true);
      showToast('YAML生成成功', 'success');
    } catch (error) {
      showToast(`生成失败: ${error.response?.data?.error || error.message}`, 'error');
    }
  };

  const handleValidate = async () => {
    try {
      const res = await axios.post('/api/validate-pipeline', {
        nodes,
        edges
      });
      
      setPipelineStats(res.data);
      
      if (res.data.valid) {
        showToast(`流水线有效！${res.data.stages} 个阶段，${res.data.totalJobs} 个任务`, 'success');
      } else {
        showToast(`验证失败: ${res.data.errors[0]}`, 'error');
      }
      
      if (res.data.warnings.length > 0) {
        setTimeout(() => {
          showToast(`警告: ${res.data.warnings[0]}`, 'info');
        }, 2000);
      }
    } catch (error) {
      showToast(`验证失败: ${error.message}`, 'error');
    }
  };

  const handleExport = async () => {
    try {
      const res = await axios.post('/api/export-pipeline', {
        nodes,
        edges,
        pipelineConfig
      }, {
        responseType: 'blob'
      });
      
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${pipelineConfig.name || 'pipeline'}.yaml`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      
      showToast('导出成功', 'success');
    } catch (error) {
      showToast(`导出失败: ${error.message}`, 'error');
    }
  };

  const handleImport = () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.yaml,.yml';
    input.onchange = async (e) => {
      const file = e.target.files[0];
      if (!file) return;
      
      const reader = new FileReader();
      reader.onload = async (event) => {
        try {
          const content = event.target.result;
          
          const res = await axios.post('/api/import-pipeline', {
            fileContent: content
          });
          
          if (res.data.success) {
            const importedNodes = res.data.nodes.map(n => ({
              ...n,
              data: {
                ...NODE_DEFAULTS[n.type] || {},
                ...n.data
              }
            }));
            
            setNodes(importedNodes);
            setEdges(res.data.edges);
            
            if (res.data.pipelineConfig) {
              setPipelineConfig(res.data.pipelineConfig);
            }
            
            showToast('导入成功', 'success');
          }
        } catch (error) {
          showToast(`导入失败: ${error.response?.data?.error || error.message}`, 'error');
        }
      };
      reader.readAsText(file);
    };
    input.click();
  };

  const handleClear = () => {
    if (confirm('确定要清空所有节点吗？')) {
      setNodes([]);
      setEdges([]);
      setSelectedNodeId(null);
      setPipelineStats(null);
      showToast('已清空', 'info');
    }
  };

  const handleLoadExample = () => {
    setNodes(initialNodes);
    setEdges(initialEdges);
    setSelectedNodeId(null);
    showToast('已加载示例流水线', 'success');
  };

  return (
    <div className="app-container">
      <header className="app-header">
        <div className="header-left">
          <span style={{ fontSize: '28px' }}>🔄</span>
          <div>
            <div className="header-title">CI/CD 可视化编排工具</div>
            <div className="header-subtitle">拖拽节点 · 构建流水线 · 生成YAML</div>
          </div>
        </div>
        
        <div className="header-right">
          <button className="btn btn-secondary" onClick={handleLoadExample}>
            📋 示例
          </button>
          <button className="btn btn-secondary" onClick={handleValidate}>
            ✅ 验证
          </button>
          <button className="btn btn-secondary" onClick={handleImport}>
            📥 导入
          </button>
          <button className="btn btn-secondary" onClick={handleExport}>
            📤 导出
          </button>
          <button className="btn btn-primary" onClick={handleGenerateYaml}>
            📄 生成 YAML
          </button>
          <button className="btn btn-danger" onClick={handleClear}>
            🗑️ 清空
          </button>
        </div>
      </header>

      <div className="main-content">
        <Sidebar
          pipelineConfig={pipelineConfig}
          onPipelineConfigChange={setPipelineConfig}
        />

        <FlowCanvas
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onNodeClick={onNodeClick}
          onPaneClick={onPaneClick}
          onAddNode={handleAddNode}
          pipelineStats={pipelineStats}
          selectedNode={selectedNode}
        />

        <ConfigPanel
          selectedNode={selectedNode}
          nodes={nodes}
          onNodeUpdate={handleNodeUpdate}
          onDeleteNode={handleDeleteNode}
        />
      </div>

      <YamlModal
        isOpen={showYamlModal}
        onClose={() => setShowYamlModal(false)}
        yamlContent={yamlContent}
        fileName={`${pipelineConfig.name || 'pipeline'}.yaml`}
      />

      <Toast
        message={toast.message}
        type={toast.type}
        onClose={() => setToast({ message: '', type: 'info' })}
      />
    </div>
  );
}

export default function App() {
  return (
    <ReactFlowProvider>
      <AppContent />
    </ReactFlowProvider>
  );
}
