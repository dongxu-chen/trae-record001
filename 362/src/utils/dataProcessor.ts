import Papa from 'papaparse';
import * as XLSX from 'xlsx';
import type { FillMethod, NormalizeMethod, OutlierMethod, CleaningRules, CleaningChanges } from '../types';
import {
  getNumericValues,
  calculateMean,
  calculateMedian,
  calculateMode,
  detectOutliersZScore,
  detectOutliersIQR,
  detectColumnType,
} from './statistics';

export async function parseFile(file: File): Promise<{ data: any[][]; columns: string[] }> {
  return new Promise((resolve, reject) => {
    const fileName = file.name.toLowerCase();

    if (fileName.endsWith('.csv')) {
      Papa.parse(file, {
        header: false,
        skipEmptyLines: 'greedy',
        complete: (results) => {
          const data = results.data as any[][];
          if (data.length === 0) {
            reject(new Error('文件为空'));
            return;
          }
          const columns = data[0].map((col: any, index: number) => String(col || `column_${index}`));
          const rows = data.slice(1);
          resolve({ data: rows, columns });
        },
        error: (error) => reject(error),
      });
    } else if (fileName.endsWith('.xlsx') || fileName.endsWith('.xls')) {
      const reader = new FileReader();
      reader.onload = (e) => {
        try {
          const data = new Uint8Array(e.target?.result as ArrayBuffer);
          const workbook = XLSX.read(data, { type: 'array' });
          const firstSheet = workbook.Sheets[workbook.SheetNames[0]];
          const jsonData = XLSX.utils.sheet_to_json(firstSheet, { header: 1 }) as any[][];

          if (jsonData.length === 0) {
            reject(new Error('文件为空'));
            return;
          }
          const columns = jsonData[0].map((col: any) => String(col || `column_${index}`));
          const rows = jsonData.slice(1);
          resolve({ data: rows, columns });
        } catch (error) {
          reject(error);
        }
      };
      reader.onerror = () => reject(new Error('文件读取失败'));
      reader.readAsArrayBuffer(file);
    } else {
      reject(new Error('不支持的文件格式，请上传CSV或Excel文件'));
    }
  });
}

export function removeDuplicates(
  data: any[][],
  columns?: string[],
  columnNames: string[] = [],
  keep: 'first' | 'last' | false = 'first'
): { data: any[][]; removed: number } {
  if (data.length === 0) return { data, removed: 0 };

  const columnIndices = columns
    ? columns.map((col) => columnNames.indexOf(col)).filter((idx) => idx !== -1)
    : data[0].map((_, idx) => idx);

  const seen = new Set<string>();
  const result: any[][] = [];
  let removed = 0;

  if (keep === 'last') {
    for (let i = data.length - 1; i >= 0; i--) {
      const key = columnIndices.map((idx) => String(data[i][idx])).join('|');
      if (!seen.has(key)) {
        seen.add(key);
        result.unshift(data[i]);
      } else {
        removed++;
      }
    }
  } else {
    for (let i = 0; i < data.length; i++) {
      const key = columnIndices.map((idx) => String(data[i][idx])).join('|');
      if (!seen.has(key)) {
        seen.add(key);
        result.push(data[i]);
      } else {
        removed++;
      }
    }
  }

  return { data: result, removed };
}

function parseDateValue(value: any): Date | null {
  if (value === null || value === undefined || value === '') return null;
  if (value instanceof Date) return value;
  const str = String(value);
  const date = new Date(str);
  return isNaN(date.getTime()) ? null : date;
}

