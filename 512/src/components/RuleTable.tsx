import type { ThresholdRule } from '@/types';
import { cn } from '@/utils/helpers';
import { METRIC_DISPLAY_CONFIG } from '@/utils/chart-config';
import { Pencil, Trash2, ToggleLeft, ToggleRight, Shield } from 'lucide-react';
import LevelBadge from '@/components/LevelBadge';

interface RuleTableProps {
  rules: ThresholdRule[];
  onEdit: (rule: ThresholdRule) => void;
  onDelete: (id: string) => void;
  onToggle: (id: string, enabled: boolean) => void;
}

function buildExpression(metric: string, conditions: ThresholdRule['conditions']): string {
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

export default function RuleTable({ rules, onEdit, onDelete, onToggle }: RuleTableProps) {
  if (rules.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-brand-text-secondary">
        <Shield className="h-12 w-12 mb-3 opacity-40" />
        <p className="text-sm">暂无预警规则，点击上方按钮新增</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-brand-border">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-brand-surface text-brand-text-secondary text-xs uppercase tracking-wider">
            <th className="px-4 py-3 text-left font-medium">规则名称</th>
            <th className="px-4 py-3 text-left font-medium">指标</th>
            <th className="px-4 py-3 text-left font-medium">条件表达式</th>
            <th className="px-4 py-3 text-left font-medium">预警等级</th>
            <th className="px-4 py-3 text-left font-medium">状态</th>
            <th className="px-4 py-3 text-right font-medium">操作</th>
          </tr>
        </thead>
        <tbody>
          {rules.map((rule, idx) => (
            <tr
              key={rule.id}
              className={cn(
                'border-t border-brand-border transition-colors hover:bg-brand-card/60',
                idx % 2 === 1 && 'bg-brand-card/30'
              )}
            >
              <td className="px-4 py-3 text-brand-text-primary font-medium">
                {rule.name}
              </td>
              <td className="px-4 py-3 text-brand-text-secondary">
                {METRIC_DISPLAY_CONFIG[rule.metric]?.label || rule.metric}
              </td>
              <td className="px-4 py-3 font-mono-num text-brand-text-secondary text-xs">
                {buildExpression(rule.metric, rule.conditions)}
              </td>
              <td className="px-4 py-3">
                <LevelBadge level={rule.level} size="sm" />
              </td>
              <td className="px-4 py-3">
                <button
                  onClick={() => onToggle(rule.id, !rule.enabled)}
                  className="flex items-center gap-1 group"
                  title={rule.enabled ? '点击禁用' : '点击启用'}
                >
                  {rule.enabled ? (
                    <ToggleRight className="h-5 w-5 text-brand-cyan transition-colors group-hover:text-brand-cyan/80" />
                  ) : (
                    <ToggleLeft className="h-5 w-5 text-brand-text-secondary transition-colors group-hover:text-brand-text-primary" />
                  )}
                  <span
                    className={cn(
                      'text-xs',
                      rule.enabled ? 'text-brand-cyan' : 'text-brand-text-secondary'
                    )}
                  >
                    {rule.enabled ? '启用' : '禁用'}
                  </span>
                </button>
              </td>
              <td className="px-4 py-3">
                <div className="flex items-center justify-end gap-1">
                  <button
                    onClick={() => onEdit(rule)}
                    className="rounded-md p-1.5 text-brand-text-secondary hover:bg-brand-card hover:text-brand-cyan transition-colors"
                    title="编辑"
                  >
                    <Pencil className="h-4 w-4" />
                  </button>
                  <button
                    onClick={() => onDelete(rule.id)}
                    className="rounded-md p-1.5 text-brand-text-secondary hover:bg-brand-card hover:text-brand-red transition-colors"
                    title="删除"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
