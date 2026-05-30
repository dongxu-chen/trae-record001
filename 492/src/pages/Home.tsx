import { LEDPreview } from '../components/LEDPreview';
import { ControlPanel } from '../components/ControlPanel';

export default function Home() {
  return (
    <div className="w-full h-full flex bg-[#0a0a0f]">
      <div className="flex-1 p-6">
        <div className="h-full flex flex-col">
          <div className="mb-6">
            <h1 className="text-3xl font-bold text-white mb-2" style={{ fontFamily: "'Orbitron', sans-serif" }}>
              <span className="text-cyan-400">LED</span> 字幕滚动组件
            </h1>
            <p className="text-gray-400 text-sm">
              自定义文字、字体、颜色、滚动速度、背景特效 · 实时预览
            </p>
          </div>
          <div className="flex-1 min-h-0">
            <LEDPreview />
          </div>
        </div>
      </div>
      <ControlPanel />
    </div>
  );
}