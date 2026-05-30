import * as XLSX from 'xlsx';
import type { Annotation, DataPoint } from '../types';

export const exportAsJSON = (annotations: Annotation[], dataPoints?: DataPoint[]) => {
  const data = {
    annotations,
    dataPoints: dataPoints || [],
    exportedAt: new Date().toISOString(),
  };
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
  downloadBlob(blob, `annotations_${Date.now()}.json`);
};

export const exportAsCSV = (annotations: Annotation[], dataPoints?: DataPoint[]) => {
  const headers = ['id', 'type', 'dataPointIndex', 'label', 'description', 'createdBy', 'createdAt'];
  if (dataPoints) {
    headers.push('dataPointX', 'dataPointY');
  }

  const rows = annotations.map((a) => {
    const row: any = {
      id: a.id,
      type: a.type,
      dataPointIndex: a.dataPointIndex,
      label: a.label,
      description: a.description || '',
      createdBy: a.createdBy,
      createdAt: a.createdAt,
    };
    if (dataPoints && dataPoints[a.dataPointIndex]) {
      row.dataPointX = dataPoints[a.dataPointIndex].x;
      row.dataPointY = dataPoints[a.dataPointIndex].y;
    }
    return row;
  });

  const csvContent = [
    headers.join(','),
    ...rows.map((row) => headers.map((h) => `"${row[h] || ''}"`).join(',')),
  ].join('\n');

  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  downloadBlob(blob, `annotations_${Date.now()}.csv`);
};

export const exportAsExcel = (annotations: Annotation[], dataPoints?: DataPoint[]) => {
  const wsData = annotations.map((a) => {
    const row: any = {
      ID: a.id,
      Type: a.type,
      'Data Point Index': a.dataPointIndex,
      Label: a.label,
      Description: a.description || '',
      'Created By': a.createdBy,
      'Created At': a.createdAt,
    };
    if (dataPoints && dataPoints[a.dataPointIndex]) {
      row['Data Point X'] = String(dataPoints[a.dataPointIndex].x);
      row['Data Point Y'] = dataPoints[a.dataPointIndex].y;
    }
    return row;
  });

  const ws = XLSX.utils.json_to_sheet(wsData);
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, 'Annotations');

  if (dataPoints) {
    const wsDataPoints = dataPoints.map((dp, idx) => ({
      Index: idx,
      X: String(dp.x),
      Y: dp.y,
    }));
    const ws2 = XLSX.utils.json_to_sheet(wsDataPoints);
    XLSX.utils.book_append_sheet(wb, ws2, 'Data Points');
  }

  XLSX.writeFile(wb, `annotations_${Date.now()}.xlsx`);
};

const downloadBlob = (blob: Blob, filename: string) => {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
};

export const getAnnotationColor = (type: string) => {
  const colors: Record<string, string> = {
    classification: '#3b82f6',
    anomaly: '#ef4444',
    trend: '#22c55e',
  };
  return colors[type] || '#6b7280';
};

export const getAnnotationTypeName = (type: string) => {
  const names: Record<string, string> = {
    classification: '分类标注',
    anomaly: '异常标记',
    trend: '趋势标注',
  };
  return names[type] || type;
};