export function fillMissingValues(
  data: any[][],
  columnIndex: number,
  method: FillMethod,
  constantValue?: number | string
): { data: any[][]; filled: number } {
  if (data.length === 0) return { data, filled: 0 };

  const values = data.map((row) => row[columnIndex]);
  const numericValues = getNumericValues(values);
  const colType = detectColumnType(values);
  const isDateColumn = colType === 'date';
  let filled = 0;

  let fillValue: any;
  if (isDateColumn) {
    if (method === 'mode') {
      fillValue = calculateMode(values.filter(v => parseDateValue(v)));
    } else {
      const dateValues = values.map(v => parseDateValue(v)).filter(v => v !== null) as Date[];
      if (dateValues.length > 0) {
        const sortedDates = dateValues.sort((a, b) => a.getTime() - b.getTime());
        fillValue = sortedDates[Math.floor(sortedDates.length / 2)];
      }
    }
  } else {
    switch (method) {
      case 'mean':
        fillValue = calculateMean(numericValues);
        break;
      case 'median':
        fillValue = calculateMedian(numericValues);
        break;
      case 'mode':
        fillValue = calculateMode(values);
        break;
      case 'constant':
        fillValue = constantValue;
        break;
      default:
        fillValue = calculateMean(numericValues);
    }
  }

  const result = data.map((row, rowIdx) => {
    const newRow = [...row];
    const value = newRow[columnIndex];
    if (value === null || value === undefined || value === '') {
      if (method === 'ffill') {
        for (let j = rowIdx - 1; j >= 0; j--) {
          if (data[j][columnIndex] !== null && data[j][columnIndex] !== undefined && data[j][columnIndex] !== '') {
            newRow[columnIndex] = data[j][columnIndex];
            filled++;
            break;
          }
        }
      } else if (method === 'bfill') {
        for (let j = rowIdx + 1; j < data.length; j++) {
          if (data[j][columnIndex] !== null && data[j][columnIndex] !== undefined && data[j][columnIndex] !== '') {
            newRow[columnIndex] = data[j][columnIndex];
            filled++;
            break;
          }
        }
      } else if (method === 'interpolate') {
        let prevIdx = -1;
        let nextIdx = -1;
        for (let j = rowIdx - 1; j >= 0; j--) {
          if (data[j][columnIndex] !== null && data[j][columnIndex] !== undefined && data[j][columnIndex] !== '') {
            prevIdx = j;
            break;
          }
        }
        for (let j = rowIdx + 1; j < data.length; j++) {
          if (data[j][columnIndex] !== null && data[j][columnIndex] !== undefined && data[j][columnIndex] !== '') {
            nextIdx = j;
            break;
          }
        }
        if (prevIdx !== -1 && nextIdx !== -1) {
          if (isDateColumn) {
            const prevDate = parseDateValue(data[prevIdx][columnIndex]);
            const nextDate = parseDateValue(data[nextIdx][columnIndex]);
            if (prevDate && nextDate) {
              const prevTime = prevDate.getTime();
              const nextTime = nextDate.getTime();
              const ratio = (rowIdx - prevIdx) / (nextIdx - prevIdx);
              const interpolatedTime = prevTime + (nextTime - prevTime) * ratio;
              newRow[columnIndex] = new Date(interpolatedTime).toISOString().split('T')[0];
              filled++;
            } else if (fillValue !== undefined) {
              newRow[columnIndex] = fillValue instanceof Date ? fillValue.toISOString().split('T')[0] : fillValue;
              filled++;
            }
          } else {
            const prevVal = Number(data[prevIdx][columnIndex]);
            const nextVal = Number(data[nextIdx][columnIndex]);
            const ratio = (rowIdx - prevIdx) / (nextIdx - prevIdx);
            newRow[columnIndex] = prevVal + (nextVal - prevVal) * ratio;
            filled++;
          }
        } else if (fillValue !== undefined) {
          if (isDateColumn && fillValue instanceof Date) {
            newRow[columnIndex] = fillValue.toISOString().split('T')[0];
          } else {
            newRow[columnIndex] = fillValue;
          }
          filled++;
        }
      } else if (fillValue !== undefined) {
        if (isDateColumn && fillValue instanceof Date) {
          newRow[columnIndex] = fillValue.toISOString().split('T')[0];
        } else {
          newRow[columnIndex] = fillValue;
        }
        filled++;
      }
    }
    return newRow;
  });

  return { data: result, filled };
}

export function handleOutliers(
  data: any[][],
  columnIndex: number,
  method: OutlierMethod,
  threshold: number,
  action: 'remove' | 'cap' | 'mark'
): { data: any[][]; handled: number; outliers: number[] } {
  if (data.length === 0) return { data, handled: 0, outliers: [] };

  const values = data.map((row) => row[columnIndex]);
  const numericValues = getNumericValues(values);

  if (numericValues.length === 0) return { data, handled: 0, outliers: [] };

  const fullNumericValues = values.map((v) => (v === null || v === undefined || v === '' ? NaN : Number(v)));
  const validIndices = fullNumericValues.map((v, i) => (!isNaN(v) && isFinite(v) ? i : -1)).filter((i) => i !== -1);
  const validValues = validIndices.map((i) => fullNumericValues[i]);

  let outlierIndices: number[] = [];
  if (method === 'zscore') {
    const outliersInValid = detectOutliersZScore(validValues, threshold);
    outlierIndices = outliersInValid.map((i) => validIndices[i]);
  } else {
    const outliersInValid = detectOutliersIQR(validValues, threshold);
    outlierIndices = outliersInValid.map((i) => validIndices[i]);
  }

  if (outlierIndices.length === 0) return { data, handled: 0, outliers: outlierIndices };

  if (action === 'remove') {
    const result = data.filter((_, idx) => !outlierIndices.includes(idx));
    return { data: result, handled: outlierIndices.length, outliers: outlierIndices };
  } else if (action === 'cap') {
    const sorted = [...validValues].sort((a, b) => a - b);
    const q1 = sorted[Math.floor(sorted.length * 0.25)];
    const q3 = sorted[Math.floor(sorted.length * 0.75)];
    const iqr = q3 - q1;
    const lowerBound = q1 - threshold * iqr;
    const upperBound = q3 + threshold * iqr;

    const result = data.map((row, idx) => {
      const newRow = [...row];
      if (outlierIndices.includes(idx)) {
        const val = Number(newRow[columnIndex]);
        if (val < lowerBound) newRow[columnIndex] = lowerBound;
        else if (val > upperBound) newRow[columnIndex] = upperBound;
      }
      return newRow;
    });
    return { data: result, handled: outlierIndices.length, outliers: outlierIndices };
  } else {
    const result = data.map((row, idx) => {
      const newRow = [...row];
      if (outlierIndices.includes(idx)) {
        newRow[columnIndex] = `${newRow[columnIndex]} (OUTLIER)`;
      }
      return newRow;
    });
    return { data: result, handled: outlierIndices.length, outliers: outlierIndices };
  }
}

