export interface Product {
  id: string;
  name: string;
  description: string;
  category: string;
  brand: string;
  model: string;
  imageUrl: string;
  createdAt: string;
}

export interface Coupon {
  id: string;
  platform: string;
  code: string;
  discount: number;
  discountType: 'percentage' | 'fixed';
  minAmount: number;
  maxDiscount: number;
  validFrom: string;
  validTo: string;
}

export interface PlatformPrice {
  id: string;
  productId: string;
  platform: 'taobao' | 'jd' | 'pdd' | 'suning';
  platformName: string;
  price: number;
  originalPrice: number;
  couponPrice?: number;
  productUrl: string;
  inStock: boolean;
  rating?: number;
  sales?: number;
  coupons: Coupon[];
  lastUpdated: string;
}

export interface PriceHistory {
  date: string;
  price: number;
  platform: string;
}

export interface PriceAlert {
  id: string;
  userId: string;
  productId: string;
  targetPrice: number;
  currentPrice?: number;
  platform: string;
  notifyType: 'email' | 'push' | 'sms';
  isActive: boolean;
  createdAt: string;
}

export interface ComparisonResult {
  product: Product;
  prices: PlatformPrice[];
  bestDeal: PlatformPrice;
  lowestEver: number;
  priceHistory: PriceHistory[];
  potentialSavings: number;
}

export interface PriceStats {
  lowest: number;
  highest: number;
  average: number;
  current: number;
  trend: number;
  volatility: number;
  isLowest: boolean;
}

export interface PurchaseRecommendation {
  recommendation: 'buy_now' | 'wait_for_drop' | 'wait_for_sale';
  confidence: number;
  predictedPrice?: number;
  bestMonth?: string;
  currentPrice: number;
  savingsIfWait: number;
}

export interface SearchResult {
  items: Product[];
  total: number;
  page: number;
  size: number;
  totalPages: number;
}

export interface HotProduct {
  product: Product;
  bestPrice: number;
  lowestEver: number;
  potentialSavings: number;
}

export interface Favorite {
  id: string;
  product: Product;
  createdAt: string;
}

export interface AlertNotification {
  alertId: string;
  userId: string;
  userEmail: string;
  productId: string;
  platform: string;
  targetPrice: number;
  currentPrice: number;
  savings: number;
  notifyType: string;
  triggeredAt: string;
}

export const PLATFORM_CONFIG: Record<string, { name: string; color: string; logo: string }> = {
  taobao: { name: '淘宝', color: '#ff4400', logo: '🐱' },
  jd: { name: '京东', color: '#e1251b', logo: '🐕' },
  pdd: { name: '拼多多', color: '#e02e24', logo: '🛒' },
  suning: { name: '苏宁', color: '#ffce00', logo: '🏬' },
  tmall: { name: '天猫', color: '#ff0036', logo: '🐱' },
};

export const RECOMMENDATION_TEXT: Record<string, { text: string; color: string; icon: string }> = {
  buy_now: { text: '建议立即购买', color: 'text-green-600', icon: '✅' },
  wait_for_drop: { text: '预计价格会下降，可以等待', color: 'text-orange-600', icon: '⏳' },
  wait_for_sale: { text: '建议等待促销活动', color: 'text-blue-600', icon: '🎁' },
};
