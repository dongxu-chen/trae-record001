import type { TransformFunction, DataRow, FieldType } from '@/types';

export const applyTransform = (
  value: any,
  transform: TransformFunction,
  row: DataRow
): any => {
  switch (transform.type) {
    case 'trim':
      return typeof value === 'string' ? value.trim() : value;

    case 'uppercase':
      return typeof value === 'string' ? value.toUpperCase() : value;

    case 'lowercase':
      return typeof value === 'string' ? value.toLowerCase() : value;

    case 'split': {
      if (typeof value !== 'string') return value;
      const parts = value.split(transform.separator);
      return parts[transform.index] ?? '';
    }

    case 'concat': {
      const values = transform.fields.map(f => row[f] ?? '');
      return values.join(transform.separator);
    }

    case 'format': {
      let result = transform.pattern;
      if (value !== undefined && value !== null) {
        result = result.replace(/\{value\}/g, String(value));
      }
      Object.entries(row).forEach(([key, val]) => {
        result = result.replace(new RegExp(`\\{${key}\\}`, 'g'), String(val ?? ''));
      });
      return result;
    }

    case 'lookup': {
      const key = String(value ?? '');
      return transform.mapping[key] ?? transform.defaultValue;
    }

    case 'prefix': {
      return transform.value + (value ?? '');
    }

    case 'suffix': {
      return (value ?? '') + transform.value;
    }

    case 'replace': {
      if (typeof value !== 'string') return value;
      const flags = transform.global ? 'g' : '';
      return value.replace(new RegExp(transform.search, flags), transform.replace);
    }

    default:
      return value;
  }
};

export const applyTransforms = (
  value: any,
  transforms: TransformFunction[],
  row: DataRow
): any => {
  let result = value;
  for (const transform of transforms) {
    result = applyTransform(result, transform, row);
  }
  return result;
};

export const generateTransformId = (): string => {
  return `transform-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
};

export const convertToType = (value: any, targetType: FieldType): any => {
  if (value === null || value === undefined || value === '') {
    return targetType === 'string' ? '' : targetType === 'number' ? 0 : targetType === 'boolean' ? false : null;
  }

  switch (targetType) {
    case 'string':
      return String(value);

    case 'number': {
      const num = Number(value);
      return isNaN(num) ? 0 : num;
    }

    case 'boolean': {
      if (typeof value === 'boolean') return value;
      const str = String(value).toLowerCase().trim();
      return ['true', 'yes', '1', '是'].includes(str);
    }

    case 'date': {
      if (value instanceof Date) return value;
      const date = new Date(value);
      return isNaN(date.getTime()) ? null : date;
    }

    default:
      return value;
  }
};
