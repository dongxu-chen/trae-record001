import { HybridDistinctCounter } from '@/utils/hyperLogLog';

export type WorkerMessageType =
  | 'CALCULATE_PIVOT'
  | 'CALCULATE_DRILLDOWN'
  | 'CANCEL'
  | 'PROGRESS';

export interface WorkerRequest {
  type: WorkerMessageType;
  id: string;
  payload?: any;
}

export interface WorkerResponse {
  type: WorkerMessageType | 'ERROR';
  id: string;
  payload?: any;
  progress?: number;
  error?: string;
}

interface DataRow {
  [key: string]: string | number;
}

interface CustomAggregationConfig {
  id: string;
  name: string;
  code: string;
}

interface ValueFieldConfig {
  field: string;
  aggregation: 'sum' | 'avg' | 'count' | 'countDistinct' | 'custom';
  customAggregationId?: string;
}

let currentData: DataRow[] = [];
let isCancelled = false;
let customAggregations: CustomAggregationConfig[] = [];

self.onmessage = (e: MessageEvent<WorkerRequest>) => {
  const { type, id, payload } = e.data;

  switch (type) {
    case 'CALCULATE_PIVOT':
      isCancelled = false;
      calculatePivot(id, payload);
      break;
    case 'CALCULATE_DRILLDOWN':
      isCancelled = false;
      calculateDrillDown(id, payload);
      break;
    case 'CANCEL':
      isCancelled = true;
      break;
  }
};

function sendProgress(id: string, progress: number) {
  const response: WorkerResponse = {
    type: 'PROGRESS',
    id,
    progress,
  };
  self.postMessage(response);
}

function sendResult(id: string, payload: any) {
  const response: WorkerResponse = {
    type: 'CALCULATE_PIVOT',
    id,
    payload,
  };
  self.postMessage(response);
}

function sendDrillDownResult(id: string, payload: any) {
  const response: WorkerResponse = {
    type: 'CALCULATE_DRILLDOWN',
    id,
    payload,
  };
  self.postMessage(response);
}

function sendError(id: string, error: string) {
  const response: WorkerResponse = {
    type: 'ERROR',
    id,
    error,
  };
  self.postMessage(response);
}

function getDistinctValues(data: DataRow[], fields: string[]): string[][] {
  const seen = new Set<string>();
  const result: string[][] = [];

  data.forEach((row) => {
    const key = fields.map((f) => String(row[f])).join('|||');
    if (!seen.has(key)) {
      seen.add(key);
      result.push(fields.map((f) => String(row[f])));
    }
  });

  return result.sort((a, b) => {
    for (let i = 0; i < a.length; i++) {
      if (a[i] < b[i]) return -1;
      if (a[i] > b[i]) return 1;
    }
    return 0;
  });
}

function filterData(
  data: DataRow[],
  filters: { [field: string]: string }
): DataRow[] {
  return data.filter((row) => {
    return Object.entries(filters).every(
      ([field, value]) => String(row[field]) === value
    );
  });
}

function executeCustomCode(
  code: string,
  values: number[],
  data: DataRow[],
  field: string
): number {
  try {
    const whitelist = new Set([
      'Math', 'Number', 'String', 'Array', 'Object',
      'parseInt', 'parseFloat', 'isNaN', 'isFinite',
      'JSON', 'Date', 'Map', 'Set',
    ]);

    const allowedGlobals: Record<string, any> = {};
    whitelist.forEach((key) => {
      allowedGlobals[key] = (self as any)[key];
    });

    const sandbox = {
      ...allowedGlobals,
      values,
      data,
      field,
      console: {
        log: () => {},
        error: () => {},
        warn: () => {},
      },
    };

    const sandboxKeys = Object.keys(sandbox);
    const sandboxValues = Object.values(sandbox);

    const wrappedCode = `
      "use strict";
      ${code}
    `;

    const fn = new Function(...sandboxKeys, wrappedCode);
    const result = fn(...sandboxValues);

    if (typeof result === 'number') {
      return isFinite(result) ? result : 0;
    }
    if (typeof result === 'string') {
      const parsed = parseFloat(result);
      return isFinite(parsed) ? parsed : 0;
    }
    return 0;
  } catch (error) {
    console.error('Custom aggregation error:', error);
    return 0;
  }
}

function calculateAggregation(
  data: DataRow[],
  field: string,
  aggregation: string,
  customAggregationId?: string
): number {
  const values = data.map((r) => Number(r[field])).filter((v) => !isNaN(v));

  if (aggregation === 'custom' && customAggregationId) {
    const customAgg = customAggregations.find((c) => c.id === customAggregationId);
    if (customAgg) {
      return executeCustomCode(customAgg.code, values, data, field);
    }
  }

  switch (aggregation) {
    case 'sum':
      return values.reduce((a, b) => a + b, 0);
    case 'avg':
      return values.length > 0
        ? values.reduce((a, b) => a + b, 0) / values.length
        : 0;
    case 'count':
      return values.length;
    case 'countDistinct':
      const hll = new HybridDistinctCounter(14);
      values.forEach((v) => hll.add('distinct', v));
      return hll.count('distinct');
    case 'custom':
      return values.reduce((a, b) => a + b, 0);
    default:
      return values.reduce((a, b) => a + b, 0);
  }
}

