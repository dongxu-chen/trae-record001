import type { PresetItem, CustomFilterDef, FilterConfig } from '@/store/filterStore';

const BASE_URL = '/api';

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  try {
    const response = await fetch(`${BASE_URL}${url}`, options);
    if (!response.ok) {
      const errorBody = await response.text().catch(() => response.statusText);
      throw new Error(`API error ${response.status}: ${errorBody}`);
    }
    return response.json() as Promise<T>;
  } catch (error) {
    if (error instanceof TypeError && error.message === 'Failed to fetch') {
      throw new Error('Network error: Unable to reach the server');
    }
    throw error;
  }
}

async function requestBlob(url: string, options?: RequestInit): Promise<Blob> {
  try {
    const response = await fetch(`${BASE_URL}${url}`, options);
    if (!response.ok) {
      const errorBody = await response.text().catch(() => response.statusText);
      throw new Error(`API error ${response.status}: ${errorBody}`);
    }
    return response.blob();
  } catch (error) {
    if (error instanceof TypeError && error.message === 'Failed to fetch') {
      throw new Error('Network error: Unable to reach the server');
    }
    throw error;
  }
}

export async function fetchPresets(): Promise<PresetItem[]> {
  return request<PresetItem[]>('/presets');
}

export async function createPreset(preset: Omit<PresetItem, 'id' | 'createdAt'>): Promise<PresetItem> {
  return request<PresetItem>('/presets', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(preset),
  });
}

export async function deletePreset(id: string): Promise<void> {
  await request<void>(`/presets/${id}`, {
    method: 'DELETE',
  });
}

export async function fetchCustomFilters(): Promise<CustomFilterDef[]> {
  return request<CustomFilterDef[]>('/filters/custom');
}

export async function uploadCustomFilter(data: Omit<CustomFilterDef, 'id' | 'compiled' | 'error'>): Promise<CustomFilterDef> {
  return request<CustomFilterDef>('/filters/custom', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
}

export async function deleteCustomFilter(id: string): Promise<void> {
  await request<void>(`/filters/custom/${id}`, {
    method: 'DELETE',
  });
}

export interface ShaderValidationResult {
  valid: boolean;
  error?: string;
}

export async function validateShader(fragmentShader: string): Promise<ShaderValidationResult> {
  return request<ShaderValidationResult>('/filters/custom/validate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ fragmentShader }),
  });
}

export async function exportSingle(imageData: Blob, config: FilterConfig): Promise<Blob> {
  const formData = new FormData();
  formData.append('image', imageData);
  formData.append('config', JSON.stringify(config));
  return requestBlob('/export/single', {
    method: 'POST',
    body: formData,
  });
}

export interface BatchExportItem {
  imageId: string;
  imageData: Blob;
  config: FilterConfig;
}

export async function exportBatch(items: BatchExportItem[]): Promise<Blob> {
  const formData = new FormData();
  items.forEach((item, index) => {
    formData.append(`image_${index}`, item.imageData);
    formData.append(`config_${index}`, JSON.stringify({ imageId: item.imageId, config: item.config }));
  });
  return requestBlob('/export/batch', {
    method: 'POST',
    body: formData,
  });
}
