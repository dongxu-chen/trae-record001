import { create } from 'zustand';
import {
  DataSource,
  FieldNode,
  LineageEdge,
  AnalysisResult,
  ETLTask,
  Report,
  TableInfo,
  SearchHistory,
  DownstreamByDepth,
  ChangeRiskAssessment,
  FieldDictionary,
  ChangeSubscription,
  ChangeNotification,
  ChangeType,
  RiskLevel,
} from '@/types';
import {
  mockDataSources,
  mockNodes,
  mockEdges,
  mockETLTasks,
  mockReports,
  mockTables,
} from '@/mock/data';
import { assessChangeRisk } from '@/services/riskAssessment';
import { getFieldDictionary } from '@/services/dataDictionary';
import {
  getSubscriptions as getSubs,
  addSubscription as addSub,
  removeSubscription as removeSub,
  notifyChange as notifyChangeService,
  getNotifications as getNotifs,
  getDownstreamOwners,
} from '@/services/subscription';

interface LineageState {
  dataSources: DataSource[];
  selectedDataSources: string[];
  searchKeyword: string;
  selectedField: FieldNode | null;
  analysisResult: AnalysisResult | null;
  isAnalyzing: boolean;
  selectedNode: FieldNode | null;
  searchHistory: SearchHistory[];
  showDataSourceModal: boolean;
  showDetailPanel: boolean;
  expandedNodes: Set<string>;
  collapsedNodes: Set<string>;

  riskAssessment: ChangeRiskAssessment | null;
  fieldDictionary: FieldDictionary | null;
  subscriptions: ChangeSubscription[];
  notifications: ChangeNotification[];
  selectedChangeType: ChangeType;

  setSearchKeyword: (keyword: string) => void;
  setSelectedDataSources: (sources: string[]) => void;
  setSelectedField: (field: FieldNode | null) => void;
  setSelectedNode: (node: FieldNode | null) => void;
  setShowDataSourceModal: (show: boolean) => void;
  setShowDetailPanel: (show: boolean) => void;
  setSelectedChangeType: (type: ChangeType) => void;

  analyzeLineage: (fieldId: string) => Promise<void>;
  addDataSource: (dataSource: Omit<DataSource, 'id'>) => void;
  removeDataSource: (id: string) => void;
  testDataSource: (id: string) => Promise<boolean>;
  toggleDataSource: (id: string) => void;

  toggleNodeExpand: (nodeId: string) => void;
  expandAll: () => void;
  collapseAll: () => void;
  getVisibleNodes: () => FieldNode[];
  getVisibleEdges: () => LineageEdge[];

  assessRisk: (fieldId: string, changeType: ChangeType) => void;
  loadFieldDictionary: (fieldId: string) => void;
  loadSubscriptions: (fieldId?: string) => void;
  addSubscription: (sub: Omit<ChangeSubscription, 'id' | 'createdAt'>) => void;
  removeSubscription: (id: string) => void;
  triggerNotification: (fieldId: string, fieldName: string, changeType: ChangeType, description: string, riskLevel: RiskLevel) => ChangeNotification[];
  loadNotifications: (fieldId?: string) => void;
  getDownstreamOwnerList: () => Array<{ name: string; email: string; role: string }>;
}

const calculateNodeDepths = (
  rootId: string,
  edges: LineageEdge[]
): Map<string, number> => {
  const depths = new Map<string, number>();
  depths.set(rootId, 0);

  const queue: string[] = [rootId];
  const visited = new Set<string>([rootId]);

  while (queue.length > 0) {
    const currentId = queue.shift()!;
    const currentDepth = depths.get(currentId) || 0;

    const childEdges = edges.filter((e) => e.source === currentId);
    for (const edge of childEdges) {
      if (!visited.has(edge.target)) {
        visited.add(edge.target);
        depths.set(edge.target, currentDepth + 1);
        queue.push(edge.target);
      }
    }
  }

  return depths;
};

const groupByDepth = (
  nodes: FieldNode[],
  depths: Map<string, number>
): DownstreamByDepth[] => {
  const depthMap = new Map<number, FieldNode[]>();

  for (const node of nodes) {
    const depth = depths.get(node.id) || 0;
    if (!depthMap.has(depth)) {
      depthMap.set(depth, []);
    }
    depthMap.get(depth)!.push(node);
  }

  return Array.from(depthMap.entries())
    .sort(([a], [b]) => a - b)
    .map(([depth, nodes]) => ({ depth, nodes }));
};

