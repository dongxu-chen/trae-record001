export type MessageType = 'start' | 'stop' | 'pause' | 'resume' | 'config' | 'result' | 'temporal' | 'frame' | 'status' | 'error';

export type SourceType = 'camera' | 'file';

export type ModelType = 'timesformer' | 'videomae';

export type StatusType = 'idle' | 'connecting' | 'running' | 'paused' | 'error';

export interface Prediction {
  action: string;
  confidence: number;
  boundingBox?: [number, number, number, number];
}

export interface RecognitionResult {
  type: 'result';
  timestamp: number;
  frameIndex: number;
  predictions: Prediction[];
  fps: number;
  latency: number;
}

export interface TemporalResult {
  type: 'temporal';
  action: string;
  startTime: number;
  endTime: number;
  duration: number;
  avgConfidence: number;
}

export interface StatusUpdate {
  type: 'status';
  status: StatusType;
  message?: string;
}

export interface StartMessage {
  type: 'start';
  source: SourceType;
  sourcePath?: string;
}

export interface StopMessage {
  type: 'stop';
}

export interface PauseMessage {
  type: 'pause';
}

export interface ResumeMessage {
  type: 'resume';
}

export interface ConfigMessage {
  type: 'config';
  model: ModelType;
  confidenceThreshold: number;
  fps: number;
}

export type ClientMessage = StartMessage | StopMessage | PauseMessage | ResumeMessage | ConfigMessage;

export type ServerMessage = RecognitionResult | TemporalResult | StatusUpdate;

export const ACTION_COLORS: Record<string, string> = {
  '跑步': '#FF7D00',
  '跳跃': '#00FFA3',
  '挥手': '#165DFF',
  '走路': '#722ED1',
  '站立': '#0FC6C2',
  '坐下': '#F53F3F',
  '躺下': '#14C9C9',
  '跌倒': '#FF4D4F',
  '喝水': '#168CFF',
  '吃饭': '#FF7A45',
};
