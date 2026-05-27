import Papa from 'papaparse';
import * as XLSX from 'xlsx';
import type { DataRow, ExportConfig } from '@/types';

export const exportAsJSON = (data: DataRow[], filename: string): void => {
  const json = JSON.stringify(data, null, 2);
  const blob = new Blob([json], { type: 'application/json' });
  downloadFile(blob, `${filename}.json`);
};

export const exportAsCSV = (
  data: DataRow[],
  filename: string,
  includeHeaders: boolean = true
): void => {
  const csv = Papa.unparse(data, {
    header: includeHeaders,
    quotes: true,
  });
  const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8' });
  downloadFile(blob, `${filename}.csv`);
};

export const exportAsExcel = (
  data: DataRow[],
  filename: string,
  includeHeaders: boolean = true
): void => {
  const ws = XLSX.utils.json_to_sheet(data, { skipHeader: !includeHeaders });
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, 'Sheet1');
  XLSX.writeFile(wb, `${filename}.xlsx`);
};

const downloadFile = (blob: Blob, filename: string): void => {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
};

export const exportData = (data: DataRow[], config: ExportConfig): void => {
  switch (config.format) {
    case 'json':
      exportAsJSON(data, config.filename);
      break;
    case 'csv':
      exportAsCSV(data, config.filename, config.includeHeaders);
      break;
    case 'xlsx':
      exportAsExcel(data, config.filename, config.includeHeaders);
      break;
  }
};
