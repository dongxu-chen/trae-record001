import Dexie from 'dexie';
import type { Table } from 'dexie';

export interface Formula {
  id?: number;
  title: string;
  latex: string;
  category: string;
  thumbnail: string;
  createdAt: Date;
  updatedAt: Date;
}

export interface Settings {
  id?: number;
  mathpixAppId: string;
  mathpixAppKey: string;
  editorMode: 'visual' | 'handwriting';
  exportFormat: 'png' | 'svg' | 'latex';
  theme: 'dark' | 'light';
}

class FormulaDB extends Dexie {
  formulas!: Table<Formula, number>;
  settings!: Table<Settings, number>;

  constructor() {
    super('MathFormulaEditor');
    this.version(1).stores({
      formulas: '++id, title, latex, category, createdAt, updatedAt',
      settings: '++id',
    });
  }
}

export const db = new FormulaDB();

export async function saveFormula(formula: Omit<Formula, 'id'>): Promise<number> {
  return await db.formulas.add(formula);
}

export async function getAllFormulas(): Promise<Formula[]> {
  return await db.formulas.orderBy('updatedAt').reverse().toArray();
}

export async function deleteFormula(id: number): Promise<void> {
  await db.formulas.delete(id);
}

export async function updateFormula(id: number, changes: Partial<Formula>): Promise<void> {
  await db.formulas.update(id, changes);
}

export async function getSettings(): Promise<Settings | undefined> {
  return await db.settings.toCollection().first();
}

export async function saveSettings(settings: Omit<Settings, 'id'>): Promise<void> {
  const existing = await getSettings();
  if (existing && existing.id) {
    await db.settings.update(existing.id, settings);
  } else {
    await db.settings.add(settings);
  }
}
