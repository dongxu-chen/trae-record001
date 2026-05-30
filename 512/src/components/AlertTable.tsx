import { Eye, Check, ChevronLeft, ChevronRight } from 'lucide-react';
import type { AlertRecord } from '@/types';
import { formatTimestamp, formatMetricValue } from '@/utils/helpers';
import { METRIC_DISPLAY_CONFIG } from '@/utils/chart-config';
import LevelBadge from '@/components/LevelBadge';

interface AlertTableProps {
  alerts: AlertRecord[];
  total: number;
  page: number;
  pageSize: number;
  onPageChange: (page: number) => void;
  onAcknowledge: (id: string) => void;
  onViewDetail: (alert: AlertRecord) => void;
}

const thClass = 'px-4 py-3 text-left text-xs font-medium text-brand-text-secondary uppercase tracking-wider';
const tdClass = 'px-4 py-3 text-sm text-brand-text-primary';
const totalPages = (total: number, pageSize: number) => Math.max(1, Math.ceil(total / pageSize));

export default function AlertTable({
  alerts, total, page, pageSize, onPageChange, onAcknowledge, onViewDetail,
}: AlertTableProps) {
  const pages = totalPages(total, pageSize);

  if (alerts.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center rounded-xl border border-brand-border bg-brand-surface py-16">
        <div className="text-4xl mb-3 opacity-30">📭</div>
        <p className="text-sm text-brand-text-secondary">暂无匹配的预警记录</p>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-brand-border bg-brand-surface overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-brand-border bg-brand-card/50">
              <th className={thClass}>时间</th>
              <th className={thClass}>指标</th>
              <th className={thClass}>预警等级</th>
              <th className={thClass}>触发值</th>
              <th className={thClass}>阈值</th>
              <th className={thClass}>规则</th>
              <th className={thClass}>状态</th>
              <th className={thClass}>操作</th>
            </tr>
          </thead>
          <tbody>
            {alerts.map((alert, idx) => {
              const metricCfg = METRIC_DISPLAY_CONFIG[alert.metric];
              const triggerStr = formatMetricValue(alert.triggerValue, alert.metric);
              const thresholdStr = formatMetricValue(alert.thresholdValue, alert.metric);
              const isOverThreshold = alert.triggerValue > alert.thresholdValue;

              return (
                <tr
                  key={alert.id}
                  className={idx % 2 === 1 ? 'bg-brand-card/30' : ''}
                >
                  <td className={`${tdClass} font-mono text-xs`}>
                    {formatTimestamp(alert.createdAt)}
                  </td>
                  <td className={tdClass}>{metricCfg?.label || alert.metric}</td>
                  <td className={tdClass}>
                    <LevelBadge level={alert.level} size="sm" />
                  </td>
                  <td className={tdClass}>
                    <span className={isOverThreshold ? 'text-brand-red font-semibold' : 'text-brand-amber font-semibold'}>
                      {triggerStr}
                    </span>
                  </td>
                  <td className={tdClass}>{thresholdStr}</td>
                  <td className={`${tdClass} max-w-[160px] truncate`}>{alert.ruleName}</td>
                  <td className={tdClass}>
                    {alert.acknowledged ? (
                      <span className="inline-flex items-center rounded-full bg-brand-green/15 px-2 py-0.5 text-xs font-medium text-brand-green">
                        已确认
                      </span>
                    ) : (
                      <span className="inline-flex items-center rounded-full bg-brand-amber/15 px-2 py-0.5 text-xs font-medium text-brand-amber">
                        未确认
                      </span>
                    )}
                  </td>
                  <td className={tdClass}>
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => onViewDetail(alert)}
                        className="rounded p-1.5 text-brand-text-secondary hover:bg-brand-card hover:text-brand-cyan transition-colors"
                        title="查看"
                      >
                        <Eye className="h-4 w-4" />
                      </button>
                      {!alert.acknowledged && (
                        <button
                          onClick={() => onAcknowledge(alert.id)}
                          className="rounded p-1.5 text-brand-text-secondary hover:bg-brand-card hover:text-brand-green transition-colors"
                          title="确认"
                        >
                          <Check className="h-4 w-4" />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between border-t border-brand-border px-4 py-3">
        <span className="text-xs text-brand-text-secondary">
          共 {total} 条记录
        </span>
        <div className="flex items-center gap-2">
          <button
            onClick={() => onPageChange(page - 1)}
            disabled={page <= 1}
            className="rounded p-1.5 text-brand-text-secondary hover:bg-brand-card hover:text-brand-text-primary disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
          <span className="text-xs text-brand-text-secondary">
            第 {page} / {pages} 页
          </span>
          <button
            onClick={() => onPageChange(page + 1)}
            disabled={page >= pages}
            className="rounded p-1.5 text-brand-text-secondary hover:bg-brand-card hover:text-brand-text-primary disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
