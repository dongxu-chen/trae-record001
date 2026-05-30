import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { METRIC_DISPLAY_CONFIG } from '@/utils/chart-config';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatTimestamp(iso: string): string {
  const d = new Date(iso);
  const now = new Date();
  const isToday = d.toDateString() === now.toDateString();
  const hh = String(d.getHours()).padStart(2, '0');
  const mm = String(d.getMinutes()).padStart(2, '0');
  const ss = String(d.getSeconds()).padStart(2, '0');
  if (isToday) return `${hh}:${mm}:${ss}`;
  const MM = String(d.getMonth() + 1).padStart(2, '0');
  const DD = String(d.getDate()).padStart(2, '0');
  return `${MM}-${DD} ${hh}:${mm}`;
}

export function formatMetricValue(value: number, metric: string): string {
  const config = METRIC_DISPLAY_CONFIG[metric];
  if (!config) return String(value);
  const formatted = value.toFixed(config.decimals);
  return config.unit ? `${formatted}${config.unit}` : formatted;
}

export function getAlertLevelColor(level: 'warning' | 'danger' | 'critical'): string {
  const map = {
    warning: '#f59e0b',
    danger: '#ef4444',
    critical: '#dc2626',
  };
  return map[level];
}

export function getAlertLevelLabel(level: 'warning' | 'danger' | 'critical'): string {
  const map = {
    warning: '警告',
    danger: '危险',
    critical: '严重',
  };
  return map[level];
}

export function getOperatorLabel(operator: string): string {
  const map: Record<string, string> = {
    '>': '大于',
    '<': '小于',
    '>=': '大于等于',
    '<=': '小于等于',
    '==': '等于',
    '!=': '不等于',
  };
  return map[operator] || operator;
}
