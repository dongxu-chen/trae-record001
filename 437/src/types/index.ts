export type NodeType = 'initial' | 'normal' | 'final' | 'parallel' | 'history';

export type CodeFormat = 'xstate' | 'spring' | 'plantuml' | 'graphviz' | 'test-jest' | 'test-plain';

export interface StateNodeData {
  label: string;
  nodeType: NodeType;
  entry?: string;
  exit?: string;
  invoke?: string;
  description?: string;
  isInitial?: boolean;
}

export interface EdgeData {
  label: string;
  guard?: string;
  actions?: string;
  event: string;
}

export interface EventRecord {
  event: string;
  from: string;
  to: string;
  timestamp: number;
}

export interface SimulatorState {
  currentState: string | null;
  history: string[];
  eventHistory: EventRecord[];
  isRunning: boolean;
  lastEvent: string | null;
}

export interface FlowState {
  nodes: any[];
  edges: any[];
  selectedNode: any | null;
  selectedEdge: any | null;
  codeFormat: CodeFormat;
  simulator: SimulatorState;
  setNodes: (nodes: any[]) => void;
  setEdges: (edges: any[]) => void;
  setSelectedNode: (node: any | null) => void;
  setSelectedEdge: (edge: any | null) => void;
  setCodeFormat: (format: CodeFormat) => void;
  updateNodeData: (nodeId: string, data: Partial<StateNodeData>) => void;
  updateEdgeData: (edgeId: string, data: Partial<EdgeData>) => void;
  setSimulatorState: (state: Partial<SimulatorState>) => void;
  resetSimulator: () => void;
  clearCanvas: () => void;
  loadExample: () => void;
}

export const nodeTypeConfig: Record<NodeType, { label: string; color: string; bgColor: string }> = {
  initial: { label: '初始状态', color: '#10b981', bgColor: 'bg-emerald-500/20' },
  normal: { label: '普通状态', color: '#6366f1', bgColor: 'bg-indigo-500/20' },
  final: { label: '终止状态', color: '#ef4444', bgColor: 'bg-red-500/20' },
  parallel: { label: '并行状态', color: '#f59e0b', bgColor: 'bg-amber-500/20' },
  history: { label: '历史状态', color: '#8b5cf6', bgColor: 'bg-violet-500/20' },
};
