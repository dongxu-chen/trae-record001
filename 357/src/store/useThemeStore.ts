import { create } from 'zustand';
import { cloneDeep, isEqual, merge } from 'lodash';
import type { ChartTheme, ChartType, SavedTheme, RecommendedTheme } from '@/types/theme';
import { defaultTheme } from '@/utils/defaultTheme';
import {
  updateThemeWithColorPalette,
  mergeThemeWithDefaults,
  validateTheme,
  compressTheme,
  setNestedValue,
} from '@/utils/themeUtils';
import { convertThemeMode, isDarkTheme } from '@/utils/themeConverter';

const STORAGE_KEY = 'chart-theme-editor-library';

function loadSavedThemes(): SavedTheme[] {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      return JSON.parse(stored);
    }
  } catch {
    console.warn('Failed to load saved themes from localStorage');
  }
  return [];
}

function saveSavedThemes(themes: SavedTheme[]): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(themes));
  } catch {
    console.warn('Failed to save themes to localStorage');
  }
}

interface ThemeStore {
  theme: ChartTheme;
  chartType: ChartType;
  isDarkMode: boolean;
  savedThemes: SavedTheme[];
  history: ChartTheme[];
  historyIndex: number;
  isDirty: boolean;

  setColorPalette: (colors: string[]) => void;
  updateTheme: (path: string, value: unknown) => void;
  updateThemePartial: (partial: Partial<ChartTheme>) => void;
  setChartType: (type: ChartType) => void;
  toggleDarkMode: () => void;
  applyRecommendedTheme: (recommended: RecommendedTheme) => void;
  saveTheme: (name: string, description: string, isShared?: boolean) => boolean;
  applySavedTheme: (id: string) => boolean;
  deleteTheme: (id: string) => boolean;
  renameTheme: (id: string, name: string, description: string) => boolean;
  toggleFavorite: (id: string) => boolean;
  resetTheme: () => void;
  undo: () => void;
  redo: () => void;
  canUndo: () => boolean;
  canRedo: () => boolean;
  importTheme: (jsonString: string) => boolean;
  exportTheme: (format?: 'pretty' | 'minified') => string;
  exportLibrary: () => string;
  importLibrary: (jsonString: string) => boolean;
  saveToHistory: () => void;
}

const MAX_HISTORY = 50;

const initialSavedThemes = loadSavedThemes();
const initialTheme = cloneDeep(defaultTheme);
const initialIsDark = isDarkTheme(initialTheme);

