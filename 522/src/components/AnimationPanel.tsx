import { useState, useEffect, useRef, useCallback } from 'react';
import {
  Play,
  Pause,
  Square,
  RotateCcw,
  Repeat,
  ArrowLeftRight,
  Sparkles,
  Clock,
  Settings,
  Activity,
} from 'lucide-react';
import {
  AnimationEngine,
  AnimationPreset,
  ANIMATION_PRESETS,
  AnimationLoopMode,
} from '@/utils/animationEngine';
import useFilterStore from '@/store/filterStore';
import { cn } from '@/lib/utils';

const presetInfo: Record<AnimationPreset, { name: string; icon: React.ReactNode; desc: string }> = {
  fadeIn: { name: '渐入', icon: <Sparkles size={16} />, desc: '从无到有' },
  pulse: { name: '脉动', icon: <Activity size={16} />, desc: '强弱交替' },
  wave: { name: '波浪', icon: <Activity size={16} />, desc: '波浪变化' },
  flash: { name: '闪烁', icon: <Activity size={16} />, desc: '快速闪烁' },
  breathe: { name: '呼吸', icon: <Activity size={16} />, desc: '缓慢呼吸' },
  custom: { name: '自定义', icon: <Settings size={16} />, desc: '自定义关键帧' },
};

const loopModeInfo: Record<AnimationLoopMode, { icon: React.ReactNode; name: string }> = {
  once: { icon: <Square size={14} />, name: '单次' },
  loop: { icon: <Repeat size={14} />, name: '循环' },
  pingpong: { icon: <ArrowLeftRight size={14} />, name: '往返' },
};

interface AnimationPanelProps {}

