import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';
import 'dayjs/locale/zh-cn';

dayjs.extend(relativeTime);
dayjs.locale('zh-cn');

export const formatTime = (timestamp: number, format: string = 'YYYY-MM-DD HH:mm:ss'): string => {
  return dayjs(timestamp).format(format);
};

export const formatRelativeTime = (timestamp: number): string => {
  return dayjs(timestamp).fromNow();
};

export const formatNumber = (num: number, decimals: number = 0): string => {
  return num.toLocaleString('zh-CN', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
};

export const formatPercent = (value: number, decimals: number = 1): string => {
  return `${value.toFixed(decimals)}%`;
};

export const formatDuration = (seconds: number): string => {
  if (seconds < 60) return `${Math.round(seconds)}秒`;
  if (seconds < 3600) return `${Math.round(seconds / 60)}分钟`;
  if (seconds < 86400) return `${Math.round(seconds / 3600)}小时`;
  return `${Math.round(seconds / 86400)}天`;
};

export const formatBytes = (bytes: number): string => {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`;
};

export const getPriorityColor = (priority: string): string => {
  switch (priority?.toUpperCase()) {
    case 'CRITICAL':
      return '#EF4444';
    case 'WARNING':
      return '#F59E0B';
    case 'INFO':
      return '#3B82F6';
    default:
      return '#6B7280';
  }
};

export const getSeverityColor = (severity: string): string => {
  switch (severity?.toUpperCase()) {
    case 'HIGH':
      return '#EF4444';
    case 'MEDIUM':
      return '#F59E0B';
    case 'LOW':
      return '#10B981';
    default:
      return '#6B7280';
  }
};

export const getScoreColor = (score: number): string => {
  if (score >= 0.8) return '#EF4444';
  if (score >= 0.6) return '#F59E0B';
  if (score >= 0.4) return '#06B6D4';
  return '#10B981';
};

export const getTrendColor = (value: number, isPositive: boolean = true): string => {
  if (value > 0) return isPositive ? '#10B981' : '#EF4444';
  if (value < 0) return isPositive ? '#EF4444' : '#10B981';
  return '#6B7280';
};

export const truncateText = (text: string, maxLength: number): string => {
  if (text.length <= maxLength) return text;
  return `${text.substring(0, maxLength)}...`;
};

export const generateChartColors = (count: number): string[] => {
  const baseColors = [
    '#3B82F6',
    '#10B981',
    '#F59E0B',
    '#EF4444',
    '#8B5CF6',
    '#06B6D4',
    '#EC4899',
    '#6366F1',
    '#14B8A6',
    '#F97316',
  ];
  
  const colors: string[] = [];
  for (let i = 0; i < count; i++) {
    colors.push(baseColors[i % baseColors.length]);
  }
  return colors;
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

export const throttle = <T extends (...args: any[]) => any>(
  func: T,
  limit: number
): ((...args: Parameters<T>) => void) => {
  let inThrottle: boolean;
  return (...args: Parameters<T>) => {
    if (!inThrottle) {
      func(...args);
      inThrottle = true;
      setTimeout(() => (inThrottle = false), limit);
    }
  };
};
