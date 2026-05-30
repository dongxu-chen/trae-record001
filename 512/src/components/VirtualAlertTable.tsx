import { useRef, useMemo, useCallback, useState, useEffect } from 'react';
import { FixedSizeList as List } from 'react-window';
import { Eye, Check, ChevronLeft, ChevronRight, Loader2, MoreVertical } from 'lucide-react';
import type { AlertRecord } from '@/types';
import { formatTimestamp, formatMetricValue } from '@/utils/helpers';
import { METRIC_DISPLAY_CONFIG } from '@/utils/chart-config';
import LevelBadge from '@/components/LevelBadge';
import FeedbackBadge from '@/components/FeedbackBadge';
import { useAlertStore } from '@/stores/alert-store';

const ROW_HEIGHT = 52;
const TABLE_HEIGHT = 600;
const HEADER_HEIGHT = 48;

const thClass = 'px-4 py-3 text-left text-xs font-medium text-brand-text-secondary uppercase tracking-wider';

interface VirtualAlertTableProps {
  alerts: AlertRecord[];
  total: number;
  page: number;
  pageSize: number;
  loading?: boolean;
  hasMore?: boolean;
  onLoadMore?: () => void;
  onPageChange?: (page: number) => void;
  onAcknowledge: (id: string) => void;
  onViewDetail: (alert: AlertRecord) => void;
}

function QuickFeedbackMenu({ alert }: { alert: AlertRecord }) {
  const [open, setOpen] = useState(false);
  const submitFeedback = useAlertStore(s => s.submitFeedback);

  const handleFeedback = async (type: 'true_positive' | 'false_positive' | 'needs_adjustment') => {
    await submitFeedback(alert.id, type);
    setOpen(false);
  };

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="rounded p-1.5 text-brand-text-secondary hover:bg-brand-card hover:text-brand-text-primary transition-colors"
        title="快速反馈"
      >
        <MoreVertical className="h-4 w-4" />
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="absolute right-0 top-full mt-1 z-20 w-36 rounded-lg border border-brand-border bg-brand-surface shadow-xl py-1 animate-fade-in">
            <button
              onClick={() => handleFeedback('true_positive')}
              className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs text-brand-green hover:bg-brand-card transition-colors"
            >
              准确预警
            </button>
            <button
              onClick={() => handleFeedback('false_positive')}
              className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs text-brand-red hover:bg-brand-card transition-colors"
            >
              误报
            </button>
            <button
              onClick={() => handleFeedback('needs_adjustment')}
              className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs text-brand-amber hover:bg-brand-card transition-colors"
            >
              需要调整
            </button>
          </div>
        </>
      )}
    </div>
  );
}

function AlertRow({ index, style, data }: { index: number; style: React.CSSProperties; data: AlertRecord[] }) {
  const alert = data[index];
  if (!alert) return null;

  const metricCfg = METRIC_DISPLAY_CONFIG[alert.metric];
  const triggerStr = formatMetricValue(alert.triggerValue, alert.metric);
  const thresholdStr = formatMetricValue(alert.thresholdValue, alert.metric);
  const isOverThreshold = alert.triggerValue > alert.thresholdValue;
  const isOdd = index % 2 === 1;

  const handleView = useCallback(() => {
    // handled by prop via context
  }, []);

  return (
    <div
      style={style}
      className={cn(
        'flex items-center border-b border-brand-border transition-colors',
        isOdd ? 'bg-brand-card/30' : ''
      )}
    >
      <div className="px-4 py-3 w-32 text-xs text-brand-text-primary font-mono">
        {formatTimestamp(alert.createdAt)}
      </div>
      <div className="px-4 py-3 w-28 text-sm text-brand-text-primary">
        {metricCfg?.label || alert.metric}
      </div>
      <div className="px-4 py-3 w-20">
        <LevelBadge level={alert.level} size="sm" />
      </div>
      <div className="px-4 py-3 w-24">
        <span
          className={cn(
            'text-sm font-semibold',
            isOverThreshold ? 'text-brand-red' : 'text-brand-amber'
          )}
        >
          {triggerStr}
        </span>
      </div>
      <div className="px-4 py-3 w-28 text-sm text-brand-text-primary font-mono">
        {thresholdStr}
      </div>
      <div className="px-4 py-3 w-40 text-sm text-brand-text-primary truncate">
        {alert.ruleName}
      </div>
      <div className="px-4 py-3 w-24">
        {alert.acknowledged ? (
          <span className="inline-flex items-center rounded-full bg-brand-green/15 px-2 py-0.5 text-xs font-medium text-brand-green">
            已确认
          </span>
        ) : (
          <span className="inline-flex items-center rounded-full bg-brand-amber/15 px-2 py-0.5 text-xs font-medium text-brand-amber">
            未确认
          </span>
        )}
      </div>
      <div className="px-4 py-3 w-12">
        <FeedbackBadge type={alert.feedbackType} />
      </div>
      <div className="px-4 py-3 flex items-center gap-1">
        <button
          onClick={() => {
            const evt = new CustomEvent('view-alert-detail', { detail: alert });
            window.dispatchEvent(evt);
          }}
          className="rounded p-1.5 text-brand-text-secondary hover:bg-brand-card hover:text-brand-cyan transition-colors"
          title="查看"
        >
          <Eye className="h-4 w-4" />
        </button>
        {!alert.acknowledged && (
          <button
            onClick={() => {
              const evt = new CustomEvent('acknowledge-alert', { detail: alert.id });
              window.dispatchEvent(evt);
            }}
            className="rounded p-1.5 text-brand-text-secondary hover:bg-brand-card hover:text-brand-green transition-colors"
            title="确认"
          >
            <Check className="h-4 w-4" />
          </button>
        )}
        <QuickFeedbackMenu alert={alert} />
      </div>
    </div>
  );
}

