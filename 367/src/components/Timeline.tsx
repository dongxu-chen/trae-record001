import { useEffect, useRef } from 'react';
import { Play, Pause, SkipBack, SkipForward } from 'lucide-react';
import { useGraphStore } from '@/store/graphStore';

export default function Timeline() {
  const currentTime = useGraphStore((s) => s.currentTime);
  const minTime = useGraphStore((s) => s.minTime);
  const maxTime = useGraphStore((s) => s.maxTime);
  const isPlaying = useGraphStore((s) => s.isPlaying);
  const playSpeed = useGraphStore((s) => s.playSpeed);
  const setCurrentTime = useGraphStore((s) => s.setCurrentTime);
  const setIsPlaying = useGraphStore((s) => s.setIsPlaying);
  const triples = useGraphStore((s) => s.triples);

  const intervalRef = useRef<number | null>(null);

  useEffect(() => {
    if (isPlaying) {
      const step = (maxTime - minTime) / 600;
      intervalRef.current = window.setInterval(() => {
        setCurrentTime((prev) => {
          const next = prev + step * playSpeed;
          if (next >= maxTime) {
            setIsPlaying(false);
            return maxTime;
          }
          return next;
        });
      }, 16);
    } else if (intervalRef.current) {
      clearInterval(intervalRef.current);
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [isPlaying, playSpeed, maxTime, minTime, setCurrentTime, setIsPlaying]);

  const formatDate = (ts: number) => {
    const d = new Date(ts);
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
  };

  const progress = maxTime > minTime ? (currentTime - minTime) / (maxTime - minTime) : 0;

  const eventMarkers = triples
    .filter((t) => t.timestamp)
    .map((t) => t.timestamp!)
    .filter((v, i, a) => a.indexOf(v) === i)
    .sort((a, b) => a - b);

  return (
    <div className="px-4 py-3 border-t border-slate-700/50 glass-panel">
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-1">
          <button
            onClick={() => {
              setCurrentTime(minTime);
              setIsPlaying(false);
            }}
            className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-700/50 rounded"
            title="回到起点"
          >
            <SkipBack size={16} />
          </button>
          <button
            onClick={() => setIsPlaying(!isPlaying)}
            className="p-2 text-cyan-400 hover:text-cyan-300 hover:bg-cyan-500/20 rounded"
            title={isPlaying ? '暂停' : '播放'}
          >
            {isPlaying ? <Pause size={18} /> : <Play size={18} />}
          </button>
          <button
            onClick={() => {
              setCurrentTime(maxTime);
              setIsPlaying(false);
            }}
            className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-700/50 rounded"
            title="跳到终点"
          >
            <SkipForward size={16} />
          </button>
        </div>

        <div className="flex-1 relative">
          <input
            type="range"
            min={minTime}
            max={maxTime}
            value={currentTime}
            onChange={(e) => {
              setCurrentTime(Number(e.target.value));
              setIsPlaying(false);
            }}
            className="w-full h-2 rounded-full bg-slate-700/50 appearance-none cursor-pointer accent-cyan-400"
          />
          <div className="absolute top-0 left-0 right-0 pointer-events-none h-2 flex items-center">
            {eventMarkers.map((ts, idx) => {
              const pos = (ts - minTime) / (maxTime - minTime);
              return (
                <div
                  key={idx}
                  className="absolute w-1 h-4 bg-yellow-400/60 rounded-full"
                  style={{ left: `${pos * 100}%`, transform: 'translateX(-50%)' }}
                />
              );
            })}
          </div>
        </div>

        <div className="w-28 text-right">
          <div className="text-xs text-cyan-400 font-mono">{formatDate(currentTime)}</div>
          <div className="text-[10px] text-slate-500">
            速度: <span className="text-slate-300">{playSpeed.toFixed(1)}x</span>
          </div>
        </div>

        <div className="flex flex-col gap-1">
          {[0.5, 1, 2].map((s) => (
            <button
              key={s}
              onClick={() => useGraphStore.getState().setPlaySpeed(s)}
              className={`text-[10px] px-2 py-0.5 rounded ${
                playSpeed === s
                  ? 'bg-cyan-500/30 text-cyan-300'
                  : 'bg-slate-700/40 text-slate-400 hover:bg-slate-700/60'
              }`}
            >
              {s}x
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
