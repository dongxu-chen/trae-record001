import { useRef } from 'react';
import {
  Play,
  Pause,
  Square,
  Camera,
  Video,
  Brain,
  SlidersHorizontal,
  Gauge,
  Upload,
} from 'lucide-react';
import { useAppStore } from '@/store/appStore';
import { cn } from '@/lib/utils';

interface ButtonProps {
  icon: React.ReactNode;
  label: string;
  onClick: () => void;
  variant?: 'primary' | 'secondary' | 'danger';
  active?: boolean;
  disabled?: boolean;
}

function ControlButton({
  icon,
  label,
  onClick,
  variant = 'secondary',
  active = false,
  disabled = false,
}: ButtonProps) {
  const baseStyles =
    'flex items-center gap-2 px-4 py-2.5 rounded-xl font-medium transition-all duration-300 transform hover:scale-105 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100';
  const variants = {
    primary:
      'bg-gradient-to-r from-cyan-500 to-blue-500 text-white hover:from-cyan-400 hover:to-blue-400 shadow-lg shadow-cyan-500/30 hover:shadow-cyan-500/50',
    secondary:
      'bg-gray-800/50 text-gray-200 hover:bg-gray-700/50 border border-gray-700/50 hover:border-gray-600/50 backdrop-blur-sm',
    danger:
      'bg-gray-800/50 text-red-400 hover:bg-red-500/20 border border-gray-700/50 hover:border-red-500/50 backdrop-blur-sm',
  };
  const activeStyles = active
    ? 'ring-2 ring-cyan-400 ring-offset-2 ring-offset-gray-900'
    : '';

  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={cn(baseStyles, variants[variant], activeStyles)}
    >
      {icon}
      <span className="text-sm">{label}</span>
    </button>
  );
}

export default function ControlBar() {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const {
    inputSource,
    model,
    confidenceThreshold,
    fps,
    isPlaying,
    isPaused,
    setInputSource,
    setModel,
    setConfidenceThreshold,
    setFps,
    setPlaying,
    setPaused,
    setVideoFile,
  } = useAppStore();

  const handleStart = () => {
    setPlaying(true);
    setPaused(false);
  };

  const handlePause = () => {
    setPaused(!isPaused);
  };

  const handleStop = () => {
    setPlaying(false);
    setPaused(false);
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setVideoFile(file);
      setInputSource('file');
    }
  };

  return (
    <div className="w-full bg-gray-900/60 backdrop-blur-xl rounded-2xl border border-gray-700/50 p-4">
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2 pr-4 border-r border-gray-700/50">
          <ControlButton
            icon={<Play className="w-4 h-4" />}
            label="Start"
            onClick={handleStart}
            variant="primary"
            disabled={isPlaying && !isPaused}
          />
          <ControlButton
            icon={<Pause className="w-4 h-4" />}
            label={isPaused ? 'Resume' : 'Pause'}
            onClick={handlePause}
            disabled={!isPlaying}
          />
          <ControlButton
            icon={<Square className="w-4 h-4" />}
            label="Stop"
            onClick={handleStop}
            variant="danger"
            disabled={!isPlaying}
          />
        </div>

        <div className="flex items-center gap-2 pr-4 border-r border-gray-700/50">
          <ControlButton
            icon={<Camera className="w-4 h-4" />}
            label="Camera"
            onClick={() => setInputSource('camera')}
            active={inputSource === 'camera'}
          />
          <ControlButton
            icon={<Video className="w-4 h-4" />}
            label="Video File"
            onClick={() => fileInputRef.current?.click()}
            active={inputSource === 'file'}
          />
          <input
            ref={fileInputRef}
            type="file"
            accept="video/*"
            onChange={handleFileUpload}
            className="hidden"
          />
          <input
            type="file"
            id="video-upload"
            accept="video/*"
            onChange={handleFileUpload}
            className="hidden"
          />
          <label
            htmlFor="video-upload"
            className="flex items-center gap-2 px-3 py-2.5 rounded-xl font-medium text-sm text-gray-300 bg-gray-800/50 border border-gray-700/50 hover:bg-gray-700/50 hover:border-gray-600/50 cursor-pointer transition-all duration-300 hover:scale-105 active:scale-95 backdrop-blur-sm"
          >
            <Upload className="w-4 h-4" />
            Upload
          </label>
        </div>

        <div className="flex items-center gap-3 pr-4 border-r border-gray-700/50">
          <div className="flex items-center gap-2">
            <Brain className="w-4 h-4 text-purple-400" />
            <select
              value={model}
              onChange={(e) =>
                setModel(e.target.value as 'TimeSformer' | 'VideoMAE')
              }
              className="bg-gray-800/50 text-gray-200 border border-gray-700/50 rounded-lg px-3 py-2 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-purple-400 focus:border-transparent transition-all duration-300 hover:bg-gray-700/50 backdrop-blur-sm"
            >
              <option value="TimeSformer">TimeSformer</option>
              <option value="VideoMAE">VideoMAE</option>
            </select>
          </div>
        </div>

        <div className="flex items-center gap-3 pr-4 border-r border-gray-700/50">
          <div className="flex items-center gap-2">
            <SlidersHorizontal className="w-4 h-4 text-yellow-400" />
            <span className="text-sm text-gray-300 font-medium">
              Threshold: {(confidenceThreshold * 100).toFixed(0)}%
            </span>
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={confidenceThreshold}
              onChange={(e) => setConfidenceThreshold(parseFloat(e.target.value))}
              className="w-24 h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-yellow-400"
            />
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Gauge className="w-4 h-4 text-cyan-400" />
          <span className="text-sm text-gray-300 font-medium">FPS:</span>
          {[15, 30, 60].map((f) => (
            <button
              key={f}
              onClick={() => setFps(f)}
              className={cn(
                'px-3 py-1.5 rounded-lg text-sm font-medium transition-all duration-300 transform hover:scale-105 active:scale-95',
                fps === f
                  ? 'bg-cyan-500 text-white shadow-lg shadow-cyan-500/30'
                  : 'bg-gray-800/50 text-gray-300 border border-gray-700/50 hover:bg-gray-700/50 backdrop-blur-sm'
              )}
            >
              {f}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
