import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse, InternalAxiosRequestConfig } from 'axios';
import type { ApiResponse } from '../types';

const request: AxiosInstance = axios.create({
  baseURL: 'http://localhost:8080',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

request.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    console.log(`[Request] ${config.method?.toUpperCase()} ${config.url}`, config.data || '');
    return config;
  },
  (error) => {
    console.error('[Request Error]', error);
    return Promise.reject(error);
  }
);

request.interceptors.response.use(
  (response: AxiosResponse) => {
    const res = response.data as ApiResponse;
    console.log(`[Response] ${response.config.method?.toUpperCase()} ${response.config.url}`, res);
    if (res.code !== 200) {
      console.error(`[API Error] Code: ${res.code}, Message: ${res.message}`);
      return Promise.reject(new Error(res.message || 'Request failed'));
    }
    return res.data as unknown as AxiosResponse;
  },
  (error) => {
    console.error('[Response Error]', error.message);
    if (error.response) {
      const { status, data } = error.response;
      if (status === 401) {
        localStorage.removeItem('token');
        window.location.href = '/login';
      }
      console.error(`[HTTP Error] Status: ${status}`, data);
    }
    return Promise.reject(error);
  }
);

export const httpGet = <T = unknown>(url: string, config?: AxiosRequestConfig): Promise<T> => {
  return request.get<unknown, T>(url, config);
};

export const httpPost = <T = unknown>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> => {
  return request.post<unknown, T>(url, data, config);
};

export const httpPut = <T = unknown>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> => {
  return request.put<unknown, T>(url, data, config);
};

export const httpDelete = <T = unknown>(url: string, config?: AxiosRequestConfig): Promise<T> => {
  return request.delete<unknown, T>(url, config);
};

export default request;
