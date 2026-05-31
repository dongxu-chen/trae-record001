import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse, InternalAxiosRequestConfig } from 'axios';
import { message } from 'antd';
import { Result } from '@/types';

const service: AxiosInstance = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

service.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    return config;
  },
  (error) => {
    console.error('Request error:', error);
    return Promise.reject(error);
  }
);

service.interceptors.response.use(
  (response: AxiosResponse<Result<any>>) => {
    const res = response.data;
    if (res.code !== 200 && res.code !== 0) {
      message.error(res.message || '请求失败');
      return Promise.reject(new Error(res.message || '请求失败'));
    }
    return res.data;
  },
  (error) => {
    console.error('Response error:', error);
    message.error(error.message || '网络错误');
    return Promise.reject(error);
  }
);

export function request<T>(config: AxiosRequestConfig): Promise<T> {
  return service(config);
}

export default service;
