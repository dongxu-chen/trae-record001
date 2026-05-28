import React, { useCallback, useRef } from 'react';
import ReactFlow, {
  ReactFlowProvider,
  addEdge,
  useNodesState,
  useEdgesState,
  Controls,
  MiniMap,
  Background,
  BackgroundVariant,
  Connection,
  Edge,
  Node,
  useReactFlow,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { NodeType, StateNodeData, EdgeData } from '../../types';
import { StateNode } from '../nodes/StateNode';
import { useFlowStore } from '../../store/useFlowStore';

const nodeTypes = {
  stateNode: StateNode,
};

let id = 0;
const getId = () => `node_${++id}`;

interface FlowCanvasContentProps {
  currentState: string | null;
}

const FlowCanvasContent: React.FC<FlowCanvasContentProps> = ({ currentState }) => {
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const { screenToFlowPosition } = useReactFlow();
  const { nodes: storeNodes, edges: storeEdges, setNodes, setEdges, setSelectedNode, setSelectedEdge } =
    useFlowStore();

  const [nodes, , onNodesChange] = useNodesState(storeNodes);
  const [edges, , onEdgesChange] = useEdgesState(storeEdges);

  React.useEffect(() => {
    setNodes(nodes);
  }, [nodes, setNodes]);

  React.useEffect(() => {
    setEdges(edges);
  }, [edges, setEdges]);

  const onConnect = useCallback(
    (params: Connection) => {
      const newEdge: Edge<EdgeData> = {
        ...params,
        id: `edge_${params.source}-${params.target}-${Date.now()}`,
        type: 'smoothstep',
        animated: true,
        style: { stroke: '#6366f1', strokeWidth: 2 },
        data: { label: 'EVENT', event: 'EVENT' },
        label: 'EVENT',
        labelStyle: { fill: '#94a3b8', fontSize: 11, fontWeight: 500 },
        labelBgStyle: { fill: '#1e293b', fillOpacity: 0.9, rx: 4, ry: 4 },
        labelBgPadding: [6, 4],
      };
      setEdges(addEdge(newEdge, edges));
    },
    [edges, setEdges]
  );

  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();

      const type = event.dataTransfer.getData('application/reactflow') as NodeType;
      if (!type) return;

      const position = screenToFlowPosition({
        x: event.clientX,
        y: event.clientY,
      });

      const newNode: Node<StateNodeData> = {
        id: getId(),
        type: 'stateNode',
        position,
        data: {
          label: `新状态`,
          nodeType: type,
          isInitial: type === 'initial',
        },
      };

      setNodes([...nodes, newNode]);
    },
    [screenToFlowPosition, nodes, setNodes]
  );

  const onNodeClick = useCallback(
    (_: React.MouseEvent, node: Node<StateNodeData>) => {
      setSelectedNode(node);
    },
    [setSelectedNode]
  );

  const onEdgeClick = useCallback(
    (_: React.MouseEvent, edge: Edge<EdgeData>) => {
      setSelectedEdge(edge);
    },
    [setSelectedEdge]
  );

  const onPaneClick = useCallback(() => {
    setSelectedNode(null);
    setSelectedEdge(null);
  }, [setSelectedNode, setSelectedEdge]);

  const nodesWithHighlight = React.useMemo(() => {
    return nodes.map((node) => ({
      ...node,
      data: {
        ...node.data,
        isActive: currentState === node.data.label,
      },
    }));
  }, [nodes, currentState]);

  return (
    <div ref={reactFlowWrapper} className="w-full h-full">
      <ReactFlow
        nodes={nodesWithHighlight}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onDrop={onDrop}
        onDragOver={onDragOver}
        onNodeClick={onNodeClick}
        onEdgeClick={onEdgeClick}
        onPaneClick={onPaneClick}
        nodeTypes={nodeTypes}
        fitView
        snapToGrid
        snapGrid={[15, 15]}
        defaultEdgeOptions={{
          type: 'smoothstep',
          animated: true,
          style: { stroke: '#6366f1', strokeWidth: 2 },
        }}
      >
        <Background variant={BackgroundVariant.Dots} gap={20} size={1} color="#334155" />
        <Controls
          className="bg-slate-800 border-slate-700 rounded-lg"
          position="bottom-left"
        />
        <MiniMap
          className="bg-slate-800 border border-slate-700 rounded-lg"
          nodeColor="#6366f1"
          nodeStrokeColor="#4f46e5"
          nodeBorderRadius={8}
          maskColor="rgba(15, 23, 42, 0.7)"
          position="bottom-right"
        />
      </ReactFlow>
    </div>
  );
};

export const FlowCanvas: React.FC = () => {
  const { simulator } = useFlowStore();

  return (
    <ReactFlowProvider>
      <FlowCanvasContent currentState={simulator.currentState} />
    </ReactFlowProvider>
  );
};
