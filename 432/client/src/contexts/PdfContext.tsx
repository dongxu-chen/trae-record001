import React, { createContext, useContext, useReducer, ReactNode, useCallback, useEffect, useRef } from 'react';
import { PdfDocument, Annotation, AnnotationType, OutlineNode, ViewerState, ToolState, AnnotationTemplate, Reviewer, ReviewSession, OcrResult, MergeConflict } from '../types';
import { generateId } from '../utils/coordinateUtils';
import { reviewApi } from '../services/api';

interface PdfState {
  document: PdfDocument | null;
  tool: ToolState;
  viewer: ViewerState;
  annotationsHistory: Annotation[][];
  historyIndex: number;
  templates: AnnotationTemplate[];
  currentReviewer: Reviewer | null;
  reviewSession: ReviewSession | null;
  otherAnnotations: (Annotation & { reviewerId: string; reviewerName: string; reviewerColor: string })[];
  ocrResults: OcrResult[];
  ocrProgress: number;
  isOcrProcessing: boolean;
}

type PdfAction =
  | { type: 'SET_DOCUMENT'; payload: PdfDocument | null }
  | { type: 'SET_CURRENT_TOOL'; payload: AnnotationType }
  | { type: 'SET_CURRENT_COLOR'; payload: string }
  | { type: 'SET_CURRENT_PAGE'; payload: number }
  | { type: 'SET_ZOOM'; payload: number }
  | { type: 'TOGGLE_SIDEBAR' }
  | { type: 'SET_SIDEBAR_TAB'; payload: 'outline' | 'search' | 'annotations' | 'reviewers' }
  | { type: 'ADD_ANNOTATION'; payload: Annotation }
  | { type: 'UPDATE_ANNOTATION'; payload: Annotation }
  | { type: 'DELETE_ANNOTATION'; payload: string }
  | { type: 'UNDO' }
  | { type: 'REDO' }
  | { type: 'SET_OUTLINES'; payload: OutlineNode[] }
  | { type: 'SET_TEMPLATES'; payload: AnnotationTemplate[] }
  | { type: 'ADD_TEMPLATE'; payload: AnnotationTemplate }
  | { type: 'UPDATE_TEMPLATE'; payload: AnnotationTemplate }
  | { type: 'DELETE_TEMPLATE'; payload: string }
  | { type: 'SET_CURRENT_REVIEWER'; payload: Reviewer | null }
  | { type: 'SET_REVIEW_SESSION'; payload: ReviewSession | null }
  | { type: 'SET_OTHER_ANNOTATIONS'; payload: (Annotation & { reviewerId: string; reviewerName: string; reviewerColor: string })[] }
  | { type: 'ADD_OTHER_ANNOTATION'; payload: Annotation & { reviewerId: string; reviewerName: string; reviewerColor: string } }
  | { type: 'SET_OCR_RESULTS'; payload: OcrResult[] }
  | { type: 'SET_OCR_PROGRESS'; payload: number }
  | { type: 'SET_OCR_PROCESSING'; payload: boolean };

const defaultTemplates: AnnotationTemplate[] = [
  { id: 'tpl-1', name: '通过', type: 'highlight', color: '#4CAF50', content: '同意', shortcut: '1', isGlobal: true, createdAt: Date.now(), updatedAt: Date.now() },
  { id: 'tpl-2', name: '驳回', type: 'highlight', color: '#F44336', content: '不同意', shortcut: '2', isGlobal: true, createdAt: Date.now(), updatedAt: Date.now() },
  { id: 'tpl-3', name: '需修改', type: 'underline', color: '#FF9800', content: '需要修改', shortcut: '3', isGlobal: true, createdAt: Date.now(), updatedAt: Date.now() },
  { id: 'tpl-4', name: '重要', type: 'highlight', color: '#FFEB3B', content: '重要内容', shortcut: '4', isGlobal: true, createdAt: Date.now(), updatedAt: Date.now() },
  { id: 'tpl-5', name: '疑问', type: 'comment', color: '#2196F3', content: '请确认此处内容', shortcut: '5', isGlobal: true, createdAt: Date.now(), updatedAt: Date.now() },
];

const initialState: PdfState = {
  document: null,
  tool: {
    currentTool: 'select',
    currentColor: '#FFEB3B',
  },
  viewer: {
    currentPage: 0,
    zoom: 1,
    sidebarOpen: true,
    sidebarTab: 'outline',
  },
  annotationsHistory: [[]],
  historyIndex: 0,
  templates: defaultTemplates,
  currentReviewer: null,
  reviewSession: null,
  otherAnnotations: [],
  ocrResults: [],
  ocrProgress: 0,
  isOcrProcessing: false,
};

