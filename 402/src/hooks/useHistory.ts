import { useState, useCallback, useEffect } from 'react';
import type { ScanRecord } from '../types';
import { loadRecords, saveRecords } from '../utils/storage';

interface UseHistoryReturn {
  records: ScanRecord[];
  filteredRecords: ScanRecord[];
  searchQuery: string;
  setSearchQuery: (query: string) => void;
  addRecord: (record: ScanRecord) => void;
  deleteRecord: (id: string) => void;
  deleteRecords: (ids: string[]) => void;
  clearRecords: () => void;
  updateNote: (id: string, note: string) => void;
}

export function useHistory(): UseHistoryReturn {
  const [records, setRecords] = useState<ScanRecord[]>([]);
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    setRecords(loadRecords());
  }, []);

  const filteredRecords = records.filter((record) => {
    if (!searchQuery.trim()) return true;
    const query = searchQuery.toLowerCase();
    return (
      record.content.toLowerCase().includes(query) ||
      (record.note && record.note.toLowerCase().includes(query))
    );
  });

  const updateRecords = useCallback((newRecords: ScanRecord[]) => {
    setRecords(newRecords);
    saveRecords(newRecords);
  }, []);

  const addRecord = useCallback((record: ScanRecord) => {
    setRecords((prev) => {
      const exists = prev.some(
        (r) => r.content === record.content && Date.now() - r.timestamp < 2000
      );
      if (exists) return prev;
      
      const newRecords = [record, ...prev];
      saveRecords(newRecords);
      return newRecords;
    });
  }, []);

  const deleteRecord = useCallback((id: string) => {
    const newRecords = records.filter((r) => r.id !== id);
    updateRecords(newRecords);
  }, [records, updateRecords]);

  const deleteRecords = useCallback((ids: string[]) => {
    const newRecords = records.filter((r) => !ids.includes(r.id));
    updateRecords(newRecords);
  }, [records, updateRecords]);

  const clearRecords = useCallback(() => {
    updateRecords([]);
  }, [updateRecords]);

  const updateNote = useCallback((id: string, note: string) => {
    const newRecords = records.map((r) =>
      r.id === id ? { ...r, note } : r
    );
    updateRecords(newRecords);
  }, [records, updateRecords]);

  return {
    records,
    filteredRecords,
    searchQuery,
    setSearchQuery,
    addRecord,
    deleteRecord,
    deleteRecords,
    clearRecords,
    updateNote,
  };
}