export function normalizeData(
  data: any[][],
  columnIndex: number,
  method: NormalizeMethod
): { data: any[][] } {
  if (data.length === 0) return { data };

  const values = data.map((row) => row[columnIndex]);
  const numericValues = getNumericValues(values);

  if (numericValues.length === 0) return { data };

  const fullNumericValues = values.map((v) => (v === null || v === undefined || v === '' ? NaN : Number(v)));

  let min: number, max: number, mean: number, std: number, median: number, q1: number, q3: number;

  if (method === 'minmax') {
    min = Math.min(...numericValues);
    max = Math.max(...numericValues);
    if (max === min) return { data };
  } else if (method === 'zscore') {
    mean = calculateMean(numericValues)!;
    std = numericValues.length > 1 ? Math.sqrt(numericValues.reduce((s, v) => s + (v - mean) ** 2, 0) / numericValues.length) : 1;
    if (std === 0) return { data };
  } else {
    const sorted = [...numericValues].sort((a, b) => a - b);
    median = sorted[Math.floor(sorted.length / 2)];
    q1 = sorted[Math.floor(sorted.length * 0.25)];
    q3 = sorted[Math.floor(sorted.length * 0.75)];
    const iqr = q3 - q1;
    if (iqr === 0) return { data };
  }

  const result = data.map((row, idx) => {
    const newRow = [...row];
    if (!isNaN(fullNumericValues[idx]) && isFinite(fullNumericValues[idx])) {
      const val = fullNumericValues[idx];
      if (method === 'minmax') {
        newRow[columnIndex] = (val - min!) / (max! - min!);
      } else if (method === 'zscore') {
        newRow[columnIndex] = (val - mean!) / std!;
      } else {
        newRow[columnIndex] = (val - median!) / (q3! - q1!);
      }
    }
    return newRow;
  });

  return { data: result };
}

interface OutlierColumnResult {
  columnIndex: number;
  data: any[][];
  handled: number;
  outlierRowIndices: number[];
  action: 'remove' | 'cap' | 'mark';
}

function processSingleColumnOutliers(
  data: any[][],
  columnIndex: number,
  method: OutlierMethod,
  threshold: number,
  action: 'remove' | 'cap' | 'mark'
): OutlierColumnResult {
  const result = handleOutliers(data, columnIndex, method, threshold, action);
  return {
    columnIndex,
    data: result.data,
    handled: result.handled,
    outlierRowIndices: result.outliers,
    action,
  };
}

