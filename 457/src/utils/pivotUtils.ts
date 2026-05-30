import { DataRow, AggregationType, ValueField, PivotResult, PivotCell } from '@/types';

const aggregators: Record<Exclude<AggregationType, 'custom'>, (values: number[]) => number> = {
  sum: (values) => values.reduce((a, b) => a + b, 0),
  avg: (values) => values.length > 0 ? values.reduce((a, b) => a + b, 0) / values.length : 0,
  count: (values) => values.length,
  countDistinct: (values) => new Set(values).size,
};

const getAggregator = (aggregation: AggregationType): ((values: number[]) => number) => {
  if (aggregation === 'custom') {
    return aggregators.sum;
  }
  return aggregators[aggregation];
};

const getDistinctValues = (data: DataRow[], fields: string[]): string[][] => {
  const seen = new Set<string>();
  const result: string[][] = [];
  
  data.forEach(row => {
    const key = fields.map(f => String(row[f])).join('|||');
    if (!seen.has(key)) {
      seen.add(key);
      result.push(fields.map(f => String(row[f])));
    }
  });
  
  return result.sort((a, b) => {
    for (let i = 0; i < a.length; i++) {
      if (a[i] < b[i]) return -1;
      if (a[i] > b[i]) return 1;
    }
    return 0;
  });
};

const filterData = (data: DataRow[], filters: { [field: string]: string }): DataRow[] => {
  return data.filter(row => {
    return Object.entries(filters).every(([field, value]) => String(row[field]) === value);
  });
};

export const calculatePivotTable = (
  data: DataRow[],
  rowFields: string[],
  colFields: string[],
  valueFields: ValueField[]
): PivotResult => {
  const rowHeaders = getDistinctValues(data, rowFields);
  const colHeaders = getDistinctValues(data, colFields);
  
  const rowTotals: (PivotCell | null)[] = [];
  const colTotals: (PivotCell | null)[] = [];
  const pivotData: (PivotCell | null)[][] = [];
  let grandTotalValue = 0;
  const grandTotalValues: number[] = [];
  
  rowHeaders.forEach((rowVals, rowIdx) => {
    const rowFilters: { [field: string]: string } = {};
    rowFields.forEach((f, i) => rowFilters[f] = rowVals[i]);
    
    const rowData = filterData(data, rowFilters);
    const rowTotalValues: number[] = [];
    pivotData[rowIdx] = [];
    
    colHeaders.forEach((colVals, colIdx) => {
      const colFilters: { [field: string]: string } = {};
      colFields.forEach((f, i) => colFilters[f] = colVals[i]);
      
      const cellData = filterData(rowData, colFilters);
      
      if (cellData.length > 0 && valueFields.length > 0) {
        const vf = valueFields[0];
        const values = cellData.map(r => Number(r[vf.field])).filter(v => !isNaN(v));
        const aggregatedValue = getAggregator(vf.aggregation)(values);
        
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
    });
    
    if (rowTotalValues.length > 0) {
      const rowTotal = getAggregator(valueFields[0]?.aggregation || 'sum')(rowTotalValues);
      rowTotals[rowIdx] = {
        value: rowTotal,
        rowFilters,
        colFilters: {},
        valueField: valueFields[0]?.field || '',
      };
      grandTotalValues.push(rowTotal);
    } else {
      rowTotals[rowIdx] = null;
    }
  });
  
  colHeaders.forEach((colVals, colIdx) => {
    const colFilters: { [field: string]: string } = {};
    colFields.forEach((f, i) => colFilters[f] = colVals[i]);
    
    const colData = filterData(data, colFilters);
    const colTotalValues: number[] = [];
    
    rowHeaders.forEach(rowVals => {
      const rowFilters: { [field: string]: string } = {};
      rowFields.forEach((f, i) => rowFilters[f] = rowVals[i]);
      
      const cellData = filterData(colData, rowFilters);
      if (cellData.length > 0 && valueFields.length > 0) {
        const vf = valueFields[0];
        const values = cellData.map(r => Number(r[vf.field])).filter(v => !isNaN(v));
        colTotalValues.push(aggregators[vf.aggregation](values));
      }
    });
    
    if (colTotalValues.length > 0) {
      colTotals[colIdx] = {
        value: getAggregator(valueFields[0]?.aggregation || 'sum')(colTotalValues),
        rowFilters: {},
        colFilters,
        valueField: valueFields[0]?.field || '',
      };
    } else {
      colTotals[colIdx] = null;
    }
  });
  
  if (grandTotalValues.length > 0) {
    grandTotalValue = getAggregator(valueFields[0]?.aggregation || 'sum')(grandTotalValues);
  }
  
  return {
    rowHeaders,
    colHeaders,
    data: pivotData,
    rowTotals,
    colTotals,
    grandTotal: grandTotalValues.length > 0 ? {
      value: grandTotalValue,
      rowFilters: {},
      colFilters: {},
      valueField: valueFields[0]?.field || '',
    } : null,
  };
};

export const getDrillDownData = (
  data: DataRow[],
  rowFilters: { [field: string]: string },
  colFilters: { [field: string]: string }
): DataRow[] => {
  const allFilters = { ...rowFilters, ...colFilters };
  return filterData(data, allFilters);
};

export const formatNumber = (num: number): string => {
  if (num >= 1000000) {
    return (num / 1000000).toFixed(2) + 'M';
  }
  if (num >= 1000) {
    return (num / 1000).toFixed(2) + 'K';
  }
  return num.toFixed(2);
};

export const getAggregationLabel = (type: AggregationType): string => {
  const labels: Record<AggregationType, string> = {
    sum: '求和',
    avg: '平均值',
    count: '计数',
    countDistinct: '去重计数',
    custom: '自定义',
  };
  return labels[type] || type;
};
