import fs from 'fs/promises';
import path from 'path';
import { fileURLToPath } from 'url';
import { v4 as uuidv4 } from 'uuid';
import type { CardData } from '../types/index.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const DATA_DIR = path.resolve(__dirname, '../../data/cards');

async function ensureDir(): Promise<void> {
  try {
    await fs.access(DATA_DIR);
  } catch {
    await fs.mkdir(DATA_DIR, { recursive: true });
  }
}

function getFilePath(id: string): string {
  return path.join(DATA_DIR, `${id}.json`);
}

export async function findAll(): Promise<CardData[]> {
  await ensureDir();
  const files = await fs.readdir(DATA_DIR);
  const cards: CardData[] = [];
  for (const file of files) {
    if (!file.endsWith('.json')) continue;
    const content = await fs.readFile(path.join(DATA_DIR, file), 'utf-8');
    cards.push(JSON.parse(content));
  }
  return cards;
}

export async function findById(id: string): Promise<CardData | null> {
  await ensureDir();
  try {
    const content = await fs.readFile(getFilePath(id), 'utf-8');
    return JSON.parse(content);
  } catch {
    return null;
  }
}

export async function create(data: Omit<CardData, 'id' | 'createdAt' | 'updatedAt'>): Promise<CardData> {
  await ensureDir();
  const now = new Date().toISOString();
  const card: CardData = {
    ...data,
    id: uuidv4(),
    createdAt: now,
    updatedAt: now,
  };
  await fs.writeFile(getFilePath(card.id), JSON.stringify(card, null, 2), 'utf-8');
  return card;
}

export async function update(id: string, data: Partial<Omit<CardData, 'id' | 'createdAt'>>): Promise<CardData | null> {
  const existing = await findById(id);
  if (!existing) return null;
  const updated: CardData = {
    ...existing,
    ...data,
    id: existing.id,
    createdAt: existing.createdAt,
    updatedAt: new Date().toISOString(),
  };
  await fs.writeFile(getFilePath(id), JSON.stringify(updated, null, 2), 'utf-8');
  return updated;
}

export async function deleteCard(id: string): Promise<boolean> {
  try {
    await fs.access(getFilePath(id));
    await fs.unlink(getFilePath(id));
    return true;
  } catch {
    return false;
  }
}
