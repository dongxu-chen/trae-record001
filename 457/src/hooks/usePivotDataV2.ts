import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import {
  DataRow,
  PivotConfig,
  PivotResult,
  DrillDownContext,
  AlertRule,
  PermissionConfig,
  CustomAggregation,
} from '@/types';
import { eventBus } from '@/utils/eventBus';
import { applyAlertRulesToResult } from '@/utils/alertRules';
import {
  filterPivotResultByPermissions,
  defaultPermissionConfig,
} from '@/utils/permissions';
import { defaultCustomAggregations } from '@/utils/customAggregations';
import { defaultAlertRules } from '@/utils/alertRules';

interface PivotWorker {
  calculatePivot: (
    data: DataRow[],
    config: PivotConfig
  ) => Promise<PivotResult>;
  calculateDrillDown: (
    rowFilters: Record<string, string>,
    colFilters: Record<string, string>
  ) => Promise<DataRow[]>;
  cancel: () => void;
  isCalculating: boolean;
  progress: number;
}

const createPivotWorker = (): PivotWorker => {
  let worker: Worker | null = null;
  let currentRequestId: string | null = null;
  let resolvePivot: ((result: PivotResult) => void) | null = null;
  let rejectPivot: ((error: string) => void) | null = null;
  let resolveDrillDown: ((result: DataRow[]) => void) | null = null;
  let rejectDrillDown: ((error: string) => void) | null = null;
  let progressCallback: ((progress: number) => void) | null = null;

  const getWorker = (): Worker => {
    if (!worker) {
      worker = new Worker(new URL('@/workers/pivot.worker.ts', import.meta.url), {
        type: 'module',
      });

      worker.onmessage = (e) => {
        const { type, id, payload, progress, error } = e.data;

        if (id !== currentRequestId) return;

        if (type === 'PROGRESS' && progressCallback) {
          progressCallback(progress);
          return;
        }

        if (type === 'CALCULATE_PIVOT' && resolvePivot) {
          resolvePivot(payload);
          cleanup();
        }

        if (type === 'CALCULATE_DRILLDOWN' && resolveDrillDown) {
          resolveDrillDown(payload.data);
          cleanup();
        }

        if (type === 'ERROR') {
          if (rejectPivot) rejectPivot(error || 'Unknown error');
          if (rejectDrillDown) rejectDrillDown(error || 'Unknown error');
          cleanup();
        }
      };

      worker.onerror = (e) => {
        const error = e.message || 'Worker error';
        if (rejectPivot) rejectPivot(error);
        if (rejectDrillDown) rejectDrillDown(error);
        cleanup();
      };
    }
    return worker;
  };

  const cleanup = () => {
    currentRequestId = null;
    resolvePivot = null;
    rejectPivot = null;
    resolveDrillDown = null;
    rejectDrillDown = null;
    progressCallback = null;
  };

  const generateId = () =>
    `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

  return {
    calculatePivot: (
      data: DataRow[],
      config: PivotConfig
    ): Promise<PivotResult> => {
      return new Promise((resolve, reject) => {
        const worker = getWorker();
        currentRequestId = generateId();
        resolvePivot = resolve;
        rejectPivot = reject;

        worker.postMessage({
          type: 'CALCULATE_PIVOT',
          id: currentRequestId,
          payload: {
            data,
            rowFields: config.rows,
            colFields: config.cols,
            valueFields: config.values,
            customAggregations: config.customAggregations,
          },
        });
      });
    },

    calculateDrillDown: (
      rowFilters: Record<string, string>,
      colFilters: Record<string, string>
    ): Promise<DataRow[]> => {
      return new Promise((resolve, reject) => {
        const worker = getWorker();
        currentRequestId = generateId();
        resolveDrillDown = resolve;
        rejectDrillDown = reject;

        worker.postMessage({
          type: 'CALCULATE_DRILLDOWN',
          id: currentRequestId,
          payload: {
            rowFilters,
            colFilters,
          },
        });
      });
    },

    cancel: () => {
      if (worker && currentRequestId) {
        worker.postMessage({
          type: 'CANCEL',
          id: currentRequestId,
        });
      }
      cleanup();
    },

    get isCalculating() {
      return currentRequestId !== null;
    },

    get progress() {
      return 0;
    },
  };
};

export const usePivotDataV2 = (initialData: DataRow[]) => {
  const [data, setData] = useState<DataRow[]>(initialData);
  const [config, setConfig] = useState<PivotConfig>({
    rows: [],
    cols: [],
    values: [],
    customAggregations: defaultCustomAggregations,
  });
  const [alertRules, setAlertRules] = useState<AlertRule[]>(defaultAlertRules);
  const [permissions, setPermissions] = useState<PermissionConfig>(defaultPermissionConfig);
  const [rawPivotResult, setRawPivotResult] = useState<PivotResult>({
    rowHeaders: [],
    colHeaders: [],
    data: [],
    rowTotals: [],
    colTotals: [],
    grandTotal: null,
  });
  const [isLoading, setIsLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [drillDown, setDrillDown] = useState<DrillDownContext>({
    rowFilters: {},
    colFilters: {},
    valueField: '',
    isOpen: false,
  });
  const [drillDownData, setDrillDownData] = useState<DataRow[]>([]);

  const workerRef = useRef<PivotWorker>(createPivotWorker());

  const pivotResult: PivotResult = useMemo(() => {
    let result = rawPivotResult;
    result = applyAlertRulesToResult(result, alertRules);
    result = filterPivotResultByPermissions(
      result,
      config.rows,
      config.cols,
      permissions
    );
    return result;
  }, [rawPivotResult, alertRules, permissions, config.rows, config.cols]);

  const calculatePivot = useCallback(async () => {
    if (config.rows.length === 0 && config.cols.length === 0) {
      setRawPivotResult({
        rowHeaders: [],
        colHeaders: [],
        data: [],
        rowTotals: [],
        colTotals: [],
        grandTotal: null,
      });
      return;
    }

    setIsLoading(true);
    setProgress(0);

    try {
      const result = await workerRef.current.calculatePivot(data, config);
      setRawPivotResult(result);

      eventBus.emit('PIVOT_DATA_UPDATED', {
        pivotResult: result,
      });
    } catch (error) {
      console.error('Pivot calculation error:', error);
    } finally {
      setIsLoading(false);
      setProgress(100);
    }
  }, [data, config]);

  useEffect(() => {
    const timer = setTimeout(() => {
      calculatePivot();
    }, 100);

    return () => clearTimeout(timer);
  }, [calculatePivot]);

  useEffect(() => {
    const unsubscribe = eventBus.on('PIVOT_CONFIG_CHANGED', (payload) => {
      setConfig((prev) => ({
        ...prev,
        rows: payload.rows,
        cols: payload.cols,
        values: payload.values as any,
      }));
    });

    return unsubscribe;
  }, []);

  useEffect(() => {
    const unsubscribe = eventBus.on('CELL_CLICKED', async (payload) => {
      setDrillDown({
        rowFilters: payload.rowFilters,
        colFilters: payload.colFilters,
        valueField: payload.valueField,
        isOpen: true,
      });

      try {
        const drillData = await workerRef.current.calculateDrillDown(
          payload.rowFilters,
          payload.colFilters
        );
        setDrillDownData(drillData);

        eventBus.emit('DRILLDOWN_DATA_READY', {
          data: drillData,
          rowFilters: payload.rowFilters,
          colFilters: payload.colFilters,
          valueField: payload.valueField,
        });
      } catch (error) {
        console.error('Drilldown calculation error:', error);
      }
    });

    return unsubscribe;
  }, []);

  const addRowField = useCallback((field: string) => {
    setConfig((prev) => {
      const newConfig = {
        ...prev,
        rows: prev.rows.includes(field) ? prev.rows : [...prev.rows, field],
      };
      eventBus.emit('PIVOT_CONFIG_CHANGED', {
        rows: newConfig.rows,
        cols: newConfig.cols,
        values: newConfig.values,
      });
      return newConfig;
    });
  }, []);

  const removeRowField = useCallback((field: string) => {
    setConfig((prev) => {
      const newConfig = {
        ...prev,
        rows: prev.rows.filter((f) => f !== field),
      };
      eventBus.emit('PIVOT_CONFIG_CHANGED', {
        rows: newConfig.rows,
        cols: newConfig.cols,
        values: newConfig.values,
      });
      return newConfig;
    });
  }, []);

  const addColField = useCallback((field: string) => {
    setConfig((prev) => {
      const newConfig = {
        ...prev,
        cols: prev.cols.includes(field) ? prev.cols : [...prev.cols, field],
      };
      eventBus.emit('PIVOT_CONFIG_CHANGED', {
        rows: newConfig.rows,
        cols: newConfig.cols,
        values: newConfig.values,
      });
      return newConfig;
    });
  }, []);

  const removeColField = useCallback((field: string) => {
    setConfig((prev) => {
      const newConfig = {
        ...prev,
        cols: prev.cols.filter((f) => f !== field),
      };
      eventBus.emit('PIVOT_CONFIG_CHANGED', {
        rows: newConfig.rows,
        cols: newConfig.cols,
        values: newConfig.values,
      });
      return newConfig;
    });
  }, []);

  const addValueField = useCallback(
    (field: string, aggregation: string = 'sum', customAggregationId?: string) => {
      setConfig((prev) => {
        const newConfig = {
          ...prev,
          values: prev.values.some((v) => v.field === field)
            ? prev.values
            : [
                ...prev.values,
                {
                  field,
                  aggregation: aggregation as any,
                  customAggregationId,
                },
              ],
        };
        eventBus.emit('PIVOT_CONFIG_CHANGED', {
          rows: newConfig.rows,
          cols: newConfig.cols,
          values: newConfig.values,
        });
        return newConfig;
      });
    },
    []
  );

  const removeValueField = useCallback((field: string) => {
    setConfig((prev) => {
      const newConfig = {
        ...prev,
        values: prev.values.filter((v) => v.field !== field),
      };
      eventBus.emit('PIVOT_CONFIG_CHANGED', {
        rows: newConfig.rows,
        cols: newConfig.cols,
        values: newConfig.values,
      });
      return newConfig;
    });
  }, []);

  const updateAggregation = useCallback(
    (field: string, aggregation: string, customAggregationId?: string) => {
      setConfig((prev) => {
        const newConfig = {
          ...prev,
          values: prev.values.map((v) =>
            v.field === field
              ? { ...v, aggregation: aggregation as any, customAggregationId }
              : v
          ),
        };
        eventBus.emit('PIVOT_CONFIG_CHANGED', {
          rows: newConfig.rows,
          cols: newConfig.cols,
          values: newConfig.values,
        });
        return newConfig;
      });
    },
    []
  );

  const addCustomAggregation = useCallback((agg: CustomAggregation) => {
    setConfig((prev) => ({
      ...prev,
      customAggregations: [...prev.customAggregations, agg],
    }));
  }, []);

  const updateCustomAggregation = useCallback(
    (id: string, updates: Partial<CustomAggregation>) => {
      setConfig((prev) => ({
        ...prev,
        customAggregations: prev.customAggregations.map((c) =>
          c.id === id ? { ...c, ...updates } : c
        ),
      }));
    },
    []
  );

  const removeCustomAggregation = useCallback((id: string) => {
    setConfig((prev) => ({
      ...prev,
      customAggregations: prev.customAggregations.filter((c) => c.id !== id),
      values: prev.values.filter((v) => v.customAggregationId !== id),
    }));
  }, []);

  const addAlertRule = useCallback((rule: AlertRule) => {
    setAlertRules((prev) => [...prev, rule]);
  }, []);

  const updateAlertRule = useCallback(
    (id: string, updates: Partial<AlertRule>) => {
      setAlertRules((prev) =>
        prev.map((r) => (r.id === id ? { ...r, ...updates } : r))
      );
    },
    []
  );

  const removeAlertRule = useCallback((id: string) => {
    setAlertRules((prev) => prev.filter((r) => r.id !== id));
  }, []);

  const updatePermissions = useCallback(
    (updates: Partial<PermissionConfig>) => {
      setPermissions((prev) => ({ ...prev, ...updates }));
    },
    []
  );

  const openDrillDown = useCallback(
    (
      rowFilters: Record<string, string>,
      colFilters: Record<string, string>,
      valueField: string,
      value: number
    ) => {
      eventBus.emit('CELL_CLICKED', {
        rowFilters,
        colFilters,
        valueField,
        value,
      });
    },
    []
  );

  const closeDrillDown = useCallback(() => {
    setDrillDown((prev) => ({ ...prev, isOpen: false }));
  }, []);

  const updateData = useCallback((newData: DataRow[]) => {
    setData(newData);
    eventBus.emit('DATA_UPLOADED', { data: newData });
  }, []);

  useEffect(() => {
    return () => {
      workerRef.current.cancel();
    };
  }, []);

  return {
    data,
    config,
    pivotResult,
    alertRules,
    permissions,
    drillDown,
    drillDownData,
    isLoading,
    progress,
    addRowField,
    removeRowField,
    addColField,
    removeColField,
    addValueField,
    removeValueField,
    updateAggregation,
    addCustomAggregation,
    updateCustomAggregation,
    removeCustomAggregation,
    addAlertRule,
    updateAlertRule,
    removeAlertRule,
    updatePermissions,
    openDrillDown,
    closeDrillDown,
    updateData,
  };
};
