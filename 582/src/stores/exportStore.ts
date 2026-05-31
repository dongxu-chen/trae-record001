import { create } from 'zustand';
import type { CardData, PrintLayoutOptions } from '@/types';

interface ExportState {
  exporting: boolean;
  generating: boolean;
  progress: number;
  downloadUrl: string | null;
  error: string | null;
  exportCard: (cardId: string, format: string, resolution: number) => Promise<void>;
  exportBatch: (cardIds: string[], format: string, resolution: number) => Promise<void>;
  exportPrint: (cardIds: string[], layout: PrintLayoutOptions) => Promise<void>;
  exportJson: (cardIds: string[]) => Promise<void>;
  batchGenerate: (cards: Array<Partial<CardData> & { name: string; templateId: string }>) => Promise<CardData[]>;
}

export const useExportStore = create<ExportState>((set) => ({
  exporting: false,
  generating: false,
  progress: 0,
  downloadUrl: null,
  error: null,

  exportCard: async (cardId: string, format: string, resolution: number) => {
    set({ exporting: true, error: null });
    try {
      const res = await fetch(`/api/export/card/${cardId}?format=${format}&resolution=${resolution}`, {
        method: 'POST',
      });
      if (!res.ok) throw new Error('Failed to export card');
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      set({ downloadUrl: url, exporting: false });
      const a = document.createElement('a');
      a.href = url;
      a.download = `card-${cardId}.${format}`;
      a.click();
    } catch (err: any) {
      set({ error: err.message, exporting: false });
    }
  },

  exportBatch: async (cardIds: string[], format: string, resolution: number) => {
    set({ exporting: true, error: null, progress: 0 });
    try {
      const res = await fetch('/api/export/batch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cardIds, format, resolution }),
      });
      if (!res.ok) throw new Error('Failed to export batch');
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      set({ downloadUrl: url, exporting: false, progress: 100 });
      const a = document.createElement('a');
      a.href = url;
      a.download = `cards-batch.zip`;
      a.click();
    } catch (err: any) {
      set({ error: err.message, exporting: false });
    }
  },

  exportPrint: async (cardIds: string[], layout: PrintLayoutOptions) => {
    set({ exporting: true, error: null, progress: 0 });
    try {
      const res = await fetch('/api/export/print', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...layout, cardIds }),
      });
      if (!res.ok) throw new Error('Failed to export print');
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      set({ downloadUrl: url, exporting: false, progress: 100 });
      const a = document.createElement('a');
      a.href = url;
      a.download = `cards-print-300dpi.pdf`;
      a.click();
    } catch (err: any) {
      set({ error: err.message, exporting: false });
    }
  },

  exportJson: async (cardIds: string[]) => {
    set({ exporting: true, error: null });
    try {
      const res = await fetch('/api/export/json', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cardIds }),
      });
      if (!res.ok) throw new Error('Failed to export JSON');
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      set({ downloadUrl: url, exporting: false });
      const a = document.createElement('a');
      a.href = url;
      a.download = 'cards-data.json';
      a.click();
    } catch (err: any) {
      set({ error: err.message, exporting: false });
    }
  },

  batchGenerate: async (cards: Array<Partial<CardData> & { name: string; templateId: string }>) => {
    set({ generating: true, error: null, progress: 0 });
    try {
      const startTime = Date.now();
      const res = await fetch('/api/export/generate/batch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cards }),
      });
      if (!res.ok) throw new Error('Failed to generate batch');
      const result = await res.json();
      const duration = ((Date.now() - startTime) / 1000).toFixed(2);
      set({ generating: false, progress: 100 });
      console.log(`⚡ 批量生成完成: ${result.count} 张, 用时 ${duration}s`);
      return result.data;
    } catch (err: any) {
      set({ error: err.message, generating: false });
      throw err;
    }
  },
}));
