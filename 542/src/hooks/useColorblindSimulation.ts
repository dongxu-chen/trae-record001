import { useEffect } from 'react';
import { useAppStore } from '@/store/useAppStore';
import { useImageProcessor } from '@/hooks/useImageProcessor';

export function useColorblindSimulation() {
  const { originalImage } = useAppStore();
  const { analyzeImageContrast } = useImageProcessor();

  useEffect(() => {
    if (originalImage) {
      analyzeImageContrast(originalImage);
    }
  }, [originalImage, analyzeImageContrast]);
}
