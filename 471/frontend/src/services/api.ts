import axios from 'axios';
import { Secret, SecretWithValue, AuditLog, CreateSecretRequest, UpdateSecretRequest } from '../types';

const api = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
    'X-User': 'admin'
  }
});

export const secretApi = {
  list: (limit = 20, offset = 0, type?: string) =>
    api.get<{ secrets: Secret[]; total: number }>('/secrets', { params: { limit, offset, type } }),

  get: (id: string) =>
    api.get<SecretWithValue>(`/secrets/${id}`),

  create: (data: CreateSecretRequest) =>
    api.post<Secret>('/secrets', data),

  update: (id: string, data: UpdateSecretRequest) =>
    api.put<Secret>(`/secrets/${id}`, data),

  delete: (id: string) =>
    api.delete(`/secrets/${id}`),

  rotate: (id: string, newValue: string) =>
    api.post(`/secrets/${id}/rotate`, { new_value: newValue })
};

export const auditApi = {
  list: (limit = 50, offset = 0, secretId?: string, user?: string) =>
    api.get<{ logs: AuditLog[]; total: number }>('/audit/logs', { params: { limit, offset, secret_id: secretId, user } }),

  stats: () =>
    api.get<{ stats: Record<string, number> }>('/audit/stats')
};

export const healthApi = {
  check: () =>
    api.get<{ status: string; services: Record<string, string> }>('/health')
};
