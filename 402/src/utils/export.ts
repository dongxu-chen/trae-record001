import type { ScanRecord } from '../types';

export function exportToCSV(records: ScanRecord[]): string {
  const headers = ['ID', '内容', '类型', '格式', '时间', '备注'];
  const rows = records.map((r) => [
    r.id,
    `"${r.content.replace(/"/g, '""')}"`,
    r.type,
    r.format || '',
    new Date(r.timestamp).toLocaleString(),
    r.note || '',
  ]);
  
  return [headers.join(','), ...rows.map((row) => row.join(','))].join('\n');
}

export function exportToJSON(records: ScanRecord[]): string {
  return JSON.stringify(records, null, 2);
}

export function downloadFile(content: string, filename: string, format: 'csv' | 'json'): void {
  const mimeTypes = {
    csv: 'text/csv;charset=utf-8;',
    json: 'application/json;charset=utf-8;',
  };
  
  const blob = new Blob(['\ufeff' + content], { type: mimeTypes[format] });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

export function exportRecords(records: ScanRecord[], format: 'csv' | 'json'): void {
  const timestamp = new Date().toISOString().split('T')[0];
  const filename = `scan-records-${timestamp}.${format}`;
  const content = format === 'csv' ? exportToCSV(records) : exportToJSON(records);
  downloadFile(content, filename, format);
}
