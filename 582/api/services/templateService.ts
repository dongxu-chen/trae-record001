import * as templateRepo from '../repository/templateRepository.js';
import type { CardTemplate } from '../types/index.js';

export async function initTemplates(): Promise<void> {
  await templateRepo.seedBuiltInTemplates();
}

export async function getAllTemplates(): Promise<CardTemplate[]> {
  return templateRepo.findAll();
}

export async function getTemplate(id: string): Promise<CardTemplate | null> {
  return templateRepo.findById(id);
}

export async function createTemplate(data: Omit<CardTemplate, 'id' | 'createdAt' | 'updatedAt'>): Promise<CardTemplate> {
  return templateRepo.create(data);
}

export async function updateTemplate(id: string, data: Partial<Omit<CardTemplate, 'id' | 'createdAt'>>): Promise<CardTemplate | null> {
  return templateRepo.update(id, data);
}

export async function deleteTemplate(id: string): Promise<boolean> {
  return templateRepo.deleteTemplate(id);
}
