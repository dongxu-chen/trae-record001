import { create } from 'zustand';
import { GraphData, GraphNode, GraphLink, PathResult, Triple } from '@/types';
import { esClient, ES_INDEX } from '@/services/elasticsearch';
import { MIN_TIMESTAMP, MAX_TIMESTAMP } from '@/utils/sampleData';

interface SelectionBox {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
}

interface GraphState {
  graph: GraphData;
  triples: Triple[];
  selectedNode: GraphNode | null;
  hoveredNode: string | null;
  searchQuery: string;
  searchResults: GraphNode[];
  typeFilter: string | null;
  availableTypes: string[];
  pathResult: PathResult | null;
  pathSource: string;
  pathTarget: string;
  importDialogOpen: boolean;
  importText: string;
  currentTime: number;
  minTime: number;
  maxTime: number;
  isPlaying: boolean;
  playSpeed: number;
  aggregationEnabled: boolean;
  selectionBox: SelectionBox | null;
  selectionMode: boolean;

  setGraph: (g: GraphData) => void;
  loadTriples: (ts: Triple[]) => void;
  selectNode: (n: GraphNode | null) => void;
  setHoveredNode: (id: string | null) => void;
  setSearchQuery: (q: string) => void;
  setTypeFilter: (t: string | null) => void;
  setPathResult: (r: PathResult | null) => void;
  setPathSource: (s: string) => void;
  setPathTarget: (t: string) => void;
  setImportDialogOpen: (o: boolean) => void;
  setImportText: (t: string) => void;
  updateNodePositions: (nodes: GraphNode[]) => void;
  setCurrentTime: (t: number | ((prev: number) => number)) => void;
  setIsPlaying: (p: boolean) => void;
  setPlaySpeed: (s: number) => void;
  setAggregationEnabled: (e: boolean) => void;
  setSelectionBox: (b: SelectionBox | null) => void;
  setSelectionMode: (m: boolean) => void;
  getFilteredGraph: () => GraphData;
  getSelectedSubgraph: () => GraphData;
  getVisibleNodes: () => Set<string>;
}

function buildGraph(triples: Triple[]): GraphData {
  const nodeMap = new Map<string, GraphNode>();
  const typeSet = new Set<string>();
  const typeOrder: string[] = [];
  const links: GraphLink[] = [];
  triples.forEach((t) => {
    if (!nodeMap.has(t.subject)) {
      if (t.subjectType && !typeSet.has(t.subjectType)) {
        typeSet.add(t.subjectType);
        typeOrder.push(t.subjectType);
      }
      const group = t.subjectType ? typeOrder.indexOf(t.subjectType) : 0;
      nodeMap.set(t.subject, {
        id: t.subject,
        label: t.subject,
        type: t.subjectType || '未知',
        group: group >= 0 ? group : 0,
        attributes: t.attributes,
        timestamp: t.timestamp,
        startDate: t.startDate,
      });
    }
    if (!nodeMap.has(t.object)) {
      if (t.objectType && !typeSet.has(t.objectType)) {
        typeSet.add(t.objectType);
        typeOrder.push(t.objectType);
      }
      const group = t.objectType ? typeOrder.indexOf(t.objectType) : 0;
      nodeMap.set(t.object, {
        id: t.object,
        label: t.object,
        type: t.objectType || '未知',
        group: group >= 0 ? group : 0,
        timestamp: t.timestamp,
        startDate: t.startDate,
      });
    }
    links.push({
      source: t.subject,
      target: t.object,
      predicate: t.predicate,
      weight: 1,
    });
  });
  const nodes = Array.from(nodeMap.values());
  return { nodes, links };
}

function aggregateNodes(nodes: GraphNode[], links: GraphLink[]): { nodes: GraphNode[]; links: GraphLink[] } {
  const typeGroups = new Map<string, GraphNode[]>();
  nodes.forEach((n) => {
    if (!typeGroups.has(n.type)) typeGroups.set(n.type, []);
    typeGroups.get(n.type)!.push(n);
  });

  const newNodes: GraphNode[] = [];
  const nodeIdMap = new Map<string, string>();
  let groupCounter = 0;

  for (const [type, groupNodes] of typeGroups) {
    if (groupNodes.length >= 3) {
      const aggId = `__agg_${type}__${groupCounter++}`;
      const representative = groupNodes[0];
      newNodes.push({
        id: aggId,
        label: `${type} (${groupNodes.length})`,
        type: type,
        group: representative.group,
        aggregated: true,
        aggregatedCount: groupNodes.length,
        aggregatedIds: groupNodes.map((n) => n.id),
      });
      groupNodes.forEach((n) => nodeIdMap.set(n.id, aggId));
    } else {
      newNodes.push(...groupNodes);
    }
  }

  const newLinks: GraphLink[] = [];
  const linkKey = new Set<string>();
  for (const link of links) {
    const s = typeof link.source === 'string' ? link.source : link.source.id;
    const t = typeof link.target === 'string' ? link.target : link.target.id;
    const newSource = nodeIdMap.get(s) || s;
    const newTarget = nodeIdMap.get(t) || t;
    if (newSource === newTarget) continue;
    const key = [newSource, newTarget].sort().join('__');
    if (!linkKey.has(key)) {
      linkKey.add(key);
      newLinks.push({ source: newSource, target: newTarget, predicate: '关联', weight: 1 });
    }
  }

  return { nodes: newNodes, links: newLinks };
}

