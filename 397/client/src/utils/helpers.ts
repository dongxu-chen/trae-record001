export const formatDate = (dateString: string): string => {
  const date = new Date(dateString);
  return date.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  });
};

export const formatNumber = (num: number): string => {
  if (num >= 10000) {
    return (num / 10000).toFixed(1) + 'w';
  }
  if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'k';
  }
  return num.toString();
};

export const getCategoryInfo = (category: string) => {
  const categories: Record<string, { label: string; color: string }> = {
    operation: { label: '运营', color: '#3B82F6' },
    sales: { label: '销售', color: '#10B981' },
    finance: { label: '财务', color: '#F59E0B' },
    ops: { label: '运维', color: '#8B5CF6' }
  };
  return categories[category] || { label: '未知', color: '#6B7280' };
};

export const getComplexityInfo = (complexity: string) => {
  const complexities: Record<string, { label: string; color: string }> = {
    simple: { label: '简单', color: '#10B981' },
    medium: { label: '中等', color: '#F59E0B' },
    complex: { label: '复杂', color: '#EF4444' }
  };
  return complexities[complexity] || { label: '未知', color: '#6B7280' };
};

export const generateId = (): string => {
  return Date.now().toString(36) + Math.random().toString(36).substr(2);
};

export const debounce = <T extends (...args: any[]) => any>(
  func: T,
  wait: number
): ((...args: Parameters<T>) => void) => {
  let timeout: NodeJS.Timeout;
  return (...args: Parameters<T>) => {
    clearTimeout(timeout);
    timeout = setTimeout(() => func(...args), wait);
  };
};
