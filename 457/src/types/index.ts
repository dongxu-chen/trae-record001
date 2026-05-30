export interface DataRow {
  [key: string]: string | number;
}

export type AggregationType = 'sum' | 'avg' | 'count' | 'countDistinct' | 'custom';

export interface CustomAggregation {
  id: string;
  name: string;
  code: string;
  description?: string;
}

export interface ValueField {
  field: string;
  aggregation: AggregationType;
  customAggregationId?: string;
}

export interface PivotConfig {
  rows: string[];
  cols: string[];
  values: ValueField[];
  customAggregations: CustomAggregation[];
}

export interface PivotCell {
  value: number;
  rowFilters: { [field: string]: string };
  colFilters: { [field: string]: string };
  valueField: string;
  alertLevel?: 'info' | 'warning' | 'danger';
}

export interface PivotResult {
  rowHeaders: string[][];
  colHeaders: string[][];
  data: (PivotCell | null)[][];
  rowTotals: (PivotCell | null)[];
  colTotals: (PivotCell | null)[];
  grandTotal: PivotCell | null;
}

export interface FieldInfo {
  name: string;
  type: 'dimension' | 'measure';
  dataType: 'string' | 'number' | 'date';
}

export type ChartType = 'bar' | 'line' | 'pie';

export interface DrillDownContext {
  rowFilters: { [field: string]: string };
  colFilters: { [field: string]: string };
  valueField: string;
  isOpen: boolean;
}

export interface AlertRule {
  id: string;
  name: string;
  field: string;
  condition: 'gt' | 'gte' | 'lt' | 'lte' | 'eq' | 'ne' | 'between';
  value1: number;
  value2?: number;
  level: 'info' | 'warning' | 'danger';
  enabled: boolean;
}

export interface PermissionConfig {
  hiddenRows: string[];
  hiddenCols: string[];
  hiddenFields: string[];
  role: 'admin' | 'user' | 'viewer';
}
