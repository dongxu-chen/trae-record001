import type {
  ValidateRequest,
  ValidateResponse,
  DerivativeRequest,
  DerivativeResponse,
  EvaluateRequest,
  EvaluateResponse,
  ExportRequest,
  ExportResponse,
} from '../types';

const API_BASE = '/api';

export const apiService = {
  async validateExpression(expression: string): Promise<ValidateResponse> {
    try {
      const response = await fetch(`${API_BASE}/function/validate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ expression } as ValidateRequest),
      });
      return await response.json();
    } catch (error) {
      return { valid: false, error: '网络请求失败，使用本地验证' };
    }
  },

  async computeDerivative(expression: string, variable: string = 'x'): Promise<DerivativeResponse> {
    try {
      const response = await fetch(`${API_BASE}/function/derivative`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ expression, variable } as DerivativeRequest),
      });
      return await response.json();
    } catch (error) {
      return { success: false, error: '网络请求失败，使用本地计算' };
    }
  },

  async evaluateExpression(expression: string, xValues: number[]): Promise<EvaluateResponse> {
    try {
      const response = await fetch(`${API_BASE}/function/evaluate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ expression, xValues } as EvaluateRequest),
      });
      return await response.json();
    } catch (error) {
      return { success: false, error: '网络请求失败', yValues: [] };
    }
  },

  async exportImage(imageData: string, width: number, height: number): Promise<ExportResponse> {
    try {
      const response = await fetch(`${API_BASE}/export/png`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ imageData, width, height } as ExportRequest),
      });
      return await response.json();
    } catch (error) {
      return { success: false, error: '导出失败，请尝试本地下载' };
    }
  },

  downloadImage(dataUrl: string, filename: string = 'graph.png') {
    const link = document.createElement('a');
    link.download = filename;
    link.href = dataUrl;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  },
};
