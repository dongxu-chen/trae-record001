import axios from 'axios';
import {
  TestConfig, TestReport, StabilityTestConfig, StabilityTestReport,
  PerformanceBaseline, BaselineComparison, AutoTuningConfig, AutoTuningReport
} from '../types';

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
});

export const startTest = async (config: TestConfig): Promise<{ testId: string }> => {
  const response = await api.post('/test/start', config);
  return response.data;
};

export const stopTest = async (testId: string): Promise<{ success: boolean }> => {
  const response = await api.get(`/test/stop/${testId}`);
  return response.data;
};

export const getReport = async (testId: string): Promise<TestReport> => {
  const response = await api.get(`/test/${testId}`);
  return response.data;
};

export const getReportList = async (): Promise<TestReport[]> => {
  const response = await api.get('/test/list');
  return response.data;
};

export const exportReport = async (testId: string, format: 'json' | 'csv') => {
  const response = await api.get(`/report/${testId}/export?format=${format}`, {
    responseType: 'blob',
  });
  const url = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', `report-${testId}.${format}`);
  document.body.appendChild(link);
  link.click();
  link.remove();
};

export const startStabilityTest = async (config: StabilityTestConfig): Promise<{ testId: string }> => {
  const response = await api.post('/stability/start', config);
  return response.data;
};

export const stopStabilityTest = async (testId: string): Promise<{ success: boolean }> => {
  const response = await api.get(`/stability/stop/${testId}`);
  return response.data;
};

export const getStabilityReport = async (testId: string): Promise<StabilityTestReport> => {
  const response = await api.get(`/stability/${testId}`);
  return response.data;
};

export const getStabilityReportList = async (): Promise<StabilityTestReport[]> => {
  const response = await api.get('/stability/list');
  return response.data;
};

export const getStabilityTestStatus = async (testId: string): Promise<{ testId: string; running: boolean }> => {
  const response = await api.get(`/stability/${testId}/status`);
  return response.data;
};

export const createBaseline = async (testId: string): Promise<PerformanceBaseline> => {
  const response = await api.post(`/baseline/create/${testId}`);
  return response.data;
};

export const getBaselineList = async (): Promise<PerformanceBaseline[]> => {
  const response = await api.get('/baseline/list');
  return response.data;
};

export const getBaselinesByAlgorithm = async (algorithm: string): Promise<PerformanceBaseline[]> => {
  const response = await api.get(`/baseline/algorithm/${algorithm}`);
  return response.data;
};

export const getBestBaseline = async (algorithm: string): Promise<PerformanceBaseline> => {
  const response = await api.get(`/baseline/best/${algorithm}`);
  return response.data;
};

export const compareWithBaseline = async (testId: string): Promise<BaselineComparison> => {
  const response = await api.get(`/baseline/compare/${testId}`);
  return response.data;
};

export const deleteBaseline = async (baselineId: string): Promise<{ success: boolean }> => {
  const response = await api.delete(`/baseline/${baselineId}`);
  return response.data;
};

export const startAutoTuning = async (config: AutoTuningConfig): Promise<{ tuningId: string }> => {
  const response = await api.post('/tuning/start', config);
  return response.data;
};

export const stopAutoTuning = async (tuningId: string): Promise<{ success: boolean }> => {
  const response = await api.get(`/tuning/stop/${tuningId}`);
  return response.data;
};

export const getTuningReport = async (tuningId: string): Promise<AutoTuningReport> => {
  const response = await api.get(`/tuning/${tuningId}`);
  return response.data;
};

export const getTuningReportList = async (): Promise<AutoTuningReport[]> => {
  const response = await api.get('/tuning/list');
  return response.data;
};

export default api;
