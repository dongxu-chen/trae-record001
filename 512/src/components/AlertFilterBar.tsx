import { Filter } from 'lucide-react';
import type { AlertHistoryQuery } from '@/types';
import { METRIC_DISPLAY_CONFIG } from '@/utils/chart-config';

interface AlertFilterBarProps {
  query: AlertHistoryQuery;
  onChange: (query: AlertHistoryQuery) => void;
  onReset: () => void;
}

const LEVEL_OPTIONS = [
  { value: '', label: '全部' },
  { value: 'warning', label: '警告' },
  { value: 'danger', label: '危险' },
  { value: 'critical', label: '严重' },
];

const METRIC_OPTIONS = [
  { value: '', label: '全部' },
  ...Object.entries(METRIC_DISPLAY_CONFIG).map(([key, cfg]) => ({
    value: key,
    label: cfg.label,
  })),
];

const ACK_OPTIONS = [
  { value: '', label: '全部' },
  { value: 'false', label: '未确认' },
  { value: 'true', label: '已确认' },
];

const selectClass =
  'rounded-lg border border-brand-border bg-brand-card px-3 py-1.5 text-sm text-brand-text-primary focus:border-brand-cyan focus:outline-none focus:ring-1 focus:ring-brand-cyan/30';
const inputClass =
  'rounded-lg border border-brand-border bg-brand-card px-3 py-1.5 text-sm text-brand-text-primary focus:border-brand-cyan focus:outline-none focus:ring-1 focus:ring-brand-cyan/30 [color-scheme:dark]';

export default function AlertFilterBar({ query, onChange, onReset }: AlertFilterBarProps) {
  const update = (patch: Partial<AlertHistoryQuery>) => {
    onChange({ ...query, ...patch, page: 1 });
  };

  return (
    <div className="flex flex-wrap items-center gap-3 rounded-xl border border-brand-border bg-brand-surface p-4">
      <Filter className="h-4 w-4 text-brand-text-secondary shrink-0" />

      <div className="flex items-center gap-2">
        <label className="text-xs text-brand-text-secondary whitespace-nowrap">预警等级</label>
        <select
          value={query.level || ''}
          onChange={(e) => update({ level: (e.target.value || undefined) as AlertHistoryQuery['level'] })}
          className={selectClass}
        >
          {LEVEL_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
      </div>

      <div className="flex items-center gap-2">
        <label className="text-xs text-brand-text-secondary whitespace-nowrap">监控指标</label>
        <select
          value={query.metric || ''}
          onChange={(e) => update({ metric: e.target.value || undefined })}
          className={selectClass}
        >
          {METRIC_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
      </div>

      <div className="flex items-center gap-2">
        <label className="text-xs text-brand-text-secondary whitespace-nowrap">确认状态</label>
        <select
          value={query.acknowledged === undefined ? '' : String(query.acknowledged)}
          onChange={(e) => {
            const v = e.target.value;
            update({ acknowledged: v === '' ? undefined : v === 'true' });
          }}
          className={selectClass}
        >
          {ACK_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
      </div>

      <div className="flex items-center gap-2">
        <label className="text-xs text-brand-text-secondary whitespace-nowrap">开始</label>
        <input
          type="datetime-local"
          value={query.startTime || ''}
          onChange={(e) => update({ startTime: e.target.value || undefined })}
          className={inputClass}
        />
      </div>

      <div className="flex items-center gap-2">
        <label className="text-xs text-brand-text-secondary whitespace-nowrap">结束</label>
        <input
          type="datetime-local"
          value={query.endTime || ''}
          onChange={(e) => update({ endTime: e.target.value || undefined })}
          className={inputClass}
        />
      </div>

      <button
        onClick={onReset}
        className="rounded-lg border border-brand-border px-3 py-1.5 text-sm text-brand-text-secondary hover:bg-brand-card hover:text-brand-text-primary transition-colors"
      >
        重置
      </button>
    </div>
  );
}
