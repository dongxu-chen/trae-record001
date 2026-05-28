export interface ScanRecord {
  id: string;
  content: string;
  type: 'qrcode' | 'barcode' | 'manual';
  format?: string;
  timestamp: number;
  note?: string;
}

export interface ScanSettings {
  continuousMode: boolean;
  torchEnabled: boolean;
  lowLightEnhance: boolean;
  frontCamera: boolean;
  exportFormat: 'csv' | 'json';
  autoSave: boolean;
  vibrateOnSuccess: boolean;
}

export interface ScanResult {
  success: boolean;
  content: string;
  format: string;
}

export interface WorkerMessage {
  type: 'scan' | 'init';
  imageData?: ImageData;
  enableLowLight?: boolean;
}

export interface WorkerResponse {
  success: boolean;
  content?: string;
  format?: string;
  error?: string;
}

export const DEFAULT_SETTINGS: ScanSettings = {
  continuousMode: false,
  torchEnabled: false,
  lowLightEnhance: false,
  frontCamera: false,
  exportFormat: 'json',
  autoSave: true,
  vibrateOnSuccess: true,
};
