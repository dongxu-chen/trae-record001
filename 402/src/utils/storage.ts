import type { ScanRecord, ScanSettings } from '../types';

const RECORDS_KEY = 'scanner_records';
const SETTINGS_KEY = 'scanner_settings';

export function loadRecords(): ScanRecord[] {
  try {
    const data = localStorage.getItem(RECORDS_KEY);
    return data ? JSON.parse(data) : [];
  } catch {
    return [];
  }
}

export function saveRecords(records: ScanRecord[]): void {
  localStorage.setItem(RECORDS_KEY, JSON.stringify(records));
}

export function addRecord(record: ScanRecord): ScanRecord[] {
  const records = loadRecords();
  records.unshift(record);
  saveRecords(records);
  return records;
}

export function deleteRecord(id: string): ScanRecord[] {
  const records = loadRecords().filter((r) => r.id !== id);
  saveRecords(records);
  return records;
}

export function deleteRecords(ids: string[]): ScanRecord[] {
  const records = loadRecords().filter((r) => !ids.includes(r.id));
  saveRecords(records);
  return records;
}

export function clearRecords(): void {
  saveRecords([]);
}

export function loadSettings(): ScanSettings {
  try {
    const data = localStorage.getItem(SETTINGS_KEY);
    if (data) {
      return JSON.parse(data);
    }
  } catch {
    // ignore
  }
  return {
    continuousMode: false,
    torchEnabled: false,
    lowLightEnhance: false,
    frontCamera: false,
    exportFormat: 'json',
    autoSave: true,
    vibrateOnSuccess: true,
  };
}

export function saveSettings(settings: ScanSettings): void {
  localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
}
