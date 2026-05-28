import { useMemo } from 'react';
import { Eye, AlertTriangle, CheckCircle2, Info } from 'lucide-react';
import { useColorStore } from '@/hooks/useColorStore';
import { checkContrast } from '@/utils/contrastChecker';
import type { WCAGResult } from '@/types';

export default function ColorContrast() {
  const { currentColor, compareColor } = useColorStore();

  const result: WCAGResult = useMemo(() => {
    return checkContrast(currentColor, compareColor);
  }, [currentColor, compareColor]);

  const getLevelBadge = () => {
    if (result.level === 'aaa') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-1 bg-green-500/20 text-green-400 rounded-full text-xs font-medium">
          <CheckCircle2 className="w-3 h-3" />
          AAA 级
        </span>
      );
    }
    if (result.level === 'aa') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-1 bg-emerald-500/20 text-emerald-400 rounded-full text-xs font-medium">
          <CheckCircle2 className="w-3 h-3" />
          AA 级
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-1 bg-red-500/20 text-red-400 rounded-full text-xs font-medium">
        <AlertTriangle className="w-3 h-3" />
        未通过
      </span>
    );
  };

  return (
    <div className="bg-[#1e1e2e] rounded-xl p-5 shadow-lg">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Eye className="w-5 h-5 text-gray-300" />
          <h3 className="text-gray-200 font-medium">WCAG 对比度</h3>
        </div>
        {getLevelBadge()}
      </div>

      <div className="text-center mb-4">
        <div className="text-4xl font-bold text-gray-100 font-mono">
          {result.ratio.toFixed(2)}
          <span className="text-lg text-gray-500">:1</span>
        </div>
        <p className="text-gray-500 text-xs mt-1">对比度</p>
      </div>

      <div className="space-y-2">
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-400">AA 级 (正文 ≥ 4.5:1)</span>
          {result.aaNormal ? (
            <CheckCircle2 className="w-4 h-4 text-green-400" />
          ) : (
            <AlertTriangle className="w-4 h-4 text-red-400" />
          )}
        </div>
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-400">AA 级 (大字号 ≥ 3:1)</span>
          {result.aaLarge ? (
            <CheckCircle2 className="w-4 h-4 text-green-400" />
          ) : (
            <AlertTriangle className="w-4 h-4 text-red-400" />
          )}
        </div>
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-400">AAA 级 (正文 ≥ 7:1)</span>
          {result.aaaNormal ? (
            <CheckCircle2 className="w-4 h-4 text-green-400" />
          ) : (
            <AlertTriangle className="w-4 h-4 text-red-400" />
          )}
        </div>
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-400">AAA 级 (大字号 ≥ 4.5:1)</span>
          {result.aaaLarge ? (
            <CheckCircle2 className="w-4 h-4 text-green-400" />
          ) : (
            <AlertTriangle className="w-4 h-4 text-red-400" />
          )}
        </div>
      </div>

      <div className="mt-4 p-3 bg-[#2a2a3e] rounded-lg">
        <div className="flex items-center gap-2 mb-2">
          <Info className="w-4 h-4 text-[#8b8cf7]" />
          <span className="text-xs text-gray-400">预览效果</span>
        </div>
        <div className="space-y-2">
          <div
            className="p-3 rounded-lg"
            style={{ backgroundColor: compareColor, color: currentColor }}
          >
            <p className="text-sm font-medium">这是一段正文文字 (16px)</p>
          </div>
          <div
            className="p-3 rounded-lg"
            style={{ backgroundColor: compareColor, color: currentColor }}
          >
            <p className="text-lg font-bold">这是大字号文字 (24px)</p>
          </div>
        </div>
      </div>
    </div>
  );
}
