import axios, { AxiosInstance } from 'axios';
import { Annotation } from '../types';

const API_BASE_URL = 'http://localhost:3001/api';

const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 300000,
});

export const pdfApi = {
  uploadPdf: async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await apiClient.post('/pdf/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  getOutline: async (fileId: string) => {
    const response = await apiClient.get(`/pdf/${fileId}/outline`);
    return response.data;
  },

  exportWithAnnotations: async (fileId: string, annotations: Annotation[]) => {
    const response = await apiClient.post(`/pdf/${fileId}/export`, {
      annotations,
    });
    return response.data;
  },

  getExportStatus: async (taskId: string) => {
    const response = await apiClient.get(`/pdf/export/${taskId}`);
    return response.data;
  },

  getPresignedUrl: async (fileId: string) => {
    const response = await apiClient.get(`/pdf/${fileId}/presign`);
    return response.data;
  },
};

export const ocrApi = {
  recognize: async (file: File, pages?: number[]) => {
    const formData = new FormData();
    formData.append('file', file);
    if (pages) {
      formData.append('pages', JSON.stringify(pages));
    }

    const response = await apiClient.post('/ocr/recognize', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  getStatus: async (taskId: string) => {
    const response = await apiClient.get(`/ocr/${taskId}/status`);
    return response.data;
  },
};

export const reviewApi = {
  createSession: async (fileId: string, reviewerName: string) => {
    const response = await apiClient.post('/review/session', {
      fileId,
      reviewerName,
    });
    return response.data;
  },

  joinSession: async (sessionId: string, reviewerName: string) => {
    const response = await apiClient.post(`/review/session/${sessionId}/join`, {
      reviewerName,
    });
    return response.data;
  },

  getSession: async (sessionId: string) => {
    const response = await apiClient.get(`/review/session/${sessionId}`);
    return response.data;
  },

  addAnnotation: async (sessionId: string, reviewerId: string, annotation: Annotation) => {
    const response = await apiClient.post(
      `/review/session/${sessionId}/annotations`,
      { reviewerId, annotation }
    );
    return response.data;
  },

  mergeAnnotations: async (sessionId: string, selectedIds: string[]) => {
    const response = await apiClient.post(
      `/review/session/${sessionId}/merge`,
      { selectedIds }
    );
    return response.data;
  },
};

export default apiClient;
