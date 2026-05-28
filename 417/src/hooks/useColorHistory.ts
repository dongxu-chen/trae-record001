import { openDB, DBSchema, IDBPDatabase } from 'idb';
import type { ColorHistory } from '@/types';

interface ColorLabDBSchema extends DBSchema {
  colorHistory: {
    key: string;
    value: ColorHistory;
    indexes: { timestamp: number; project: string };
  };
}

const DB_NAME = 'ColorLabDB';
const DB_VERSION = 2;
const STORE_NAME = 'colorHistory';
const MAX_RECORDS = 100;

let dbPromise: Promise<IDBPDatabase<ColorLabDBSchema>> | null = null;

function getDB(): Promise<IDBPDatabase<ColorLabDBSchema>> {
  if (!dbPromise) {
    dbPromise = openDB<ColorLabDBSchema>(DB_NAME, DB_VERSION, {
      upgrade(database, oldVersion) {
        if (!database.objectStoreNames.contains(STORE_NAME)) {
          const store = database.createObjectStore(STORE_NAME, { keyPath: 'id' });
          store.createIndex('timestamp', 'timestamp');
          store.createIndex('project', 'project');
        } else if (oldVersion < 2) {
          const store = database.transaction(STORE_NAME, 'readonly').objectStore(STORE_NAME);
          if (!store.indexNames.contains('project')) {
            database.createIndex(STORE_NAME, 'project', 'project');
          }
        }
      },
    });
  }
  return dbPromise;
}

function generateId(): string {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

export async function addColorToHistory(
  hex: string,
  rgb: { r: number; g: number; b: number },
  project?: string,
): Promise<void> {
  const db = await getDB();
  const tx = db.transaction(STORE_NAME, 'readwrite');
  const store = tx.objectStore(STORE_NAME);
  const record: ColorHistory = {
    id: generateId(),
    hex,
    rgb,
    timestamp: Date.now(),
    project,
  };
  await store.put(record);

  const count = await store.count();
  if (count > MAX_RECORDS) {
    const records = await store.index('timestamp').getAll();
    const toDelete = records
      .sort((a, b) => a.timestamp - b.timestamp)
      .slice(0, count - MAX_RECORDS);
    for (const rec of toDelete) {
      await store.delete(rec.id);
    }
  }

  await tx.done;
}

export async function getColorHistory(project?: string): Promise<ColorHistory[]> {
  const db = await getDB();
  let records: ColorHistory[];
  if (project && project !== 'all') {
    records = await db.getAllFromIndex(STORE_NAME, 'project', project);
  } else {
    records = await db.getAll(STORE_NAME);
  }
  return records.sort((a, b) => b.timestamp - a.timestamp);
}

export async function getProjects(): Promise<string[]> {
  const db = await getDB();
  const records = await db.getAll(STORE_NAME);
  const projects = new Set<string>();
  records.forEach((r) => {
    if (r.project) projects.add(r.project);
  });
  return Array.from(projects).sort();
}

export async function updateColorProject(id: string, project: string | undefined): Promise<void> {
  const db = await getDB();
  const tx = db.transaction(STORE_NAME, 'readwrite');
  const store = tx.objectStore(STORE_NAME);
  const record = await store.get(id);
  if (record) {
    record.project = project;
    await store.put(record);
  }
  await tx.done;
}

export async function deleteColorFromHistory(id: string): Promise<void> {
  const db = await getDB();
  await db.delete(STORE_NAME, id);
}

export async function clearColorHistory(): Promise<void> {
  const db = await getDB();
  await db.clear(STORE_NAME);
}
