import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import type { SeverityLevel, RiskLevel } from '@/types';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function severityColor(severity: SeverityLevel): string {
  const map: Record<SeverityLevel, string> = {
    CRITICAL: 'text-dep-critical',
    HIGH: 'text-dep-high',
    MEDIUM: 'text-dep-medium',
    LOW: 'text-dep-low',
  };
  return map[severity] || 'text-dep-muted';
}

export function severityBg(severity: SeverityLevel): string {
  const map: Record<SeverityLevel, string> = {
    CRITICAL: 'bg-dep-critical/15 border-dep-critical/30',
    HIGH: 'bg-dep-high/15 border-dep-high/30',
    MEDIUM: 'bg-dep-medium/15 border-dep-medium/30',
    LOW: 'bg-dep-low/15 border-dep-low/30',
  };
  return map[severity] || 'bg-dep-card border-dep-border';
}

export function riskColor(risk: RiskLevel): string {
  const map: Record<RiskLevel, string> = {
    SAFE: 'text-dep-safe',
    LOW_RISK: 'text-dep-low',
    MEDIUM_RISK: 'text-dep-medium',
    HIGH_RISK: 'text-dep-critical',
  };
  return map[risk] || 'text-dep-muted';
}

export function riskBg(risk: RiskLevel): string {
  const map: Record<RiskLevel, string> = {
    SAFE: 'bg-dep-safe/15 border-dep-safe/30',
    LOW_RISK: 'bg-dep-low/15 border-dep-low/30',
    MEDIUM_RISK: 'bg-dep-medium/15 border-dep-medium/30',
    HIGH_RISK: 'bg-dep-critical/15 border-dep-critical/30',
  };
  return map[risk] || 'bg-dep-card border-dep-border';
}

export function healthScoreColor(score: number): string {
  if (score >= 80) return 'text-dep-safe';
  if (score >= 60) return 'text-dep-medium';
  if (score >= 40) return 'text-dep-high';
  return 'text-dep-critical';
}

export function formatNumber(n: number): string {
  return n.toLocaleString();
}

export function timeAgo(date: string): string {
  const now = new Date();
  const d = new Date(date);
  const diff = now.getTime() - d.getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return '刚刚';
  if (mins < 60) return `${mins}分钟前`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}小时前`;
  const days = Math.floor(hours / 24);
  return `${days}天前`;
}
