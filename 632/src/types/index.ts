export type AlgorithmType = 'ssaa' | 'edaa' | 'msaa';
export type ComplexityLevel = 'simple' | 'medium' | 'complex';
export type ContentType = 'photo' | 'text' | 'illustration' | 'video';
export type SubpixelLayoutType = 'rgb' | 'bgr' | 'none';

export interface ProcessingParams {
  algorithm: AlgorithmType;
  threshold: number;
  intensity: number;
  sampleRate: number;
  kernelSize: number;
  edgeBlur: number;
  sharpness: number;
  textOptimization: boolean;
  subpixelLayout: SubpixelLayoutType;
  contentMode: ContentType;
  temporalAA: boolean;
  frameBlend: number;
}

export interface TemporalSettings {
  enabled: boolean;
  frameHistorySize: number;
  motionBlendFactor: number;
  staticBlendFactor: number;
  useClipping: boolean;
  jitterAmount: number;
}

export interface ComplexityInfo {
  level: ComplexityLevel;
  score: number;
  edgeDensity: number;
  colorVariance: number;
  detailLevel: number;
}

export interface ImageItem {
  id: string;
  file?: File;
  name: string;
  originalUrl: string;
  processedUrl?: string;
  originalData?: ImageData;
  processedData?: ImageData;
  status: 'pending' | 'processing' | 'completed' | 'error';
  progress: number;
  params?: ProcessingParams;
  error?: string;
  width?: number;
  height?: number;
  complexity?: ComplexityInfo;
  useAutoParams?: boolean;
  contentType?: ContentType;
  textConfidence?: number;
  isAnimated?: boolean;
  frameCount?: number;
}

export interface WorkerMessage {
  type: 'process' | 'cancel' | 'progress' | 'result' | 'error';
  id: string;
  imageData?: ImageData;
  params?: ProcessingParams;
  progress?: number;
  result?: ImageData;
  error?: string;
}

export interface AlgorithmInfo {
  id: AlgorithmType;
  name: string;
  description: string;
  icon: string;
}

export const ALGORITHMS: AlgorithmInfo[] = [
  {
    id: 'ssaa',
    name: 'SSAA',
    description: 'GPU超采样抗锯齿 - 高质量极速',
    icon: 'Zap'
  },
  {
    id: 'edaa',
    name: 'EDAA',
    description: '方向性边缘抗锯齿 - 针对性平滑',
    icon: 'Scan'
  },
  {
    id: 'msaa',
    name: 'MSAA',
    description: '多重采样抗锯齿 - 质量与速度平衡',
    icon: 'Grid3x3'
  }
];

export const DEFAULT_PARAMS: ProcessingParams = {
  algorithm: 'edaa',
  threshold: 50,
  intensity: 70,
  sampleRate: 2,
  kernelSize: 3,
  edgeBlur: 3,
  sharpness: 50,
  textOptimization: true,
  subpixelLayout: 'rgb',
  contentMode: 'photo',
  temporalAA: false,
  frameBlend: 30
};

export interface BatchResult {
  id: string;
  name: string;
  status: 'completed' | 'error';
  url?: string;
  error?: string;
}

export interface BatchTask {
  taskId: string;
  total: number;
  completed: number;
  results: BatchResult[];
}
