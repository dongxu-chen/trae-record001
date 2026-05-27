import { useState, useCallback } from 'react';

interface UseClipboardReturn {
  copied: boolean;
  copyToClipboard: (text: string) => Promise<void>;
}

export const useClipboard = (): UseClipboardReturn => {
  const [copied, setCopied] = useState(false);

  const copyToClipboard = useCallback(async (text: string): Promise<void> => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  }, []);

  return { copied, copyToClipboard };
};
