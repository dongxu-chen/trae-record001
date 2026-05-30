import type { TransactionStatus, TransactionMode, AlertLevel, DiagnosisSeverity } from '@/types';

export function statusColor(status: TransactionStatus | string): string {
  const map: Record<string, string> = {
    BEGIN: 'bg-blue-500/20 text-blue-400 border border-blue-500/30',
    COMMITTING: 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30',
    COMMITTED: 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30',
    ROLLBACKING: 'bg-amber-500/20 text-amber-400 border border-amber-500/30',
    ROLLEDBACK: 'bg-orange-500/20 text-orange-400 border border-orange-500/30',
    TIMEOUT: 'bg-red-500/20 text-red-400 border border-red-500/30',
    FAILED: 'bg-red-600/20 text-red-500 border border-red-600/30',
    UNKNOWN: 'bg-gray-500/20 text-gray-400 border border-gray-500/30',
  };
  return map[status] || map.UNKNOWN;
}

export function modeColor(mode: TransactionMode | string): string {
  const map: Record<string, string> = {
    TCC: 'bg-purple-500/20 text-purple-400 border border-purple-500/30',
    SAGA: 'bg-amber-500/20 text-amber-400 border border-amber-500/30',
    AT: 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30',
    XA: 'bg-sky-500/20 text-sky-400 border border-sky-500/30',
  };
  return map[mode] || map.AT;
}

export function alertLevelColor(level: AlertLevel | string): string {
  const map: Record<string, string> = {
    INFO: 'bg-blue-500/20 text-blue-400 border border-blue-500/30',
    WARNING: 'bg-amber-500/20 text-amber-400 border border-amber-500/30',
    CRITICAL: 'bg-red-500/20 text-red-400 border border-red-500/30',
    EMERGENCY: 'bg-red-700/20 text-red-500 border border-red-700/30',
  };
  return map[level] || map.INFO;
}

export function severityColor(severity: DiagnosisSeverity | string): string {
  const map: Record<string, string> = {
    LOW: 'bg-blue-500/20 text-blue-400',
    MEDIUM: 'bg-amber-500/20 text-amber-400',
    HIGH: 'bg-red-500/20 text-red-400',
    CRITICAL: 'bg-red-700/20 text-red-500',
  };
  return map[severity] || map.LOW;
}

export function severityDot(severity: DiagnosisSeverity | string): string {
  const map: Record<string, string> = {
    LOW: 'bg-blue-400',
    MEDIUM: 'bg-amber-400',
    HIGH: 'bg-red-400',
    CRITICAL: 'bg-red-600 animate-pulse',
  };
  return map[severity] || 'bg-gray-400';
}

export function formatTime(iso: string | null | undefined): string {
  if (!iso) return '-';
  try {
    return new Date(iso).toLocaleString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  } catch {
    return iso;
  }
}

export function formatDuration(beginTime: string | null, endTime: string | null): string {
  if (!beginTime) return '-';
  const start = new Date(beginTime).getTime();
  const end = endTime ? new Date(endTime).getTime() : Date.now();
  const ms = end - start;
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  return `${(ms / 60000).toFixed(1)}m`;
}

export function truncate(str: string | null | undefined, len = 16): string {
  if (!str) return '-';
  return str.length > len ? str.slice(0, len) + '...' : str;
}