export const useGraphStore = create<GraphState>((set, get) => ({
  graph: { nodes: [], links: [] },
  triples: [],
  selectedNode: null,
  hoveredNode: null,
  searchQuery: '',
  searchResults: [],
  typeFilter: null,
  availableTypes: [],
  pathResult: null,
  pathSource: '',
  pathTarget: '',
  importDialogOpen: false,
  importText: '',
  currentTime: MAX_TIMESTAMP,
  minTime: MIN_TIMESTAMP,
  maxTime: MAX_TIMESTAMP,
  isPlaying: false,
  playSpeed: 1,
  aggregationEnabled: false,
  selectionBox: null,
  selectionMode: false,

  setGraph: (g) => set({ graph: g }),

  loadTriples: (ts) => {
    const g = buildGraph(ts);
    esClient.clear(ES_INDEX);
    esClient.bulk(ES_INDEX, g.nodes);
    const types = Array.from(new Set(g.nodes.map((n) => n.type)));
    const timestamps = ts.filter((t) => t.timestamp).map((t) => t.timestamp!);
    const minT = timestamps.length ? Math.min(...timestamps) : MIN_TIMESTAMP;
    const maxT = timestamps.length ? Math.max(...timestamps) : MAX_TIMESTAMP;
    set({
      graph: g,
      triples: ts,
      availableTypes: types,
      selectedNode: null,
      searchResults: [],
      pathResult: null,
      minTime: minT,
      maxTime: maxT,
      currentTime: maxT,
    });
  },

  selectNode: (n) => set({ selectedNode: n }),
  setHoveredNode: (id) => set({ hoveredNode: id }),

  setSearchQuery: (q) => {
    let results: GraphNode[] = [];
    if (q.trim()) {
      const { typeFilter } = get();
      const res = esClient.search(ES_INDEX, q, typeFilter || undefined);
      results = res.hits.hits.map((h) => h._source);
    }
    set({ searchQuery: q, searchResults: results });
  },

  setTypeFilter: (t) => {
    set({ typeFilter: t });
    const { searchQuery } = get();
    if (searchQuery.trim()) {
      const res = esClient.search(ES_INDEX, searchQuery, t || undefined);
      set({ searchResults: res.hits.hits.map((h) => h._source) });
    }
  },

  setPathResult: (r) => set({ pathResult: r }),
  setPathSource: (s) => set({ pathSource: s }),
  setPathTarget: (t) => set({ pathTarget: t }),
  setImportDialogOpen: (o) => set({ importDialogOpen: o }),
  setImportText: (t) => set({ importText: t }),

  updateNodePositions: (nodes) => {
    const cur = get().graph;
    const idToNode = new Map(cur.nodes.map((n) => [n.id, n]));
    nodes.forEach((n) => {
      const existing = idToNode.get(n.id);
      if (existing) {
        existing.x = n.x;
        existing.y = n.y;
        existing.vx = n.vx;
        existing.vy = n.vy;
      }
    });
    set({ graph: { ...cur, nodes: [...cur.nodes] } });
  },

  setCurrentTime: (t) => set((state) => ({ currentTime: typeof t === 'function' ? t(state.currentTime) : t })),
  setIsPlaying: (p) => set({ isPlaying: p }),
  setPlaySpeed: (s) => set({ playSpeed: s }),
  setAggregationEnabled: (e) => set({ aggregationEnabled: e }),
  setSelectionBox: (b) => set({ selectionBox: b }),
  setSelectionMode: (m) => set({ selectionMode: m }),

  getVisibleNodes: () => {
    const { graph, currentTime, triples } = get();
    const visible = new Set<string>();
    triples.forEach((t) => {
      if (t.timestamp && t.timestamp <= currentTime) {
        visible.add(t.subject);
        visible.add(t.object);
      } else if (!t.timestamp) {
        visible.add(t.subject);
        visible.add(t.object);
      }
    });
    graph.nodes.forEach((n) => {
      if (!n.timestamp) visible.add(n.id);
    });
    return visible;
  },

  getFilteredGraph: () => {
    const { graph, currentTime, triples, aggregationEnabled } = get();
    const visibleIds = new Set<string>();
    const validLinks = new Set<string>();

    triples.forEach((t) => {
      if (!t.timestamp || t.timestamp <= currentTime) {
        visibleIds.add(t.subject);
        visibleIds.add(t.object);
        validLinks.add(`${t.subject}__${t.object}__${t.predicate}`);
      }
    });

    let filteredNodes = graph.nodes.filter((n) => visibleIds.has(n.id));
    let filteredLinks = graph.links.filter((l) => {
      const s = typeof l.source === 'string' ? l.source : l.source.id;
      const t = typeof l.target === 'string' ? l.target : l.target.id;
      return visibleIds.has(s) && visibleIds.has(t);
    });

    if (aggregationEnabled) {
      const agg = aggregateNodes(filteredNodes, filteredLinks);
      filteredNodes = agg.nodes;
      filteredLinks = agg.links;
    }

    return { nodes: filteredNodes, links: filteredLinks };
  },

  getSelectedSubgraph: () => {
    const { graph, selectionBox } = get();
    if (!selectionBox) return { nodes: [], links: [] };
    const minX = Math.min(selectionBox.x1, selectionBox.x2);
    const maxX = Math.max(selectionBox.x1, selectionBox.x2);
    const minY = Math.min(selectionBox.y1, selectionBox.y2);
    const maxY = Math.max(selectionBox.y1, selectionBox.y2);

    const selectedNodes = graph.nodes.filter(
      (n) => n.x != null && n.y != null && n.x >= minX && n.x <= maxX && n.y >= minY && n.y <= maxY
    );
    const selectedIds = new Set(selectedNodes.map((n) => n.id));
    const selectedLinks = graph.links.filter((l) => {
      const s = typeof l.source === 'string' ? l.source : l.source.id;
      const t = typeof l.target === 'string' ? l.target : l.target.id;
      return selectedIds.has(s) && selectedIds.has(t);
    });
    return { nodes: selectedNodes, links: selectedLinks };
  },
}));
