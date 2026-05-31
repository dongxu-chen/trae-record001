import { create } from 'zustand';
import type { CardTemplate } from '@/types';

interface TemplateState {
  templates: CardTemplate[];
  currentTemplate: CardTemplate | null;
  loading: boolean;
  error: string | null;
  fetchTemplates: () => Promise<void>;
  fetchTemplate: (id: string) => Promise<void>;
  createTemplate: (template: Partial<CardTemplate>) => Promise<CardTemplate>;
  updateTemplate: (id: string, template: Partial<CardTemplate>) => Promise<void>;
  deleteTemplate: (id: string) => Promise<void>;
  setCurrentTemplate: (template: CardTemplate | null) => void;
}

const API_BASE = '/api/templates';

export const useTemplateStore = create<TemplateState>((set) => ({
  templates: [],
  currentTemplate: null,
  loading: false,
  error: null,

  fetchTemplates: async () => {
    set({ loading: true, error: null });
    try {
      const res = await fetch(API_BASE);
      if (!res.ok) throw new Error('Failed to fetch templates');
      const data = await res.json();
      set({ templates: data.data ?? data, loading: false });
    } catch (err: any) {
      set({ error: err.message, loading: false });
    }
  },

  fetchTemplate: async (id: string) => {
    set({ loading: true, error: null });
    try {
      const res = await fetch(`${API_BASE}/${id}`);
      if (!res.ok) throw new Error('Failed to fetch template');
      const data = await res.json();
      set({ currentTemplate: data.data ?? data, loading: false });
    } catch (err: any) {
      set({ error: err.message, loading: false });
    }
  },

  createTemplate: async (template: Partial<CardTemplate>) => {
    set({ loading: true, error: null });
    try {
      const res = await fetch(API_BASE, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(template),
      });
      if (!res.ok) throw new Error('Failed to create template');
      const data = await res.json();
      const newTemplate = data.data ?? data;
      set((state) => ({
        templates: [...state.templates, newTemplate],
        currentTemplate: newTemplate,
        loading: false,
      }));
      return newTemplate;
    } catch (err: any) {
      set({ error: err.message, loading: false });
      throw err;
    }
  },

  updateTemplate: async (id: string, template: Partial<CardTemplate>) => {
    set({ error: null });
    try {
      const res = await fetch(`${API_BASE}/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(template),
      });
      if (!res.ok) throw new Error('Failed to update template');
      const data = await res.json();
      const updated = data.data ?? data;
      set((state) => ({
        templates: state.templates.map((t) => (t.id === id ? updated : t)),
        currentTemplate: state.currentTemplate?.id === id ? updated : state.currentTemplate,
      }));
    } catch (err: any) {
      set({ error: err.message });
    }
  },

  deleteTemplate: async (id: string) => {
    set({ error: null });
    try {
      const res = await fetch(`${API_BASE}/${id}`, { method: 'DELETE' });
      if (!res.ok) throw new Error('Failed to delete template');
      set((state) => ({
        templates: state.templates.filter((t) => t.id !== id),
        currentTemplate: state.currentTemplate?.id === id ? null : state.currentTemplate,
      }));
    } catch (err: any) {
      set({ error: err.message });
    }
  },

  setCurrentTemplate: (template: CardTemplate | null) => set({ currentTemplate: template }),
}));
