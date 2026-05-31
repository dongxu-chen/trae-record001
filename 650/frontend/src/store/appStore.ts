import { create } from 'zustand';
import type { Prediction, TemporalResult, StatusType, SourceType, ModelType } from '../types';

export interface ActionResult {
  label: string;
  confidence: number;
  timestamp: number;
}

export interface ConnectionStatus {
  isConnected: boolean;
  isReconnecting: boolean;
  reconnectAttempts: number;
  lastError: string | null;
}

export interface TemporalAction {
  id: string;
  action: string;
  startTime: number;
  endTime: number;
  duration: number;
  avgConfidence: number;
  color: string;
}

export interface AppState {
  inputSource: SourceType;
  model: ModelType;
  confidenceThreshold: number;
  fps: number;
  isPlaying: boolean;
  isPaused: boolean;
  currentTimestamp: number;
  currentFps: number;
  latency: number;
  topActions: Prediction[];
  temporalActions: TemporalAction[];
  connection: ConnectionStatus;
  videoFile: File | null;
  recognitionStatus: StatusType;
  connectionStatus: StatusType;
  setInputSource: (source: SourceType) => void;
  setModel: (model: ModelType) => void;
  setConfidenceThreshold: (threshold: number) => void;
  setFps: (fps: number) => void;
  setPlaying: (playing: boolean) => void;
  setPaused: (paused: boolean) => void;
  setCurrentTimestamp: (timestamp: number) => void;
  setCurrentFps: (fps: number) => void;
  setLatency: (latency: number) => void;
  setTopActions: (actions: Prediction[]) => void;
  addTemporalAction: (action: TemporalResult) => void;
  setConnection: (status: Partial<ConnectionStatus>) => void;
  setVideoFile: (file: File | null) => void;
  setRecognitionStatus: (status: StatusType) => void;
  setConnectionStatus: (status: StatusType) => void;
  resetRecognition: () => void;
}

const ACTION_COLORS: Record<string, string> = {
  '跑步': '#FF7D00',
  '跳跃': '#00FFA3',
  '挥手': '#165DFF',
  '走路': '#722ED1',
  '站立': '#0FC6C2',
  '坐下': '#F53F3F',
  '蹲下': '#14C9C9',
  '其他': '#86909C',
};

const initialState: Omit<AppState, keyof {
  setInputSource: never;
  setModel: never;
  setConfidenceThreshold: never;
  setFps: never;
  setPlaying: never;
  setPaused: never;
  setCurrentTimestamp: never;
  setCurrentFps: never;
  setLatency: never;
  setTopActions: never;
  addTemporalAction: never;
  setConnection: never;
  setVideoFile: never;
  setRecognitionStatus: never;
  setConnectionStatus: never;
  resetRecognition: never;
}> = {
  inputSource: 'camera',
  model: 'timesformer',
  confidenceThreshold: 0.5,
  fps: 30,
  isPlaying: false,
  isPaused: false,
  currentTimestamp: 0,
  currentFps: 0,
  latency: 0,
  topActions: [],
  temporalActions: [],
  connection: {
    isConnected: false,
    isReconnecting: false,
    reconnectAttempts: 0,
    lastError: null,
  },
  videoFile: null,
  recognitionStatus: 'idle',
  connectionStatus: 'idle',
};

export const useAppStore = create<AppState>((set) => ({
  ...initialState,

  setInputSource: (source) => set({ inputSource: source }),
  setModel: (model) => set({ model }),
  setConfidenceThreshold: (threshold) => set({ confidenceThreshold: threshold }),
  setFps: (fps) => set({ fps }),
  setPlaying: (playing) => set({ isPlaying: playing }),
  setPaused: (paused) => set({ isPaused: paused }),
  setCurrentTimestamp: (timestamp) => set({ currentTimestamp: timestamp }),
  setCurrentFps: (fps) => set({ currentFps: fps }),
  setLatency: (latency) => set({ latency }),

  setTopActions: (actions) => {
    const { confidenceThreshold } = useAppStore.getState();
    const filtered = actions.filter(a => a.confidence >= confidenceThreshold);
    set({ topActions: filtered.slice(0, 3) });
  },

  addTemporalAction: (action) => {
    const color = ACTION_COLORS[action.action] || '#86909C';
    const temporalAction: TemporalAction = {
      id: `${action.action}-${Date.now()}`,
      action: action.action,
      startTime: action.startTime,
      endTime: action.endTime,
      duration: action.duration,
      avgConfidence: action.avgConfidence,
      color,
    };
    set((state) => ({
      temporalActions: [...state.temporalActions, temporalAction],
    }));
  },

  setConnection: (status) =>
    set((state) => ({ connection: { ...state.connection, ...status } })),

  setVideoFile: (file) => set({ videoFile: file }),

  setRecognitionStatus: (status) => {
    set({
      recognitionStatus: status,
      isPlaying: status === 'running',
      isPaused: status === 'paused',
    });
  },

  setConnectionStatus: (status) => {
    set({ connectionStatus: status });
  },

  resetRecognition: () => {
    set({
      currentTimestamp: 0,
      topActions: [],
      temporalActions: [],
      recognitionStatus: 'idle',
    });
  },
}));
