import { useState } from 'react';
import { AlertTriangle, Copy, ChevronDown, ChevronUp, Eye, Code, Palette } from 'lucide-react';
import type { ContrastIssue } from '@/types';
import { rgbToHex } from '@/utils/color';
import { cn } from '@/lib/utils';
import CodeFixPanel from '@/components/CodeFixPanel';

interface IssueCardProps {
  issue: ContrastIssue;
  onCopy?: (text: string) => void;
}

const REGION_TYPE_LABELS: Record<string, string> = {
  text: '文本区域',
  graphic: '图形区域',
  background: '背景区域',
  complex: '复杂区域（已排除）',
};

const COLORBLIND_LABELS: Record<string, string> = {
  protanopia: '红色盲',
  protanomaly: '红色弱',
  deuteranopia: '绿色盲',
  deuteranomaly: '绿色弱',
  tritanopia: '蓝色盲',
  tritanomaly: '蓝色弱',
  achromatopsia: '全色盲',
  achromatomaly: '全色弱',
};

export function IssueCard({ issue, onCopy }: IssueCardProps) {
  const [expanded, setExpanded] = useState(false);
  const [activeTab, setActiveTab] = useState<'color' | 'code'>('color');
  const fgHex = rgbToHex(issue.foreground);
  const bgHex = rgbToHex(issue.background);

  const severityConfig = {
    critical: { label: '严重', color: 'text-red-500 bg-red-500/10 border-red-500/20' },
    major: { label: '重要', color: 'text-[#ff6b35] bg-[#ff6b35]/10 border-[#ff6b35]/20' },
    minor: { label: '轻微', color: 'text-yellow-500 bg-yellow-500/10 border-yellow-500/20' },
  };

  const sev = severityConfig[issue.severity];

  return (
    <div className="bg-zinc-900 rounded-xl border border-zinc-800 overflow-hidden hover:border-zinc-700 transition-colors">
      <div className="p-4 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className={cn('w-4 h-4', sev.color.split(' ')[0])} />
            <span className={cn('px-2 py-0.5 rounded text-xs font-medium border', sev.color)}>
              {sev.label}
            </span>
            <span className="px-2 py-0.5 rounded text-xs text-zinc-500 bg-zinc-800">
              {REGION_TYPE_LABELS[issue.regionType] || issue.regionType}
            </span>
          </div>
          <span className="text-sm font-mono font-bold text-[#ff6b35]">
            {issue.contrastRatio.toFixed(2)}:1
          </span>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex-1 flex items-center gap-2">
            <div
              className="w-8 h-8 rounded border border-zinc-700 shrink-0"
              style={{ backgroundColor: fgHex }}
            />
            <div className="text-xs font-mono text-zinc-400">
              <p>前景</p>
              <p>{fgHex.toUpperCase()}</p>
            </div>
          </div>
          <div className="text-zinc-600">→</div>
          <div className="flex-1 flex items-center gap-2">
            <div
              className="w-8 h-8 rounded border border-zinc-700 shrink-0"
              style={{ backgroundColor: bgHex }}
            />
            <div className="text-xs font-mono text-zinc-400">
              <p>背景</p>
              <p>{bgHex.toUpperCase()}</p>
            </div>
          </div>
        </div>

        <div
          className="rounded-lg p-2.5"
          style={{ color: fgHex, backgroundColor: bgHex }}
        >
          <p className="text-sm font-medium">对比度不足的文字示例 Aa</p>
          <p className="text-xs mt-0.5">Small text sample</p>
        </div>

        {issue.affectedColorblindTypes.length > 0 && (
          <div className="flex flex-wrap gap-1">
            <span className="text-xs text-zinc-500 mr-1">受影响：</span>
            {issue.affectedColorblindTypes.map((type) => (
              <span
                key={type}
                className="px-1.5 py-0.5 rounded text-xs bg-red-500/10 text-red-400"
                title={COLORBLIND_LABELS[type]}
              >
                {COLORBLIND_LABELS[type]}
              </span>
            ))}
          </div>
        )}

        <button
          onClick={() => setExpanded(!expanded)}
          className="w-full flex items-center justify-center gap-1 py-2 text-xs text-zinc-400 hover:text-zinc-300 transition-colors"
        >
          {expanded ? (
            <>
              <ChevronUp className="w-3.5 h-3.5" />
              收起
            </>
          ) : (
            <>
              <ChevronDown className="w-3.5 h-3.5" />
              查看修复建议
            </>
          )}
        </button>
      </div>

      {expanded && (
        <div className="border-t border-zinc-800 p-4 space-y-4 bg-zinc-900/50">
          <div className="flex gap-2 p-1 bg-zinc-950 rounded-lg">
            <button
              onClick={() => setActiveTab('color')}
              className={`flex-1 py-2 rounded-md text-xs font-medium transition-colors flex items-center justify-center gap-1.5 ${
                activeTab === 'color'
                  ? 'bg-zinc-800 text-zinc-200'
                  : 'text-zinc-500 hover:text-zinc-300'
              }`}
            >
              <Palette className="w-3.5 h-3.5" />
              颜色修复
            </button>
            <button
              onClick={() => setActiveTab('code')}
              className={`flex-1 py-2 rounded-md text-xs font-medium transition-colors flex items-center justify-center gap-1.5 ${
                activeTab === 'code'
                  ? 'bg-zinc-800 text-zinc-200'
                  : 'text-zinc-500 hover:text-zinc-300'
              }`}
            >
              <Code className="w-3.5 h-3.5" />
              代码修复
            </button>
          </div>

          {activeTab === 'color' && (
            <div className="space-y-4">
              <h4 className="text-sm font-medium text-zinc-300 flex items-center gap-2">
                <Eye className="w-4 h-4 text-[#00d4aa]" />
                颜色修复建议
              </h4>

              {issue.suggestions.slice(0, 3).map((sug, idx) => {
                const sugHex = rgbToHex(sug.suggested);
                return (
                  <div key={idx} className="space-y-2">
                    <div className="flex items-center gap-2">
                      <div className="flex-1 flex items-center gap-2">
                        <div
                          className="w-10 h-10 rounded-lg border border-zinc-700 shrink-0"
                          style={{ backgroundColor: sugHex }}
                        />
                        <div>
                          <p className="text-xs font-mono text-zinc-300">
                            {sugHex.toUpperCase()}
                          </p>
                          <p className="text-xs text-zinc-500">
                            {sug.contrastRatio.toFixed(2)}:1
                          </p>
                        </div>
                      </div>
                      <div className="flex gap-1">
                        {sug.aaPass && (
                          <span className="px-1.5 py-0.5 rounded text-xs font-mono bg-[#00d4aa]/10 text-[#00d4aa]">
                            AA
                          </span>
                        )}
                        {sug.aaaPass && (
                          <span className="px-1.5 py-0.5 rounded text-xs font-mono bg-[#00d4aa]/10 text-[#00d4aa]">
                            AAA
                          </span>
                        )}
                      </div>
                      {onCopy && (
                        <button
                          onClick={() => onCopy(sugHex.toUpperCase())}
                          className="text-zinc-500 hover:text-[#00d4aa] transition-colors"
                        >
                          <Copy className="w-3.5 h-3.5" />
                        </button>
                      )}
                    </div>

                    {sug.visualLabels && sug.visualLabels.length > 0 && (
                      <div className="flex gap-2">
                        {sug.visualLabels.map((label, lidx) => (
                          <div
                            key={lidx}
                            className="px-2 py-1 rounded text-xs bg-zinc-800 text-zinc-400 flex items-center gap-1"
                          >
                            <span
                              className="font-bold"
                              style={{ color: sugHex }}
                            >
                              {label.value}
                            </span>
                            <span className="text-[10px] text-zinc-500">{label.display}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}

              {issue.suggestions[0]?.alternatives && (
                <>
                  <h4 className="text-sm font-medium text-zinc-300 pt-2 border-t border-zinc-800">
                    图形+标签替代方案
                  </h4>
                  <div className="grid grid-cols-2 gap-2">
                    {issue.suggestions[0].alternatives.map((alt, idx) => (
                      <div
                        key={idx}
                        className="p-3 rounded-lg bg-zinc-800/50 border border-zinc-700/50"
                      >
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-lg">{alt.icon}</span>
                          <span className="text-xs font-medium text-zinc-300">
                            {alt.label}
                          </span>
                        </div>
                        <p className="text-[11px] text-zinc-500 leading-relaxed">
                          {alt.description}
                        </p>
                      </div>
                    ))}
                  </div>
                </>
              )}
            </div>
          )}

          {activeTab === 'code' && issue.suggestions[0] && (
            <CodeFixPanel
              suggestion={issue.suggestions[0]}
              selector={issue.cssSelector}
            />
          )}
        </div>
      )}
    </div>
  );
}
