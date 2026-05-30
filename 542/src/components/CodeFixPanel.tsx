import { useState } from 'react';
import { Code, Copy, Check, FileCode, FileJson, FileText, Paintbrush } from 'lucide-react';
import type { CodeFix, EnhancedSuggestion, CodeFormat } from '@/types';
import { rgbToHex } from '@/utils/color';
import { formatCodeDiff } from '@/utils/codeFixGenerator';

interface CodeFixPanelProps {
  suggestion: EnhancedSuggestion;
  selector?: string;
}

const formatIcons: Record<CodeFormat, React.ReactNode> = {
  css: <FileCode className="w-4 h-4" />,
  tailwind: <FileJson className="w-4 h-4" />,
  inline: <FileText className="w-4 h-4" />,
  scss: <Paintbrush className="w-4 h-4" />,
};

const formatLabels: Record<CodeFormat, string> = {
  css: 'CSS',
  tailwind: 'Tailwind',
  inline: '内联样式',
  scss: 'SCSS',
};

export default function CodeFixPanel({ suggestion, selector = '.element' }: CodeFixPanelProps) {
  const [activeFormat, setActiveFormat] = useState<CodeFormat>('css');
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);

  const filteredFixes = suggestion.codeFixes.filter(
    (fix) => fix.format === activeFormat
  );

  const handleCopy = async (text: string, index: number) => {
    await navigator.clipboard.writeText(text);
    setCopiedIndex(index);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  const origHex = rgbToHex(suggestion.original);
  const suggHex = rgbToHex(suggestion.suggested);

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3 mb-4">
        <div className="w-8 h-8 rounded-lg bg-[#00d4aa]/10 flex items-center justify-center">
          <Code className="w-4 h-4 text-[#00d4aa]" />
        </div>
        <div>
          <h4 className="text-sm font-medium text-zinc-200">代码修复建议</h4>
          <p className="text-xs text-zinc-500">复制修复代码到你的项目中</p>
        </div>
      </div>

      <div className="flex gap-2 bg-zinc-900 rounded-lg p-1">
        {(['css', 'tailwind', 'inline', 'scss'] as CodeFormat[]).map((format) => (
          <button
            key={format}
            onClick={() => setActiveFormat(format)}
            className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded-md text-xs font-medium transition-colors ${
              activeFormat === format
                ? 'bg-[#00d4aa]/10 text-[#00d4aa]'
                : 'text-zinc-500 hover:text-zinc-300'
            }`}
          >
            {formatIcons[format]}
            {formatLabels[format]}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-2 gap-3 mb-4">
        <div className="bg-zinc-900 rounded-lg p-3 border border-zinc-800">
          <div className="flex items-center gap-2 mb-2">
            <div
              className="w-5 h-5 rounded border border-zinc-700"
              style={{ backgroundColor: origHex }}
            />
            <span className="text-xs text-zinc-500">原始颜色</span>
          </div>
          <code className="text-sm text-zinc-300 font-mono">{origHex}</code>
        </div>
        <div className="bg-zinc-900 rounded-lg p-3 border border-[#00d4aa]/30">
          <div className="flex items-center gap-2 mb-2">
            <div
              className="w-5 h-5 rounded border border-[#00d4aa]/30"
              style={{ backgroundColor: suggHex }}
            />
            <span className="text-xs text-[#00d4aa]">建议颜色</span>
          </div>
          <code className="text-sm text-[#00d4aa] font-mono">{suggHex}</code>
        </div>
      </div>

      <div className="space-y-3">
        {filteredFixes.map((fix, index) => (
          <div key={index} className="bg-zinc-900 rounded-lg overflow-hidden border border-zinc-800">
            <div className="px-3 py-2 border-b border-zinc-800 flex items-center justify-between">
              <span className="text-xs text-zinc-500">{fix.property}</span>
              <button
                onClick={() => handleCopy(fix.fixed, index)}
                className="flex items-center gap-1.5 px-2 py-1 rounded text-xs text-zinc-400 hover:text-[#00d4aa] hover:bg-zinc-800 transition-colors"
              >
                {copiedIndex === index ? (
                  <>
                    <Check className="w-3.5 h-3.5 text-[#00d4aa]" />
                    已复制
                  </>
                ) : (
                  <>
                    <Copy className="w-3.5 h-3.5" />
                    复制
                  </>
                )}
              </button>
            </div>
            <div className="p-3">
              <pre className="text-xs font-mono text-red-400 mb-2 line-through opacity-60">
                {fix.original}
              </pre>
              <pre className="text-xs font-mono text-[#00d4aa]">{fix.fixed}</pre>
            </div>
          </div>
        ))}
      </div>

      <div className="bg-zinc-900/50 rounded-lg p-4 border border-zinc-800">
        <p className="text-xs text-zinc-400 mb-2">Git 风格差异</p>
        <pre className="text-xs font-mono text-zinc-500 whitespace-pre-wrap">
          {filteredFixes.map((fix) => formatCodeDiff(fix)).join('\n\n')}
        </pre>
      </div>
    </div>
  );
}
