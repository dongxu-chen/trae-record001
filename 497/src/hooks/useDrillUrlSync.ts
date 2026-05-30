import { useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useDrillStore } from './useDrillStore';
import { namesToPath, pathToNames } from '@/utils/drillUtils';
import { getDataByPath } from '@/data/mockData';
import { encodeDrillState, decodeDrillState } from '@/utils/shortCode';

export function useDrillUrlSync() {
  const [searchParams, setSearchParams] = useSearchParams();
  const { path, chartType, currentLevel, setCurrentData, restoreState, setLoading } =
    useDrillStore();
  const isInitialized = useRef(false);
  const isSyncing = useRef(false);

  useEffect(() => {
    if (isInitialized.current) return;

    const shortCode = searchParams.get('s');
    const pathParam = searchParams.get('path');
    const chartTypeParam = searchParams.get('chartType') as 'bar' | 'pie' | 'line' | null;
    const levelParam = searchParams.get('level');

    let names: string[] = [];
    let finalChartType: 'bar' | 'pie' | 'line' = 'bar';
    let finalLevel: number = 0;

    if (shortCode) {
      const decoded = decodeDrillState(shortCode);
      if (decoded) {
        names = decoded.path;
        finalChartType = decoded.chartType as 'bar' | 'pie' | 'line';
        finalLevel = names.length;
      }
    } else if (pathParam) {
      names = pathParam.split(',').filter(Boolean);
      finalChartType = chartTypeParam || 'bar';
      finalLevel = levelParam ? parseInt(levelParam, 10) : names.length;
    }

    const newPath = namesToPath(names);
    const data = getDataByPath(names);

    restoreState({
      path: newPath,
      currentLevel: finalLevel,
      chartType: finalChartType,
    });

    setTimeout(() => {
      setCurrentData(data);
      setLoading(false);
      isInitialized.current = true;
    }, 800);
  }, []);

  useEffect(() => {
    if (!isInitialized.current || isSyncing.current) return;

    isSyncing.current = true;

    const names = pathToNames(path);
    const shortCode = encodeDrillState(names, chartType);

    setSearchParams(
      {
        s: shortCode,
        l: currentLevel.toString(),
      },
      { replace: true }
    );

    setTimeout(() => {
      isSyncing.current = false;
    }, 0);
  }, [path, currentLevel, chartType]);

  useEffect(() => {
    const handlePopState = () => {
      isSyncing.current = true;
      isInitialized.current = false;
      setLoading(true);

      const shortCode = searchParams.get('s');
      const pathParam = searchParams.get('path');
      const chartTypeParam = searchParams.get('chartType') as 'bar' | 'pie' | 'line' | null;
      const levelParam = searchParams.get('level');

      let names: string[] = [];
      let finalChartType: 'bar' | 'pie' | 'line' = 'bar';
      let finalLevel: number = 0;

      if (shortCode) {
        const decoded = decodeDrillState(shortCode);
        if (decoded) {
          names = decoded.path;
          finalChartType = decoded.chartType as 'bar' | 'pie' | 'line';
          finalLevel = names.length;
        }
      } else if (pathParam) {
        names = pathParam.split(',').filter(Boolean);
        finalChartType = chartTypeParam || 'bar';
        finalLevel = levelParam ? parseInt(levelParam, 10) : names.length;
      }

      const newPath = namesToPath(names);
      const data = getDataByPath(names);

      setTimeout(() => {
        restoreState({
          path: newPath,
          currentLevel: finalLevel,
          chartType: finalChartType,
        });
        setCurrentData(data);
        setLoading(false);
        isInitialized.current = true;
        isSyncing.current = false;
      }, 300);
    };

    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, [searchParams, restoreState, setCurrentData, setLoading]);

  return null;
}
