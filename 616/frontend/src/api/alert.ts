import { request } from './request';
import { AlertRule, AlertRuleDTO } from '@/types';

export const alertApi = {
  list: (params?: {
    name?: string;
    enabled?: boolean;
    notificationType?: string;
  }): Promise<AlertRule[]> => {
    return request<AlertRule[]>({
      url: '/alert-rules',
      method: 'get',
      params,
    });
  },

  getById: (id: string): Promise<AlertRule> => {
    return request<AlertRule>({
      url: `/alert-rules/${id}`,
      method: 'get',
    });
  },

  create: (data: AlertRuleDTO): Promise<AlertRule> => {
    return request<AlertRule>({
      url: '/alert-rules',
      method: 'post',
      data,
    });
  },

  update: (id: string, data: AlertRuleDTO): Promise<AlertRule> => {
    return request<AlertRule>({
      url: `/alert-rules/${id}`,
      method: 'put',
      data,
    });
  },

  delete: (id: string): Promise<boolean> => {
    return request<boolean>({
      url: `/alert-rules/${id}`,
      method: 'delete',
    });
  },

  enable: (id: string): Promise<boolean> => {
    return request<boolean>({
      url: `/alert-rules/${id}/enable`,
      method: 'post',
    });
  },

  disable: (id: string): Promise<boolean> => {
    return request<boolean>({
      url: `/alert-rules/${id}/disable`,
      method: 'post',
    });
  },
};
