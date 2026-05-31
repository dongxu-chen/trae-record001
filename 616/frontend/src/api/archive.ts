import { request } from './request';
import { DeadLetterMessage, PageResult } from '@/types';
import { MqType, ProcessStatus } from '@/types/enums';

export const archiveApi = {
  list: (params?: {
    mqType?: MqType;
    topic?: string;
    messageId?: string;
    processStatus?: ProcessStatus;
    startTime?: string;
    endTime?: string;
    archiveIndex?: string;
    pageNum?: number;
    pageSize?: number;
  }): Promise<PageResult<DeadLetterMessage>> => {
    return request<PageResult<DeadLetterMessage>>({
      url: '/archives',
      method: 'get',
      params,
    });
  },

  restore: (id: string, params?: {
    targetIndex?: string;
    operator?: string;
  }): Promise<boolean> => {
    return request<boolean>({
      url: `/archives/${id}/restore`,
      method: 'post',
      params,
    });
  },

  listIndexes: (params?: {
    prefix?: string;
    includeStats?: boolean;
  }): Promise<Record<string, any>[]> => {
    return request<Record<string, any>[]>({
      url: '/archives/indexes',
      method: 'get',
      params,
    });
  },
};
