import axios, { AxiosInstance, AxiosRequestConfig } from 'axios';
import {
  User,
  Template,
  Comment,
  AuthResponse,
  TemplateListResponse,
  CommentListResponse,
  LoginForm,
  RegisterForm,
  TemplateFilter,
  Statistics
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000/api';

const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export const authAPI = {
  login: (data: LoginForm) =>
    api.post<AuthResponse>('/auth/login', data).then(res => res.data),
  
  register: (data: RegisterForm) =>
    api.post<AuthResponse>('/auth/register', data).then(res => res.data),
  
  getProfile: () =>
    api.get<{ user: User }>('/auth/profile').then(res => res.data),
};

export const templateAPI = {
  getTemplates: (params?: TemplateFilter) =>
    api.get<TemplateListResponse>('/templates', { params }).then(res => res.data),
  
  getTemplateById: (id: string) =>
    api.get<{ template: Template }>(`/templates/${id}`).then(res => res.data),
  
  createTemplate: (data: FormData) =>
    api.post('/templates', data, {
      headers: { 'Content-Type': 'multipart/form-data' }
    }).then(res => res.data),
  
  updateTemplate: (id: string, data: FormData) =>
    api.put(`/templates/${id}`, data, {
      headers: { 'Content-Type': 'multipart/form-data' }
    }).then(res => res.data),
  
  deleteTemplate: (id: string) =>
    api.delete(`/templates/${id}`).then(res => res.data),
  
  downloadTemplate: (id: string) =>
    api.post<{ downloadUrl: string; template: Template }>(`/templates/${id}/download`).then(res => res.data),
  
  rateTemplate: (id: string, rating: number) =>
    api.post<{ rating: number; ratingCount: number; userRating: number }>(`/templates/${id}/rate`, { rating }).then(res => res.data),

  applyTemplate: (id: string, mode: 'merge' | 'overwrite', backup?: any) =>
    api.post(`/templates/${id}/apply`, { mode, backup }).then(res => res.data),

  getUserRating: (id: string) =>
    api.get<{ hasRated: boolean; userRating: number | null }>(`/templates/${id}/user-rating`).then(res => res.data),
};

export const commentAPI = {
  getComments: (templateId: string, page = 1, limit = 10) =>
    api.get<CommentListResponse>(`/templates/${templateId}/comments`, {
      params: { page, limit }
    }).then(res => res.data),
  
  createComment: (templateId: string, content: string, rating: number) =>
    api.post<{ comment: Comment }>(`/templates/${templateId}/comments`, {
      content,
      rating
    }).then(res => res.data),
  
  replyComment: (commentId: string, content: string) =>
    api.post(`/templates/comments/${commentId}/reply`, { content }).then(res => res.data),
  
  deleteComment: (commentId: string) =>
    api.delete(`/templates/comments/${commentId}`).then(res => res.data),
};

export const userAPI = {
  getMyTemplates: (page = 1, limit = 12) =>
    api.get<TemplateListResponse>('/user/templates', {
      params: { page, limit }
    }).then(res => res.data),
  
  getFavorites: (page = 1, limit = 12) =>
    api.get<TemplateListResponse>('/user/favorites', {
      params: { page, limit }
    }).then(res => res.data),
  
  addFavorite: (templateId: string) =>
    api.post(`/user/favorites/${templateId}`).then(res => res.data),
  
  removeFavorite: (templateId: string) =>
    api.delete(`/user/favorites/${templateId}`).then(res => res.data),
  
  getDownloadHistory: (page = 1, limit = 12) =>
    api.get<TemplateListResponse>('/user/downloads', {
      params: { page, limit }
    }).then(res => res.data),
  
  getStatistics: () =>
    api.get<{ statistics: Statistics; downloadTrend: Array<{ _id: string; count: number }> }>('/user/statistics').then(res => res.data),
};

export const recommendAPI = {
  getRecommendations: (limit = 8, type = 'hybrid') =>
    api.get<{ recommendations: (Template & { reason: string })[]; type: string; count: number }>('/recommend', {
      params: { limit, type }
    }).then(res => res.data),
  
  getViewHistory: (page = 1, limit = 20) =>
    api.get<{ history: any[]; pagination: any }>('/recommend/history', {
      params: { page, limit }
    }).then(res => res.data),
  
  recordView: (templateId: string, duration?: number) =>
    api.post(`/recommend/view/${templateId}`, { duration }).then(res => res.data),
};

export const adminAPI = {
  getPendingTemplates: (page = 1, limit = 20) =>
    api.get<{ templates: Template[]; pagination: any }>('/admin/templates/pending', {
      params: { page, limit }
    }).then(res => res.data),
  
  approveTemplate: (id: string, note?: string) =>
    api.post(`/admin/templates/${id}/approve`, { note }).then(res => res.data),
  
  rejectTemplate: (id: string, reason?: string) =>
    api.post(`/admin/templates/${id}/reject`, { reason }).then(res => res.data),
  
  getReviewStatus: (id: string) =>
    api.get<{
      status: string;
      reviewNote: string;
      rejectReason: string;
      reviewedAt: string | null;
      reviewedBy: any;
      submittedAt: string;
    }>(`/admin/templates/${id}/review-status`).then(res => res.data),
  
  getStatistics: () =>
    api.get('/admin/statistics').then(res => res.data),
};

export default api;
