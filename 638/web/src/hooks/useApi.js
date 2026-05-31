import { useState, useEffect, useCallback, useRef } from 'react';
import { api } from '../utils/api';

export function useApi(callback, deps = []) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await callback();
      setData(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, deps);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { data, loading, error, refetch: fetchData };
}

export function useAutotune(ns, deploy) {
  return useApi(() => api.getAutotune(ns, deploy), [ns, deploy]);
}

export function useDashboard() {
  const result = useApi(() => api.getDashboard(), []);
  const intervalRef = useRef(null);

  useEffect(() => {
    intervalRef.current = setInterval(() => {
      result.refetch();
    }, 10000);
    return () => clearInterval(intervalRef.current);
  }, [result.refetch]);

  return result;
}

export function useTuning() {
  const result = useApi(() => api.getTuning(), []);
  const intervalRef = useRef(null);

  useEffect(() => {
    intervalRef.current = setInterval(() => {
      result.refetch();
    }, 10000);
    return () => clearInterval(intervalRef.current);
  }, [result.refetch]);

  return result;
}

export function useTuningHistory() {
  const result = useApi(() => api.getTuningHistory(), []);
  const intervalRef = useRef(null);

  useEffect(() => {
    intervalRef.current = setInterval(() => {
      result.refetch();
    }, 15000);
    return () => clearInterval(intervalRef.current);
  }, [result.refetch]);

  return result;
}

export function useLinkages() {
  const result = useApi(() => api.getLinkages(), []);
  const intervalRef = useRef(null);

  useEffect(() => {
    intervalRef.current = setInterval(() => {
      result.refetch();
    }, 10000);
    return () => clearInterval(intervalRef.current);
  }, [result.refetch]);

  return result;
}

export function usePendingLinkages() {
  const result = useApi(() => api.getPendingLinkages(), []);
  const intervalRef = useRef(null);

  useEffect(() => {
    intervalRef.current = setInterval(() => {
      result.refetch();
    }, 5000);
    return () => clearInterval(intervalRef.current);
  }, [result.refetch]);

  return result;
}

export function useCostBenefitHistory() {
  return useApi(() => api.getCostBenefitHistory(), []);
}
