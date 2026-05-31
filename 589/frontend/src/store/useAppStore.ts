import { create } from 'zustand';
import type { Product, PriceAlert, Favorite, AlertNotification } from '../types';

interface AppState {
  searchQuery: string;
  setSearchQuery: (query: string) => void;

  selectedProduct: Product | null;
  setSelectedProduct: (product: Product | null) => void;

  alerts: PriceAlert[];
  setAlerts: (alerts: PriceAlert[]) => void;
  addAlert: (alert: PriceAlert) => void;
  removeAlert: (alertId: string) => void;

  favorites: Favorite[];
  setFavorites: (favorites: Favorite[]) => void;
  addFavorite: (favorite: Favorite) => void;
  removeFavorite: (favoriteId: string) => void;

  notifications: AlertNotification[];
  addNotification: (notification: AlertNotification) => void;
  removeNotification: (id: string) => void;
  clearNotifications: () => void;

  isLoading: boolean;
  setIsLoading: (loading: boolean) => void;

  sidebarOpen: boolean;
  setSidebarOpen: (open: boolean) => void;
}

export const useAppStore = create<AppState>((set) => ({
  searchQuery: '',
  setSearchQuery: (query) => set({ searchQuery: query }),

  selectedProduct: null,
  setSelectedProduct: (product) => set({ selectedProduct: product }),

  alerts: [],
  setAlerts: (alerts) => set({ alerts }),
  addAlert: (alert) => set((state) => ({ alerts: [alert, ...state.alerts] })),
  removeAlert: (alertId) => set((state) => ({
    alerts: state.alerts.filter((a) => a.id !== alertId),
  })),

  favorites: [],
  setFavorites: (favorites) => set({ favorites }),
  addFavorite: (favorite) => set((state) => ({ favorites: [favorite, ...state.favorites] })),
  removeFavorite: (favoriteId) => set((state) => ({
    favorites: state.favorites.filter((f) => f.id !== favoriteId),
  })),

  notifications: [],
  addNotification: (notification) => set((state) => ({
    notifications: [notification, ...state.notifications].slice(0, 50),
  })),
  removeNotification: (id) => set((state) => ({
    notifications: state.notifications.filter((n) => n.alertId !== id),
  })),
  clearNotifications: () => set({ notifications: [] }),

  isLoading: false,
  setIsLoading: (loading) => set({ isLoading: loading }),

  sidebarOpen: false,
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
}));
