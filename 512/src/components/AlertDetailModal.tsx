import { useEffect, useRef, useState } from 'react';
import ReactECharts from 'echarts-for-react';
import { AlertTriangle, Check, X, ThumbsUp, ThumbsDown, MessageSquare, Send } from 'lucide-react';
import type { AlertRecord, AlertFeedback } from '@/types';
import { formatTimestamp, formatMetricValue, cn } from '@/utils/helpers';
import { METRIC_DISPLAY_CONFIG, buildAlertChartOption } from '@/utils/chart-config';
import LevelBadge from '@/components/LevelBadge';
import FeedbackBadge from '@/components/FeedbackBadge';
import { useAlertStore } from '@/stores/alert-store';

interface AlertDetailModalProps {
  open: boolean;
  alert: AlertRecord | null;
  onClose: () => void;
  onAcknowledge?: (id: string) => void;
}

const FEEDBACK_OPTIONS = [
  { type: 'true_positive' as const, label: '准确预警', icon: ThumbsUp, color: 'text-brand-green hover:bg-brand-green/15' },
  { type: 'false_positive' as const, label: '误报', icon: ThumbsDown, color: 'text-brand-red hover:bg-brand-red/15' },
  { type: 'needs_adjustment' as const, label: '需要调整', icon: AlertTriangle, color: 'text-brand-amber hover:bg-brand-amber/15' },
];