export const useLineageStore = create<LineageState>((set, get) => ({
  dataSources: mockDataSources,
  selectedDataSources: ['ds-001', 'ds-002', 'ds-003'],
  searchKeyword: '',
  selectedField: null,
  analysisResult: null,
  isAnalyzing: false,
  selectedNode: null,
  searchHistory: [],
  showDataSourceModal: false,
  showDetailPanel: true,
  expandedNodes: new Set<string>(),
  collapsedNodes: new Set<string>(),
  riskAssessment: null,
  fieldDictionary: null,
  subscriptions: [],
  notifications: [],
  selectedChangeType: 'type_change',

  setSearchKeyword: (keyword) => set({ searchKeyword: keyword }),
  setSelectedDataSources: (sources) => set({ selectedDataSources: sources }),
  setSelectedField: (field) => set({ selectedField: field }),
  setSelectedNode: (node) => set({ selectedNode: node }),
  setShowDataSourceModal: (show) => set({ showDataSourceModal: show }),
  setShowDetailPanel: (show) => set({ showDetailPanel: show }),

  analyzeLineage: async (fieldId) => {
    set({ isAnalyzing: true });

    await new Promise((resolve) => setTimeout(resolve, 1500));

    const allNodes = mockNodes;
    const allEdges = mockEdges;

    const findDownstreamNodes = (
      nodeId: string,
      visited: Set<string> = new Set()
    ): string[] => {
      if (visited.has(nodeId)) return [];
      visited.add(nodeId);

      const downstreamEdges = allEdges.filter((e) => e.source === nodeId);
      const downstream: string[] = [];

      for (const edge of downstreamEdges) {
        downstream.push(edge.target);
        downstream.push(...findDownstreamNodes(edge.target, visited));
      }

      return downstream;
    };

    const downstreamNodeIds = [...new Set(findDownstreamNodes(fieldId))];
    const allRelatedIds = [fieldId, ...downstreamNodeIds];

    const relatedNodes = allNodes.filter((n) => allRelatedIds.includes(n.id));
    const relatedEdges = allEdges.filter(
      (e) => allRelatedIds.includes(e.source) && allRelatedIds.includes(e.target)
    );

    const nodeDepths = calculateNodeDepths(fieldId, relatedEdges);

    const nodesWithDepth = relatedNodes.map((node) => {
      const depth = nodeDepths.get(node.id) || 0;
      const hasChildren = relatedEdges.some((e) => e.source === node.id);
      return {
        ...node,
        depth,
        hasChildren,
        isExpanded: true,
      };
    });

    const etlTaskIds = nodesWithDepth
      .filter((n) => n.type === 'etl')
      .map((n) => n.name);
    const reportIds = nodesWithDepth
      .filter((n) => n.type === 'report')
      .map((n) => n.name);
    const tableIds = nodesWithDepth
      .filter((n) => n.type === 'table')
      .map((n) => n.id);

    const maxDepth = Math.max(...Array.from(nodeDepths.values()), 0);
    const downstreamByDepth = groupByDepth(nodesWithDepth, nodeDepths);

    const result: AnalysisResult = {
      fieldId,
      fieldName: allNodes.find((n) => n.id === fieldId)?.name || '',
      graph: {
        nodes: nodesWithDepth,
        edges: relatedEdges,
      },
      statistics: {
        totalDownstreamNodes: downstreamNodeIds.length,
        etlTasks: etlTaskIds.length,
        reports: reportIds.length,
        tables: nodesWithDepth.filter((n) => n.type === 'table').length,
        maxDepth,
      },
      downstreamList: {
        etlTasks: mockETLTasks.filter((t) => etlTaskIds.includes(t.name)),
        reports: mockReports.filter((r) => reportIds.includes(r.name)),
        tables: mockTables.filter((t) => tableIds.includes(t.id)),
      },
      downstreamByDepth,
    };

    const historyItem: SearchHistory = {
      id: Date.now().toString(),
      fieldId,
      fieldName: result.fieldName,
      timestamp: new Date().toISOString(),
      datasources: get().selectedDataSources,
    };

    const allExpanded = new Set(nodesWithDepth.map((n) => n.id));

    set((state) => ({
      analysisResult: result,
      isAnalyzing: false,
      expandedNodes: allExpanded,
      collapsedNodes: new Set(),
      searchHistory: [historyItem, ...state.searchHistory].slice(0, 10),
    }));
  },

  addDataSource: (dataSource) => {
    const newDataSource: DataSource = {
      ...dataSource,
      id: `ds-${Date.now()}`,
    };
    set((state) => ({
      dataSources: [...state.dataSources, newDataSource],
    }));
  },

  removeDataSource: (id) => {
    set((state) => ({
      dataSources: state.dataSources.filter((ds) => ds.id !== id),
      selectedDataSources: state.selectedDataSources.filter((s) => s !== id),
    }));
  },

  testDataSource: async (id) => {
    set((state) => ({
      dataSources: state.dataSources.map((ds) =>
        ds.id === id ? { ...ds, status: 'connecting' as const } : ds
      ),
    }));

    await new Promise((resolve) => setTimeout(resolve, 1000));

    const success = Math.random() > 0.1;

    set((state) => ({
      dataSources: state.dataSources.map((ds) =>
        ds.id === id
          ? { ...ds, status: success ? 'connected' as const : 'disconnected' as const }
          : ds
      ),
    }));

    return success;
  },

  toggleDataSource: (id) => {
    set((state) => {
      const isSelected = state.selectedDataSources.includes(id);
      return {
        selectedDataSources: isSelected
          ? state.selectedDataSources.filter((s) => s !== id)
          : [...state.selectedDataSources, id],
      };
    });
  },

  toggleNodeExpand: (nodeId) => {
    set((state) => {
      const expanded = new Set(state.expandedNodes);
      const collapsed = new Set(state.collapsedNodes);

      if (expanded.has(nodeId)) {
        expanded.delete(nodeId);
        collapsed.add(nodeId);
      } else {
        expanded.add(nodeId);
        collapsed.delete(nodeId);
      }

      return { expandedNodes: expanded, collapsedNodes: collapsed };
    });
  },

  expandAll: () => {
    set((state) => {
      if (!state.analysisResult) return state;
      const allIds = new Set(state.analysisResult.graph.nodes.map((n) => n.id));
      return { expandedNodes: allIds, collapsedNodes: new Set() };
    });
  },

  collapseAll: () => {
    set((state) => {
      if (!state.analysisResult) return state;
      const rootId = state.analysisResult.fieldId;
      return { expandedNodes: new Set([rootId]), collapsedNodes: new Set() };
    });
  },

  getVisibleNodes: () => {
    const { analysisResult, collapsedNodes } = get();
    if (!analysisResult) return [];

    const { nodes, edges } = analysisResult.graph;
    const visibleIds = new Set<string>();
    const rootId = analysisResult.fieldId;

    const addVisibleChildren = (nodeId: string) => {
      visibleIds.add(nodeId);

      if (collapsedNodes.has(nodeId)) return;

      const childEdges = edges.filter((e) => e.source === nodeId);
      for (const edge of childEdges) {
        addVisibleChildren(edge.target);
      }
    };

    addVisibleChildren(rootId);

    return nodes.filter((n) => visibleIds.has(n.id));
  },

  getVisibleEdges: () => {
    const { analysisResult, collapsedNodes } = get();
    if (!analysisResult) return [];

    const { edges } = analysisResult.graph;
    const rootId = analysisResult.fieldId;
    const visibleSourceIds = new Set<string>();

    const collectVisibleSources = (nodeId: string) => {
      visibleSourceIds.add(nodeId);

      if (collapsedNodes.has(nodeId)) return;

      const childEdges = edges.filter((e) => e.source === nodeId);
      for (const edge of childEdges) {
        collectVisibleSources(edge.target);
      }
    };

    collectVisibleSources(rootId);

    return edges.filter(
      (e) => visibleSourceIds.has(e.source) && !collapsedNodes.has(e.source)
    );
  },

  setSelectedChangeType: (type) => set({ selectedChangeType: type }),

  assessRisk: (fieldId, changeType) => {
    const { analysisResult } = get();
    if (!analysisResult) return;
    const fieldName = analysisResult.fieldName;
    const assessment = assessChangeRisk(fieldId, fieldName, changeType, analysisResult);
    set({ riskAssessment: assessment });
  },

  loadFieldDictionary: (fieldId) => {
    const { selectedField } = get();
    if (!selectedField) return;
    const dict = getFieldDictionary(fieldId, selectedField.name, selectedField.table, selectedField.database);
    set({ fieldDictionary: dict });
  },

  loadSubscriptions: (fieldId) => {
    const subs = getSubs(fieldId);
    set({ subscriptions: subs });
  },

  addSubscription: (sub) => {
    addSub(sub);
    const subs = getSubs(sub.fieldId);
    set({ subscriptions: subs });
  },

  removeSubscription: (id) => {
    removeSub(id);
    const { subscriptions } = get();
    set({ subscriptions: subscriptions.filter(s => s.id !== id) });
  },

  triggerNotification: (fieldId, fieldName, changeType, description, riskLevel) => {
    const newNotifs = notifyChangeService(fieldId, fieldName, changeType, description, riskLevel);
    set((state) => ({ notifications: [...state.notifications, ...newNotifs] }));
    return newNotifs;
  },

  loadNotifications: (fieldId) => {
    const notifs = getNotifs(fieldId);
    set({ notifications: notifs });
  },

  getDownstreamOwnerList: () => {
    const { analysisResult } = get();
    if (!analysisResult) return [];
    return getDownstreamOwners(analysisResult);
  },
}));
