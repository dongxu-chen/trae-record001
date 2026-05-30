import { Lightbulb, Copy, ArrowRight } from 'lucide-react';
import type { ColorSuggestion } from '@/types';
import { rgbToHex } from '@/utils/color';

interface SuggestionCardProps {
  suggestion: ColorSuggestion;
  onCopy?: (text: string) => void;
  onPreview?: (color: ColorSuggestion) => void;
}

export function SuggestionCard({ suggestion, onCopy, onPreview }: SuggestionCardProps) {
  const origHex = rgbToHex(suggestion.original);
  const sugHex = rgbToHex(suggestion.suggested);

  return (
    <div className="bg-zinc-900 rounded-xl border border-zinc-800 p-4 space-y-3 hover:border-zinc-700 transition-colors">
      <div className="flex items-center gap-2">
        <Lightbulb className="w-4 h-4 text-[#00d4aa]" />
        <span className="text-sm font-medium text-zinc-300">修复建议</span>
      </div>

      <div className="flex items-center gap-3">
        <div className="text-center">
          <div
            className="w-14 h-14 rounded-lg border border-zinc-700 mx-auto"
            style={{ backgroundColor: origHex }}
          />
          <p className="text-xs font-mono text-zinc-500 mt-1">{origHex.toUpperCase()}</p>
          <p className="text-xs text-zinc-600">原始</p>
        </div>

        <ArrowRight className="w-5 h-5 text-zinc-600 shrink-0" />

        <div className="text-center">
          <div
            className="w-14 h-14 rounded-lg border border-[#00d4aa]/30 mx-auto ring-1 ring-[#00d4aa]/20"
            style={{ backgroundColor: sugHex }}
          />
          <p className="text-xs font-mono text-[#00d4aa] mt-1">{sugHex.toUpperCase()}</p>
          <p className="text-xs text-zinc-600">建议</p>
        </div>
      </div>

      <div
        className="rounded-lg p-2.5"
        style={{ color: sugHex, backgroundColor: rgbToHex({ r: 0, g: 0, b: 0 }) }}
      >
        <p className="text-sm font-medium">建议颜色示例 Aa</p>
        <p className="text-xs">对比度 {suggestion.contrastRatio.toFixed(2)}:1</p>
      </div>

      <div className="flex items-center gap-2">
        {suggestion.aaPass && (
          <span className="px-2 py-0.5 rounded text-xs font-mono bg-[#00d4aa]/10 text-[#00d4aa] border border-[#00d4aa]/20">
            AA 通过
          </span>
        )}
        {suggestion.aaaPass && (
          <span className="px-2 py-0.5 rounded text-xs font-mono bg-[#00d4aa]/10 text-[#00d4aa] border border-[#00d4aa]/20">
            AAA 通过
          </span>
        )}
        <div className="ml-auto flex gap-1">
          {onPreview && (
            <button
              onClick={() => onPreview(suggestion)}
              className="px-3 py-1.5 rounded-lg text-xs text-zinc-400 hover:text-[#00d4aa] hover:bg-[#00d4aa]/5 transition-colors"
            >
              预览
            </button>
          )}
          {onCopy && (
            <button
              onClick={() => onCopy(sugHex.toUpperCase())}
              className="px-3 py-1.5 rounded-lg text-xs text-zinc-400 hover:text-[#00d4aa] hover:bg-[#00d4aa]/5 transition-colors flex items-center gap-1"
            >
              <Copy className="w-3 h-3" />
              复制
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
