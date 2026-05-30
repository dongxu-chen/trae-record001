import { AlertRule, PivotCell } from '@/types';

export const defaultAlertRules: AlertRule[] = [
  {
    id: 'high_sales_warning',
    name: '销售额过高预警',
    field: '销售额',
    condition: 'gt',
    value1: 15000,
    level: 'warning',
    enabled: true,
  },
  {
    id: 'low_profit_danger',
    name: '利润过低危险',
    field: '利润',
    condition: 'lt',
    value1: 1000,
    level: 'danger',
    enabled: true,
  },
  {
    id: 'abnormal_growth',
    name: '异常销量区间',
    field: '销量',
    condition: 'between',
    value1: 50,
    value2: 100,
    level: 'info',
    enabled: false,
  },
];

export const evaluateAlertRule = (
  rule: AlertRule,
  value: number
): boolean => {
  if (!rule.enabled) return false;

  switch (rule.condition) {
    case 'gt':
      return value > rule.value1;
    case 'gte':
      return value >= rule.value1;
    case 'lt':
      return value < rule.value1;
    case 'lte':
      return value <= rule.value1;
    case 'eq':
      return value === rule.value1;
    case 'ne':
      return value !== rule.value1;
    case 'between':
      return (
        rule.value2 !== undefined &&
        value >= rule.value1 &&
        value <= rule.value2
      );
    default:
      return false;
  }
};

export const getAlertLevelForCell = (
  value: number,
  field: string,
  rules: AlertRule[]
): 'info' | 'warning' | 'danger' | undefined => {
  const fieldRules = rules.filter(
    (r) => r.enabled && r.field === field
  );

  for (const rule of fieldRules) {
    if (evaluateAlertRule(rule, value)) {
      return rule.level;
    }
  }

  return undefined;
};

export const applyAlertRulesToCell = (
  cell: PivotCell,
  rules: AlertRule[]
): PivotCell => {
  const alertLevel = getAlertLevelForCell(
    cell.value,
    cell.valueField,
    rules
  );
  return {
    ...cell,
    alertLevel,
  };
};

export const applyAlertRulesToResult = (
  result: any,
  rules: AlertRule[]
): any => {
  if (!result || rules.length === 0) return result;

  const applyToCell = (cell: any): any => {
    if (!cell) return cell;
    return applyAlertRulesToCell(cell, rules);
  };

  return {
    ...result,
    data: result.data?.map((row: any[]) => row.map(applyToCell)),
    rowTotals: result.rowTotals?.map(applyToCell),
    colTotals: result.colTotals?.map(applyToCell),
    grandTotal: result.grandTotal ? applyToCell(result.grandTotal) : null,
  };
};

export const getConditionLabel = (condition: AlertRule['condition']): string => {
  const labels: Record<AlertRule['condition'], string> = {
    gt: '大于',
    gte: '大于等于',
    lt: '小于',
    lte: '小于等于',
    eq: '等于',
    ne: '不等于',
    between: '在...之间',
  };
  return labels[condition];
};

export const getLevelColor = (level: 'info' | 'warning' | 'danger'): string => {
  const colors = {
    info: '#3B82F6',
    warning: '#F59E0B',
    danger: '#EF4444',
  };
  return colors[level];
};

export const getLevelBgColor = (level: 'info' | 'warning' | 'danger'): string => {
  const colors = {
    info: 'bg-blue-50',
    warning: 'bg-amber-50',
    danger: 'bg-red-50',
  };
  return colors[level];
};

export const getLevelBorderColor = (level: 'info' | 'warning' | 'danger'): string => {
  const colors = {
    info: 'border-l-4 border-l-blue-500',
    warning: 'border-l-4 border-l-amber-500',
    danger: 'border-l-4 border-l-red-500',
  };
  return colors[level];
};
