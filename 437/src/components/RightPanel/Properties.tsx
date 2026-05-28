import React from 'react';
import { Settings, Trash2, CircleDot } from 'lucide-react';
import { useFlowStore } from '../../store/useFlowStore';
import { NodeType, nodeTypeConfig } from '../../types';

export const Properties: React.FC = () => {
  const {
    selectedNode,
    selectedEdge,
    updateNodeData,
    updateEdgeData,
    setNodes,
    setEdges,
    nodes,
    edges,
  } = useFlowStore();

  const handleNodeDelete = () => {
    if (selectedNode) {
      setNodes(nodes.filter((n) => n.id !== selectedNode.id));
      setEdges(edges.filter((e) => e.source !== selectedNode.id && e.target !== selectedNode.id));
    }
  };

  const handleEdgeDelete = () => {
    if (selectedEdge) {
      setEdges(edges.filter((e) => e.id !== selectedEdge.id));
    }
  };

  if (!selectedNode && !selectedEdge) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-slate-500 p-6">
        <CircleDot size={48} className="mb-4 opacity-50" />
        <p className="text-sm text-center">选择一个节点或连接线</p>
        <p className="text-xs mt-2 text-center">以编辑其属性</p>
      </div>
    );
  }

  if (selectedNode) {
    return (
      <div className="h-full overflow-y-auto p-4">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Settings size={18} className="text-slate-400" />
            <span className="font-semibold text-slate-200">节点属性</span>
          </div>
          <button
            onClick={handleNodeDelete}
            className="p-2 rounded-lg text-rose-400 hover:bg-rose-500/20 transition-colors"
            title="删除节点"
          >
            <Trash2 size={16} />
          </button>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1.5">节点类型</label>
            <div
              className="px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 text-sm"
              style={{ color: nodeTypeConfig[selectedNode.data.nodeType as NodeType].color }}
            >
              {nodeTypeConfig[selectedNode.data.nodeType as NodeType].label}
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1.5">状态名称</label>
            <input
              type="text"
              value={selectedNode.data.label}
              onChange={(e) => updateNodeData(selectedNode.id, { label: e.target.value })}
              className="w-full px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 text-sm text-slate-200 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 transition-colors"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1.5">描述</label>
            <textarea
              value={selectedNode.data.description || ''}
              onChange={(e) => updateNodeData(selectedNode.id, { description: e.target.value })}
              rows={2}
              className="w-full px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 text-sm text-slate-200 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 transition-colors resize-none"
              placeholder="状态描述..."
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1.5">
              进入动作 (Entry Actions)
            </label>
            <input
              type="text"
              value={selectedNode.data.entry || ''}
              onChange={(e) => updateNodeData(selectedNode.id, { entry: e.target.value })}
              className="w-full px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 text-sm text-slate-200 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 transition-colors font-mono"
              placeholder="onEnter(), logStart()"
            />
            <p className="text-xs text-slate-500 mt-1">多个动作用逗号分隔</p>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1.5">
              退出动作 (Exit Actions)
            </label>
            <input
              type="text"
              value={selectedNode.data.exit || ''}
              onChange={(e) => updateNodeData(selectedNode.id, { exit: e.target.value })}
              className="w-full px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 text-sm text-slate-200 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 transition-colors font-mono"
              placeholder="cleanup(), saveState()"
            />
            <p className="text-xs text-slate-500 mt-1">多个动作用逗号分隔</p>
          </div>
        </div>
      </div>
    );
  }

  if (selectedEdge) {
    return (
      <div className="h-full overflow-y-auto p-4">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Settings size={18} className="text-slate-400" />
            <span className="font-semibold text-slate-200">转移属性</span>
          </div>
          <button
            onClick={handleEdgeDelete}
            className="p-2 rounded-lg text-rose-400 hover:bg-rose-500/20 transition-colors"
            title="删除连接线"
          >
            <Trash2 size={16} />
          </button>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1.5">事件名称</label>
            <input
              type="text"
              value={selectedEdge.data?.event || selectedEdge.label || ''}
              onChange={(e) => {
                updateEdgeData(selectedEdge.id, { event: e.target.value, label: e.target.value });
                setEdges(
                  edges.map((edge) =>
                    edge.id === selectedEdge.id ? { ...edge, label: e.target.value } : edge
                  )
                );
              }}
              className="w-full px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 text-sm text-slate-200 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 transition-colors font-mono"
              placeholder="START, SUBMIT, CANCEL"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1.5">
              守卫条件 (Guard)
            </label>
            <input
              type="text"
              value={selectedEdge.data?.guard || ''}
              onChange={(e) => updateEdgeData(selectedEdge.id, { guard: e.target.value })}
              className="w-full px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 text-sm text-slate-200 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 transition-colors font-mono"
              placeholder="isValid(), canProceed()"
            />
            <p className="text-xs text-slate-500 mt-1">条件函数名</p>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1.5">
              执行动作 (Actions)
            </label>
            <input
              type="text"
              value={selectedEdge.data?.actions || ''}
              onChange={(e) => updateEdgeData(selectedEdge.id, { actions: e.target.value })}
              className="w-full px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 text-sm text-slate-200 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 transition-colors font-mono"
              placeholder="logEvent(), notify()"
            />
            <p className="text-xs text-slate-500 mt-1">多个动作用逗号分隔</p>
          </div>
        </div>
      </div>
    );
  }

  return null;
};
