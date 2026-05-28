import { create } from 'zustand';
import { Edge, Node } from 'reactflow';
import { FlowState, StateNodeData, EdgeData } from '../types';

const exampleNodes: Node<StateNodeData>[] = [
  {
    id: '1',
    type: 'stateNode',
    position: { x: 100, y: 200 },
    data: { label: '闲置', nodeType: 'initial', isInitial: true },
  },
  {
    id: '2',
    type: 'stateNode',
    position: { x: 350, y: 100 },
    data: { label: '运行中', nodeType: 'normal', entry: 'startTimer()', exit: 'stopTimer()' },
  },
  {
    id: '3',
    type: 'stateNode',
    position: { x: 350, y: 300 },
    data: { label: '暂停', nodeType: 'normal' },
  },
  {
    id: '4',
    type: 'stateNode',
    position: { x: 600, y: 200 },
    data: { label: '完成', nodeType: 'final' },
  },
];

const exampleEdges: Edge<EdgeData>[] = [
  {
    id: 'e1-2',
    source: '1',
    target: '2',
    data: { label: '开始', event: 'START', actions: 'logStart()' },
    label: 'START',
    type: 'smoothstep',
  },
  {
    id: 'e2-3',
    source: '2',
    target: '3',
    data: { label: '暂停', event: 'PAUSE', guard: 'canPause()' },
    label: 'PAUSE',
    type: 'smoothstep',
  },
  {
    id: 'e3-2',
    source: '3',
    target: '2',
    data: { label: '继续', event: 'RESUME' },
    label: 'RESUME',
    type: 'smoothstep',
  },
  {
    id: 'e2-4',
    source: '2',
    target: '4',
    data: { label: '完成', event: 'COMPLETE' },
    label: 'COMPLETE',
    type: 'smoothstep',
  },
];

export const useFlowStore = create<FlowState>((set, get) => ({
  nodes: [],
  edges: [],
  selectedNode: null,
  selectedEdge: null,
  codeFormat: 'xstate',
  simulator: {
    currentState: null,
    history: [],
    eventHistory: [],
    isRunning: false,
    lastEvent: null,
  },

  setNodes: (nodes) => set({ nodes }),
  setEdges: (edges) => set({ edges }),
  setSelectedNode: (selectedNode) => set({ selectedNode, selectedEdge: null }),
  setSelectedEdge: (selectedEdge) => set({ selectedEdge, selectedNode: null }),
  setCodeFormat: (codeFormat) => set({ codeFormat }),

  updateNodeData: (nodeId, data) => {
    set((state) => ({
      nodes: state.nodes.map((node) =>
        node.id === nodeId ? { ...node, data: { ...node.data, ...data } } : node
      ),
    }));
  },

  updateEdgeData: (edgeId, data) => {
    set((state) => ({
      edges: state.edges.map((edge) =>
        edge.id === edgeId ? { ...edge, data: { ...edge.data, ...data } } : edge
      ),
    }));
  },

  setSimulatorState: (state) =>
    set((prev) => ({
      simulator: { ...prev.simulator, ...state },
    })),

  resetSimulator: () =>
    set({
      simulator: {
        currentState: null,
        history: [],
        eventHistory: [],
        isRunning: false,
        lastEvent: null,
      },
    }),

  clearCanvas: () => set({ nodes: [], edges: [], selectedNode: null, selectedEdge: null }),

  loadExample: () =>
    set({
      nodes: exampleNodes,
      edges: exampleEdges,
      selectedNode: null,
      selectedEdge: null,
    }),
}));
