import type { PlatformPrice, PriceHistory } from '../types';

export function formatPrice(price: number | string | undefined | null): string {
  if (price === undefined || price === null) return '¥--';
  const num = typeof price === 'string' ? parseFloat(price) : price;
  if (isNaN(num)) return '¥--';
  return `¥${num.toFixed(2)}`;
}

export function formatDiscount(discount: number, type: 'percentage' | 'fixed'): string {
  if (type === 'percentage') {
    return `${discount}% OFF`;
  }
  return formatPrice(discount);
}

export function formatSavings(original: number, current: number): string {
  const savings = original - current;
  const percent = ((savings / original) * 100).toFixed(1);
  return `省${formatPrice(savings)} (${percent}%)`;
}

export function formatDate(dateStr: string | Date): string {
  const date = typeof dateStr === 'string' ? new Date(dateStr) : dateStr;
  return date.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  });
}

export function formatDateTime(dateStr: string | Date): string {
  const date = typeof dateStr === 'string' ? new Date(dateStr) : dateStr;
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function formatRelativeTime(dateStr: string | Date): string {
  const date = typeof dateStr === 'string' ? new Date(dateStr) : dateStr;
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMins < 1) return '刚刚';
  if (diffMins < 60) return `${diffMins}分钟前`;
  if (diffHours < 24) return `${diffHours}小时前`;
  if (diffDays < 7) return `${diffDays}天前`;
  return formatDate(date);
}

export function formatSales(sales: number | undefined): string {
  if (!sales) return '0';
  if (sales >= 10000) {
    return `${(sales / 10000).toFixed(1)}万`;
  }
  return sales.toString();
}

export function getPriceChangeClass(current: number, previous: number): string {
  if (current < previous) return 'text-green-600';
  if (current > previous) return 'text-red-600';
  return 'text-gray-600';
}

export function getPriceChangeIcon(current: number, previous: number): string {
  if (current < previous) return '↓';
  if (current > previous) return '↑';
  return '→';
}

export function getPriceColor(price: number, lowest: number, highest: number): string {
  if (price <= lowest * 1.01) return 'text-green-600';
  if (price >= highest * 0.99) return 'text-red-600';
  return 'text-gray-900';
}

export function aggregatePriceHistory(history: PriceHistory[]): { date: string; price: number }[] {
  const aggregated: Record<string, number[]> = {};

  history.forEach((item) => {
    const date = item.date;
    if (!aggregated[date]) {
      aggregated[date] = [];
    }
    aggregated[date].push(item.price);
  });

  return Object.entries(aggregated)
    .map(([date, prices]) => ({
      date,
      price: prices.reduce((a, b) => a + b, 0) / prices.length,
    }))
    .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());
}

export function getPlatformPriceById(prices: PlatformPrice[], platform: string): PlatformPrice | undefined {
  return prices.find((p) => p.platform === platform);
}

export function getLowestPrice(prices: PlatformPrice[]): number {
  const inStock = prices.filter((p) => p.inStock);
  if (inStock.length === 0) return 0;
  return Math.min(...inStock.map((p) => p.couponPrice ?? p.price));
}

export function getHighestPrice(prices: PlatformPrice[]): number {
  return Math.max(...prices.map((p) => p.originalPrice ?? p.price));
}

export function calculatePotentialSavings(prices: PlatformPrice[]): number {
  const highest = getHighestPrice(prices);
  const lowest = getLowestPrice(prices);
  return highest - lowest;
}

export function isPriceDrop(
  history: PriceHistory[],
  currentPrice: number,
  threshold: number = 0.05
): boolean {
  if (history.length < 7) return false;
  const recentAvg = history
    .slice(-7)
    .reduce((a, b) => a + b.price, 0) / 7;
  return currentPrice < recentAvg * (1 - threshold);
}
