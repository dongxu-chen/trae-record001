import type {
  Product,
  PlatformPrice,
  ComparisonResult,
  PriceHistory,
  PriceStats,
  PurchaseRecommendation,
  SearchResult,
  HotProduct,
  PriceAlert,
  Coupon,
  Favorite,
  CouponMatchRequest
} from '../types';

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';
const MOCK_USER_ID = 'user-001';

const headers = {
  'Content-Type': 'application/json',
  'X-User-Id': MOCK_USER_ID,
};

async function request<T>(url: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${BASE_URL}${url}`, {
    ...options,
    headers: {
      ...headers,
      ...options.headers,
    },
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
}

export const productApi = {
  search: (q: string, page = 1, size = 20, category?: string): Promise<SearchResult> => {
    const params = new URLSearchParams({ q, page: String(page), size: String(size) });
    if (category) params.append('category', category);
    return request<SearchResult>(`/products/search?${params}`);
  },

  getById: (id: string): Promise<Product> => {
    return request<Product>(`/products/${id}`);
  },

  getPrices: (id: string): Promise<ComparisonResult> => {
    return request<ComparisonResult>(`/products/${id}/prices`);
  },

  getHistory: (id: string, days = 30): Promise<PriceHistory[]> => {
    return request<PriceHistory[]>(`/products/${id}/history?days=${days}`);
  },

  getStats: (id: string, days = 30): Promise<PriceStats> => {
    return request<PriceStats>(`/products/${id}/stats?days=${days}`);
  },

  getRecommendation: (id: string): Promise<PurchaseRecommendation> => {
    return request<PurchaseRecommendation>(`/products/${id}/recommendation`);
  },

  getHot: (limit = 20): Promise<HotProduct[]> => {
    return request<HotProduct[]>(`/products/hot?limit=${limit}`);
  },

  getCategories: (): Promise<string[]> => {
    return request<string[]>('/products/categories');
  },

  create: (data: Partial<Product>): Promise<Product> => {
    return request<Product>('/products', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },
};

export const couponApi = {
  getAll: (platform?: string): Promise<Coupon[]> => {
    const url = platform ? `/coupons?platform=${platform}` : '/coupons';
    return request<Coupon[]>(url);
  },

  match: (data: CouponMatchRequest): Promise<{ matched: Coupon[]; count: number; bestDeal: any }> => {
    return request('/coupons/match', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  getSummary: (productId: string, platform: string, price: number): Promise<any> => {
    return request(`/coupons/summary?productId=${productId}&platform=${platform}&price=${price}`);
  },

  getStats: (): Promise<Record<string, any>> => {
    return request('/coupons/stats');
  },

  create: (data: Partial<Coupon>): Promise<Coupon> => {
    return request<Coupon>('/coupons', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  deactivate: (id: string): Promise<{ success: boolean }> => {
    return request(`/coupons/${id}/deactivate`, {
      method: 'PUT',
    });
  },
};

export const alertApi = {
  getAll: (activeOnly = true): Promise<PriceAlert[]> => {
    return request<PriceAlert[]>(`/alerts?active_only=${activeOnly}`);
  },

  create: (data: Partial<PriceAlert>): Promise<PriceAlert> => {
    return request<PriceAlert>('/alerts', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  delete: (id: string): Promise<{ success: boolean }> => {
    return request(`/alerts/${id}`, {
      method: 'DELETE',
    });
  },

  deactivate: (id: string): Promise<{ success: boolean }> => {
    return request(`/alerts/${id}/deactivate`, {
      method: 'PUT',
    });
  },

  getStats: (): Promise<any> => {
    return request('/alerts/stats');
  },

  check: (): Promise<{ triggered: any[]; count: number }> => {
    return request('/alerts/check', {
      method: 'POST',
    });
  },
};

export const favoriteApi = {
  getAll: (): Promise<Favorite[]> => {
    return request<Favorite[]>('/user/favorites');
  },

  add: (productId: string): Promise<{ success: boolean; message?: string }> => {
    return request('/user/favorites', {
      method: 'POST',
      body: JSON.stringify({ productId }),
    });
  },

  remove: (id: string): Promise<{ success: boolean }> => {
    return request(`/user/favorites/${id}`, {
      method: 'DELETE',
    });
  },
};
