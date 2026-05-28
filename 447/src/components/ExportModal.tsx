import { useState, useCallback, useMemo } from 'react';
import { X, Image, FileCode, Download, Copy, Check, BookOpen } from 'lucide-react';
import { toPng, toSvg } from 'html-to-image';
import katex from 'katex';
import { useEditorStore } from '@/store/useEditorStore';
import { latexPresets, generateLatexDocument, generateSnippet, type LatexPreset } from '@/utils/latexPresets';

type ExportFormat = 'png' | 'svg' | 'latex';

export default function ExportModal() {
  const { showExportModal, toggleExportModal, latex } = useEditorStore();
  const [format, setFormat] = useState<ExportFormat>('png');
  const [scale, setScale] = useState(2);
  const [copied, setCopied] = useState(false);
  const [presetId, setPresetId] = useState('amsmath');
  const [latexOutput, setLatexOutput] = useState<'snippet' | 'document'>('snippet');

  const activePreset = useMemo(
    () => latexPresets.find((p) => p.id === presetId) ?? latexPresets[1],
    [presetId],
  );

  const outputLatex = useMemo(() => {
    if (!latex) return '';
    if (latexOutput === 'document') {
      return generateLatexDocument(latex, activePreset);
    }
    return generateSnippet(latex, activePreset);
  }, [latex, activePreset, latexOutput]);

  const handleCopyLatex = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(outputLatex);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // fallback
    }
  }, [outputLatex]);

  const handleDownloadLatex = useCallback(() => {
    const blob = new Blob([outputLatex], { type: 'text/x-tex;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.download = 'formula.tex';
    link.href = url;
    link.click();
    URL.revokeObjectURL(url);
  }, [outputLatex]);

  const handleExport = useCallback(async () => {
    if (format === 'latex') {
      handleDownloadLatex();
      handleCopyLatex();
      return;
    }

    const targetEl = document.getElementById('katex-preview');
    if (!targetEl) return;

    try {
      if (format === 'png') {
        const dataUrl = await toPng(targetEl, {
          pixelRatio: scale,
          backgroundColor: '#0F172A',
        });
        const link = document.createElement('a');
        link.download = 'formula.png';
        link.href = dataUrl;
        link.click();
      } else if (format === 'svg') {
        const dataUrl = await toSvg(targetEl, {
          backgroundColor: '#0F172A',
        });
        const link = document.createElement('a');
        link.download = 'formula.svg';
        link.href = dataUrl;
        link.click();
      }
    } catch (err) {
      console.error('Export failed:', err);
    }
  }, [format, scale, handleCopyLatex, handleDownloadLatex]);

  if (!showExportModal) return null;

  const formats: { id: ExportFormat; label: string; icon: typeof Image; desc: string }[] = [
    { id: 'png', label: 'PNG', icon: Image, desc: '高清位图，适合文档插入' },
    { id: 'svg', label: 'SVG', icon: FileCode, desc: '矢量图，无损缩放' },
    { id: 'latex', label: 'LaTeX', icon: FileCode, desc: 'LaTeX源代码，多种宏包预设' },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 animate-fade-in" onClick={toggleExportModal}>
      <div
        className="bg-bg-secondary rounded-xl shadow-2xl w-[540px] max-h-[90vh] animate-scale-in overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-5 py-3 border-b border-border-custom shrink-0">
          <span className="text-sm font-medium text-text-primary">导出公式</span>
          <button onClick={toggleExportModal} className="p-1 text-text-muted hover:text-text-primary transition-colors rounded hover:bg-bg-tertiary">
            <X size={16} />
          </button>
        </div>

        <div className="p-5 space-y-4 overflow-y-auto scrollbar-thin">
          <div className="space-y-2">
            <span className="text-xs text-text-muted uppercase tracking-wide">导出格式</span>
            <div className="grid grid-cols-3 gap-2">
              {formats.map((f) => (
                <button
                  key={f.id}
                  onClick={() => setFormat(f.id)}
                  className={`flex flex-col items-center gap-1.5 p-3 rounded-lg border transition-all ${
                    format === f.id
                      ? 'border-accent bg-accent/10 text-accent'
                      : 'border-border-custom bg-bg-tertiary text-text-secondary hover:text-text-primary hover:border-text-muted'
                  }`}
                >
                  <f.icon size={20} />
                  <span className="text-xs font-medium">{f.label}</span>
                </button>
              ))}
            </div>
            <p className="text-xs text-text-muted mt-1">{formats.find((f) => f.id === format)?.desc}</p>
          </div>

          {format === 'png' && (
            <div className="space-y-2">
              <span className="text-xs text-text-muted uppercase tracking-wide">缩放倍数</span>
              <div className="flex items-center gap-3">
                <input
                  type="range"
                  min="1"
                  max="4"
                  step="1"
                  value={scale}
                  onChange={(e) => setScale(Number(e.target.value))}
                  className="flex-1 accent-accent"
                />
                <span className="text-sm text-text-primary font-mono w-8 text-center">{scale}x</span>
              </div>
            </div>
          )}

          {format === 'latex' && (
            <>
              <div className="space-y-2">
                <span className="text-xs text-text-muted uppercase tracking-wide">宏包预设</span>
                <div className="grid grid-cols-3 gap-1.5">
                  {latexPresets.map((p) => (
                    <button
                      key={p.id}
                      onClick={() => setPresetId(p.id)}
                      className={`px-2.5 py-2 rounded-lg border text-left transition-all ${
                        presetId === p.id
                          ? 'border-accent bg-accent/10'
                          : 'border-border-custom bg-bg-tertiary hover:border-text-muted'
                      }`}
                    >
                      <div className={`text-xs font-medium ${presetId === p.id ? 'text-accent' : 'text-text-primary'}`}>
                        {p.name}
                      </div>
                      <div className="text-[10px] text-text-muted mt-0.5 leading-tight">
                        {p.packages.length > 0 ? p.packages.join(', ') : '无宏包'}
                      </div>
                    </button>
                  ))}
                </div>
                <p className="text-xs text-text-muted">{activePreset.description}</p>
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-text-muted uppercase tracking-wide">输出模式</span>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => setLatexOutput('snippet')}
                    className={`flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg border transition-all ${
                      latexOutput === 'snippet'
                        ? 'border-accent bg-accent/10 text-accent'
                        : 'border-border-custom bg-bg-tertiary text-text-secondary hover:text-text-primary'
                    }`}
                  >
                    <FileCode size={12} />
                    代码片段
                  </button>
                  <button
                    onClick={() => setLatexOutput('document')}
                    className={`flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg border transition-all ${
                      latexOutput === 'document'
                        ? 'border-accent bg-accent/10 text-accent'
                        : 'border-border-custom bg-bg-tertiary text-text-secondary hover:text-text-primary'
                    }`}
                  >
                    <BookOpen size={12} />
                    完整文档
                  </button>
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-text-muted uppercase tracking-wide">LaTeX 代码</span>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={handleCopyLatex}
                      className="flex items-center gap-1 text-xs text-accent hover:text-accent-hover transition-colors"
                    >
                      {copied ? <Check size={10} /> : <Copy size={10} />}
                      {copied ? '已复制' : '复制'}
                    </button>
                    <button
                      onClick={handleDownloadLatex}
                      className="flex items-center gap-1 text-xs text-text-muted hover:text-accent transition-colors"
                    >
                      <Download size={10} />
                      下载 .tex
                    </button>
                  </div>
                </div>
                <pre className="bg-bg-tertiary rounded-lg p-3 font-mono text-xs text-text-primary max-h-40 overflow-y-auto scrollbar-thin border border-border-custom whitespace-pre-wrap break-all">
                  {outputLatex || '(空)'}
                </pre>
              </div>
            </>
          )}

          <div className="space-y-2">
            <span className="text-xs text-text-muted uppercase tracking-wide">预览</span>
            <div className="bg-bg-primary rounded-lg p-4 overflow-auto katex-preview min-h-[60px] flex items-center justify-center">
              {latex ? (
                <div
                  dangerouslySetInnerHTML={{
                    __html: (() => {
                      try {
                        return katex.renderToString(latex, { displayMode: true, throwOnError: false });
                      } catch {
                        return '<span style="color:#EF4444">预览失败</span>';
                      }
                    })(),
                  }}
                />
              ) : (
                <span className="text-text-muted text-sm">无公式内容</span>
              )}
            </div>
          </div>
        </div>

        <div className="flex items-center justify-end gap-2 px-5 py-3 border-t border-border-custom shrink-0">
          <button
            onClick={toggleExportModal}
            className="px-4 py-1.5 text-sm text-text-secondary bg-bg-tertiary rounded-lg hover:text-text-primary transition-colors"
          >
            取消
          </button>
          <button
            onClick={handleExport}
            disabled={!latex.trim()}
            className="flex items-center gap-1.5 px-4 py-1.5 text-sm bg-accent text-bg-primary font-medium rounded-lg hover:bg-accent-hover transition-colors disabled:opacity-40"
          >
            {format === 'latex' ? <Copy size={14} /> : <Download size={14} />}
            {format === 'latex' ? (copied ? '已复制+下载' : '复制并下载') : '导出'}
          </button>
        </div>
      </div>
    </div>
  );
}
