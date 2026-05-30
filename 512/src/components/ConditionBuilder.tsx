import { useState } from 'react';
import type { AlertCondition } from '@/types';
import { METRIC_DISPLAY_CONFIG } from '@/utils/chart-config';
import { Plus, X } from 'lucide-react';
import { cn } from '@/utils/helpers';

const OPERATORS = ['>', '<', '>=', '<=', '==', '!='] as const;
const LOGICS = ['AND', 'OR'] as const;

interface ConditionBuilderProps {
  metric: string;
  conditions: AlertCondition[];
  onChange: (conditions: AlertCondition[]) => void;
}

function buildPreview(metric: string, conditions: AlertCondition[]): string {
  const label = METRIC_DISPLAY_CONFIG[metric]?.label || metric;
  return conditions
    .map((c, i) => {
      const part = `${label} ${c.operator} ${c.value}`;
      if (i < conditions.length - 1 && c.logic) {
        return `${part} ${c.logic}`;
      }
      return part;
    })
    .join(' ');
}

export default function ConditionBuilder({ metric, conditions, onChange }: ConditionBuilderProps) {
  const [nextId] = useState(Date.now());

  const addCondition = () => {
    const logic: AlertCondition['logic'] = conditions.length > 0 ? 'AND' : undefined;
    onChange([
      ...conditions.map((c, i) =>
        i === conditions.length - 1 ? { ...c, logic: 'AND' as const } : c
      ),
      { field: metric, operator: '>', value: 0, logic: undefined },
    ]);
  };

  const removeCondition = (index: number) => {
    const updated = conditions.filter((_, i) => i !== index);
    if (updated.length > 0) {
      updated[updated.length - 1] = { ...updated[updated.length - 1], logic: undefined };
    }
    onChange(updated);
  };

  const updateCondition = (index: number, patch: Partial<AlertCondition>) => {
    onChange(conditions.map((c, i) => (i === index ? { ...c, ...patch } : c)));
  };

  const label = METRIC_DISPLAY_CONFIG[metric]?.label || metric;

  return (
    <div className="space-y-2">
      {conditions.map((cond, idx) => (
        <div key={idx} className="flex items-center gap-2">
          <span className="shrink-0 text-xs text-brand-text-secondary w-16 truncate" title={label}>
            {label}
          </span>

          <select
            value={cond.operator}
            onChange={(e) =>
              updateCondition(idx, { operator: e.target.value as AlertCondition['operator'] })
            }
            className="rounded-md border border-brand-border bg-brand-card px-2 py-1.5 text-xs text-brand-text-primary focus:border-brand-cyan focus:ring-1 focus:ring-brand-cyan outline-none"
          >
            {OPERATORS.map((op) => (
              <option key={op} value={op}>{op}</option>
            ))}
          </select>

          <input
            type="number"
            value={cond.value}
            onChange={(e) => updateCondition(idx, { value: Number(e.target.value) })}
            className="w-24 rounded-md border border-brand-border bg-brand-card px-2 py-1.5 text-xs text-brand-text-primary focus:border-brand-cyan focus:ring-1 focus:ring-brand-cyan outline-none font-mono-num"
          />

          {idx < conditions.length - 1 ? (
            <select
              value={cond.logic || 'AND'}
              onChange={(e) =>
                updateCondition(idx, { logic: e.target.value as AlertCondition['logic'] })
              }
              className="rounded-md border border-brand-border bg-brand-card px-2 py-1.5 text-xs text-brand-cyan focus:border-brand-cyan focus:ring-1 focus:ring-brand-cyan outline-none font-semibold"
            >
              {LOGICS.map((l) => (
                <option key={l} value={l}>{l}</option>
              ))}
            </select>
          ) : (
            <span className="w-12" />
          )}

          <button
            type="button"
            onClick={() => removeCondition(idx)}
            disabled={conditions.length <= 1}
            className={cn(
              'rounded-md p-1 transition-colors',
              conditions.length <= 1
                ? 'text-brand-border cursor-not-allowed'
                : 'text-brand-text-secondary hover:text-brand-red hover:bg-brand-card'
            )}
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      ))}

      <button
        type="button"
        onClick={addCondition}
        className="flex items-center gap-1 rounded-md px-2 py-1 text-xs text-brand-cyan hover:bg-brand-card transition-colors"
      >
        <Plus className="h-3.5 w-3.5" />
        添加条件
      </button>

      {conditions.length > 0 && (
        <div className="rounded-md bg-brand-dark px-3 py-2">
          <span className="text-[10px] text-brand-text-secondary">表达式预览：</span>
          <span className="ml-1 font-mono-num text-xs text-brand-cyan">
            {buildPreview(metric, conditions)}
          </span>
        </div>
      )}
    </div>
  );
}
