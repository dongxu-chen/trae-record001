import { useState, useEffect } from 'react';
import ReactECharts from 'echarts-for-react';
import { Lightbulb, ChevronDown, ChevronUp, Loader2, Check } from 'lucide-react';
import { useAlertStore } from '@/stores/alert-store';
import { cn } from '@/utils/helpers';
import { METRIC_DISPLAY_CONFIG } from '@/utils/chart-config';
import type { ThresholdRecommendation, AlertCondition } from '@/types';

interface SmartThresholdPanelProps {
  metric: string;
  onApply: (recommendation: ThresholdRecommendation) => void;
}

const METHODS = [
  { value: 'zscore', label: 'Z-Score', desc: '基于标准差' },
  { value: 'percentile', label: '百分位数', desc: '基于统计分布' },
  { value: 'iqr', label: 'IQR', desc: '四分位距法' },
] as const;

const SENSITIVITY_LABELS: Record<string, string> = {
  low: '低',
  medium: '中',
  high: '高',
};

export default function SmartThresholdPanel({ metric, onApply }: SmartThresholdPanelProps) {
  const [expanded, setExpanded] = useState(false);
  const [method, setMethod] = useState<'zscore' | 'percentile' | 'iqr'>('zscore');
  const [sensitivity, setSensitivity] = useState<'low' | 'medium' | 'high'>('medium');
  const [loading, setLoading] = useState(false);
  const [recommendation, setRecommendation] = useState<ThresholdRecommendation | null>(null);
  const fetchSmartThreshold = useAlertStore(s => s.fetchSmartThreshold);

  useEffect(() => {
    if (!expanded) return;
    const fetchData = async () => {
      setLoading(true);
      try {
        const result = await fetchSmartThreshold(metric, method, sensitivity);
        setRecommendation(result);
      } catch (e) {
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [expanded, metric, method, sensitivity, fetchSmartThreshold]);

  const chartOption = recommendation ? {
    backgroundColor: 'transparent',
    grid: { left: 40, right: 20, top: 20, bottom: 30 },
    xAxis: {
      type: 'category',
      data: ['', '均值', 'P95', '警告', '危险', '严重', ''],
      axisLine: { lineStyle: { color: '#374151' } },
      axisLabel: { color: '#9CA3AF', fontSize: 10 },
    },
    yAxis: {
      type: 'value',
      axisLine: { lineStyle: { color: '#374151' } },
      splitLine: { lineStyle: { color: '#1F2937' } },
      axisLabel: { color: '#9CA3AF', fontSize: 10 },
    },
    series: [
      {
        type: 'bar',
        data: [null, recommendation.stats.mean, recommendation.stats.p95, recommendation.warning, recommendation.danger, recommendation.critical, null],
        itemStyle: {
          color: (params: any) => {
            const colors = ['#6B7280', '#00d4ff', '#00d4ff', '#f59e0b', '#ef4444', '#dc2626', '#6B7280'];
            return colors[params.dataIndex];
          },
        },
        barWidth: 20,
      },
    ],
  } : null;

  const handleApply = () => {
    if (recommendation) {
      onApply(recommendation);
    }
  };

  return (
    <div className="rounded-lg border border-brand-border bg-brand-card overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center justify-between px-4 py-3 text-left hover:bg-brand-surface transition-colors"
      >
        <div className="flex items-center gap-2">
          <Lightbulb className="h-4 w-4 text-brand-amber" />
          <span className="text-sm font-medium text-brand-text-primary">智能阈值推荐</span>
        </div>
        {expanded ? (
          <ChevronUp className="h-4 w-4 text-brand-text-secondary" />
        ) : (
          <ChevronDown className="h-4 w-4 text-brand-text-secondary" />
        )}
      </button>

      {expanded && (
        <div className="border-t border-brand-border px-4 py-4 space-y-4 animate-fade-in">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="mb-1.5 block text-xs text-brand-text-secondary">分析方法</label>
              <select
                value={method}
                onChange={(e) => setMethod(e.target.value as any)}
                className="w-full rounded-md border border-brand-border bg-brand-surface px-3 py-2 text-sm text-brand-text-primary outline-none focus:border-brand-cyan focus:ring-1 focus:ring-brand-cyan"
              >
                {METHODS.map(m => (
                  <option key={m.value} value={m.value}>{m.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1.5 block text-xs text-brand-text-secondary">灵敏度: {SENSITIVITY_LABELS[sensitivity]}</label>
              <input
                type="range"
                min="0"
                max="2"
                value={['low', 'medium', 'high'].indexOf(sensitivity)}
                onChange={(e) => {
                  const vals: ('low' | 'medium' | 'high')[] = ['low', 'medium', 'high'];
                  setSensitivity(vals[parseInt(e.target.value)]);
                }}
                className="w-full h-2 bg-brand-border rounded-lg appearance-none cursor-pointer accent-brand-cyan"
              />
              <div className="flex justify-between text-[10px] text-brand-text-secondary mt-1">
                <span>保守</span>
                <span>敏感</span>
              </div>
            </div>
          </div>

          {loading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 text-brand-cyan animate-spin" />
            </div>
          ) : recommendation ? (
            <>
              <div className="grid grid-cols-3 gap-3">
                <div className="rounded-lg bg-brand-surface p-3">
                  <div className="text-[10px] text-brand-text-secondary mb-1">警告阈值</div>
                  <div className="text-lg font-semibold text-brand-amber">{recommendation.warning.toFixed(1)}</div>
                </div>
                <div className="rounded-lg bg-brand-surface p-3">
                  <div className="text-[10px] text-brand-text-secondary mb-1">危险阈值</div>
                  <div className="text-lg font-semibold text-brand-red">{recommendation.danger.toFixed(1)}</div>
                </div>
                <div className="rounded-lg bg-brand-surface p-3">
                  <div className="text-[10px] text-brand-text-secondary mb-1">严重阈值</div>
                  <div className="text-lg font-semibold text-red-500">{recommendation.critical.toFixed(1)}</div>
                </div>
              </div>

              <div className="rounded-lg border border-brand-border bg-brand-surface p-2">
                <ReactECharts option={chartOption} style={{ height: 160 }} />
              </div>

              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4 text-xs text-brand-text-secondary">
                  <span>置信度: <span className="text-brand-green">{(recommendation.confidence * 100).toFixed(0)}%</span></span>
                  <span>样本量: <span className="text-brand-cyan">{recommendation.sampleSize}</span></span>
                </div>
                <button
                  onClick={handleApply}
                  className="flex items-center gap-1.5 rounded-md bg-brand-cyan px-4 py-2 text-sm font-medium text-brand-dark hover:bg-brand-cyan/90 transition-colors"
                >
                  <Check className="h-4 w-4" />
                  应用推荐
                </button>
              </div>
            </>
          ) : null}
        </div>
      )}
    </div>
  );
}
