import { request } from './request';
import { AnalysisResult } from '@/types';

export interface DeadLetterAnalysisResult {
  id: string;
  analysisResult: AnalysisResult;
  analyzedAt: string;
}

export const analysisApi = {
  analyze: (id: string, deepAnalysis?: boolean): Promise<DeadLetterAnalysisResult> => {
    return request<DeadLetterAnalysisResult>({
      url: '/analysis/analyze',
      method: 'post',
      params: { id, deepAnalysis },
    });
  },

  batchAnalyze: (ids: string[], deepAnalysis?: boolean): Promise<DeadLetterAnalysisResult[]> => {
    return request<DeadLetterAnalysisResult[]>({
      url: '/analysis/batch-analyze',
      method: 'post',
      data: ids,
      params: { deepAnalysis },
    });
  },

  getSuggestions: (id: string): Promise<Record<string, any>> => {
    return request<Record<string, any>>({
      url: `/analysis/suggestions/${id}`,
      method: 'get',
    });
  },
};