const pdfReducer = (state: PdfState, action: PdfAction): PdfState => {
  switch (action.type) {
    case 'SET_DOCUMENT':
      return {
        ...state,
        document: action.payload,
        annotationsHistory: action.payload ? [action.payload.annotations] : [[]],
        historyIndex: 0,
      };

    case 'SET_CURRENT_TOOL':
      return {
        ...state,
        tool: { ...state.tool, currentTool: action.payload },
      };

    case 'SET_CURRENT_COLOR':
      return {
        ...state,
        tool: { ...state.tool, currentColor: action.payload },
      };

    case 'SET_CURRENT_PAGE':
      return {
        ...state,
        viewer: { ...state.viewer, currentPage: action.payload },
      };

    case 'SET_ZOOM':
      return {
        ...state,
        viewer: { ...state.viewer, zoom: action.payload },
      };

    case 'TOGGLE_SIDEBAR':
      return {
        ...state,
        viewer: { ...state.viewer, sidebarOpen: !state.viewer.sidebarOpen },
      };

    case 'SET_SIDEBAR_TAB':
      return {
        ...state,
        viewer: { ...state.viewer, sidebarTab: action.payload },
      };

    case 'ADD_ANNOTATION': {
      if (!state.document) return state;
      const newAnnotations = [...state.document.annotations, action.payload];
      const newHistory = state.annotationsHistory.slice(0, state.historyIndex + 1);
      newHistory.push(newAnnotations);
      return {
        ...state,
        document: { ...state.document, annotations: newAnnotations },
        annotationsHistory: newHistory,
        historyIndex: newHistory.length - 1,
      };
    }

    case 'UPDATE_ANNOTATION': {
      if (!state.document) return state;
      const newAnnotations = state.document.annotations.map(a =>
        a.id === action.payload.id ? action.payload : a
      );
      const newHistory = state.annotationsHistory.slice(0, state.historyIndex + 1);
      newHistory.push(newAnnotations);
      return {
        ...state,
        document: { ...state.document, annotations: newAnnotations },
        annotationsHistory: newHistory,
        historyIndex: newHistory.length - 1,
      };
    }

    case 'DELETE_ANNOTATION': {
      if (!state.document) return state;
      const newAnnotations = state.document.annotations.filter(a => a.id !== action.payload);
      const newHistory = state.annotationsHistory.slice(0, state.historyIndex + 1);
      newHistory.push(newAnnotations);
      return {
        ...state,
        document: { ...state.document, annotations: newAnnotations },
        annotationsHistory: newHistory,
        historyIndex: newHistory.length - 1,
      };
    }

    case 'UNDO': {
      if (state.historyIndex <= 0 || !state.document) return state;
      const newIndex = state.historyIndex - 1;
      return {
        ...state,
        document: {
          ...state.document,
          annotations: state.annotationsHistory[newIndex],
        },
        historyIndex: newIndex,
      };
    }

    case 'REDO': {
      if (state.historyIndex >= state.annotationsHistory.length - 1 || !state.document) return state;
      const newIndex = state.historyIndex + 1;
      return {
        ...state,
        document: {
          ...state.document,
          annotations: state.annotationsHistory[newIndex],
        },
        historyIndex: newIndex,
      };
    }

    case 'SET_OUTLINES':
      if (!state.document) return state;
      return {
        ...state,
        document: { ...state.document, outlines: action.payload },
      };

    case 'SET_TEMPLATES':
      return {
        ...state,
        templates: action.payload,
      };

    case 'ADD_TEMPLATE':
      return {
        ...state,
        templates: [...state.templates, action.payload],
      };

    case 'UPDATE_TEMPLATE':
      return {
        ...state,
        templates: state.templates.map(t =>
          t.id === action.payload.id ? action.payload : t
        ),
      };

    case 'DELETE_TEMPLATE':
      return {
        ...state,
        templates: state.templates.filter(t => t.id !== action.payload),
      };

    case 'SET_CURRENT_REVIEWER':
      return {
        ...state,
        currentReviewer: action.payload,
      };

    case 'SET_REVIEW_SESSION':
      return {
        ...state,
        reviewSession: action.payload,
      };

    case 'SET_OTHER_ANNOTATIONS':
      return {
        ...state,
        otherAnnotations: action.payload,
      };

    case 'ADD_OTHER_ANNOTATION':
      return {
        ...state,
        otherAnnotations: [...state.otherAnnotations, action.payload],
      };

    case 'SET_OCR_RESULTS':
      return {
        ...state,
        ocrResults: action.payload,
      };

    case 'SET_OCR_PROGRESS':
      return {
        ...state,
        ocrProgress: action.payload,
      };

    case 'SET_OCR_PROCESSING':
      return {
        ...state,
        isOcrProcessing: action.payload,
      };

    default:
      return state;
  }
};

interface PdfContextType {
  state: PdfState;
  dispatch: React.Dispatch<PdfAction>;
  addAnnotation: (annotation: Omit<Annotation, 'id' | 'createdAt'>) => void;
  undo: () => void;
  redo: () => void;
  canUndo: boolean;
  canRedo: boolean;
  applyTemplate: (template: AnnotationTemplate, position?: { x: number; y: number; pageIndex: number }) => void;
  createReviewSession: (fileId: string, reviewerName: string) => Promise<void>;
  joinReviewSession: (sessionId: string, reviewerName: string) => Promise<void>;
  syncAnnotations: () => Promise<void>;
  mergeAnnotations: (selectedIds: string[]) => Promise<{ mergedAnnotations: Annotation[]; conflicts: MergeConflict[] }>;
}

