import { PermissionConfig, DataRow, PivotResult } from '@/types';

export const defaultPermissionConfig: PermissionConfig = {
  hiddenRows: [],
  hiddenCols: [],
  hiddenFields: [],
  role: 'admin',
};

export const checkFieldVisible = (
  fieldName: string,
  permissions: PermissionConfig
): boolean => {
  return !permissions.hiddenFields.includes(fieldName);
};

export const checkRowVisible = (
  rowValues: string[],
  rowFields: string[],
  permissions: PermissionConfig
): boolean => {
  for (let i = 0; i < rowFields.length; i++) {
    const field = rowFields[i];
    const value = rowValues[i];
    const hiddenKey = `${field}:${value}`;
    if (permissions.hiddenRows.includes(hiddenKey)) {
      return false;
    }
  }
  return true;
};

export const checkColVisible = (
  colValues: string[],
  colFields: string[],
  permissions: PermissionConfig
): boolean => {
  for (let i = 0; i < colFields.length; i++) {
    const field = colFields[i];
    const value = colValues[i];
    const hiddenKey = `${field}:${value}`;
    if (permissions.hiddenCols.includes(hiddenKey)) {
      return false;
    }
  }
  return true;
};

export const filterDataByPermissions = (
  data: DataRow[],
  permissions: PermissionConfig
): DataRow[] => {
  if (permissions.hiddenFields.length === 0) {
    return data;
  }

  return data.map((row) => {
    const filteredRow: DataRow = {};
    Object.entries(row).forEach(([key, value]) => {
      if (!permissions.hiddenFields.includes(key)) {
        filteredRow[key] = value;
      }
    });
    return filteredRow;
  });
};

export const filterPivotResultByPermissions = (
  result: PivotResult,
  rowFields: string[],
  colFields: string[],
  permissions: PermissionConfig
): PivotResult => {
  const visibleRowIndices: number[] = [];
  const visibleColIndices: number[] = [];

  result.rowHeaders.forEach((rowVals, idx) => {
    if (checkRowVisible(rowVals, rowFields, permissions)) {
      visibleRowIndices.push(idx);
    }
  });

  result.colHeaders.forEach((colVals, idx) => {
    if (checkColVisible(colVals, colFields, permissions)) {
      visibleColIndices.push(idx);
    }
  });

  const filteredData = visibleRowIndices.map((rowIdx) =>
    visibleColIndices.map((colIdx) => result.data[rowIdx]?.[colIdx] ?? null)
  );

  const filteredRowTotals = visibleRowIndices.map(
    (rowIdx) => result.rowTotals[rowIdx] ?? null
  );

  const filteredColTotals = visibleColIndices.map(
    (colIdx) => result.colTotals[colIdx] ?? null
  );

  return {
    rowHeaders: visibleRowIndices.map((idx) => result.rowHeaders[idx]),
    colHeaders: visibleColIndices.map((idx) => result.colHeaders[idx]),
    data: filteredData,
    rowTotals: filteredRowTotals,
    colTotals: filteredColTotals,
    grandTotal: result.grandTotal,
  };
};

export const getRoleLabel = (role: PermissionConfig['role']): string => {
  const labels = {
    admin: '管理员',
    user: '普通用户',
    viewer: '查看者',
  };
  return labels[role];
};

export const getRolePermissions = (
  role: PermissionConfig['role']
): {
  canEditConfig: boolean;
  canExportData: boolean;
  canViewSensitiveData: boolean;
  canCustomAggregation: boolean;
} => {
  switch (role) {
    case 'admin':
      return {
        canEditConfig: true,
        canExportData: true,
        canViewSensitiveData: true,
        canCustomAggregation: true,
      };
    case 'user':
      return {
        canEditConfig: true,
        canExportData: true,
        canViewSensitiveData: false,
        canCustomAggregation: true,
      };
    case 'viewer':
      return {
        canEditConfig: false,
        canExportData: false,
        canViewSensitiveData: false,
        canCustomAggregation: false,
      };
  }
};

export const formatHiddenRowKey = (field: string, value: string): string => {
  return `${field}:${value}`;
};

export const parseHiddenRowKey = (
  key: string
): { field: string; value: string } => {
  const [field, ...rest] = key.split(':');
  return { field, value: rest.join(':') };
};
