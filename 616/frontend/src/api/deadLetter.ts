import { request } from './request';
import { DeadLetterMessage, PageResult, DeadLetterQueryParams, ReplayRequest, ArchiveRequest, Statistics } from '@/types';
import { MqType } from '@/types/enums';

export const deadLetterApi = {
  list: (params: DeadLetterQueryParams): Promise<PageResult<DeadLetterMessage>> => {
    return request<PageResult<DeadLetterMessage>>({
      url: '/dead-letters',
      method: 'get',
      params,
    });
  },

  getById: (id: string): Promise<DeadLetterMessage> => {
    return request<DeadLetterMessage>({
      url: `/dead-letters/${id}`,
      method: 'get',
    });
  },

  replay: (id: string, data?: ReplayRequest): Promise<boolean> => {
    return request<boolean>({
      url: `/dead-letters/${id}/replay`,
      method: 'post',
      data,
    });
  },

  batchReplay: (data: ReplayRequest): Promise<number> => {
    return request<number>({
      url: '/dead-letters/batch-replay',
      method: 'post',
      data,
    });
  },

  archive: (id: string, data?: ArchiveRequest): Promise<boolean> => {
    return request<boolean>({
      url: `/dead-letters/${id}/archive`,
      method: 'post',
      data,
    });
  },

  batchArchive: (data: ArchiveRequest): Promise<number> => {
    return request<number>({
      url: '/dead-letters/batch-archive',
      method: 'post',
      data,
    });
  },

  ignore: (id: string, remark?: string): Promise<boolean> => {
    return request<boolean>({
      url: `/dead-letters/${id}/ignore`,
      method: 'post',
      params: { remark },
    });
  },

  batchIgnore: (ids: string[], remark?: string): Promise<number> => {
    return request<number>({
      url: '/dead-letters/batch-ignore',
      method: 'post',
      data: ids,
      params: { remark },
    });
  },

  getStatistics: (): Promise<Statistics> => {
    return request<Statistics>({
      url: '/dead-letters/statistics',
      method: 'get',
    });
  },

  getAggregation: (params?: {
    mqType?: MqType;
    groupBy?: string;
    startTime?: string;
    endTime?: string;
  }): Promise<Record<string, any>> => {
    return request<Record<string, any>>({
      url: '/dead-letters/aggregation',
      method: 'get',
      params,
    });
  },
};
