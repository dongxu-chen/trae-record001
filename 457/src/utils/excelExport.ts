import * as XLSX from 'xlsx';
import { DataRow, PivotResult } from '@/types';

export const exportToExcel = (
  pivotResult: PivotResult,
  rowFields: string[],
  colFields: string[],
  filename: string = 'pivot_table.xlsx'
) => {
  const { rowHeaders, colHeaders, data, rowTotals, colTotals, grandTotal } = pivotResult;
  
  const wsData: (string | number)[][] = [];
  
  const headerRow1: (string | number)[] = [''];
  if (rowFields.length > 0) {
    headerRow1.push(...rowFields.slice(1).map(() => ''));
  }
  
  colHeaders.forEach(colVals => {
    colVals.forEach((val, idx) => {
      if (idx === 0) {
        headerRow1.push(val);
      }
    });
  });
  headerRow1.push('总计');
  wsData.push(headerRow1);
  
  if (colFields.length > 1) {
    for (let colLevel = 1; colLevel < colFields.length; colLevel++) {
      const subHeaderRow: (string | number)[] = [''];
      if (rowFields.length > 0) {
        subHeaderRow.push(...rowFields.slice(1).map(() => ''));
      }
      colHeaders.forEach(colVals => {
        subHeaderRow.push(colVals[colLevel] || '');
      });
      subHeaderRow.push('');
      wsData.push(subHeaderRow);
    }
  }
  
  rowHeaders.forEach((rowVals, rowIdx) => {
    const row: (string | number)[] = [...rowVals];
    colHeaders.forEach((_, colIdx) => {
      const cell = data[rowIdx]?.[colIdx];
      row.push(cell?.value ?? '');
    });
    row.push(rowTotals[rowIdx]?.value ?? '');
    wsData.push(row);
  });
  
  const totalRow: (string | number)[] = ['总计'];
  if (rowFields.length > 0) {
    totalRow.push(...rowFields.slice(1).map(() => ''));
  }
  colHeaders.forEach((_, colIdx) => {
    totalRow.push(colTotals[colIdx]?.value ?? '');
  });
  totalRow.push(grandTotal?.value ?? '');
  wsData.push(totalRow);
  
  const ws = XLSX.utils.aoa_to_sheet(wsData);
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, '透视表');
  XLSX.writeFile(wb, filename);
};

export const exportDrillDownToExcel = (
  data: DataRow[],
  filename: string = 'drill_down_data.xlsx'
) => {
  const ws = XLSX.utils.json_to_sheet(data);
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, '明细数据');
  XLSX.writeFile(wb, filename);
};

export const parseExcelFile = (file: File): Promise<DataRow[]> => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const data = e.target?.result;
        const workbook = XLSX.read(data, { type: 'binary' });
        const sheetName = workbook.SheetNames[0];
        const sheet = workbook.Sheets[sheetName];
        const jsonData = XLSX.utils.sheet_to_json(sheet) as DataRow[];
        resolve(jsonData);
      } catch (error) {
        reject(error);
      }
    };
    reader.onerror = reject;
    reader.readAsBinaryString(file);
  });
};
