import type { Project, Annotation, Statistics } from '../types';

const API_BASE = 'http://localhost:3001/api';

export const api = {
  async getProjects(): Promise<Project[]> {
    const response = await fetch(`${API_BASE}/projects`);
    return response.json();
  },

  async createProject(data: Omit<Project, 'id' | 'createdAt' | 'updatedAt'>): Promise<Project> {
    const response = await fetch(`${API_BASE}/projects`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return response.json();
  },

  async getProject(id: string): Promise<Project> {
    const response = await fetch(`${API_BASE}/projects/${id}`);
    return response.json();
  },

  async deleteProject(id: string): Promise<void> {
    await fetch(`${API_BASE}/projects/${id}`, { method: 'DELETE' });
  },

  async getAnnotations(projectId: string): Promise<Annotation[]> {
    const response = await fetch(`${API_BASE}/projects/${projectId}/annotations`);
    return response.json();
  },

  async getStatistics(projectId: string): Promise<Statistics> {
    const response = await fetch(`${API_BASE}/projects/${projectId}/statistics`);
    return response.json();
  },

  async exportAnnotations(projectId: string, format: 'json' | 'csv' | 'excel'): Promise<Blob> {
    const response = await fetch(`${API_BASE}/projects/${projectId}/export?format=${format}`);
    return response.blob();
  },

  async uploadDataFile(projectId: string, file: File): Promise<{ dataPoints: any[] }> {
    const formData = new FormData();
    formData.append('file', file);
    const response = await fetch(`${API_BASE}/projects/${projectId}/upload`, {
      method: 'POST',
      body: formData,
    });
    return response.json();
  },
};
