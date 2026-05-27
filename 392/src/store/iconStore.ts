import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { Icon, IconLibrary, ViewMode, FavoriteItem, RecentItem, UploadedIcon } from '../types';
import { fontawesomeIcons } from '../data/fontawesome';
import { materialIcons } from '../data/material';

interface IconState {
  currentLibrary: IconLibrary;
  selectedCategory: string | null;
  searchQuery: string;
  selectedIcons: Set<string>;
  activeIconId: string | null;
  currentColor: string;
  currentSize: number;
  viewMode: ViewMode;
  favorites: Record<string, FavoriteItem>;
  recent: Record<string, RecentItem>;
  uploadedIcons: UploadedIcon[];
  showFavoritesPanel: boolean;
  showRecentPanel: boolean;
  showUploadModal: boolean;
  showBrandRecognitionModal: boolean;
  showStylePanel: boolean;
  showReplacementPanel: boolean;
  copyFormat: 'svg' | 'jsx';
  useFilterMode: boolean;
  downloadProgress: number;
  isDownloading: boolean;
  
  setCurrentLibrary: (library: IconLibrary) => void;
  setSelectedCategory: (category: string | null) => void;
  setSearchQuery: (query: string) => void;
  toggleIconSelection: (iconId: string) => void;
  clearSelection: () => void;
  setActiveIcon: (iconId: string | null) => void;
  setCurrentColor: (color: string) => void;
  setCurrentSize: (size: number) => void;
  setViewMode: (mode: ViewMode) => void;
  toggleFavorite: (iconId: string) => void;
  addToRecent: (iconId: string) => void;
  addUploadedIcon: (icon: UploadedIcon) => void;
  removeUploadedIcon: (iconId: string) => void;
  setShowFavoritesPanel: (show: boolean) => void;
  setShowRecentPanel: (show: boolean) => void;
  setShowUploadModal: (show: boolean) => void;
  setShowBrandRecognitionModal: (show: boolean) => void;
  setShowStylePanel: (show: boolean) => void;
  setShowReplacementPanel: (show: boolean) => void;
  setCopyFormat: (format: 'svg' | 'jsx') => void;
  setUseFilterMode: (use: boolean) => void;
  setDownloadProgress: (progress: number) => void;
  setIsDownloading: (downloading: boolean) => void;
}

export const useIconStore = create<IconState>()(
  persist(
    (set) => ({
      currentLibrary: 'fontawesome',
      selectedCategory: null,
      searchQuery: '',
      selectedIcons: new Set(),
      activeIconId: null,
      currentColor: '#4F46E5',
      currentSize: 24,
      viewMode: 'grid',
      favorites: {},
      recent: {},
      uploadedIcons: [],
      showFavoritesPanel: true,
      showRecentPanel: true,
      showUploadModal: false,
      showBrandRecognitionModal: false,
      showStylePanel: false,
      showReplacementPanel: false,
      copyFormat: 'svg',
      useFilterMode: false,
      downloadProgress: 0,
      isDownloading: false,
      
      setCurrentLibrary: (library) => set({ currentLibrary: library, selectedCategory: null }),
      setSelectedCategory: (category) => set({ selectedCategory: category }),
      setSearchQuery: (query) => set({ searchQuery: query }),
      toggleIconSelection: (iconId) => set((state) => {
        const newSet = new Set(state.selectedIcons);
        if (newSet.has(iconId)) {
          newSet.delete(iconId);
        } else {
          newSet.add(iconId);
        }
        return { selectedIcons: newSet };
      }),
      clearSelection: () => set({ selectedIcons: new Set() }),
      setActiveIcon: (iconId) => set({ activeIconId: iconId }),
      setCurrentColor: (color) => set({ currentColor: color }),
      setCurrentSize: (size) => set({ currentSize: size }),
      setViewMode: (mode) => set({ viewMode: mode }),
      toggleFavorite: (iconId) => set((state) => {
        const newFavorites = { ...state.favorites };
        if (newFavorites[iconId]) {
          delete newFavorites[iconId];
        } else {
          newFavorites[iconId] = { iconId, addedAt: Date.now() };
        }
        return { favorites: newFavorites };
      }),
      addToRecent: (iconId) => set((state) => {
        const newRecent = { ...state.recent };
        newRecent[iconId] = { iconId, usedAt: Date.now() };
        return { recent: newRecent };
      }),
      addUploadedIcon: (icon) => set((state) => ({
        uploadedIcons: [...state.uploadedIcons, icon]
      })),
      removeUploadedIcon: (iconId) => set((state) => ({
        uploadedIcons: state.uploadedIcons.filter(i => i.id !== iconId)
      })),
      setShowFavoritesPanel: (show) => set({ showFavoritesPanel: show }),
      setShowRecentPanel: (show) => set({ showRecentPanel: show }),
      setShowUploadModal: (show) => set({ showUploadModal: show }),
      setShowBrandRecognitionModal: (show) => set({ showBrandRecognitionModal: show }),
      setShowStylePanel: (show) => set({ showStylePanel: show }),
      setShowReplacementPanel: (show) => set({ showReplacementPanel: show }),
      setCopyFormat: (format) => set({ copyFormat: format }),
      setUseFilterMode: (use) => set({ useFilterMode: use }),
      setDownloadProgress: (progress) => set({ downloadProgress: progress }),
      setIsDownloading: (downloading) => set({ isDownloading: downloading }),
    }),
    {
      name: 'icon-browser-storage',
      partialize: (state) => ({
        favorites: state.favorites,
        recent: state.recent,
        uploadedIcons: state.uploadedIcons,
        currentLibrary: state.currentLibrary,
        viewMode: state.viewMode,
        currentColor: state.currentColor,
      }),
    }
  )
);

export const getAllIcons = (): Icon[] => {
  return [...fontawesomeIcons, ...materialIcons];
};

export const getIconsByLibrary = (library: IconLibrary): Icon[] => {
  const state = useIconStore.getState();
  if (library === 'custom') {
    return state.uploadedIcons;
  }
  if (library === 'fontawesome') {
    return fontawesomeIcons;
  }
  return materialIcons;
};

export const getFilteredIcons = (): Icon[] => {
  const state = useIconStore.getState();
  let icons = getIconsByLibrary(state.currentLibrary);
  
  if (state.selectedCategory) {
    icons = icons.filter(icon => icon.category === state.selectedCategory);
  }
  
  if (state.searchQuery.trim()) {
    const query = state.searchQuery.toLowerCase();
    icons = icons.filter(icon => 
      icon.name.toLowerCase().includes(query) ||
      icon.tags.some(tag => tag.toLowerCase().includes(query))
    );
  }
  
  return icons;
};

export const getIconById = (iconId: string): Icon | undefined => {
  const state = useIconStore.getState();
  const allIcons = [...fontawesomeIcons, ...materialIcons, ...state.uploadedIcons];
  return allIcons.find(icon => icon.id === iconId);
};