const PdfContext = createContext<PdfContextType | null>(null);

export const PdfProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [state, dispatch] = useReducer(pdfReducer, initialState);
  const syncIntervalRef = useRef<number | null>(null);

  const addAnnotation = useCallback((annotation: Omit<Annotation, 'id' | 'createdAt'>) => {
    const newAnnotation = {
      ...annotation,
      id: generateId(),
      createdAt: Date.now(),
    };
    
    dispatch({
      type: 'ADD_ANNOTATION',
      payload: newAnnotation,
    });

    if (state.reviewSession && state.currentReviewer) {
      reviewApi.addAnnotation(
        state.reviewSession.sessionId,
        state.currentReviewer.id,
        newAnnotation
      ).catch((err) => {
        console.error('Failed to sync annotation to server:', err);
      });
    }
  }, [state.reviewSession, state.currentReviewer]);

  const undo = useCallback(() => {
    dispatch({ type: 'UNDO' });
  }, []);

  const redo = useCallback(() => {
    dispatch({ type: 'REDO' });
  }, []);

  const applyTemplate = useCallback((template: AnnotationTemplate, position?: { x: number; y: number; pageIndex: number }) => {
    const pos = position || { x: 0.1, y: 0.1, pageIndex: state.viewer.currentPage };
    
    addAnnotation({
      type: template.type,
      pageIndex: pos.pageIndex,
      position: {
        x: pos.x,
        y: pos.y,
        width: template.type === 'comment' ? undefined : 0.15,
        height: template.type === 'comment' ? undefined : 0.05,
      },
      color: template.color,
      content: template.content,
    });
  }, [addAnnotation, state.viewer.currentPage]);

  const createReviewSession = useCallback(async (fileId: string, reviewerName: string) => {
    try {
      const result = await reviewApi.createSession(fileId, reviewerName);
      dispatch({ type: 'SET_REVIEW_SESSION', payload: result.session });
      dispatch({
        type: 'SET_CURRENT_REVIEWER',
        payload: result.session.reviewers.find((r: Reviewer) => r.id === result.reviewerId),
      });
    } catch (error) {
      console.error('Failed to create review session:', error);
      throw error;
    }
  }, []);

  const joinReviewSession = useCallback(async (sessionId: string, reviewerName: string) => {
    try {
      const result = await reviewApi.joinSession(sessionId, reviewerName);
      dispatch({ type: 'SET_REVIEW_SESSION', payload: result.session });
      dispatch({
        type: 'SET_CURRENT_REVIEWER',
        payload: result.session.reviewers.find((r: Reviewer) => r.id === result.reviewerId),
      });
    } catch (error) {
      console.error('Failed to join review session:', error);
      throw error;
    }
  }, []);

  const syncAnnotations = useCallback(async () => {
    if (!state.reviewSession) return;

    try {
      const result = await reviewApi.getSession(state.reviewSession.sessionId);
      const currentReviewerId = state.currentReviewer?.id;
      
      const otherAnnotations = result.annotations.filter(
        (a: any) => a.reviewerId !== currentReviewerId
      );
      
      dispatch({ type: 'SET_OTHER_ANNOTATIONS', payload: otherAnnotations });
    } catch (error) {
      console.error('Failed to sync annotations:', error);
    }
  }, [state.reviewSession, state.currentReviewer]);

  const mergeAnnotations = useCallback(async (selectedIds: string[]) => {
    if (!state.reviewSession) {
      throw new Error('No active review session');
    }

    const result = await reviewApi.mergeAnnotations(state.reviewSession.sessionId, selectedIds);
    return result;
  }, [state.reviewSession]);

  useEffect(() => {
    if (state.reviewSession && state.currentReviewer) {
      syncIntervalRef.current = setInterval(syncAnnotations, 3000);
      
      return () => {
        if (syncIntervalRef.current) {
          clearInterval(syncIntervalRef.current);
        }
      };
    }
  }, [state.reviewSession, state.currentReviewer, syncAnnotations]);

  const canUndo = state.historyIndex > 0;
  const canRedo = state.historyIndex < state.annotationsHistory.length - 1;

  return (
    <PdfContext.Provider value={{
      state,
      dispatch,
      addAnnotation,
      undo,
      redo,
      canUndo,
      canRedo,
      applyTemplate,
      createReviewSession,
      joinReviewSession,
      syncAnnotations,
      mergeAnnotations,
    }}>
      {children}
    </PdfContext.Provider>
  );
};

export const usePdfContext = () => {
  const context = useContext(PdfContext);
  if (!context) {
    throw new Error('usePdfContext must be used within a PdfProvider');
  }
  return context;
};
