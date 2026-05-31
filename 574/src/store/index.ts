import { create } from 'zustand';
import type { Paper, HierarchicalGraphData, GraphNode, SourceType, SubGraphData } from '@/types';

interface AppState {
  searchQuery: string;
  setSearchQuery: (query: string) => void;

  selectedSource: SourceType;
  setSelectedSource: (source: SourceType) => void;

  searchResults: Paper[];
  setSearchResults: (results: Paper[]) => void;

  selectedPapers: Paper[];
  addSelectedPaper: (paper: Paper) => void;
  removeSelectedPaper: (doi: string) => void;
  clearSelectedPapers: () => void;

  graphData: HierarchicalGraphData | null;
  setGraphData: (data: HierarchicalGraphData | null) => void;

  selectedNode: GraphNode | null;
  setSelectedNode: (node: GraphNode | null) => void;

  highlightedNodes: Set<string>;
  setHighlightedNodes: (nodes: Set<string>) => void;

  expandedCommunities: Set<string>;
  toggleCommunityExpanded: (level: number, communityId: number) => void;
  expandCommunity: (level: number, communityId: number) => void;
  collapseCommunity: (level: number, communityId: number) => void;

  currentLevel: number;
  setCurrentLevel: (level: number) => void;

  subGraphs: Record<string, SubGraphData>;
  addSubGraph: (nodeId: string, data: SubGraphData) => void;

  loading: boolean;
  setLoading: (loading: boolean) => void;

  currentPage: string;
  setCurrentPage: (page: string) => void;
}

export const useAppStore = create<AppState>((set) => ({
  searchQuery: '',
  setSearchQuery: (query) => set({ searchQuery: query }),

  selectedSource: 'crossref',
  setSelectedSource: (source) => set({ selectedSource: source }),

  searchResults: [],
  setSearchResults: (results) => set({ searchResults: results }),

  selectedPapers: [],
  addSelectedPaper: (paper) =>
    set((state) => ({
      selectedPapers: state.selectedPapers.some((p) => p.doi === paper.doi)
        ? state.selectedPapers
        : [...state.selectedPapers, paper],
    })),
  removeSelectedPaper: (doi) =>
    set((state) => ({
      selectedPapers: state.selectedPapers.filter((p) => p.doi !== doi),
    })),
  clearSelectedPapers: () => set({ selectedPapers: [] }),

  graphData: null,
  setGraphData: (data) => set({ graphData: data }),

  selectedNode: null,
  setSelectedNode: (node) => set({ selectedNode: node }),

  highlightedNodes: new Set(),
  setHighlightedNodes: (nodes) => set({ highlightedNodes: nodes }),

  expandedCommunities: new Set(),
  toggleCommunityExpanded: (level, communityId) =>
    set((state) => {
      const key = `${level}-${communityId}`;
      const newExpanded = new Set(state.expandedCommunities);
      if (newExpanded.has(key)) {
        newExpanded.delete(key);
      } else {
        newExpanded.add(key);
      }
      return { expandedCommunities: newExpanded };
    }),
  expandCommunity: (level, communityId) =>
    set((state) => {
      const key = `${level}-${communityId}`;
      const newExpanded = new Set(state.expandedCommunities);
      newExpanded.add(key);
      return { expandedCommunities: newExpanded };
    }),
  collapseCommunity: (level, communityId) =>
    set((state) => {
      const key = `${level}-${communityId}`;
      const newExpanded = new Set(state.expandedCommunities);
      newExpanded.delete(key);
      return { expandedCommunities: newExpanded };
    }),

  currentLevel: 0,
  setCurrentLevel: (level) => set({ currentLevel: level }),

  subGraphs: {},
  addSubGraph: (nodeId, data) =>
    set((state) => ({
      subGraphs: { ...state.subGraphs, [nodeId]: data },
    })),

  loading: false,
  setLoading: (loading) => set({ loading }),

  currentPage: 'search',
  setCurrentPage: (page) => set({ currentPage: page }),
}));
