import Papa from 'papaparse';
import * as XLSX from 'xlsx';
import type { SourceField, FieldType, DataRow } from '@/types';

const detectFieldType = (values: any[]): FieldType => {
  if (values.length === 0) return 'string';
  
  const nonNullValues = values.filter(v => v !== null && v !== undefined && v !== '');
  if (nonNullValues.length === 0) return 'string';

  const allNumbers = nonNullValues.every(v => !isNaN(Number(v)));
  if (allNumbers) return 'number';

  const allBooleans = nonNullValues.every(v => 
    typeof v === 'boolean' || 
    ['true', 'false', 'yes', 'no', '是', '否'].includes(String(v).toLowerCase())
  );
  if (allBooleans) return 'boolean';

  const datePatterns = [
    /^\d{4}-\d{2}-\d{2}$/,
    /^\d{4}\/\d{2}\/\d{2}$/,
    /^\d{2}-\d{2}-\d{4}$/,
    /^\d{2}\/\d{2}\/\d{4}$/,
    /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/,
  ];
  const allDates = nonNullValues.every(v => {
    const str = String(v);
    return datePatterns.some(pattern => pattern.test(str));
  });
  if (allDates) return 'date';

  return 'string';
};

const getSampleValues = (values: any[], count: number = 3): string[] => {
  return values
    .filter(v => v !== null && v !== undefined && v !== '')
    .slice(0, count)
    .map(v => String(v).slice(0, 50));
};

export const parseCSV = async (file: File): Promise<{ fields: SourceField[]; data: DataRow[] }> => {
  return new Promise((resolve, reject) => {
    Papa.parse(file, {
      header: true,
      skipEmptyLines: true,
      complete: (results) => {
        const data = results.data as DataRow[];
        if (data.length === 0) {
          resolve({ fields: [], data: [] });
          return;
        }

        const headers = Object.keys(data[0]);
        const fields: SourceField[] = headers.map((header, index) => {
          const columnValues = data.map(row => row[header]);
          return {
            id: `source-${index}`,
            name: header,
            type: detectFieldType(columnValues),
            sampleValues: getSampleValues(columnValues),
          };
        });

        resolve({ fields, data });
      },
      error: (error) => reject(error),
    });
  });
};

export const parseExcel = async (file: File): Promise<{ fields: SourceField[]; data: DataRow[] }> => {
  const buffer = await file.arrayBuffer();
  const workbook = XLSX.read(buffer, { type: 'array' });
  const firstSheet = workbook.Sheets[workbook.SheetNames[0]];
  const data = XLSX.utils.sheet_to_json(firstSheet) as DataRow[];

  if (data.length === 0) {
    return { fields: [], data: [] };
  }

  const headers = Object.keys(data[0]);
  const fields: SourceField[] = headers.map((header, index) => {
    const columnValues = data.map(row => row[header]);
    return {
      id: `source-${index}`,
      name: header,
      type: detectFieldType(columnValues),
      sampleValues: getSampleValues(columnValues),
    };
  });

  return { fields, data };
};

export const parseJSON = async (file: File): Promise<{ fields: SourceField[]; data: DataRow[] }> => {
  const text = await file.text();
  let data: DataRow[];

  try {
    const parsed = JSON.parse(text);
    if (Array.isArray(parsed)) {
      data = parsed;
    } else if (typeof parsed === 'object' && parsed !== null) {
      data = [parsed];
    } else {
      throw new Error('JSON格式无效，请提供对象数组');
    }
  } catch (error) {
    throw new Error('JSON解析失败');
  }

  if (data.length === 0) {
    return { fields: [], data: [] };
  }

  const headers = Object.keys(data[0]);
  const fields: SourceField[] = headers.map((header, index) => {
    const columnValues = data.map(row => row[header]);
    return {
      id: `source-${index}`,
      name: header,
      type: detectFieldType(columnValues),
      sampleValues: getSampleValues(columnValues),
    };
  });

  return { fields, data };
};

export const parseFile = async (file: File): Promise<{ fields: SourceField[]; data: DataRow[] }> => {
  const extension = file.name.split('.').pop()?.toLowerCase();

  switch (extension) {
    case 'csv':
      return parseCSV(file);
    case 'xlsx':
    case 'xls':
      return parseExcel(file);
    case 'json':
      return parseJSON(file);
    default:
      throw new Error(`不支持的文件格式: ${extension}`);
  }
};
