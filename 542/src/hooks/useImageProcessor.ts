import { useCallback, useRef } from 'react';
import { useAppStore } from '@/store/useAppStore';
import {
  analyzeImageRegions,
  getColorAtPixel,
} from '@/utils/imageAnalysis';
import { simulateColorblind } from '@/utils/colorblind';
import type { ColorblindType } from '@/types';

export function useImageProcessor() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const {
    originalImage,
    selectedType,
    setOriginalImage,
    setContrastIssues,
    setWcagReport,
    setIsAnalyzing,
    setPickedColor,
    setSimulatedPickedColor,
  } = useAppStore();

  const loadImage = useCallback(
    (file: File) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        const img = new Image();
        img.onload = () => {
          const canvas = document.createElement('canvas');
          const maxWidth = 1200;
          const scale = img.width > maxWidth ? maxWidth / img.width : 1;
          canvas.width = img.width * scale;
          canvas.height = img.height * scale;

          const ctx = canvas.getContext('2d')!;
          ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
          const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
          setOriginalImage(imageData);
          canvasRef.current = canvas;
        };
        img.src = e.target?.result as string;
      };
      reader.readAsDataURL(file);
    },
    [setOriginalImage]
  );

  const loadImageFromUrl = useCallback(
    (url: string) => {
      const img = new Image();
      img.crossOrigin = 'anonymous';
      img.onload = () => {
        const canvas = document.createElement('canvas');
        const maxWidth = 1200;
        const scale = img.width > maxWidth ? maxWidth / img.width : 1;
        canvas.width = img.width * scale;
        canvas.height = img.height * scale;

        const ctx = canvas.getContext('2d')!;
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
        const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
        setOriginalImage(imageData);
        canvasRef.current = canvas;
      };
      img.src = url;
    },
    [setOriginalImage]
  );

  const analyzeImageContrast = useCallback(
    (imageData: ImageData) => {
      setIsAnalyzing(true);
      requestAnimationFrame(() => {
        const { issues, report } = analyzeImageRegions(imageData);
        setContrastIssues(issues);
        setWcagReport(report);
        setIsAnalyzing(false);
      });
    },
    [setContrastIssues, setWcagReport, setIsAnalyzing]
  );

  const pickColor = useCallback(
    (x: number, y: number) => {
      if (!originalImage) return;
      const color = getColorAtPixel(originalImage, x, y);
      if (color) {
        setPickedColor(color);
        const simulated = simulateColorblind(color, selectedType);
        setSimulatedPickedColor(simulated);
      }
    },
    [originalImage, selectedType, setPickedColor, setSimulatedPickedColor]
  );

  return {
    loadImage,
    loadImageFromUrl,
    analyzeImageContrast,
    pickColor,
    canvasRef,
  };
}
