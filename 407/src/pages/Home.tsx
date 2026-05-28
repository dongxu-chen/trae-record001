import { TerrainScene } from '@/components/terrain/TerrainScene';
import { Header } from '@/components/ui/Header';
import { useTerrainGUI } from '@/hooks/useTerrainGUI';

export default function Home() {
  useTerrainGUI();

  return (
    <div className="w-full h-screen overflow-hidden bg-slate-900">
      <Header />
      <TerrainScene />
      <div className="fixed bottom-4 left-4 z-40 text-white/50 text-xs font-mono bg-black/30 backdrop-blur-sm px-3 py-2 rounded-lg">
        <p>🖱️ 拖拽旋转 · 滚轮缩放 · 右键平移</p>
      </div>
    </div>
  );
}
