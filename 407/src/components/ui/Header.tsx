import { RefreshCw, Shuffle, Play, Pause } from 'lucide-react';
import { useTerrainStore } from '@/store/terrainStore';
import { useState } from 'react';

export function Header() {
  const autoRotate = useTerrainStore((s) => s.autoRotate);
  const set = useTerrainStore((s) => s.set);
  const randomize = useTerrainStore((s) => s.randomize);
  const reset = useTerrainStore((s) => s.reset);
  const [hint, setHint] = useState('');

  const showHint = (text: string) => {
    setHint(text);
    setTimeout(() => setHint(''), 1500);
  };

  return (
    <header className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-6 py-4 backdrop-blur-md bg-black/30 border-b border-white/10">
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <span className="text-3xl">🏔️</span>
          <div>
            <h1 className="text-xl font-bold text-white tracking-wide" style={{ fontFamily: "'Space Grotesk', sans-serif" }}>
              3D 地形生成器
            </h1>
            <p className="text-xs text-white/60" style={{ fontFamily: "'JetBrains Mono', monospace" }}>
              Procedural Terrain · LOD · Sculpting · Erosion
            </p>
          </div>
        </div>
      </div>

      <div className="flex items-center gap-3">
        {hint && (
          <span className="text-sm text-white/80 bg-white/10 px-3 py-1 rounded-full animate-pulse">
            {hint}
          </span>
        )}

        <button
          onClick={() => { set('autoRotate', !autoRotate); showHint(autoRotate ? '暂停旋转' : '自动旋转'); }}
          className="p-2 rounded-lg bg-white/10 hover:bg-white/20 text-white transition-all hover:scale-105"
          title="自动旋转"
        >
          {autoRotate ? <Pause size={18} /> : <Play size={18} />}
        </button>

        <button
          onClick={() => { randomize(); showHint('新地形已生成'); }}
          className="p-2 rounded-lg bg-amber-500/80 hover:bg-amber-500 text-white transition-all hover:scale-105"
          title="随机种子"
        >
          <Shuffle size={18} />
        </button>

        <button
          onClick={() => { reset(); showHint('参数已重置'); }}
          className="p-2 rounded-lg bg-white/10 hover:bg-white/20 text-white transition-all hover:scale-105"
          title="重置参数"
        >
          <RefreshCw size={18} />
        </button>
      </div>
    </header>
  );
}
