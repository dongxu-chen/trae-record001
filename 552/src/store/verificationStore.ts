import { create } from 'zustand';
import type { VerifyResponse, VerifyOptions, VerificationRecord, FileInfo, BatchVerifyResponse, BatchFileStatus } from '../../shared';

interface VerificationState {
  currentFile: File | null;
  fileInfo: FileInfo | null;
  verifyOptions: VerifyOptions;
  verificationResult: VerifyResponse | null;
  verificationHistory: VerificationRecord[];
  isVerifying: boolean;
  isLoading: boolean;
  error: string | null;
  progress: number;
  currentStep: string;
  batchFiles: File[];
  batchResult: BatchVerifyResponse | null;
  isBatchVerifying: boolean;
  setCurrentFile: (file: File | null) => void;
  setFileInfo: (info: FileInfo | null) => void;
  setVerifyOptions: (options: Partial<VerifyOptions>) => void;
  setVerificationResult: (result: VerifyResponse | null) => void;
  addVerificationToHistory: (record: VerificationRecord) => void;
  removeFromHistory: (id: string) => void;
  clearHistory: () => void;
  setIsVerifying: (value: boolean) => void;
  setIsLoading: (value: boolean) => void;
  setError: (error: string | null) => void;
  setProgress: (progress: number) => void;
  setCurrentStep: (step: string) => void;
  resetState: () => void;
  loadHistoryFromStorage: () => void;
  setBatchFiles: (files: File[]) => void;
  addBatchFiles: (files: File[]) => void;
  removeBatchFile: (index: number) => void;
  clearBatchFiles: () => void;
  setBatchResult: (result: BatchVerifyResponse | null) => void;
  setIsBatchVerifying: (value: boolean) => void;
}

const defaultVerifyOptions: VerifyOptions = {
  verifyLevel: 'standard',
  complianceStandard: 'cn-es',
  checkRevocation: true,
  checkTimestamp: true,
};

const HISTORY_STORAGE_KEY = 'esv_verification_history';
const MAX_HISTORY_ITEMS = 100;

export const useVerificationStore = create<VerificationState>((set, get) => ({
  currentFile: null,
  fileInfo: null,
  verifyOptions: defaultVerifyOptions,
  verificationResult: null,
  verificationHistory: [],
  isVerifying: false,
  isLoading: false,
  error: null,
  progress: 0,
  currentStep: '',
  batchFiles: [],
  batchResult: null,
  isBatchVerifying: false,

  setCurrentFile: (file) => set({ currentFile: file }),
  setFileInfo: (info) => set({ fileInfo: info }),
  setVerifyOptions: (options) =>
    set((state) => ({
      verifyOptions: { ...state.verifyOptions, ...options },
    })),
  setVerificationResult: (result) => set({ verificationResult: result }),

  addVerificationToHistory: (record) => {
    const currentHistory = get().verificationHistory;
    const newHistory = [record, ...currentHistory].slice(0, MAX_HISTORY_ITEMS);
    set({ verificationHistory: newHistory });
    localStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(newHistory));
  },

  removeFromHistory: (id) => {
    const newHistory = get().verificationHistory.filter((item) => item.id !== id);
    set({ verificationHistory: newHistory });
    localStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(newHistory));
  },

  clearHistory: () => {
    set({ verificationHistory: [] });
    localStorage.removeItem(HISTORY_STORAGE_KEY);
  },

  setIsVerifying: (value) => set({ isVerifying: value }),
  setIsLoading: (value) => set({ isLoading: value }),
  setError: (error) => set({ error }),
  setProgress: (progress) => set({ progress }),
  setCurrentStep: (step) => set({ currentStep: step }),

  resetState: () =>
    set({
      currentFile: null,
      fileInfo: null,
      verificationResult: null,
      isVerifying: false,
      isLoading: false,
      error: null,
      progress: 0,
      currentStep: '',
      verifyOptions: defaultVerifyOptions,
    }),

  loadHistoryFromStorage: () => {
    try {
      const stored = localStorage.getItem(HISTORY_STORAGE_KEY);
      if (stored) {
        const history = JSON.parse(stored) as VerificationRecord[];
        set({ verificationHistory: history });
      }
    } catch (e) {
      console.error('Failed to load verification history:', e);
    }
  },

  setBatchFiles: (files) => set({ batchFiles: files }),
  addBatchFiles: (files) => set((state) => {
    const existing = new Set(state.batchFiles.map(f => f.name + f.size));
    const newFiles = files.filter(f => !existing.has(f.name + f.size));
    return { batchFiles: [...state.batchFiles, ...newFiles] };
  }),
  removeBatchFile: (index) => set((state) => ({
    batchFiles: state.batchFiles.filter((_, i) => i !== index),
  })),
  clearBatchFiles: () => set({ batchFiles: [], batchResult: null }),
  setBatchResult: (result) => set({ batchResult: result }),
  setIsBatchVerifying: (value) => set({ isBatchVerifying: value }),
}));