export default function AnimationPanel({}: AnimationPanelProps) {
  const animationEngineRef = useRef<AnimationEngine | null>(null);
  const { filterIntensity, setFilterIntensity } = useFilterStore();

  const [selectedPreset, setSelectedPreset] = useState<AnimationPreset>('pulse');
  const [loopMode, setLoopMode] = useState<AnimationLoopMode>('loop');
  const [isPlaying, setIsPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [duration, setDuration] = useState(2000);
  const [currentValue, setCurrentValue] = useState(0);

  const ensureEngine = useCallback(() => {
    if (!animationEngineRef.current) {
      animationEngineRef.current = new AnimationEngine();
      animationEngineRef.current.setOnUpdate((values, state) => {
        const intensity = values.get('intensity');
        if (intensity !== undefined) {
          setCurrentValue(intensity);
          setFilterIntensity(intensity);
        }
        setProgress(state.progress);
        setIsPlaying(state.isPlaying);
      });
    }
    return animationEngineRef.current;
  }, [setFilterIntensity]);

  const applyPreset = useCallback(
    (preset: AnimationPreset) => {
      const engine = ensureEngine();
      const animations = ANIMATION_PRESETS[preset];
      const adjusted = animations.map((a) => ({ ...a, duration, loopMode }));
      engine.setAnimations(adjusted);
      engine.setLoopMode(loopMode);
      setSelectedPreset(preset);
    },
    [ensureEngine, duration, loopMode]
  );

  const handlePlayPause = useCallback(() => {
    const engine = ensureEngine();
    if (isPlaying) {
      engine.pause();
    } else {
      applyPreset(selectedPreset);
      engine.play();
    }
    setIsPlaying(!isPlaying);
  }, [ensureEngine, isPlaying, selectedPreset, applyPreset]);

  const handleStop = useCallback(() => {
    const engine = ensureEngine();
    engine.stop();
    setIsPlaying(false);
    setProgress(0);
    setCurrentValue(0);
  }, [ensureEngine]);

  const handleSeek = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const engine = ensureEngine();
      const newProgress = parseFloat(e.target.value);
      engine.seek(newProgress);
    },
    [ensureEngine]
  );

  const handleLoopModeChange = useCallback(
    (mode: AnimationLoopMode) => {
      setLoopMode(mode);
      const engine = ensureEngine();
      engine.setLoopMode(mode);
      if (isPlaying) {
        applyPreset(selectedPreset);
      }
    },
    [ensureEngine, isPlaying, selectedPreset, applyPreset]
  );

  const handleDurationChange = useCallback(
    (d: number) => {
      setDuration(d);
      if (isPlaying) {
        applyPreset(selectedPreset);
      }
    },
    [isPlaying, selectedPreset, applyPreset]
  );

  useEffect(() => {
    return () => {
      if (animationEngineRef.current) {
        animationEngineRef.current.destroy();
        animationEngineRef.current = null;
      }
    };
  }, []);

  return (
    <div className="glass-panel rounded-xl overflow-hidden">
      <div className="p-4 border-b border-surface-border">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-neon-amber to-neon-cyan flex items-center justify-center">
            <Activity size={16} className="text-white" />
          </div>
          <div>
            <h3 className="font-display font-semibold text-sm neon-text">滤镜动画</h3>
            <p className="text-xs text-gray-500">强度随时间变化</p>
          </div>
        </div>
        <div className="flex items-center gap-1 bg-surface-card rounded-lg p-0.5">
          {(Object.keys(loopModeInfo) as AnimationLoopMode[]).map((mode) => (
            <button
              key={mode}
              onClick={() => handleLoopModeChange(mode)}
              title={loopModeInfo[mode].name}
              className={cn(
                'p-1.5 rounded-md transition-all',
                loopMode === mode
                  ? 'bg-neon-amber/20 text-neon-amber'
                  : 'text-gray-400 hover:text-white'
              )}
            >
              {loopModeInfo[mode].icon}
            </button>
          ))}
        </div>
      </div>
    </div>

    <div className="p-3 space-y-3">
      <div className="space-y-1.5">
        <div className="flex items-center justify-between">
          <label className="text-xs font-medium text-gray-400">动画模式</label>
          <div className="flex items-center gap-1 text-xs text-gray-500">
            <Clock size={12} />
            {Math.round(duration / 100) / 10}s
          </div>
        </div>
        <div className="grid grid-cols-3 gap-1.5">
          {(Object.keys(presetInfo) as AnimationPreset[]).slice(0, 6).map((preset) => (
            <button
              key={preset}
              onClick={() => {
                setSelectedPreset(preset);
                if (isPlaying) {
                  applyPreset(preset);
                }
              }}
              className={cn(
                'p-2 rounded-lg text-xs transition-all flex flex-col items-center gap-1',
                selectedPreset === preset
                  ? 'bg-gradient-to-br from-neon-amber/20 to-neon-cyan/20 border border-neon-amber/40 text-neon-amber'
                  : 'bg-surface-card border border-transparent hover:bg-surface-hover text-gray-400'
              )}
            >
              {presetInfo[preset].icon}
              <span>{presetInfo[preset].name}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="space-y-1.5">
        <div className="flex items-center justify-between">
          <label className="text-xs font-medium text-gray-400">动画时长</label>
          <span className="text-xs text-neon-cyan font-mono">{duration}ms</span>
        </div>
        <input
          type="range"
          min={500}
          max={10000}
          step={100}
          value={duration}
          onChange={(e) => handleDurationChange(parseInt(e.target.value))}
          className="range-neon w-full"
        />
        <div className="flex justify-between text-[10px] text-gray-600">
          <span>0.5s</span>
          <span>5s</span>
          <span>10s</span>
        </div>
      </div>

      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <label className="text-xs font-medium text-gray-400">时间轴</label>
          <span className="text-xs text-gray-500">
            {Math.round(progress * 100)}% · {Math.round(currentValue * 100)}%
          </span>
        </div>
        <div className="relative">
          <input
            type="range"
            min={0}
            max={1}
            step={0.001}
            value={progress}
            onChange={handleSeek}
            className="range-neon w-full"
            disabled={isPlaying}
          />
          {isPlaying && (
            <div className="absolute top-0 left-0 h-1.5 rounded-full bg-gradient-to-r from-neon-amber to-neon-cyan pointer-events-none transition-all"
              style={{ width: `${progress * 100}%` }}
            />
          )}
        </div>
      </div>

      <div className="h-16 bg-surface-dark rounded-lg p-3 flex items-center justify-center gap-4">
        <div className="flex-1 h-full flex items-center gap-2">
          <div
            className="h-full flex-1 rounded-md bg-surface-card overflow-hidden relative">
            <div
              className="h-full bg-gradient-to-r from-neon-amber/80 to-neon-cyan/80 transition-all"
              style={{ width: `${currentValue * 100}%` }}
            />
          </div>
        </div>
        <span className="text-xs font-mono text-neon-cyan w-12 text-right">
          {Math.round(currentValue * 100)}%
        </span>
      </div>

      <div className="flex gap-2">
        <button
          onClick={handlePlayPause}
          className={cn(
            'flex-1 py-2 rounded-lg font-medium flex items-center justify-center gap-2 transition-all',
            isPlaying
              ? 'bg-surface-card hover:bg-surface-hover text-white'
              : 'bg-gradient-to-r from-neon-amber to-neon-cyan text-white hover:shadow-lg hover:shadow-neon-amber/20'
          )}
        >
          {isPlaying ? <Pause size={16} /> : <Play size={16} />}
          {isPlaying ? '暂停' : '播放'}
        </button>
        <button
          onClick={handleStop}
          className="px-4 py-2 rounded-lg bg-surface-card hover:bg-surface-hover transition-colors"
          title="停止"
        >
          <RotateCcw size={16} />
        </button>
      </div>

      <div className="flex items-center justify-between text-xs text-gray-500">
        <span>基础强度: {Math.round(filterIntensity * 100)}%</span>
        <span>{presetInfo[selectedPreset].desc}</span>
      </div>
    </div>
    </div>
  );
}
