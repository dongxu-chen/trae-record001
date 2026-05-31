import fs from 'fs/promises';
import path from 'path';
import { fileURLToPath } from 'url';
import { v4 as uuidv4 } from 'uuid';
import type { CardTemplate } from '../types/index.js';
import { builtInTemplates } from '../data/templates.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const DATA_DIR = path.resolve(__dirname, '../../data/templates');

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

export async function seedBuiltInTemplates(): Promise<void> {
  await ensureDir();
  for (const template of builtInTemplates) {
    const filePath = getFilePath(template.id);
    try {
      await fs.access(filePath);
    } catch {
      await fs.writeFile(filePath, JSON.stringify(template, null, 2), 'utf-8');
    }
  }
}

export async function findAll(): Promise<CardTemplate[]> {
  await ensureDir();
  const files = await fs.readdir(DATA_DIR);
  const templates: CardTemplate[] = [];
  for (const file of files) {
    if (!file.endsWith('.json')) continue;
    const content = await fs.readFile(path.join(DATA_DIR, file), 'utf-8');
    templates.push(JSON.parse(content));
  }
  return templates;
}

export async function findById(id: string): Promise<CardTemplate | null> {
  await ensureDir();
  try {
    const content = await fs.readFile(getFilePath(id), 'utf-8');
    return JSON.parse(content);
  } catch {
    return null;
  }
}

export async function create(data: Omit<CardTemplate, 'id' | 'createdAt' | 'updatedAt'>): Promise<CardTemplate> {
  await ensureDir();
  const now = new Date().toISOString();
  const template: CardTemplate = {
    ...data,
    id: uuidv4(),
    createdAt: now,
    updatedAt: now,
  };
  await fs.writeFile(getFilePath(template.id), JSON.stringify(template, null, 2), 'utf-8');
  return template;
}

export async function update(id: string, data: Partial<Omit<CardTemplate, 'id' | 'createdAt'>>): Promise<CardTemplate | null> {
  const existing = await findById(id);
  if (!existing) return null;
  const updated: CardTemplate = {
    ...existing,
    ...data,
    id: existing.id,
    createdAt: existing.createdAt,
    updatedAt: new Date().toISOString(),
  };
  await fs.writeFile(getFilePath(id), JSON.stringify(updated, null, 2), 'utf-8');
  return updated;
}

export async function deleteTemplate(id: string): Promise<boolean> {
  const existing = await findById(id);
  if (!existing) return false;
  if (existing.builtIn) return false;
  try {
    await fs.unlink(getFilePath(id));
    return true;
  } catch {
    return false;
  }
}
