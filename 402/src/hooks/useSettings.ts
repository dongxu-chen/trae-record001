import { useState, useCallback, useEffect } from 'react';
import type { ScanSettings } from '../types';
import { loadSettings, saveSettings } from '../utils/storage';

interface UseSettingsReturn {
  settings: ScanSettings;
  updateSettings: (partial: Partial<ScanSettings>) => void;
  resetSettings: () => void;
}

const DEFAULT_SETTINGS: ScanSettings = {
  continuousMode: false,
  torchEnabled: false,
  lowLightEnhance: false,
  frontCamera: false,
  exportFormat: 'json',
  autoSave: true,
  vibrateOnSuccess: true,
};

export function useSettings(): UseSettingsReturn {
  const [settings, setSettings] = useState<ScanSettings>(DEFAULT_SETTINGS);

  useEffect(() => {
    setSettings(loadSettings());
  }, []);

  const updateSettings = useCallback((partial: Partial<ScanSettings>) => {
    setSettings((prev) => {
      const newSettings = { ...prev, ...partial };
      saveSettings(newSettings);
      return newSettings;
    });
  }, []);

  const resetSettings = useCallback(() => {
    setSettings(DEFAULT_SETTINGS);
    saveSettings(DEFAULT_SETTINGS);
  }, []);

  return {
    settings,
    updateSettings,
    resetSettings,
  };
}
