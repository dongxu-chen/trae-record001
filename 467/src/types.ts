export type ImageFormat = 'jpeg' | 'png' | 'webp';

export type OperationMode = 'compress' | 'convert';

export interface CompressionSettings {
  quality: number;
  format: ImageFormat;
  maxWidthOrHeight?: number;
}

export interface SmartSuggestion {
  format: ImageFormat;
  quality: number;
  reason: string;
  estimatedRatio: number;
}

export interface ImageItem {
  id: string;
  file: File;
  originalUrl: string;
  originalSize: number;
  originalFormat: ImageFormat;
  compressedUrl?: string;
  compressedSize?: number;
  status: 'pending' | 'analyzing' | 'compressing' | 'completed' | 'error';
  progress: number;
  error?: string;
  width: number;
  height: number;
  estimatedSize?: number;
  suggestion?: SmartSuggestion;
  hasAlpha: boolean;
  colorComplexity: 'low' | 'medium' | 'high';
}

export interface CompressProgress {
  imageId: string;
  progress: number;
}

export interface CompressResult {
  imageId: string;
  success: boolean;
  compressedBlob?: Blob;
  compressedSize: number;
  error?: string;
}

export interface WorkerMessage {
  type: 'compress' | 'convert' | 'analyze' | 'progress' | 'result' | 'error';
  imageId?: string;
  file?: File;
  settings?: CompressionSettings;
  width?: number;
  height?: number;
  progress?: number;
  success?: boolean;
  compressedBlob?: Blob;
  compressedSize?: number;
  error?: string;
  targetFormat?: ImageFormat;
  hasAlpha?: boolean;
  colorComplexity?: 'low' | 'medium' | 'high';
  sampleRatio?: number;
}
