import { useRef, useEffect, useState } from 'react';
import { Camera, Video, Clock, Gauge } from 'lucide-react';
import { useAppStore, type ActionResult } from '@/store/appStore';
import { cn } from '@/lib/utils';

function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  const ms = Math.floor((seconds % 1) * 100);
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}.${ms.toString().padStart(2, '0')}`;
}

function getBorderColor(confidence: number): string {
  if (confidence >= 0.8) return 'border-emerald-400';
  if (confidence >= 0.6) return 'border-cyan-400';
  if (confidence >= 0.4) return 'border-yellow-400';
  return 'border-red-400';
}

function getGlowColor(confidence: number): string {
  if (confidence >= 0.8) return 'shadow-emerald-400/50';
  if (confidence >= 0.6) return 'shadow-cyan-400/50';
  if (confidence >= 0.4) return 'shadow-yellow-400/50';
  return 'shadow-red-400/50';
}

export default function VideoPlayer() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const {
    inputSource,
    videoFile,
    isPlaying,
    isPaused,
    currentTimestamp,
    currentFps,
    topActions,
  } = useAppStore();

  useEffect(() => {
    if (inputSource === 'camera' && isPlaying && !isPaused) {
      setIsLoading(true);
      navigator.mediaDevices
        .getUserMedia({ video: { width: 1280, height: 720 } })
        .then((stream) => {
          streamRef.current = stream;
          if (videoRef.current) {
            videoRef.current.srcObject = stream;
            videoRef.current.play();
          }
          setIsLoading(false);
        })
        .catch(() => setIsLoading(false));
    } else if (inputSource === 'file' && videoFile && isPlaying && !isPaused) {
      setIsLoading(true);
      const url = URL.createObjectURL(videoFile);
      if (videoRef.current) {
        videoRef.current.src = url;
        videoRef.current.play();
      }
      setIsLoading(false);
    } else {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
        streamRef.current = null;
      }
      if (videoRef.current) {
        videoRef.current.pause();
        videoRef.current.srcObject = null;
        videoRef.current.src = '';
      }
    }

    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
      }
    };
  }, [inputSource, videoFile, isPlaying, isPaused]);

  useEffect(() => {
    if (videoRef.current) {
      if (isPaused) {
        videoRef.current.pause();
      } else if (isPlaying) {
        videoRef.current.play().catch(() => {});
      }
    }
  }, [isPaused, isPlaying]);

  return (
    <div className="relative w-full h-full bg-gray-950 rounded-2xl overflow-hidden border border-gray-700/50 shadow-2xl">
      <div className="absolute inset-0 bg-gradient-to-br from-cyan-500/5 via-transparent to-purple-500/5 pointer-events-none z-10" />
      <div className="absolute inset-0 border-2 border-transparent bg-gradient-to-r from-cyan-500 via-purple-500 to-pink-500 [mask:linear-gradient(#fff_0_0)_content-box,linear-gradient(#fff_0_0)] [mask-composite:exclude] rounded-2xl pointer-events-none z-20 opacity-50" />

      <div className="absolute top-4 left-4 z-30 flex items-center gap-2 px-3 py-1.5 bg-gray-900/80 backdrop-blur-sm rounded-lg border border-gray-700/50">
        {inputSource === 'camera' ? (
          <Camera className="w-4 h-4 text-cyan-400" />
        ) : (
          <Video className="w-4 h-4 text-purple-400" />
        )}
        <span className="text-xs font-medium text-gray-200">
          {inputSource === 'camera' ? 'Camera Input' : 'File Input'}
        </span>
      </div>

      <div className="absolute top-4 right-4 z-30 flex items-center gap-4">
        <div className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-900/80 backdrop-blur-sm rounded-lg border border-gray-700/50">
          <Clock className="w-4 h-4 text-cyan-400" />
          <span className="text-xs font-mono text-gray-200">
            {formatTime(currentTimestamp)}
          </span>
        </div>
        <div className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-900/80 backdrop-blur-sm rounded-lg border border-gray-700/50">
          <Gauge className="w-4 h-4 text-emerald-400" />
          <span className="text-xs font-mono text-gray-200">
            {currentFps.toFixed(1)} FPS
          </span>
        </div>
      </div>

      <div className="relative w-full h-full">
        {isLoading && (
          <div className="absolute inset-0 flex items-center justify-center bg-gray-900 z-40">
            <div className="w-8 h-8 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" />
          </div>
        )}
        <video
          ref={videoRef}
          className="w-full h-full object-cover"
          muted
          playsInline
        />
        <canvas
          ref={canvasRef}
          className="absolute inset-0 w-full h-full pointer-events-none"
        />
      </div>

      <div className="absolute bottom-4 left-4 right-4 z-30 flex flex-wrap gap-2">
        {topActions.slice(0, 3).map((action: ActionResult, index: number) => (
          <div
            key={`${action.label}-${index}`}
            className={cn(
              'px-3 py-2 rounded-lg backdrop-blur-md bg-gray-900/70 border-2 shadow-lg transition-all duration-300',
              getBorderColor(action.confidence),
              getGlowColor(action.confidence)
            )}
          >
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold text-gray-400">#{index + 1}</span>
              <span className="text-sm font-semibold text-white">{action.label}</span>
              <span
                className={cn(
                  'text-xs font-mono font-bold',
                  action.confidence >= 0.8 ? 'text-emerald-400' :
                  action.confidence >= 0.6 ? 'text-cyan-400' :
                  action.confidence >= 0.4 ? 'text-yellow-400' : 'text-red-400'
                )}
              >
                {(action.confidence * 100).toFixed(1)}%
              </span>
            </div>
          </div>
        ))}
      </div>

      <div className="absolute bottom-4 right-4 z-10 w-16 h-16 border border-cyan-500/30 rounded-tl-2xl border-b-0 border-r-0" />
      <div className="absolute top-4 right-4 z-10 w-16 h-16 border border-purple-500/30 rounded-bl-2xl border-t-0 border-r-0" />
      <div className="absolute bottom-4 left-4 z-10 w-16 h-16 border border-pink-500/30 rounded-tr-2xl border-b-0 border-l-0" />
      <div className="absolute top-4 left-4 z-10 w-16 h-16 border border-emerald-500/30 rounded-br-2xl border-t-0 border-l-0" />
    </div>
  );
}
