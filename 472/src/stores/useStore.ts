import { create } from 'zustand';
import type { Project, Annotation, User, OnlineUser, DataPoint } from '../types';

interface AppState {
  currentUser: User;
  projects: Project[];
  currentProject: Project | null;
  annotations: Annotation[];
  onlineUsers: OnlineUser[];
  selectedAnnotationType: 'classification' | 'anomaly' | 'trend';
  selectedDataPointIndex: number | null;
  isLoading: boolean;

  setCurrentUser: (user: User) => void;
  setProjects: (projects: Project[]) => void;
  setCurrentProject: (project: Project | null) => void;
  setAnnotations: (annotations: Annotation[]) => void;
  addAnnotation: (annotation: Annotation) => void;
  updateAnnotation: (annotation: Annotation) => void;
  deleteAnnotation: (annotationId: string) => void;
  setOnlineUsers: (users: OnlineUser[]) => void;
  setSelectedAnnotationType: (type: 'classification' | 'anomaly' | 'trend') => void;
  setSelectedDataPointIndex: (index: number | null) => void;
  setIsLoading: (loading: boolean) => void;
}

const generateId = () => Math.random().toString(36).substr(2, 9);

export const useStore = create<AppState>((set) => ({
  currentUser: {
    id: generateId(),
    name: '用户_' + Math.floor(Math.random() * 1000),
    color: '#' + Math.floor(Math.random()*16777215).toString(16).padStart(6, '0'),
  },
  projects: [],
  currentProject: null,
  annotations: [],
  onlineUsers: [],
  selectedAnnotationType: 'classification',
  selectedDataPointIndex: null,
  isLoading: false,

  setCurrentUser: (user) => set({ currentUser: user }),
  setProjects: (projects) => set({ projects }),
  setCurrentProject: (project) => set({ currentProject: project }),
  setAnnotations: (annotations) => set({ annotations }),
  addAnnotation: (annotation) =>
    set((state) => ({
      annotations: [...state.annotations, annotation],
    })),
  updateAnnotation: (annotation) =>
    set((state) => ({
      annotations: state.annotations.map((a) =>
        a.id === annotation.id ? annotation : a
      ),
    })),
  deleteAnnotation: (annotationId) =>
    set((state) => ({
      annotations: state.annotations.filter((a) => a.id !== annotationId),
    })),
  setOnlineUsers: (users) => set({ onlineUsers: users }),
  setSelectedAnnotationType: (type) => set({ selectedAnnotationType: type }),
  setSelectedDataPointIndex: (index) => set({ selectedDataPointIndex: index }),
  setIsLoading: (loading) => set({ isLoading: loading }),
}));

export { generateId };
