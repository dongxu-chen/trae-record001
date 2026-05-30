import { useEffect, useMemo } from 'react';
import { AlertTriangle } from 'lucide-react';
import { useAlertStore } from '@/stores/alert-store';
import MetricCard from '@/components/MetricCard';
import RealtimeChart from '@/components/RealtimeChart';
import AlertStatusBadge from '@/components/AlertStatusBadge';

const METRICS = ['CPU', 'Memory', 'Network', 'DiskIO', 'Latency', 'ErrorRate'] as const;

const CHART_METRICS = ['CPU', 'Memory'] as const;

export default function Dashboard() {
  const rules = useAlertStore(s => s.rules);
  const metrics = useAlertStore(s => s.metrics);
  const realtimeAlerts = useAlertStore(s => s.realtimeAlerts);
  const correlations = useAlertStore(s => s.correlations);
  const activeAlertMetric = useAlertStore(s => s.activeAlertMetric);
  const fetchRules = useAlertStore(s => s.fetchRules);
  const fetchRelatedMetrics = useAlertStore(s => s.fetchRelatedMetrics);
  const setActiveAlertMetric = useAlertStore(s => s.setActiveAlertMetric);

  useEffect(() => {
    fetchRules();
  }, [fetchRules]);

  useEffect(() => {
    const unacknowledged = realtimeAlerts.find(a => !a.acknowledged);
    if (unacknowledged && unacknowledged.metric !== activeAlertMetric) {
      setActiveAlertMetric(unacknowledged.metric);
      fetchRelatedMetrics(unacknowledged.metric);
    } else if (!unacknowledged && activeAlertMetric) {
      setActiveAlertMetric(null);
    }
  }, [realtimeAlerts, activeAlertMetric, setActiveAlertMetric, fetchRelatedMetrics]);

  const warningCount = realtimeAlerts.filter(a => a.level === 'warning' && !a.acknowledged).length;
  const dangerCount = realtimeAlerts.filter(a => a.level === 'danger' && !a.acknowledged).length;
  const criticalCount = realtimeAlerts.filter(a => a.level === 'critical' && !a.acknowledged).length;
  const totalAlertCount = warningCount + dangerCount + criticalCount;

  const correlatedMetrics = useMemo(() => {
    if (!activeAlertMetric) return [];
    return correlations[activeAlertMetric] || [];
  }, [activeAlertMetric, correlations]);

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-3">
        {METRICS.map((metric, index) => (
          <div
            key={metric}
            className="animate-fade-in-up"
            style={{ animationDelay: `${index * 80}ms`, animationFillMode: 'both' }}
          >
            <MetricCard
              metric={metric}
              data={metrics[metric] ?? []}
              rules={rules}
            />
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {CHART_METRICS.map((metric, index) => (
          <div
            key={metric}
            className="animate-fade-in-up"
            style={{ animationDelay: `${(METRICS.length + index) * 80}ms`, animationFillMode: 'both' }}
          >
            <RealtimeChart
              metric={metric}
              data={metrics[metric] ?? []}
              rules={rules}
              correlatedMetrics={correlatedMetrics}
              activeAlert={activeAlertMetric}
            />
          </div>
        ))}
      </div>

      <div
        className="animate-fade-in-up rounded-lg border border-brand-border bg-brand-card p-4"
        style={{ animationDelay: `${(METRICS.length + CHART_METRICS.length) * 80}ms`, animationFillMode: 'both' }}
      >
        <div className="flex items-center gap-3 mb-3">
          <AlertTriangle className="h-5 w-5 text-brand-amber" />
          <span className="text-sm font-medium text-brand-text-primary">告警概览</span>
          <span className="font-mono-num text-xs text-brand-text-secondary">
            共 {totalAlertCount} 条未确认告警
          </span>
        </div>
        <div className="flex flex-wrap gap-3">
          <AlertStatusBadge level="warning" count={warningCount} active={warningCount > 0} />
          <AlertStatusBadge level="danger" count={dangerCount} active={dangerCount > 0} />
          <AlertStatusBadge level="critical" count={criticalCount} active={criticalCount > 0} />
        </div>
      </div>
    </div>
  );
}
