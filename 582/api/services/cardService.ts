import * as cardRepo from '../repository/cardRepository.js';
import type { CardData } from '../types/index.js';

export async function getAllCards(): Promise<CardData[]> {
  return cardRepo.findAll();
}

export async function getCard(id: string): Promise<CardData | null> {
  return cardRepo.findById(id);
}

export async function createCard(data: Omit<CardData, 'id' | 'createdAt' | 'updatedAt'>): Promise<CardData> {
  return cardRepo.create(data);
}

export async function updateCard(id: string, data: Partial<Omit<CardData, 'id' | 'createdAt'>>): Promise<CardData | null> {
  return cardRepo.update(id, data);
}

export async function deleteCard(id: string): Promise<boolean> {
  return cardRepo.deleteCard(id);
}
