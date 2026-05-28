import { useEffect, useRef, useState, useCallback } from 'react';
import type { ScanRecord } from '../types';

interface UseScannerGunReturn {
  isGunMode: boolean;
  setIsGunMode: (mode: boolean) => void;
  gunInput: string;
  gunRecords: ScanRecord[];
  clearGunInput: () => void;
}

const KEYPRESS_THRESHOLD = 50;
const MIN_GUN_LENGTH = 3;
const GUN_PREFIX_TIMEOUT = 100;

export function useScannerGun(
  onScan: (content: string) => void,
  _autoSave: boolean
): UseScannerGunReturn {
  const [isGunMode, setIsGunMode] = useState(false);
  const [gunInput, setGunInput] = useState('');
  const [gunRecords, setGunRecords] = useState<ScanRecord[]>([]);
  
  const bufferRef = useRef<string>('');
  const lastKeyTimeRef = useRef<number>(0);
  const timeoutRef = useRef<number | null>(null);

  const clearGunInput = useCallback(() => {
    setGunInput('');
    bufferRef.current = '';
    setGunRecords([]);
  }, []);

  const processGunInput = useCallback((content: string) => {
    if (content.length < MIN_GUN_LENGTH) return;

    const record: ScanRecord = {
      id: Date.now().toString(),
      content,
      type: 'qrcode',
      format: 'scanner_gun',
      timestamp: Date.now(),
    };

    setGunRecords((prev) => [record, ...prev].slice(0, 10));
    setGunInput(content);
    onScan(content);

    bufferRef.current = '';
  }, [onScan]);

  useEffect(() => {
    if (!isGunMode) {
      bufferRef.current = '';
      return;
    }

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Enter') {
        if (bufferRef.current.length >= MIN_GUN_LENGTH) {
          processGunInput(bufferRef.current.trim());
        }
        e.preventDefault();
        return;
      }

      if (e.key.length === 1 && !e.ctrlKey && !e.metaKey && !e.altKey) {
        const now = Date.now();
        const timeSinceLastKey = now - lastKeyTimeRef.current;

        if (timeSinceLastKey > KEYPRESS_THRESHOLD && bufferRef.current.length > 0) {
          bufferRef.current = '';
        }

        bufferRef.current += e.key;
        lastKeyTimeRef.current = now;

        if (timeoutRef.current) {
          clearTimeout(timeoutRef.current);
        }

        timeoutRef.current = window.setTimeout(() => {
          if (bufferRef.current.length >= MIN_GUN_LENGTH) {
            processGunInput(bufferRef.current.trim());
          }
        }, GUN_PREFIX_TIMEOUT);
      }
    };

    window.addEventListener('keydown', handleKeyDown);

    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, [isGunMode, processGunInput]);

  return {
    isGunMode,
    setIsGunMode,
    gunInput,
    gunRecords,
    clearGunInput,
  };
}
