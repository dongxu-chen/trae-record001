import { create } from 'zustand';
import { Annotation, User, Point, AnnotationType } from '../../shared/types';
import { AIRecommendation } from '../utils/aiAnalysis';

type ToolType = 'select' | AnnotationType;

interface AppState {
  sessionId: string | null;
  currentUser: User | null;
  users: User[];
  annotations: Annotation[];
  selectedAnnotationId: string | null;
  activeTool: ToolType;
  chartData: any;
  chartType: string;
  isConnected: boolean;
  selectedColor: string;
  isCreating: boolean;
  tempAnnotation: Partial<Annotation> | null;
  version: number;
  permissions: 'read' | 'write';
  chartBounds: { left: number; top: number; width: number; height: number } | null;
  aiRecommendations: AIRecommendation[];
  isAnalyzing: boolean;
  searchQuery: string;
  searchFilters: {
    searchContent: boolean;
    searchAuthor: boolean;
    searchType: boolean;
  };
  selectedTemplateCategory: string;
  showAIRecommendations: boolean;
  showTemplates: boolean;
  setSessionId: (id: string | null) => void;
  setCurrentUser: (user: User | null) => void;
  setUsers: (users: User[]) => void;
  setAnnotations: (annotations: Annotation[]) => void;
  addAnnotation: (annotation: Annotation) => void;
  updateAnnotation: (annotation: Annotation) => void;
  deleteAnnotation: (id: string) => void;
  setSelectedAnnotationId: (id: string | null) => void;
  setActiveTool: (tool: ToolType) => void;
  setChartData: (data: any) => void;
  setChartType: (type: string) => void;
  setIsConnected: (connected: boolean) => void;
  setSelectedColor: (color: string) => void;
  setIsCreating: (creating: boolean) => void;
  setTempAnnotation: (annotation: Partial<Annotation> | null | ((prev: Partial<Annotation> | null) => Partial<Annotation> | null)) => void;
  setVersion: (version: number) => void;
  setPermissions: (permissions: 'read' | 'write') => void;
  setChartBounds: (bounds: { left: number; top: number; width: number; height: number } | null) => void;
  setAIRecommendations: (recommendations: AIRecommendation[]) => void;
  setIsAnalyzing: (analyzing: boolean) => void;
  setSearchQuery: (query: string) => void;
  setSearchFilters: (filters: Partial<{ searchContent: boolean; searchAuthor: boolean; searchType: boolean }>) => void;
  setSelectedTemplateCategory: (category: string) => void;
  setShowAIRecommendations: (show: boolean) => void;
  setShowTemplates: (show: boolean) => void;
  reset: () => void;
}

const initialState = {
  sessionId: null,
  currentUser: null,
  users: [],
  annotations: [],
  selectedAnnotationId: null,
  activeTool: 'select' as ToolType,
  chartData: null,
  chartType: 'line',
  isConnected: false,
  selectedColor: '#ef4444',
  isCreating: false,
  tempAnnotation: null,
  version: 0,
  permissions: 'write' as 'read' | 'write',
  chartBounds: null,
  aiRecommendations: [],
  isAnalyzing: false,
  searchQuery: '',
  searchFilters: {
    searchContent: true,
    searchAuthor: true,
    searchType: true,
  },
  selectedTemplateCategory: '全部',
  showAIRecommendations: false,
  showTemplates: false,
};

export const useStore = create<AppState>((set) => ({
  ...initialState,
  setSessionId: (id) => set({ sessionId: id }),
  setCurrentUser: (user) => set({ currentUser: user }),
  setUsers: (users) => set({ users }),
  setAnnotations: (annotations) => set({ annotations }),
  addAnnotation: (annotation) =>
    set((state) => ({ annotations: [...state.annotations, annotation] })),
  updateAnnotation: (annotation) =>
    set((state) => ({
      annotations: state.annotations.map((a) =>
        a.id === annotation.id ? annotation : a
      ),
    })),
  deleteAnnotation: (id) =>
    set((state) => ({
      annotations: state.annotations.filter((a) => a.id !== id),
      selectedAnnotationId:
        state.selectedAnnotationId === id ? null : state.selectedAnnotationId,
    })),
  setSelectedAnnotationId: (id) => set({ selectedAnnotationId: id }),
  setActiveTool: (tool) => set({ activeTool: tool, selectedAnnotationId: null }),
  setChartData: (data) => set({ chartData: data }),
  setChartType: (type) => set({ chartType: type }),
  setIsConnected: (connected) => set({ isConnected: connected }),
  setSelectedColor: (color) => set({ selectedColor: color }),
  setIsCreating: (creating) => set({ isCreating: creating }),
  setTempAnnotation: (annotation) =>
    set((state) => ({
      tempAnnotation: typeof annotation === 'function' ? annotation(state.tempAnnotation) : annotation,
    })),
  setVersion: (version) => set({ version }),
  setPermissions: (permissions) => set({ permissions }),
  setChartBounds: (bounds) => set({ chartBounds: bounds }),
  setAIRecommendations: (recommendations) => set({ aiRecommendations: recommendations }),
  setIsAnalyzing: (analyzing) => set({ isAnalyzing: analyzing }),
  setSearchQuery: (query) => set({ searchQuery: query }),
  setSearchFilters: (filters) =>
    set((state) => ({
      searchFilters: { ...state.searchFilters, ...filters },
    })),
  setSelectedTemplateCategory: (category) => set({ selectedTemplateCategory: category }),
  setShowAIRecommendations: (show) => set({ showAIRecommendations: show }),
  setShowTemplates: (show) => set({ showTemplates: show }),
  reset: () => set(initialState),
}));
