import axios from 'axios';
import type {
  Document,
  Query,
  Annotation,
  SearchRequest,
  SearchResponse,
  EvaluationResult,
  EvaluationMetrics,
  ConfusionMatrixData,
  ModelComparisonData,
  FailureCase,
  FailureCaseStratifiedSample,
  ModelComparisonDrillDown,
  QueryTypeStats,
  Stats,
  ModelInfo,
  ClickEvent,
  AutoAnnotationResult,
  ABTestConfig,
  ABTestAssignment,
  ABTestMetrics,
  TrainingSample,
  FeedbackLearningResult,
  RetrainingResult,
} from '@/types';

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
});

export const healthCheck = () => api.get('/health');

export const getStats = (): Promise<{ data: Stats }> => api.get('/stats');

export const getDocuments = (page = 1, pageSize = 20) =>
  api.get<Document[]>('/documents', { params: { page, page_size: pageSize } });

export const getDocument = (docId: string) => api.get<Document>(`/documents/${docId}`);

export const createDocument = (doc: Omit<Document, 'created_at'>) =>
  api.post<Document>('/documents', doc);

export const createDocumentsBatch = (docs: Array<Omit<Document, 'created_at'>>) =>
  api.post('/documents/batch', docs);

export const getQueries = (page = 1, pageSize = 20) =>
  api.get<Query[]>('/queries', { params: { page, page_size: pageSize } });

export const getQuery = (queryId: string) => api.get<Query>(`/queries/${queryId}`);

export const createQuery = (query: Omit<Query, 'created_at'>) =>
  api.post<Query>('/queries', query);

export const createQueriesBatch = (queries: Array<Omit<Query, 'created_at'>>) =>
  api.post('/queries/batch', queries);

export const getAnnotations = (page = 1, pageSize = 20) =>
  api.get<Annotation[]>('/annotations', { params: { page, page_size: pageSize } });

export const getQueryAnnotations = (queryId: string) =>
  api.get<Annotation[]>(`/annotations/query/${queryId}`);

export const createAnnotation = (annotation: Omit<Annotation, 'created_at' | 'updated_at'>) =>
  api.post<Annotation>('/annotations', annotation);

export const createAnnotationsBatch = (queryId: string, annotations: Array<Omit<Annotation, 'created_at' | 'updated_at'>>, requestId?: string) =>
  api.post('/annotations/batch', { query_id: queryId, annotations, request_id: requestId });

export const search = (request: SearchRequest): Promise<{ data: SearchResponse }> =>
  api.post('/search', request);

export const evaluate = (request: SearchRequest): Promise<{ data: EvaluationResult }> =>
  api.post('/evaluate', request);

export const batchEvaluate = (modelName = 'default', k = 10, queryType?: string) =>
  api.get('/evaluate/batch', { params: { model_name: modelName, k, query_type: queryType } });

export const getConfusionMatrix = (modelName = 'default', k = 10, queryType?: string): Promise<{ data: ConfusionMatrixData }> =>
  api.get('/confusion-matrix', { params: { model_name: modelName, k, query_type: queryType } });

export const getModelComparison = (models: string[] = ['default'], kValues: number[] = [1, 3, 5, 10, 20], queryType?: string) =>
  api.get<ModelComparisonData[]>('/model-comparison', {
    params: { models, k_values: kValues, query_type: queryType },
    paramsSerializer: {
      indexes: null,
    },
  });

export const getModelComparisonDrilldown = (models: string[] = ['default'], kValues: number[] = [1, 3, 5, 10, 20]) =>
  api.get<ModelComparisonDrillDown[]>('/model-comparison/drilldown', {
    params: { models, k_values: kValues },
    paramsSerializer: {
      indexes: null,
    },
  });

export const getQueryTypeStats = (modelName = 'default', k = 10): Promise<{ data: QueryTypeStats[] }> =>
  api.get('/query-types/stats', { params: { model_name: modelName, k } });

export const getFailureCases = (modelName = 'default', k = 10, minRecall = 0.5, queryType?: string): Promise<{ data: FailureCase[] }> =>
  api.get('/failure-cases', { params: { model_name: modelName, k, min_recall: minRecall, query_type: queryType } });

export const getFailureCasesStratified = (modelName = 'default', k = 10, minRecall = 0.8, samplesPerStratum = 3): Promise<{ data: FailureCaseStratifiedSample }> =>
  api.get('/failure-cases/stratified', { params: { model_name: modelName, k, min_recall: minRecall, samples_per_stratum: samplesPerStratum } });

export const getEvaluations = (page = 1, pageSize = 20, modelName?: string) =>
  api.get<EvaluationResult[]>('/evaluations', {
    params: { page, page_size: pageSize, model_name: modelName },
  });

export const getModels = (): Promise<{ data: ModelInfo[] }> => api.get('/models');

export const createModel = (model: ModelInfo) => api.post<ModelInfo>('/models', model);

export const recordClickEvent = (event: Partial<ClickEvent>) =>
  api.post('/click-events', event);

export const recordClickEventsBatch = (events: Partial<ClickEvent>[]) =>
  api.post('/click-events/batch', events);

export const getClickEvents = (requestId?: string, queryId?: string, sessionId?: string) =>
  api.get<ClickEvent[]>('/click-events', { params: { request_id: requestId, query_id: queryId, session_id: sessionId } });

export const generateAutoAnnotations = (requestId: string, queryId: string, minDwellTime = 3, maxAnnotations = 10) =>
  api.post<AutoAnnotationResult>('/auto-annotation', {
    request_id: requestId,
    query_id: queryId,
    min_dwell_time: minDwellTime,
    max_annotations: maxAnnotations
  });

export const createABTest = (config: Partial<ABTestConfig>) =>
  api.post<ABTestConfig>('/ab-tests', config);

export const listABTests = (status?: string) =>
  api.get<ABTestConfig[]>('/ab-tests', { params: { status } });

export const updateABTest = (testId: string, config: Partial<ABTestConfig>) =>
  api.put<ABTestConfig>(`/ab-tests/${testId}`, config);

export const assignABTestGroup = (testId: string, sessionId: string) =>
  api.post<ABTestAssignment>(`/ab-tests/${testId}/assign`, null, { params: { session_id: sessionId } });

export const getABTestMetrics = (testId: string, k = 10) =>
  api.get<ABTestMetrics>(`/ab-tests/${testId}/metrics`, { params: { k } });

export const generateTrainingData = (modelName: string, feedbackType = 'relevance', minConfidence = 0.7) =>
  api.post<FeedbackLearningResult>('/feedback-learning/generate', {
    model_name: modelName,
    feedback_type: feedbackType,
    min_confidence: minConfidence
  });

export const retrainModel = (config: { model_name: string; base_model?: string; training_data_source?: string; test_ratio?: number }) =>
  api.post<RetrainingResult>('/feedback-learning/retrain', config);

export const recordFeedback = (feedbackData: Record<string, any>) =>
  api.post('/feedback-learning/record', feedbackData);

export default api;
