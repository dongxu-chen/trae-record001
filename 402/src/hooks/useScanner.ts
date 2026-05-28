import { useState, useCallback, useRef, useEffect } from 'react';
import type { ScanResult } from '../types';

interface UseScannerReturn {
  isScanning: boolean;
  lastResult: ScanResult | null;
  startScanning: () => void;
  stopScanning: () => void;
  setContinuousMode: (mode: boolean) => void;
  continuousMode: boolean;
  scanQueueSize: number;
}

interface FrameQueueItem {
  id: number;
  imageData: ImageData;
  timestamp: number;
}

const MAX_QUEUE_SIZE = 3;
const SCAN_INTERVAL = 100;

export function useScanner(
  videoRef: React.RefObject<HTMLVideoElement>,
  isCameraActive: boolean,
  lowLightEnhance: boolean
): UseScannerReturn {
  const [isScanning, setIsScanning] = useState(false);
  const [lastResult, setLastResult] = useState<ScanResult | null>(null);
  const [continuousMode, setContinuousMode] = useState(false);
  const [scanQueueSize, setScanQueueSize] = useState(0);
  
  const workerRef = useRef<Worker | null>(null);
  const animationFrameRef = useRef<number | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const frameQueueRef = useRef<FrameQueueItem[]>([]);
  const isWorkerBusyRef = useRef(false);
  const lastScanTimeRef = useRef(0);
  const lastContentRef = useRef<string | null>(null);
  const frameIdRef = useRef(0);
  const continuousModeRef = useRef(continuousMode);
  const lowLightEnhanceRef = useRef(lowLightEnhance);
  const isScanningRef = useRef(isScanning);

  useEffect(() => {
    continuousModeRef.current = continuousMode;
  }, [continuousMode]);

  useEffect(() => {
    lowLightEnhanceRef.current = lowLightEnhance;
  }, [lowLightEnhance]);

  useEffect(() => {
    isScanningRef.current = isScanning;
  }, [isScanning]);

  const processNextFrame = useCallback(() => {
    if (!workerRef.current || frameQueueRef.current.length === 0) {
      return;
    }

    const frame = frameQueueRef.current.shift();
    if (!frame) return;

    setScanQueueSize(frameQueueRef.current.length);

    isWorkerBusyRef.current = true;
    
    workerRef.current.postMessage({
      type: 'scan',
      imageData: frame.imageData,
      enableLowLight: lowLightEnhanceRef.current,
    }, [frame.imageData.data.buffer]);
  }, []);

  const captureFrame = useCallback(() => {
    if (!isScanningRef.current || !videoRef.current) {
      return;
    }

    const video = videoRef.current;
    if (video.readyState < 2 || video.videoWidth === 0) {
      animationFrameRef.current = requestAnimationFrame(captureFrame);
      return;
    }

    const now = Date.now();
    if (now - lastScanTimeRef.current < SCAN_INTERVAL) {
      animationFrameRef.current = requestAnimationFrame(captureFrame);
      return;
    }

    if (!canvasRef.current) {
      canvasRef.current = document.createElement('canvas');
    }

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d', { willReadFrequently: true });
    
    if (ctx) {
      const scaleFactor = 0.5;
      canvas.width = video.videoWidth * scaleFactor;
      canvas.height = video.videoHeight * scaleFactor;
      
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      
      const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
      
      if (frameQueueRef.current.length < MAX_QUEUE_SIZE) {
        frameIdRef.current++;
        frameQueueRef.current.push({
          id: frameIdRef.current,
          imageData,
          timestamp: now,
        });
        setScanQueueSize(frameQueueRef.current.length);
        
        if (!isWorkerBusyRef.current) {
          processNextFrame();
        }
      }
    }

    animationFrameRef.current = requestAnimationFrame(captureFrame);
  }, [videoRef, processNextFrame]);

  const stopScanning = useCallback(() => {
    setIsScanning(false);
    
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
      animationFrameRef.current = null;
    }
    
    frameQueueRef.current = [];
    setScanQueueSize(0);
  }, []);

  useEffect(() => {
    if (typeof window !== 'undefined' && window.Worker) {
      workerRef.current = new Worker(
        new URL('../workers/qrScanner.worker.ts', import.meta.url),
        { type: 'module' }
      );

      workerRef.current.onmessage = (e: MessageEvent) => {
        isWorkerBusyRef.current = false;
        
        if (e.data.success && e.data.content) {
          const now = Date.now();
          const content = e.data.content;
          
          if (content !== lastContentRef.current || now - lastScanTimeRef.current > 2000) {
            lastContentRef.current = content;
            lastScanTimeRef.current = now;
            
            const result: ScanResult = {
              success: true,
              content: e.data.content,
              format: e.data.format || 'qr_code',
            };
            
            setLastResult(result);
            
            if (!continuousModeRef.current) {
              stopScanning();
            }
            
            if ('vibrate' in navigator) {
              navigator.vibrate(100);
            }
          }
        }
        
        processNextFrame();
      };

      workerRef.current.postMessage({ type: 'init' });

      return () => {
        if (workerRef.current) {
          workerRef.current.terminate();
          workerRef.current = null;
        }
      };
    }
  }, [processNextFrame, stopScanning]);

  const startScanning = useCallback(() => {
    if (!isCameraActive || isScanningRef.current) return;
    
    setIsScanning(true);
    setLastResult(null);
    lastContentRef.current = null;
    lastScanTimeRef.current = 0;
    frameQueueRef.current = [];
    isWorkerBusyRef.current = false;
    
    animationFrameRef.current = requestAnimationFrame(captureFrame);
  }, [isCameraActive, captureFrame]);

  useEffect(() => {
    return () => {
      stopScanning();
    };
  }, [stopScanning]);

  return {
    isScanning,
    lastResult,
    startScanning,
    stopScanning,
    setContinuousMode,
    continuousMode,
    scanQueueSize,
  };
}