export async function processDataCleaning(
  data: any[][],
  columns: string[],
  rules: CleaningRules,
  onProgress?: (step: string, progress: number) => void
): Promise<{
  data: any[][];
  changes: CleaningChanges;
  logs: string[];
}> {
  const startTime = Date.now();
  let currentData = [...data];
  const logs: string[] = [];
  const changes: CleaningChanges = {
    rowsRemoved: 0,
    rowsAdded: 0,
    valuesFilled: 0,
    outliersHandled: 0,
    duplicatesRemoved: 0,
  };

  const totalSteps = [
    rules.removeDuplicates.enabled,
    rules.handleMissing.enabled,
    rules.detectOutliers.enabled,
    rules.normalize.enabled,
  ].filter(Boolean).length;
  let currentStep = 0;

  if (rules.removeDuplicates.enabled) {
    currentStep++;
    onProgress?.('删除重复值', (currentStep / totalSteps) * 25);
    const result = removeDuplicates(currentData, rules.removeDuplicates.columns, columns, rules.removeDuplicates.keep);
    currentData = result.data;
    changes.duplicatesRemoved = result.removed;
    changes.rowsRemoved += result.removed;
    logs.push(`删除了 ${result.removed} 条重复数据`);
  }

  if (rules.handleMissing.enabled) {
    currentStep++;
    onProgress?.('填充缺失值', (currentStep / totalSteps) * 50);
    let totalFilled = 0;
    for (let i = 0; i < columns.length; i++) {
      const colName = columns[i];
      const colConfig = rules.handleMissing.columns[colName];
      const method = colConfig?.method || rules.handleMissing.defaultMethod;
      const value = colConfig?.value;
      const result = fillMissingValues(currentData, i, method, value);
      currentData = result.data;
      totalFilled += result.filled;
    }
    changes.valuesFilled = totalFilled;
    logs.push(`填充了 ${totalFilled} 个缺失值`);
  }

  if (rules.detectOutliers.enabled) {
    currentStep++;
    onProgress?.('处理异常值', (currentStep / totalSteps) * 75);

    const numericColumnIndices: number[] = [];
    const columnConfigs: Array<{
      method: OutlierMethod;
      threshold: number;
      action: 'remove' | 'cap' | 'mark';
    }> = [];

    for (let i = 0; i < columns.length; i++) {
      const colName = columns[i];
      const colValues = currentData.map((row) => row[i]);
      const colType = detectColumnType(colValues);

      if (colType === 'numeric') {
        numericColumnIndices.push(i);
        const colConfig = rules.detectOutliers.columns[colName];
        columnConfigs.push({
          method: colConfig?.method || rules.detectOutliers.defaultMethod,
          threshold: colConfig?.threshold || rules.detectOutliers.defaultThreshold,
          action: colConfig?.action || 'remove',
        });
      }
    }

    if (numericColumnIndices.length > 0) {
      const outlierTasks = numericColumnIndices.map((colIdx, idx) =>
        processSingleColumnOutliers(
          currentData,
          colIdx,
          columnConfigs[idx].method,
          columnConfigs[idx].threshold,
          columnConfigs[idx].action
        )
      );

      const outlierResults = await Promise.all(outlierTasks);

      const allOutlierRows = new Set<number>();
      const cappedData = [...currentData];
      let totalHandled = 0;
      let rowsToRemove = 0;

      outlierResults.forEach((result) => {
        totalHandled += result.handled;
        if (result.action === 'remove') {
          result.outlierRowIndices.forEach((idx) => allOutlierRows.add(idx));
        } else if (result.action === 'cap') {
          for (let i = 0; i < result.data.length; i++) {
            const origVal = cappedData[i][result.columnIndex];
            const newVal = result.data[i][result.columnIndex];
            if (String(origVal) !== String(newVal)) {
              cappedData[i] = [...result.data[i]];
            }
          }
        } else {
          for (let i = 0; i < result.data.length; i++) {
            cappedData[i] = [...result.data[i]];
          }
        }
      });

      if (allOutlierRows.size > 0) {
        rowsToRemove = allOutlierRows.size;
        currentData = cappedData.filter((_, idx) => !allOutlierRows.has(idx));
      } else {
        currentData = cappedData;
      }

      changes.outliersHandled = totalHandled;
      changes.rowsRemoved += rowsToRemove;
      logs.push(`处理了 ${totalHandled} 个异常值`);
    }
  }

  if (rules.normalize.enabled) {
    currentStep++;
    onProgress?.('数据标准化', (currentStep / totalSteps) * 100);
    for (let i = 0; i < columns.length; i++) {
      const colName = columns[i];
      const colConfig = rules.normalize.columns[colName];
      const method = colConfig?.method || rules.normalize.defaultMethod;
      const result = normalizeData(currentData, i, method);
      currentData = result.data;
    }
    logs.push('完成数据标准化');
  }

  logs.push(`清洗完成，耗时 ${((Date.now() - startTime) / 1000).toFixed(2)} 秒`);

  return { data: currentData, changes, logs };
}

export function exportToCSV(data: any[][], columns: string[], filename: string = 'cleaned_data.csv'): void {
  const csvContent = [columns.join(','), ...data.map((row) => row.map((cell) => `"${cell ?? ''}"`).join(','))].join('\n');
  const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = filename;
  link.click();
  URL.revokeObjectURL(link.href);
}

export function exportToExcel(data: any[][], columns: string[], filename: string = 'cleaned_data.xlsx'): void {
  const wsData = [columns, ...data];
  const ws = XLSX.utils.aoa_to_sheet(wsData);
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, 'Sheet1');
  XLSX.writeFile(wb, filename);
}
