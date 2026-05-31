import type { AnalysisResult } from '../../shared/types';

export async function previewData(data: Record<string, any>[]): Promise<{
  columns: string[];
  preview: Record<string, any>[];
  stats: {
    rowCount: number;
    columnCount: number;
    missingValues: Record<string, number>;
    dtypes: Record<string, string>;
  };
  columnInfo: Array<{
    name: string;
    type: string;
    uniqueValues: number;
    sampleValues: any[];
  }>;
}> {
  const response = await fetch('/api/causal/preview', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ data }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to preview data');
  }

  return response.json();
}

export async function lassoSelect(
  data: Record<string, any>[],
  treatment: string,
  outcome: string,
  candidate_covariates: string[],
  method: string = 'double_lasso'
): Promise<{
  selected_covariates: string[];
  covariate_importance: Array<{
    covariate: string;
    treatment_importance: number;
    outcome_importance: number;
    selection_frequency: number;
    combined_importance: number;
  }>;
  method_used: string;
}> {
  const response = await fetch('/api/causal/lasso-select', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ data, treatment, outcome, candidate_covariates, method }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to perform LASSO selection');
  }

  return response.json();
}

export async function analyzePSM(
  data: Record<string, any>[],
  treatment: string,
  outcome: string,
  covariates: string[],
  useAutoSelection: boolean = false,
  autoSelectionMethod: string = 'double_lasso'
): Promise<AnalysisResult> {
  const response = await fetch('/api/causal/analyze/psm', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ data, treatment, outcome, covariates, useAutoSelection, autoSelectionMethod }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to perform PSM analysis');
  }

  return response.json();
}

export async function analyzeDID(
  data: Record<string, any>[],
  treatment: string,
  outcome: string,
  covariates: string[],
  timeVariable?: string,
  postTreatmentIndicator?: string,
  useAutoSelection: boolean = false,
  autoSelectionMethod: string = 'double_lasso'
): Promise<AnalysisResult> {
  const response = await fetch('/api/causal/analyze/did', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      data,
      treatment,
      outcome,
      covariates,
      timeVariable,
      postTreatmentIndicator,
      useAutoSelection,
      autoSelectionMethod,
    }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to perform DID analysis');
  }

  return response.json();
}

export async function generateReport(
  result: AnalysisResult,
  method: string,
  treatment: string,
  outcome: string,
  covariates: string[],
  sampleSize: any,
  format: string = 'html'
): Promise<{
  success: boolean;
  format: string;
  content: string;
  filename: string;
}> {
  const response = await fetch('/api/causal/generate-report', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      result,
      method,
      treatment,
      outcome,
      covariates,
      sampleSize,
      format,
    }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to generate report');
  }

  return response.json();
}