function calculatePivot(
  id: string,
  payload: {
    data: DataRow[];
    rowFields: string[];
    colFields: string[];
    valueFields: ValueFieldConfig[];
    customAggregations?: CustomAggregationConfig[];
  }
) {
  try {
    const { data, rowFields, colFields, valueFields, customAggregations: customAggs } = payload;
    currentData = data;
    if (customAggs) {
      customAggregations = customAggs;
    }

    const totalSteps = 4;
    let currentStep = 0;

    sendProgress(id, (currentStep++ / totalSteps) * 100);

    if (isCancelled) return;

    const rowHeaders = getDistinctValues(data, rowFields);
    sendProgress(id, (currentStep++ / totalSteps) * 100);

    if (isCancelled) return;

    const colHeaders = getDistinctValues(data, colFields);
    sendProgress(id, (currentStep++ / totalSteps) * 100);

    if (isCancelled) return;

    const vf = valueFields[0] || { field: '', aggregation: 'sum' };
    const pivotData: (any | null)[][] = [];
    const rowTotals: (any | null)[] = [];
    const colTotals: (any | null)[] = [];

    const totalCells = rowHeaders.length * colHeaders.length;
    let processedCells = 0;

    rowHeaders.forEach((rowVals, rowIdx) => {
      if (isCancelled) return;

      const rowFilters: { [field: string]: string } = {};
      rowFields.forEach((f, i) => (rowFilters[f] = rowVals[i]));

      const rowData = filterData(data, rowFilters);
      const rowTotalValues: number[] = [];
      pivotData[rowIdx] = [];

      colHeaders.forEach((colVals, colIdx) => {
        if (isCancelled) return;

        const colFilters: { [field: string]: string } = {};
        colFields.forEach((f, i) => (colFilters[f] = colVals[i]));

        const cellData = filterData(rowData, colFilters);

        if (cellData.length > 0 && vf.field) {
          const aggregatedValue = calculateAggregation(
            cellData,
            vf.field,
            vf.aggregation,
            vf.customAggregationId
          );

          pivotData[rowIdx][colIdx] = {
            value: aggregatedValue,
            rowFilters,
            colFilters,
            valueField: vf.field,
          };

          rowTotalValues.push(aggregatedValue);
        } else {
          pivotData[rowIdx][colIdx] = null;
        }

        processedCells++;
        if (processedCells % 100 === 0) {
          const cellProgress = processedCells / totalCells;
          sendProgress(
            id,
            ((currentStep - 1 + cellProgress) / totalSteps) * 100
          );
        }
      });

      if (rowTotalValues.length > 0) {
        const rowTotal = calculateAggregation(
          rowData,
          vf.field,
          vf.aggregation,
          vf.customAggregationId
        );
        rowTotals[rowIdx] = {
          value: rowTotal,
          rowFilters,
          colFilters: {},
          valueField: vf.field,
        };
      } else {
        rowTotals[rowIdx] = null;
      }
    });

    if (isCancelled) return;

    colHeaders.forEach((colVals, colIdx) => {
      const colFilters: { [field: string]: string } = {};
      colFields.forEach((f, i) => (colFilters[f] = colVals[i]));

      const colData = filterData(data, colFilters);

      if (colData.length > 0 && vf.field) {
        colTotals[colIdx] = {
          value: calculateAggregation(colData, vf.field, vf.aggregation, vf.customAggregationId),
          rowFilters: {},
          colFilters,
          valueField: vf.field,
        };
      } else {
        colTotals[colIdx] = null;
      }
    });

    sendProgress(id, 100);

    let grandTotal = null;
    if (data.length > 0 && vf.field) {
      grandTotal = {
        value: calculateAggregation(data, vf.field, vf.aggregation, vf.customAggregationId),
        rowFilters: {},
        colFilters: {},
        valueField: vf.field,
      };
    }

    sendResult(id, {
      rowHeaders,
      colHeaders,
      data: pivotData,
      rowTotals,
      colTotals,
      grandTotal,
    });
  } catch (error: any) {
    sendError(id, error.message || 'Unknown error');
  }
}

function calculateDrillDown(
  id: string,
  payload: {
    rowFilters: { [field: string]: string };
    colFilters: { [field: string]: string };
  }
) {
  try {
    const { rowFilters, colFilters } = payload;
    const allFilters = { ...rowFilters, ...colFilters };

    sendProgress(id, 50);

    const result = filterData(currentData, allFilters);

    sendProgress(id, 100);

    sendDrillDownResult(id, {
      data: result,
      rowFilters,
      colFilters,
    });
  } catch (error: any) {
    sendError(id, error.message || 'Unknown error');
  }
}
