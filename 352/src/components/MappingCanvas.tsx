import { useCallback, useEffect, useMemo } from 'react';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  addEdge,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
  type Connection,
  type NodeProps,
  Handle,
  Position,
  MarkerType,
} from 'reactflow';
import { Type, Hash, Calendar, CheckSquare } from 'lucide-react';
import { useAppStore } from '@/store';
import type { FieldType, FlowNodeData } from '@/types';

const typeIcons: Record<FieldType, React.ReactNode> = {
  string: <Type className="w-3 h-3" />,
  number: <Hash className="w-3 h-3" />,
  date: <Calendar className="w-3 h-3" />,
  boolean: <CheckSquare className="w-3 h-3" />,
};

const typeColors: Record<FieldType, string> = {
  string: 'border-blue-300 bg-blue-50',
  number: 'border-emerald-300 bg-emerald-50',
  date: 'border-amber-300 bg-amber-50',
  boolean: 'border-purple-300 bg-purple-50',
};

function FieldNode({ data, selected }: NodeProps<FlowNodeData>) {
  return (
    <div
      className={`px-4 py-3 rounded-lg border-2 shadow-sm min-w-[160px] ${
        typeColors[data.type]
      } ${selected ? 'ring-2 ring-blue-500 ring-offset-2' : ''}`}
    >
      {!data.isSource && (
        <Handle
          type="target"
          position={Position.Left}
          className="!bg-blue-500 !w-3 !h-3 !border-2 !border-white"
        />
      )}
      <div className="flex items-center justify-between gap-3">
        <span className="text-sm font-medium text-slate-800 truncate">
          {data.label}
        </span>
        <span className="text-slate-600">
          {typeIcons[data.type]}
        </span>
      </div>
      {data.isSource && (
        <Handle
          type="source"
          position={Position.Right}
          className="!bg-emerald-500 !w-3 !h-3 !border-2 !border-white"
        />
      )}
    </div>
  );
}

const nodeTypes = {
  field: FieldNode,
};

export default function MappingCanvas() {
  const {
    sourceFields,
    targetFields,
    mappings,
    addMapping,
    removeMapping,
    setSelectedMapping,
    selectedMapping,
  } = useAppStore();

  const initialNodes = useMemo<Node<FlowNodeData>[]>(() => {
    const sourceNodes: Node<FlowNodeData>[] = sourceFields.map((field, index) => ({
      id: `source-${field.id}`,
      type: 'field',
      position: { x: 50, y: 50 + index * 80 },
      data: {
        label: field.name,
        type: field.type,
        isSource: true,
        fieldId: field.id,
      },
    }));

    const targetNodes: Node<FlowNodeData>[] = targetFields.map((field, index) => ({
      id: `target-${field.id}`,
      type: 'field',
      position: { x: 500, y: 50 + index * 80 },
      data: {
        label: field.name,
        type: field.type,
        isSource: false,
        fieldId: field.id,
      },
    }));

    return [...sourceNodes, ...targetNodes];
  }, [sourceFields, targetFields]);

  const initialEdges = useMemo<Edge[]>(() => {
    return mappings
      .filter((m) => m.sourceFieldId)
      .map((mapping) => ({
        id: mapping.id,
        source: `source-${mapping.sourceFieldId}`,
        target: `target-${mapping.targetFieldId}`,
        animated: true,
        style: { stroke: '#94a3b8', strokeWidth: 2 },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: '#94a3b8',
        },
      }));
  }, [mappings]);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  useEffect(() => {
    setNodes(initialNodes);
  }, [initialNodes, setNodes]);

  useEffect(() => {
    setEdges(initialEdges);
  }, [initialEdges, setEdges]);

  const onConnect = useCallback(
    (params: Connection) => {
      const sourceFieldId = params.source?.replace('source-', '');
      const targetFieldId = params.target?.replace('target-', '');

      if (sourceFieldId && targetFieldId) {
        const existingMapping = mappings.find(
          (m) => m.targetFieldId === targetFieldId
        );

        if (existingMapping) {
          removeMapping(existingMapping.id);
        }

        addMapping({
          id: `mapping-${Date.now()}`,
          sourceFieldId,
          targetFieldId,
          outputType: null,
          transforms: [],
        });

        setEdges((eds) =>
          addEdge(
            {
              ...params,
              animated: true,
              style: { stroke: '#94a3b8', strokeWidth: 2 },
              markerEnd: {
                type: MarkerType.ArrowClosed,
                color: '#94a3b8',
              },
            },
            eds
          )
        );
      }
    },
    [mappings, addMapping, removeMapping, setEdges]
  );

  const onEdgeClick = useCallback(
    (_: React.MouseEvent, edge: Edge) => {
      setSelectedMapping(edge.id);
    },
    [setSelectedMapping]
  );

  useEffect(() => {
    const handleFieldDropped = (e: Event) => {
      const customEvent = e as CustomEvent;
      const { sourceFieldId, targetFieldId } = customEvent.detail;

      const existingMapping = mappings.find(
        (m) => m.targetFieldId === targetFieldId
      );

      if (existingMapping) {
        removeMapping(existingMapping.id);
      }

      addMapping({
        id: `mapping-${Date.now()}`,
        sourceFieldId,
        targetFieldId,
        transforms: [],
      });
    };

    window.addEventListener('fieldDropped', handleFieldDropped as EventListener);
    return () => {
      window.removeEventListener('fieldDropped', handleFieldDropped as EventListener);
    };
  }, [mappings, addMapping, removeMapping]);

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
      onConnect={onConnect}
      onEdgeClick={onEdgeClick}
      nodeTypes={nodeTypes}
      fitView
      className="bg-slate-50"
      defaultEdgeOptions={{
        type: 'smoothstep',
      }}
    >
      <Background color="#cbd5e1" gap={20} />
      <Controls className="bg-white rounded-lg shadow-lg border border-slate-200" />
      <MiniMap
        className="bg-white rounded-lg shadow-lg border border-slate-200"
        nodeColor={(node) => {
          return (node.data as FlowNodeData).isSource ? '#3b82f6' : '#10b981';
        }}
      />
    </ReactFlow>
  );
}
