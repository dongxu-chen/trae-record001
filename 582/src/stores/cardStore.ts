import { create } from 'zustand';
import type { CardData } from '@/types';

interface CardState {
  cards: CardData[];
  currentCard: CardData | null;
  loading: boolean;
  error: string | null;
  fetchCards: () => Promise<void>;
  fetchCard: (id: string) => Promise<void>;
  createCard: (card: Partial<CardData>) => Promise<CardData>;
  updateCard: (id: string, card: Partial<CardData>) => Promise<void>;
  deleteCard: (id: string) => Promise<void>;
  setCurrentCard: (card: CardData | null) => void;
  resetCurrentCard: () => void;
}

const API_BASE = '/api/cards';

export const useCardStore = create<CardState>((set, get) => ({
  cards: [],
  currentCard: null,
  loading: false,
  error: null,

  fetchCards: async () => {
    set({ loading: true, error: null });
    try {
      const res = await fetch(API_BASE);
      if (!res.ok) throw new Error('Failed to fetch cards');
      const data = await res.json();
      set({ cards: data.data ?? data, loading: false });
    } catch (err: any) {
      set({ error: err.message, loading: false });
    }
  },

  fetchCard: async (id: string) => {
    set({ loading: true, error: null });
    try {
      const res = await fetch(`${API_BASE}/${id}`);
      if (!res.ok) throw new Error('Failed to fetch card');
      const data = await res.json();
      set({ currentCard: data.data ?? data, loading: false });
    } catch (err: any) {
      set({ error: err.message, loading: false });
    }
  },

  createCard: async (card: Partial<CardData>) => {
    set({ loading: true, error: null });
    try {
      const res = await fetch(API_BASE, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(card),
      });
      if (!res.ok) throw new Error('Failed to create card');
      const data = await res.json();
      const newCard = data.data ?? data;
      set((state) => ({
        cards: [...state.cards, newCard],
        currentCard: newCard,
        loading: false,
      }));
      return newCard;
    } catch (err: any) {
      set({ error: err.message, loading: false });
      throw err;
    }
  },

  updateCard: async (id: string, card: Partial<CardData>) => {
    set({ error: null });
    try {
      const res = await fetch(`${API_BASE}/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(card),
      });
      if (!res.ok) throw new Error('Failed to update card');
      const data = await res.json();
      const updated = data.data ?? data;
      set((state) => ({
        cards: state.cards.map((c) => (c.id === id ? updated : c)),
        currentCard: state.currentCard?.id === id ? updated : state.currentCard,
      }));
    } catch (err: any) {
      set({ error: err.message });
    }
  },

  deleteCard: async (id: string) => {
    set({ error: null });
    try {
      const res = await fetch(`${API_BASE}/${id}`, { method: 'DELETE' });
      if (!res.ok) throw new Error('Failed to delete card');
      set((state) => ({
        cards: state.cards.filter((c) => c.id !== id),
        currentCard: state.currentCard?.id === id ? null : state.currentCard,
      }));
    } catch (err: any) {
      set({ error: err.message });
    }
  },

  setCurrentCard: (card: CardData | null) => set({ currentCard: card }),

  resetCurrentCard: () => set({ currentCard: null }),
}));
