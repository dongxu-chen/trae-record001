import { useState, useEffect } from 'react';
import type { ThresholdRule, AlertCondition, ConditionGroup, ThresholdRecommendation } from '@/types';
import { cn } from '@/utils/helpers';
import { METRIC_DISPLAY_CONFIG } from '@/utils/chart-config';
import { X } from 'lucide-react';
import VisualConditionBuilder from '@/components/VisualConditionBuilder';
import SmartThresholdPanel from '@/components/SmartThresholdPanel';
const METRICS = Object.keys(METRIC_DISPLAY_CONFIG);
const LEVELS: { value: ThresholdRule['level']; label: string; color: string; ring: string }[] = [
  { value: 'warning', label: '警告', color: 'border-brand-amber text-brand-amber', ring: 'ring-brand-amber' },
  { value: 'danger', label: '危险', color: 'border-brand-red text-brand-red', ring: 'ring-brand-red' },
  { value: 'critical', label: '严重', color: 'border-red-700 text-red-400', ring: 'ring-red-700' },
];

function generateId() {
  return `cond-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

interface RuleEditorProps {
  open: boolean;
  rule: ThresholdRule | null;
  onClose: () => void;
  onSave: (data: Omit<ThresholdRule, 'id' | 'createdAt' | 'updatedAt'>) => void;
}

export default function RuleEditor({ open, rule, onClose, onSave }: RuleEditorProps) {
  const [name, setName] = useState('');
  const [metric, setMetric] = useState('CPU');
  const [level, setLevel] = useState<ThresholdRule['level']>('warning');
  const [conditions, setConditions] = useState<AlertCondition[]>([
    { id: generateId(), field: 'CPU', operator: '>', value: 70, logic: undefined },
  ]);
  const [groups, setGroups] = useState<ConditionGroup[]>([]);
  const [errors, setErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    if (open) {
      if (rule) {
        setName(rule.name);
        setMetric(rule.metric);
        setLevel(rule.level);
        const condsWithIds = rule.conditions.map((c) => ({
          id: generateId(),
          ...c,
        }));
        setConditions(condsWithIds.length > 0 ? condsWithIds : [
          { id: generateId(), field: rule.metric, operator: '>', value: 70, logic: undefined },
        ]);
        setGroups([]);
      } else {
        setName('');
        setMetric('CPU');
        setLevel('warning');
        setConditions([{ id: generateId(), field: 'CPU', operator: '>', value: 70, logic: undefined }]);
        setGroups([]);
      }
      setErrors({});
    }
  }, [open, rule]);

  useEffect(() => {
    setConditions((prev) => prev.map((c) => ({ ...c, field: metric })));
  }, [metric]);

  const validate = (): boolean => {
    const e: Record<string, string> = {};
    if (!name.trim()) e.name = '请输入规则名称';
    if (conditions.length === 0) e.conditions = '至少需要一个条件';
    if (conditions.some((c) => c.value === undefined || c.value === null || isNaN(c.value))) {
      e.conditions = '请填写条件阈值';
    }
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const handleSave = () => {
    if (!validate()) return;
    const cleanConditions = conditions.map(({ id, ...c }, i) => ({
      ...c,
      logic: i < conditions.length - 1 ? c.logic : undefined,
    }));
    onSave({
      name: name.trim(),
      metric,
      level,
      conditions: cleanConditions,
      enabled: rule?.enabled ?? true,
    });
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />
      <div className="relative w-full max-w-lg rounded-xl border border-brand-border bg-brand-surface shadow-2xl animate-slide-in-modal">
        <div className="flex items-center justify-between border-b border-brand-border px-5 py-4">
          <h3 className="text-base font-semibold text-brand-text-primary">
            {rule ? '编辑规则' : '新增规则'}
          </h3>
          <button
            onClick={onClose}
            className="rounded-md p-1 text-brand-text-secondary hover:text-brand-text-primary hover:bg-brand-card transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="space-y-4 px-5 py-4">
          <div>
            <label className="mb-1 block text-xs text-brand-text-secondary">规则名称</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="输入规则名称"
              className={cn(
                'w-full rounded-md border bg-brand-card px-3 py-2 text-sm text-brand-text-primary placeholder:text-brand-text-secondary/50 outline-none focus:ring-1',
                errors.name ? 'border-brand-red ring-1 ring-brand-red' : 'border-brand-border focus:border-brand-cyan focus:ring-brand-cyan'
              )}
            />
            {errors.name && <p className="mt-1 text-xs text-brand-red">{errors.name}</p>}
          </div>

          <div>
            <label className="mb-1 block text-xs text-brand-text-secondary">监控指标</label>
            <select
              value={metric}
              onChange={(e) => setMetric(e.target.value)}
              className="w-full rounded-md border border-brand-border bg-brand-card px-3 py-2 text-sm text-brand-text-primary outline-none focus:border-brand-cyan focus:ring-1 focus:ring-brand-cyan"
            >
              {METRICS.map((m) => (
                <option key={m} value={m}>
                  {METRIC_DISPLAY_CONFIG[m]?.label || m}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="mb-1 block text-xs text-brand-text-secondary">预警等级</label>
            <div className="flex gap-3">
              {LEVELS.map((l) => (
                <label
                  key={l.value}
                  className={cn(
                    'flex cursor-pointer items-center gap-2 rounded-md border px-3 py-2 text-sm transition-all',
                    level === l.value
                      ? `${l.color} ring-1 ${l.ring}`
                      : 'border-brand-border text-brand-text-secondary hover:border-brand-border/80'
                  )}
                >
                  <input
                    type="radio"
                    name="level"
                    value={l.value}
                    checked={level === l.value}
                    onChange={() => setLevel(l.value)}
                    className="sr-only"
                  />
                  {l.label}
                </label>
              ))}
            </div>
          </div>

          <div>
            <label className="mb-1 block text-xs text-brand-text-secondary">条件表达式</label>
            <VisualConditionBuilder
              metric={metric}
              conditions={conditions}
              groups={groups}
              onChange={setConditions}
              onGroupsChange={setGroups}
            />
            {errors.conditions && <p className="mt-1 text-xs text-brand-red">{errors.conditions}</p>}
          </div>

          <SmartThresholdPanel
            metric={metric}
            onApply={(rec: ThresholdRecommendation) => {
              const thresholdMap: Record<string, number> = {
                warning: rec.warning,
                danger: rec.danger,
                critical: rec.critical,
              };
              setConditions([{
                id: generateId(),
                field: metric,
                operator: '>',
                value: thresholdMap[level] ?? rec.warning,
                logic: undefined,
              }]);
            }}
          />
        </div>

        <div className="flex items-center justify-end gap-2 border-t border-brand-border px-5 py-3">
          <button
            onClick={onClose}
            className="rounded-md border border-brand-border px-4 py-2 text-sm text-brand-text-secondary hover:bg-brand-card transition-colors"
          >
            取消
          </button>
          <button
            onClick={handleSave}
            className="rounded-md bg-brand-cyan px-4 py-2 text-sm font-medium text-brand-dark hover:bg-brand-cyan/90 transition-colors"
          >
            保存
          </button>
        </div>
      </div>
    </div>
  );
}