export const useThemeStore = create<ThemeStore>((set, get) => ({
  theme: initialTheme,
  chartType: 'line',
  isDarkMode: initialIsDark,
  savedThemes: initialSavedThemes,
  history: [cloneDeep(initialTheme)],
  historyIndex: 0,
  isDirty: false,

  saveToHistory: () => {
    const { theme, history, historyIndex } = get();
    const currentHistory = history.slice(0, historyIndex + 1);
    const lastTheme = currentHistory[currentHistory.length - 1];

    if (!isEqual(theme, lastTheme)) {
      const newHistory = [...currentHistory, cloneDeep(theme)];
      if (newHistory.length > MAX_HISTORY) {
        newHistory.shift();
      }
      set({
        history: newHistory,
        historyIndex: newHistory.length - 1,
        isDirty: true,
      });
    }
  },

  setColorPalette: (colors: string[]) => {
    const { theme, saveToHistory } = get();
    const updatedTheme = updateThemeWithColorPalette(theme, colors);
    set({ theme: updatedTheme });
    setTimeout(saveToHistory, 0);
  },

  updateTheme: (path: string, value: unknown) => {
    const { theme, saveToHistory } = get();
    const updated = setNestedValue(theme as unknown as Record<string, unknown>, path, value) as unknown as ChartTheme;
    set({ theme: updated });
    setTimeout(saveToHistory, 0);
  },

  updateThemePartial: (partial: Partial<ChartTheme>) => {
    const { theme, saveToHistory } = get();
    const updated = merge(cloneDeep(theme), partial);
    set({ theme: updated });
    setTimeout(saveToHistory, 0);
  },

  setChartType: (type: ChartType) => {
    set({ chartType: type });
  },

  toggleDarkMode: () => {
    const { theme, isDarkMode, saveToHistory } = get();
    const newDarkMode = !isDarkMode;
    const convertedTheme = convertThemeMode(theme, newDarkMode);
    set({
      theme: convertedTheme,
      isDarkMode: newDarkMode,
    });
    setTimeout(saveToHistory, 0);
  },

  applyRecommendedTheme: (recommended: RecommendedTheme) => {
    const { saveToHistory } = get();
    const mergedTheme = mergeThemeWithDefaults(recommended.theme);
    const newDarkMode = isDarkTheme(mergedTheme);
    set({
      theme: mergedTheme,
      isDarkMode: newDarkMode,
    });
    setTimeout(saveToHistory, 0);
  },

  saveTheme: (name: string, description: string, isShared: boolean = false): boolean => {
    if (!name.trim()) return false;

    const { theme, savedThemes } = get();
    const newSavedTheme: SavedTheme = {
      id: `theme-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      name: name.trim(),
      description: description.trim(),
      theme: cloneDeep(theme),
      isFavorite: false,
      createdAt: Date.now(),
      updatedAt: Date.now(),
      isShared,
      author: '当前用户',
    };

    const updatedThemes = [...savedThemes, newSavedTheme];
    saveSavedThemes(updatedThemes);
    set({ savedThemes: updatedThemes });
    return true;
  },

  applySavedTheme: (id: string): boolean => {
    const { savedThemes, saveToHistory } = get();
    const saved = savedThemes.find((t) => t.id === id);
    if (!saved) return false;

    const newDarkMode = isDarkTheme(saved.theme);
    set({
      theme: cloneDeep(saved.theme),
      isDarkMode: newDarkMode,
    });
    setTimeout(saveToHistory, 0);
    return true;
  },

  deleteTheme: (id: string): boolean => {
    const { savedThemes } = get();
    const index = savedThemes.findIndex((t) => t.id === id);
    if (index === -1) return false;

    const updatedThemes = savedThemes.filter((t) => t.id !== id);
    saveSavedThemes(updatedThemes);
    set({ savedThemes: updatedThemes });
    return true;
  },

  renameTheme: (id: string, name: string, description: string): boolean => {
    if (!name.trim()) return false;

    const { savedThemes } = get();
    const index = savedThemes.findIndex((t) => t.id === id);
    if (index === -1) return false;

    const updatedThemes = [...savedThemes];
    updatedThemes[index] = {
      ...updatedThemes[index],
      name: name.trim(),
      description: description.trim(),
      updatedAt: Date.now(),
    };
    saveSavedThemes(updatedThemes);
    set({ savedThemes: updatedThemes });
    return true;
  },

  toggleFavorite: (id: string): boolean => {
    const { savedThemes } = get();
    const index = savedThemes.findIndex((t) => t.id === id);
    if (index === -1) return false;

    const updatedThemes = [...savedThemes];
    updatedThemes[index] = {
      ...updatedThemes[index],
      isFavorite: !updatedThemes[index].isFavorite,
      updatedAt: Date.now(),
    };
    saveSavedThemes(updatedThemes);
    set({ savedThemes: updatedThemes });
    return true;
  },

  resetTheme: () => {
    const resetTheme = cloneDeep(defaultTheme);
    set({
      theme: resetTheme,
      isDarkMode: false,
      history: [resetTheme],
      historyIndex: 0,
      isDirty: false,
    });
  },

  undo: () => {
    const { history, historyIndex } = get();
    if (historyIndex > 0) {
      const newIndex = historyIndex - 1;
      const newTheme = cloneDeep(history[newIndex]);
      set({
        theme: newTheme,
        historyIndex: newIndex,
        isDarkMode: isDarkTheme(newTheme),
      });
    }
  },

  redo: () => {
    const { history, historyIndex } = get();
    if (historyIndex < history.length - 1) {
      const newIndex = historyIndex + 1;
      const newTheme = cloneDeep(history[newIndex]);
      set({
        theme: newTheme,
        historyIndex: newIndex,
        isDarkMode: isDarkTheme(newTheme),
      });
    }
  },

  canUndo: () => {
    return get().historyIndex > 0;
  },

  canRedo: () => {
    return get().historyIndex < get().history.length - 1;
  },

  importTheme: (jsonString: string): boolean => {
    try {
      const parsed = JSON.parse(jsonString);
      if (!validateTheme(parsed)) {
        return false;
      }
      const mergedTheme = mergeThemeWithDefaults(parsed);
      const newDarkMode = isDarkTheme(mergedTheme);
      set({
        theme: mergedTheme,
        isDarkMode: newDarkMode,
        history: [cloneDeep(mergedTheme)],
        historyIndex: 0,
        isDirty: true,
      });
      return true;
    } catch {
      return false;
    }
  },

  exportTheme: (format: 'pretty' | 'minified' = 'pretty'): string => {
    const { theme } = get();
    return compressTheme(theme, format);
  },

  exportLibrary: (): string => {
    const { savedThemes } = get();
    return JSON.stringify(savedThemes, null, 2);
  },

  importLibrary: (jsonString: string): boolean => {
    try {
      const parsed = JSON.parse(jsonString);
      if (!Array.isArray(parsed)) return false;
      saveSavedThemes(parsed);
      set({ savedThemes: parsed });
      return true;
    } catch {
      return false;
    }
  },
}));

export const useTheme = () => useThemeStore((state) => state.theme);
export const useChartType = () => useThemeStore((state) => state.chartType);
export const useIsDarkMode = () => useThemeStore((state) => state.isDarkMode);
export const useSavedThemes = () => useThemeStore((state) => state.savedThemes);
export const useThemeActions = () => ({
  setColorPalette: useThemeStore((state) => state.setColorPalette),
  updateTheme: useThemeStore((state) => state.updateTheme),
  updateThemePartial: useThemeStore((state) => state.updateThemePartial),
  setChartType: useThemeStore((state) => state.setChartType),
  toggleDarkMode: useThemeStore((state) => state.toggleDarkMode),
  applyRecommendedTheme: useThemeStore((state) => state.applyRecommendedTheme),
  saveTheme: useThemeStore((state) => state.saveTheme),
  applySavedTheme: useThemeStore((state) => state.applySavedTheme),
  deleteTheme: useThemeStore((state) => state.deleteTheme),
  renameTheme: useThemeStore((state) => state.renameTheme),
  toggleFavorite: useThemeStore((state) => state.toggleFavorite),
  resetTheme: useThemeStore((state) => state.resetTheme),
  undo: useThemeStore((state) => state.undo),
  redo: useThemeStore((state) => state.redo),
  canUndo: useThemeStore((state) => state.canUndo),
  canRedo: useThemeStore((state) => state.canRedo),
  importTheme: useThemeStore((state) => state.importTheme),
  exportTheme: useThemeStore((state) => state.exportTheme),
  exportLibrary: useThemeStore((state) => state.exportLibrary),
  importLibrary: useThemeStore((state) => state.importLibrary),
});
