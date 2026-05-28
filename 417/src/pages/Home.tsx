import { Palette } from 'lucide-react';
import ColorConverter from '@/components/ColorConverter';
import ColorPreview from '@/components/ColorPreview';
import ColorCompare from '@/components/ColorCompare';
import ColorPickerComp from '@/components/ColorPickerComp';
import PresetPalette from '@/components/PresetPalette';
import ColorHistory from '@/components/ColorHistory';
import ColorSchemeGenerator from '@/components/ColorSchemeGenerator';
import ColorContrast from '@/components/ColorContrast';
import EyeDropperTool from '@/components/EyeDropperTool';

export default function Home() {
  return (
    <div className="min-h-screen bg-[#13131f] text-gray-200">
      <header className="px-6 py-4 border-b border-white/5">
        <div className="max-w-7xl mx-auto flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#5b5fc7] to-[#a855f7] flex items-center justify-center">
            <Palette className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-semibold text-white">ColorLab</h1>
            <p className="text-xs text-gray-500">专业颜色空间转换工具</p>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto p-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <ColorConverter />
            <ColorHistory />
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <ColorPickerComp />
              <PresetPalette />
            </div>
          </div>

          <div className="space-y-6">
            <ColorPreview />
            <ColorCompare />
            <ColorContrast />
            <EyeDropperTool />
            <ColorSchemeGenerator />
          </div>
        </div>
      </main>

      <footer className="text-center py-6 text-gray-600 text-xs border-t border-white/5">
        <p>ColorLab &copy; 2026 — RGB · HEX · HSL · CMYK · LAB</p>
      </footer>
    </div>
  );
}
