export interface Document {
  doc_id: string;
  title: string;
  content: string;
  metadata?: Record<string, any>;
  created_at: string;
}

export interface Query {
  query_id: string;
  query_text: string;
  description?: string;
  query_type?: string;
  created_at: string;
}

export interface Annotation {
  query_id: string;
  doc_id: string;
  relevance: number;
  annotator?: string;
  request_id?: string;
  created_at: string;
  updated_at?: string;
}

export interface SearchResult {
  doc_id: string;
  score: number;
  rank: number;
  title?: string;
  content?: string;
  relevant?: boolean;
}

export interface SearchRequest {
  query_text: string;
  model_name?: string;
  k?: number;
  index?: string;
  request_id?: string;
  query_type?: string;
}

export interface SearchResponse {
  query_id: string;
  query_text: string;
  model_name: string;
  k: number;
  results: SearchResult[];
  total: number;
  took: number;
  request_id: string;
  query_type?: string;
}

export interface EvaluationMetrics {
  recall_at_k: number;
  precision_at_k: number;
  f1_at_k: number;
  hit_rate: number;
  mrr: number;
  ndcg_at_k: number;
  map_at_k: number;
  average_precision: number;
}

export interface EvaluationResult {
  evaluation_id: string;
  model_name: string;
  query_id: string;
  query_text: string;
  k: number;
  results: SearchResult[];
  metrics: EvaluationMetrics;
  created_at: string;
}

export interface ConfusionMatrixData {
  tp: number;
  fp: number;
  fn: number;
  tn: number;
  accuracy: number;
  precision: number;
  recall: number;
  f1_score: number;
  specificity: number;
}

export interface ModelComparisonData {
  model_name: string;
  k_values: number[];
  recall_scores: number[];
  precision_scores: number[];
  f1_scores: number[];
  hit_rates: number[];
  ndcg_scores: number[];
}

export interface FailureCase {
  query_id: string;
  query_text: string;
  expected_docs: string[];
  returned_docs: SearchResult[];
  missing_docs: Array<{ doc_id: string; title?: string; content?: string }>;
  irrelevant_docs: SearchResult[];
  metrics: EvaluationMetrics;
  query_type?: string;
  failure_reason?: string;
  failure_severity?: string;
}

export interface FailureCaseStratifiedSample {
  total_cases: number;
  sampled_cases: number;
  strata: Array<{
    query_type: string;
    failure_reason: string;
    total_count: number;
    sampled_count: number;
  }>;
  cases: FailureCase[];
}

export interface ModelComparisonDrillDown {
  query_type: string;
  query_count: number;
  comparisons: ModelComparisonData[];
}

export interface QueryTypeStats {
  query_type: string;
  count: number;
  avg_recall: number;
  avg_precision: number;
  avg_f1: number;
  avg_ndcg: number;
}

export interface Stats {
  documents_count: number;
  queries_count: number;
  annotations_count: number;
  evaluations_count: number;
  annotated_queries_count: number;
}

export interface ModelInfo {
  model_name: string;
  description?: string;
  endpoint?: string;
  is_active: boolean;
}

export interface ClickEvent {
  request_id: string;
  query_id: string;
  doc_id: string;
  rank: number;
  click_position: number;
  dwell_time: number;
  click_type: string;
  session_id?: string;
  created_at: string;
}

export interface AutoAnnotationResult {
  request_id: string;
  query_id: string;
  auto_generated: boolean;
  annotations_count: number;
  annotations: Array<Record<string, any>>;
  message: string;
}

export interface ABTestConfig {
  test_id: string;
  test_name: string;
  control_model: string;
  treatment_model: string;
  traffic_split: number;
  status: string;
  start_date?: string;
  end_date?: string;
  description?: string;
  created_at: string;
  updated_at?: string;
}

export interface ABTestAssignment {
  test_id: string;
  session_id: string;
  group: string;
  model_name: string;
  assigned_at: string;
}

export interface ABTestMetrics {
  test_id: string;
  test_name: string;
  control_model: string;
  treatment_model: string;
  control: Record<string, number>;
  treatment: Record<string, number>;
  lift: Record<string, number>;
  confidence: Record<string, number>;
  sample_size: {
    control: number;
    treatment: number;
  };
}

export interface TrainingSample {
  query_id: string;
  query_text: string;
  doc_id: string;
  doc_title?: string;
  relevance: number;
  source: string;
  confidence: number;
  created_at: string;
}

export interface FeedbackLearningResult {
  model_name: string;
  total_samples: number;
  high_confidence_samples: number;
  training_samples: TrainingSample[];
  export_path?: string;
  message: string;
}

export interface RetrainingResult {
  model_name: string;
  new_version: string;
  training_samples: number;
  validation_samples: number;
  training_metrics: Record<string, number>;
  validation_metrics: Record<string, number>;
  status: string;
  message: string;
}
