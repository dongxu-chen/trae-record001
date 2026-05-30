import { useCallback } from 'react';
import { Link } from 'react-router-dom';
import {
  FileText,
  AlertTriangle,
  CheckCircle2,
  Copy,
  ArrowLeft,
  Shield,
  TrendingUp,
} from 'lucide-react';
import { useAppStore } from '@/store/useAppStore';
import { IssueCard } from '@/components/IssueCard';
import { SuggestionCard } from '@/components/SuggestionCard';
import { cn } from '@/lib/utils';
import type { ColorSuggestion } from '@/types';

export default function Report() {
  const { wcagReport, contrastIssues } = useAppStore();

  const handleCopy = useCallback((text: string) => {
    navigator.clipboard.writeText(text).catch(() => {});
  }, []);

  if (!wcagReport) {
    return (
      <div className="flex flex-col items-center justify-center py-24">
        <div className="w-16 h-16 rounded-2xl bg-zinc-800 flex items-center justify-center mb-4">
          <FileText className="w-8 h-8 text-zinc-600" />
        </div>
        <h2 className="text-xl font-bold text-zinc-300 mb-2">暂无检测报告</h2>
        <p className="text-sm text-zinc-500 mb-6">请先在检测工作台上传图片进行分析</p>
        <Link
          to="/"
          className="px-6 py-2.5 rounded-lg bg-[#00d4aa] text-zinc-900 font-medium text-sm hover:bg-[#00d4aa]/90 transition-colors"
        >
          前往检测工作台
        </Link>
      </div>
    );
  }

  const allSuggestions = contrastIssues.flatMap((issue) => issue.suggestions);

  const circumference = 2 * Math.PI * 40;
  const offset = circumference - (wcagReport.passRate / 100) * circumference;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-zinc-100">WCAG 合规报告</h1>
          <p className="text-sm text-zinc-500 mt-1">
            基于 WCAG 2.1 标准的对比度检测结果
          </p>
        </div>
        <Link
          to="/"
          className="px-4 py-2 rounded-lg text-sm text-zinc-400 hover:text-zinc-200 border border-zinc-700 hover:border-zinc-600 transition-colors flex items-center gap-2"
        >
          <ArrowLeft className="w-4 h-4" />
          返回工作台
        </Link>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-zinc-900 rounded-xl border border-zinc-800 p-6 flex items-center gap-6">
          <div className="relative w-24 h-24 shrink-0">
            <svg className="w-24 h-24 -rotate-90" viewBox="0 0 96 96">
              <circle
                cx="48"
                cy="48"
                r="40"
                fill="none"
                stroke="#27272a"
                strokeWidth="8"
              />
              <circle
                cx="48"
                cy="48"
                r="40"
                fill="none"
                stroke={wcagReport.passRate >= 80 ? '#00d4aa' : wcagReport.passRate >= 50 ? '#ff6b35' : '#ef4444'}
                strokeWidth="8"
                strokeDasharray={circumference}
                strokeDashoffset={offset}
                strokeLinecap="round"
                className="transition-all duration-1000"
              />
            </svg>
            <div className="absolute inset-0 flex items-center justify-center">
              <span className="text-2xl font-bold font-mono text-zinc-100">
                {wcagReport.passRate}%
              </span>
            </div>
          </div>
          <div>
            <p className="text-sm text-zinc-500">WCAG 合规率</p>
            <p className="text-xs text-zinc-600 mt-1">
              {wcagReport.passed} 通过 / {wcagReport.failed} 未通过
            </p>
          </div>
        </div>

        <div className="bg-zinc-900 rounded-xl border border-zinc-800 p-6 space-y-4">
          <div className="flex items-center gap-2">
            <Shield className="w-4 h-4 text-[#00d4aa]" />
            <span className="text-sm font-medium text-zinc-300">合规概览</span>
          </div>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-[#00d4aa]" />
                <span className="text-sm text-zinc-400">通过</span>
              </div>
              <span className="font-mono text-[#00d4aa]">{wcagReport.passed}</span>
            </div>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-[#ff6b35]" />
                <span className="text-sm text-zinc-400">未通过</span>
              </div>
              <span className="font-mono text-[#ff6b35]">{wcagReport.failed}</span>
            </div>
          </div>
        </div>

        <div className="bg-zinc-900 rounded-xl border border-zinc-800 p-6 space-y-4">
          <div className="flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-[#00d4aa]" />
            <span className="text-sm font-medium text-zinc-300">区域分析</span>
          </div>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="w-2.5 h-2.5 rounded-full bg-[#00d4aa]" />
                <span className="text-sm text-zinc-400">已分析区域</span>
              </div>
              <span className="font-mono text-[#00d4aa]">{wcagReport.analyzedRegions || 0}</span>
            </div>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="w-2.5 h-2.5 rounded-full bg-zinc-600" />
                <span className="text-sm text-zinc-400">排除复杂区域</span>
              </div>
              <span className="font-mono text-zinc-500">{wcagReport.excludedComplexRegions || 0}</span>
            </div>
          </div>
        </div>

        <div className="bg-zinc-900 rounded-xl border border-zinc-800 p-6 space-y-4">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-[#ff6b35]" />
            <span className="text-sm font-medium text-zinc-300">严重程度分布</span>
          </div>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="w-2.5 h-2.5 rounded-full bg-red-500" />
                <span className="text-sm text-zinc-400">严重</span>
              </div>
              <span className="font-mono text-red-500">{wcagReport.criticalCount}</span>
            </div>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="w-2.5 h-2.5 rounded-full bg-[#ff6b35]" />
                <span className="text-sm text-zinc-400">重要</span>
              </div>
              <span className="font-mono text-[#ff6b35]">{wcagReport.majorCount}</span>
            </div>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="w-2.5 h-2.5 rounded-full bg-yellow-500" />
                <span className="text-sm text-zinc-400">轻微</span>
              </div>
              <span className="font-mono text-yellow-500">{wcagReport.minorCount}</span>
            </div>
          </div>
        </div>
      </div>

      {contrastIssues.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-lg font-bold text-zinc-200 flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-[#ff6b35]" />
            对比度问题列表
            <span className="text-sm font-normal text-zinc-500">
              ({contrastIssues.length} 个问题)
            </span>
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {contrastIssues.map((issue) => (
              <IssueCard key={issue.id} issue={issue} onCopy={handleCopy} />
            ))}
          </div>
        </div>
      )}

      {allSuggestions.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-lg font-bold text-zinc-200 flex items-center gap-2">
            <CheckCircle2 className="w-5 h-5 text-[#00d4aa]" />
            修复建议
            <span className="text-sm font-normal text-zinc-500">
              ({allSuggestions.length} 条建议)
            </span>
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {allSuggestions.slice(0, 9).map((suggestion, idx) => (
              <SuggestionCard
                key={idx}
                suggestion={suggestion}
                onCopy={handleCopy}
              />
            ))}
          </div>
        </div>
      )}

      <div className="bg-zinc-900 rounded-xl border border-zinc-800 p-6">
        <h2 className="text-lg font-bold text-zinc-200 mb-4 flex items-center gap-2">
          <Shield className="w-5 h-5 text-[#00d4aa]" />
          WCAG 2.1 标准说明
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-sm">
          <div className="space-y-2">
            <h3 className="font-medium text-[#00d4aa]">AA 级别（最低要求）</h3>
            <ul className="space-y-1 text-zinc-400">
              <li>• 普通文本对比度 ≥ 4.5:1</li>
              <li>• 大文本（18pt+ 或 14pt+粗体）对比度 ≥ 3:1</li>
              <li>• 非文本组件对比度 ≥ 3:1</li>
            </ul>
          </div>
          <div className="space-y-2">
            <h3 className="font-medium text-[#00d4aa]">AAA 级别（增强要求）</h3>
            <ul className="space-y-1 text-zinc-400">
              <li>• 普通文本对比度 ≥ 7:1</li>
              <li>• 大文本对比度 ≥ 4.5:1</li>
              <li>• 非文本组件对比度 ≥ 4.5:1</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