export default function AlertDetailModal({ open, alert, onClose, onAcknowledge }: AlertDetailModalProps) {
  const panelRef = useRef<HTMLDivElement>(null);
  const [selectedFeedback, setSelectedFeedback] = useState<'true_positive' | 'false_positive' | 'needs_adjustment' | null>(null);
  const [feedbackComment, setFeedbackComment] = useState('');
  const [feedbacks, setFeedbacks] = useState<AlertFeedback[]>([]);
  const submitFeedback = useAlertStore(s => s.submitFeedback);

  useEffect(() => {
    if (open) {
      setSelectedFeedback(null);
      setFeedbackComment('');
      setFeedbacks([]);
    }
  }, [open, alert?.id]);

  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [open, onClose]);

  useEffect(() => {
    if (open) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => { document.body.style.overflow = ''; };
  }, [open]);

  const handleSubmitFeedback = async () => {
    if (!selectedFeedback || !alert) return;
    await submitFeedback(alert.id, selectedFeedback, feedbackComment.trim() || undefined);
    setFeedbacks(prev => [{
      id: Date.now().toString(),
      alertId: alert.id,
      ruleId: alert.ruleId,
      type: selectedFeedback,
      comment: feedbackComment.trim() || undefined,
      createdAt: new Date().toISOString(),
    }, ...prev]);
    setSelectedFeedback(null);
    setFeedbackComment('');
  };

  if (!open || !alert) return null;

  const metricCfg = METRIC_DISPLAY_CONFIG[alert.metric];
  const triggerIndex = alert.snapshot.seriesData.length - 1;
  const chartOption = buildAlertChartOption(alert.metric, alert.snapshot, triggerIndex);

  const metrics = [
    { label: '触发值', value: formatMetricValue(alert.triggerValue, alert.metric) },
    { label: '阈值', value: formatMetricValue(alert.thresholdValue, alert.metric) },
    { label: '指标', value: metricCfg?.label || alert.metric },
    { label: '表达式', value: alert.expression },
  ];

  const handleOverlayClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) onClose();
  };

  return (
    <div
      onClick={handleOverlayClick}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm animate-fade-in"
    >
      <div
        ref={panelRef}
        className="relative w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-xl border border-brand-border bg-brand-surface shadow-2xl animate-slide-up"
      >
        <div className="sticky top-0 z-10 flex items-center justify-between border-b border-brand-border bg-brand-surface/95 backdrop-blur-sm px-6 py-4">
          <div className="flex items-center gap-3">
            <AlertTriangle className="h-5 w-5 text-brand-amber" />
            <LevelBadge level={alert.level} active />
            <span className="text-sm font-semibold text-brand-text-primary">{alert.ruleName}</span>
          </div>
          <div className="flex items-center gap-3">
            <span className="font-mono text-xs text-brand-text-secondary">
              {formatTimestamp(alert.createdAt)}
            </span>
            <button
              onClick={onClose}
              className="rounded p-1 text-brand-text-secondary hover:bg-brand-card hover:text-brand-text-primary transition-colors"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>

        <div className="px-6 py-4 space-y-5">
          <div className="grid grid-cols-2 gap-3">
            {metrics.map((m) => (
              <div key={m.label} className="rounded-lg bg-brand-card p-3">
                <div className="text-xs text-brand-text-secondary mb-1">{m.label}</div>
                <div className="text-sm font-mono text-brand-text-primary truncate">{m.value}</div>
              </div>
            ))}
          </div>

          <div>
            <h3 className="text-xs font-medium text-brand-text-secondary mb-2">趋势回放</h3>
            <div className="rounded-lg border border-brand-border bg-brand-card p-2">
              <ReactECharts option={chartOption} style={{ height: 250 }} />
            </div>
          </div>

          <div>
            <h3 className="text-xs font-medium text-brand-text-secondary mb-2">告警信息</h3>
            <p className="text-sm text-brand-text-primary leading-relaxed">{alert.message}</p>
          </div>

          <div className="border-t border-brand-border pt-4">
            <h3 className="text-xs font-medium text-brand-text-secondary mb-3 flex items-center gap-1.5">
              <MessageSquare className="h-3.5 w-3.5" />
              反馈评价
            </h3>
            {!alert.hasFeedback ? (
              <div className="space-y-3">
                <div className="flex gap-2">
                  {FEEDBACK_OPTIONS.map((opt) => {
                    const Icon = opt.icon;
                    const isSelected = selectedFeedback === opt.type;
                    return (
                      <button
                        key={opt.type}
                        onClick={() => setSelectedFeedback(isSelected ? null : opt.type)}
                        className={cn(
                          'flex-1 flex items-center justify-center gap-1.5 rounded-lg px-3 py-2 text-sm transition-all',
                          isSelected
                            ? opt.color.replace('hover:', '') + ' ring-1 ring-current'
                            : 'bg-brand-card text-brand-text-secondary hover:text-brand-text-primary'
                        )}
                      >
                        <Icon className="h-4 w-4" />
                        {opt.label}
                      </button>
                    );
                  })}
                </div>
                {selectedFeedback && (
                  <div className="space-y-2 animate-fade-in">
                    <textarea
                      value={feedbackComment}
                      onChange={(e) => setFeedbackComment(e.target.value)}
                      placeholder="添加备注说明（可选）"
                      className="w-full rounded-lg border border-brand-border bg-brand-card px-3 py-2 text-sm text-brand-text-primary placeholder:text-brand-text-secondary/50 outline-none focus:border-brand-cyan focus:ring-1 focus:ring-brand-cyan resize-none"
                      rows={2}
                    />
                    <button
                      onClick={handleSubmitFeedback}
                      className="flex items-center gap-1.5 rounded-lg bg-brand-cyan px-4 py-2 text-sm font-medium text-brand-dark hover:bg-brand-cyan/90 transition-colors"
                    >
                      <Send className="h-4 w-4" />
                      提交反馈
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <FeedbackBadge type={alert.feedbackType} showLabel size="md" />
                <span className="text-xs text-brand-text-secondary">已反馈</span>
              </div>
            )}
          </div>

          {feedbacks.length > 0 && (
            <div className="border-t border-brand-border pt-4">
              <h3 className="text-xs font-medium text-brand-text-secondary mb-3">反馈历史</h3>
              <div className="space-y-2">
                {feedbacks.map((fb) => (
                  <div key={fb.id} className="rounded-lg bg-brand-card p-3">
                    <div className="flex items-center justify-between mb-1">
                      <FeedbackBadge type={fb.type} showLabel />
                      <span className="text-[10px] text-brand-text-secondary">
                        {formatTimestamp(fb.createdAt)}
                      </span>
                    </div>
                    {fb.comment && (
                      <p className="text-xs text-brand-text-secondary">{fb.comment}</p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="flex items-center justify-end gap-3 border-t border-brand-border px-6 py-4">
          {!alert.acknowledged && onAcknowledge && (
            <button
              onClick={() => onAcknowledge(alert.id)}
              className="flex items-center gap-1.5 rounded-lg bg-brand-green/15 px-4 py-2 text-sm font-medium text-brand-green hover:bg-brand-green/25 transition-colors"
            >
              <Check className="h-4 w-4" />
              确认告警
            </button>
          )}
          <button
            onClick={onClose}
            className="rounded-lg border border-brand-border px-4 py-2 text-sm text-brand-text-secondary hover:bg-brand-card hover:text-brand-text-primary transition-colors"
          >
            关闭
          </button>
        </div>
      </div>
    </div>
  );
}
