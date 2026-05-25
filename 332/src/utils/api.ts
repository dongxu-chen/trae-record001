import type {
  DynamicCode,
  StatisticsOverview,
  QRStyle,
  QRCodeType,
  LandingPageAnalysis,
  ManagementOverview,
} from '@/types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:3001/api';

interface ApiResponse<T> {
  success: boolean;
  data?: T;
  message?: string;
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<ApiResponse<T>> {
  const token = localStorage.getItem('auth-storage');
  let authToken: string | null = null;
  
  if (token) {
    try {
      const parsed = JSON.parse(token);
      authToken = parsed.state?.token || null;
    } catch {
      // ignore
    }
  }

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };

  if (authToken) {
    headers['Authorization'] = `Bearer ${authToken}`;
  }

  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers,
    });

    const data = await response.json();
    
    if (!response.ok) {
      return {
        success: false,
        message: data.message || '请求失败',
      };
    }

    return { success: true, data };
  } catch (error) {
    return {
      success: false,
      message: error instanceof Error ? error.message : '网络错误',
    };
  }
}

export const authAPI = {
  register: (email: string, password: string, name: string) =>
    request<{ token: string; user: { id: string; email: string; name: string } }>(
      '/auth/register',
      {
        method: 'POST',
        body: JSON.stringify({ email, password, name }),
      }
    ),

  login: (email: string, password: string) =>
    request<{ token: string; user: { id: string; email: string; name: string } }>(
      '/auth/login',
      {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      }
    ),
};

export const dynamicCodeAPI = {
  create: (data: {
    name: string;
    originalUrl: string;
    type: QRCodeType;
    style: QRStyle;
  }) =>
    request<DynamicCode>('/dynamic', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  list: () =>
    request<DynamicCode[]>('/dynamic', {
      method: 'GET',
    }),

  update: (id: string, data: Partial<DynamicCode>) =>
    request<DynamicCode>(`/dynamic/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),

  delete: (id: string) =>
    request<void>(`/dynamic/${id}`, {
      method: 'DELETE',
    }),
};

export const statsAPI = {
  getOverview: (timeRange: string = '7d') =>
    request<StatisticsOverview>(`/stats/overview?timeRange=${timeRange}`, {
      method: 'GET',
    }),

  getCodeStats: (codeId: string, timeRange: string = '7d') =>
    request<StatisticsOverview>(`/stats/${codeId}?timeRange=${timeRange}`, {
      method: 'GET',
    }),

  getLandingAnalysis: (codeId: string, timeRange: string = '30d') =>
    request<LandingPageAnalysis>(`/stats/landing/${codeId}?timeRange=${timeRange}`, {
      method: 'GET',
    }),

  getManagementOverview: () =>
    request<ManagementOverview>(`/stats/management`, {
      method: 'GET',
    }),

  exportCSV: (timeRange: string = '30d') =>
    request<string>(`/stats/export?timeRange=${timeRange}`, {
      method: 'GET',
    }),
};

export const qrCodeAPI = {
  save: (data: {
    name: string;
    type: QRCodeType;
    content: string;
    style: QRStyle;
  }) =>
    request<{ id: string }>('/qrcodes', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  list: () =>
    request<Array<{ id: string; name: string; type: QRCodeType; content: string; style: QRStyle; createdAt: string }>>(
      '/qrcodes',
      {
        method: 'GET',
      }
    ),

  delete: (id: string) =>
    request<void>(`/qrcodes/${id}`, {
      method: 'DELETE',
    }),
};
