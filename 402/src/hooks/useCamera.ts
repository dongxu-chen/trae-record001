import { useState, useCallback, useRef, useEffect } from 'react';

interface UseCameraReturn {
  stream: MediaStream | null;
  videoRef: React.RefObject<HTMLVideoElement>;
  isActive: boolean;
  error: string | null;
  startCamera: (facingMode?: 'user' | 'environment') => Promise<void>;
  stopCamera: () => void;
  switchCamera: () => void;
  torchSupported: boolean;
  torchEnabled: boolean;
  toggleTorch: () => void;
}

export function useCamera(): UseCameraReturn {
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [isActive, setIsActive] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [torchSupported, setTorchSupported] = useState(false);
  const [torchEnabled, setTorchEnabled] = useState(false);
  const [facingMode, setFacingMode] = useState<'user' | 'environment'>('environment');
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);

  const startCamera = useCallback(async (mode?: 'user' | 'environment') => {
    try {
      setError(null);
      const currentMode = mode || facingMode;
      
      const constraints: MediaStreamConstraints = {
        video: {
          facingMode: currentMode,
          width: { ideal: 1280 },
          height: { ideal: 720 },
        },
        audio: false,
      };

      const mediaStream = await navigator.mediaDevices.getUserMedia(constraints);
      streamRef.current = mediaStream;
      setStream(mediaStream);
      setIsActive(true);

      const track = mediaStream.getVideoTracks()[0];
      if (track) {
        const capabilities = track.getCapabilities() as MediaTrackCapabilities & { torch?: boolean };
        setTorchSupported(!!capabilities.torch);
      }

      if (videoRef.current) {
        videoRef.current.srcObject = mediaStream;
        await videoRef.current.play().catch(() => {});
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '无法访问摄像头');
      setIsActive(false);
    }
  }, [facingMode]);

  const stopCamera = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
      setStream(null);
      setIsActive(false);
      setTorchEnabled(false);
    }
  }, []);

  const switchCamera = useCallback(() => {
    const newMode = facingMode === 'user' ? 'environment' : 'user';
    setFacingMode(newMode);
    stopCamera();
    setTimeout(() => startCamera(newMode), 100);
  }, [facingMode, startCamera, stopCamera]);

  const toggleTorch = useCallback(() => {
    if (!streamRef.current || !torchSupported) return;
    
    const track = streamRef.current.getVideoTracks()[0];
    if (track) {
      const newState = !torchEnabled;
      track.applyConstraints({
        advanced: [{ torch: newState } as MediaTrackConstraints],
      } as MediaTrackConstraints);
      setTorchEnabled(newState);
    }
  }, [torchSupported, torchEnabled]);

  useEffect(() => {
    return () => {
      stopCamera();
    };
  }, [stopCamera]);

  return {
    stream,
    videoRef,
    isActive,
    error,
    startCamera,
    stopCamera,
    switchCamera,
    torchSupported,
    torchEnabled,
    toggleTorch,
  };
}
