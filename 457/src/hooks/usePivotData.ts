import { useState, useMemo } from 'react';
import { DataRow, PivotConfig, PivotResult, DrillDownContext } from '@/types';
import { calculatePivotTable, getDrillDownData } from '@/utils/pivotUtils';

export const usePivotData = (initialData: DataRow[]) => {
  const [data] = useState<DataRow[]>(initialData);
  const [config, setConfig] = useState<PivotConfig>({
    rows: [],
    cols: [],
    values: [],
    customAggregations: [],
  });
  const [drillDown, setDrillDown] = useState<DrillDownContext>({
    rowFilters: {},
    colFilters: {},
    valueField: '',
    isOpen: false,
  });

  const pivotResult: PivotResult = useMemo(() => {
    return calculatePivotTable(
      data,
      config.rows,
      config.cols,
      config.values
    );
  }, [data, config]);

  const drillDownData: DataRow[] = useMemo(() => {
    if (!drillDown.isOpen) return [];
    return getDrillDownData(data, drillDown.rowFilters, drillDown.colFilters);
  }, [data, drillDown]);

  const addRowField = (field: string) => {
    setConfig(prev => ({
      ...prev,
      rows: prev.rows.includes(field) ? prev.rows : [...prev.rows, field],
    }));
  };

  const removeRowField = (field: string) => {
    setConfig(prev => ({
      ...prev,
      rows: prev.rows.filter(f => f !== field),
    }));
  };

  const addColField = (field: string) => {
    setConfig(prev => ({
      ...prev,
      cols: prev.cols.includes(field) ? prev.cols : [...prev.cols, field],
    }));
  };

  const removeColField = (field: string) => {
    setConfig(prev => ({
      ...prev,
      cols: prev.cols.filter(f => f !== field),
    }));
  };

  const addValueField = (field: string, aggregation: string = 'sum') => {
    setConfig(prev => ({
      ...prev,
      values: prev.values.some(v => v.field === field)
        ? prev.values
        : [...prev.values, { field, aggregation: aggregation as any }],
    }));
  };

  const removeValueField = (field: string) => {
    setConfig(prev => ({
      ...prev,
      values: prev.values.filter(v => v.field !== field),
    }));
  };

  const updateAggregation = (field: string, aggregation: string) => {
    setConfig(prev => ({
      ...prev,
      values: prev.values.map(v =>
        v.field === field ? { ...v, aggregation: aggregation as any } : v
      ),
    }));
  };

  const openDrillDown = (
    rowFilters: { [field: string]: string },
    colFilters: { [field: string]: string },
    valueField: string
  ) => {
    setDrillDown({
      rowFilters,
      colFilters,
      valueField,
      isOpen: true,
    });
  };

  const closeDrillDown = () => {
    setDrillDown(prev => ({ ...prev, isOpen: false }));
  };

  return {
    data,
    config,
    pivotResult,
    drillDown,
    drillDownData,
    addRowField,
    removeRowField,
    addColField,
    removeColField,
    addValueField,
    removeValueField,
    updateAggregation,
    openDrillDown,
    closeDrillDown,
  };
};
