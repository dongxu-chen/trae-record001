import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { QRStyle, QRFormData, SavedQRCode, DynamicCode } from '@/types';
import { defaultStyle, defaultFormData } from '@/types';

interface AppState {
  style: QRStyle;
  formData: QRFormData;
  savedQRCodes: SavedQRCode[];
  currentContent: string;
  setStyle: (style: Partial<QRStyle>) => void;
  setFormData: (data: Partial<QRFormData>) => void;
  setCurrentContent: (content: string) => void;
  saveQRCode: (code: Omit<SavedQRCode, 'id' | 'createdAt'>) => void;
  deleteQRCode: (id: string) => void;
  resetStyle: () => void;
  resetFormData: () => void;
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      style: { ...defaultStyle },
      formData: { ...defaultFormData },
      savedQRCodes: [],
      currentContent: '',

      setStyle: (newStyle) =>
        set((state) => ({
          style: { ...state.style, ...newStyle },
        })),

      setFormData: (newData) =>
        set((state) => ({
          formData: { ...state.formData, ...newData },
        })),

      setCurrentContent: (content) =>
        set({
          currentContent: content,
        }),

      saveQRCode: (code) =>
        set((state) => ({
          savedQRCodes: [
            {
              ...code,
              id: `qr_${Date.now()}`,
              createdAt: new Date().toISOString(),
            },
            ...state.savedQRCodes,
          ],
        })),

      deleteQRCode: (id) =>
        set((state) => ({
          savedQRCodes: state.savedQRCodes.filter((code) => code.id !== id),
        })),

      resetStyle: () =>
        set({
          style: { ...defaultStyle },
        }),

      resetFormData: () =>
        set({
          formData: { ...defaultFormData },
        }),
    }),
    {
      name: 'qr-code-storage',
      partialize: (state) => ({
        style: state.style,
        savedQRCodes: state.savedQRCodes,
      }),
    }
  )
);

interface AuthState {
  token: string | null;
  user: { id: string; email: string; name: string } | null;
  login: (token: string, user: { id: string; email: string; name: string }) => void;
  logout: () => void;
  isAuthenticated: () => boolean;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      token: null,
      user: null,

      login: (token, user) =>
        set({
          token,
          user,
        }),

      logout: () =>
        set({
          token: null,
          user: null,
        }),

      isAuthenticated: () => !!get().token,
    }),
    {
      name: 'auth-storage',
    }
  )
);

interface DynamicCodeState {
  codes: DynamicCode[];
  loading: boolean;
  error: string | null;
  setCodes: (codes: DynamicCode[]) => void;
  addCode: (code: DynamicCode) => void;
  updateCode: (id: string, updates: Partial<DynamicCode>) => void;
  deleteCode: (id: string) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
}

export const useDynamicCodeStore = create<DynamicCodeState>((set) => ({
  codes: [],
  loading: false,
  error: null,

  setCodes: (codes) => set({ codes }),
  addCode: (code) => set((state) => ({ codes: [code, ...state.codes] })),
  updateCode: (id, updates) =>
    set((state) => ({
      codes: state.codes.map((code) =>
        code.id === id ? { ...code, ...updates } : code
      ),
    })),
  deleteCode: (id) =>
    set((state) => ({
      codes: state.codes.filter((code) => code.id !== id),
    })),
  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error }),
}));
