import { Sparkles } from 'lucide-react';
import { useColorStore } from '@/hooks/useColorStore';

const PRESET_COLORS = [
  '#EF4444', '#F97316', '#F59E0B', '#EAB308',
  '#84CC16', '#22C55E', '#10B981', '#14B8A6',
  '#06B6D4', '#3B82F6', '#6366F1', '#8B5CF6',
  '#A855F7', '#D946EF', '#EC4899', '#F43F5E',
  '#000000', '#525252', '#A3A3A3', '#FFFFFF',
];

export default function PresetPalette() {
  const { setCurrentColor } = useColorStore();

  return (
    <div className="bg-[#1e1e2e] rounded-xl p-5 shadow-lg">
      <div className="flex items-center gap-2 mb-4">
        <Sparkles className="w-5 h-5 text-gray-300" />
        <h3 className="text-gray-200 font-medium">预设色板</h3>
      </div>
      <div className="grid grid-cols-10 gap-2">
        {PRESET_COLORS.map((color) => (
          <button
            key={color}
            onClick={() => setCurrentColor(color)}
            className="w-7 h-7 rounded-lg transition-transform hover:scale-110 border border-white/10"
            style={{ backgroundColor: color }}
            title={color}
          />
        ))}
      </div>
    </div>
  );
}