function cn(...classes: (string | false | null | undefined)[]) {
  return classes.filter(Boolean).join(' ');
}

export default function VirtualAlertTable({
  alerts,
  total,
  page,
  pageSize,
  loading = false,
  onPageChange,
  onAcknowledge,
  onViewDetail,
}: VirtualAlertTableProps) {
  const listRef = useRef<List>(null);
  const totalPages = useMemo(() => Math.max(1, Math.ceil(total / pageSize)), [total, pageSize]);

  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollToItem(0, 'start');
    }
  }, [alerts]);

  if (alerts.length === 0 && !loading) {
    return (
      <div className="flex flex-col items-center justify-center rounded-xl border border-brand-border bg-brand-surface py-16">
        <div className="text-4xl mb-3 opacity-30">📭</div>
        <p className="text-sm text-brand-text-secondary">暂无匹配的预警记录</p>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-brand-border bg-brand-surface overflow-hidden">
      <div className="w-full overflow-x-auto">
        <div className="min-w-[900px]">
          <div
            className="flex items-center border-b border-brand-border bg-brand-card/50 sticky top-0 z-10"
            style={{ height: HEADER_HEIGHT }}
          >
            <div className={cn(thClass, 'w-32')}>时间</div>
            <div className={cn(thClass, 'w-28')}>指标</div>
            <div className={cn(thClass, 'w-20')}>预警等级</div>
            <div className={cn(thClass, 'w-24')}>触发值</div>
            <div className={cn(thClass, 'w-28')}>阈值</div>
            <div className={cn(thClass, 'w-40')}>规则</div>
            <div className={cn(thClass, 'w-24')}>状态</div>
            <div className={cn(thClass, 'w-12')}>反馈</div>
            <div className={cn(thClass)}>操作</div>
          </div>

          {loading ? (
            <div className="flex flex-col items-center justify-center py-16" style={{ height: TABLE_HEIGHT }}>
              <Loader2 className="h-8 w-8 text-brand-cyan animate-spin mb-3" />
              <p className="text-sm text-brand-text-secondary">加载中...</p>
            </div>
          ) : (
            <List
              ref={listRef as React.Ref<List>}
              height={TABLE_HEIGHT}
              itemCount={alerts.length}
              itemSize={ROW_HEIGHT}
              width="100%"
              itemData={alerts}
              className="scrollbar-thin"
            >
              {AlertRow}
            </List>
          )}
        </div>
      </div>

      <div className="flex items-center justify-between border-t border-brand-border px-4 py-3">
        <span className="text-xs text-brand-text-secondary">
          共 {total} 条记录
        </span>
        {onPageChange && (
          <div className="flex items-center gap-2">
            <button
              onClick={() => onPageChange(page - 1)}
              disabled={page <= 1 || loading}
              className="rounded p-1.5 text-brand-text-secondary hover:bg-brand-card hover:text-brand-text-primary disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <span className="text-xs text-brand-text-secondary">
              第 {page} / {totalPages} 页
            </span>
            <button
              onClick={() => onPageChange(page + 1)}
              disabled={page >= totalPages || loading}
              className="rounded p-1.5 text-brand-text-secondary hover:bg-brand-card hover:text-brand-text-primary disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
