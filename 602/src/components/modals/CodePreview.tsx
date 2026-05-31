import React, { useState, useMemo } from 'react';
import { Copy, Check, Code, FileCode, FileText, X } from 'lucide-react';
import { useProjectStore } from '@/store/useProjectStore';
import { useEditorStore } from '@/store/useEditorStore';
import { exportSVG, exportJS } from '@/utils/exporters';

type CodeFormat = 'svg' | 'html' | 'embed';

export const CodePreview: React.FC = () => {
  const { project } = useProjectStore();
  const { setActiveModal } = useEditorStore();
  const [format, setFormat] = useState<CodeFormat>('html');
  const [compressed, setCompressed] = useState(false);
  const [copied, setCopied] = useState(false);

  const code = useMemo(() => {
    switch (format) {
      case 'svg':
        return exportSVG(project, { compressed, minify: compressed });
      case 'html':
        return exportJS(project, { compressed, minify: compressed });
      case 'embed':
        return generateEmbedCode();
      default:
        return '';
    }
  }, [format, compressed, project]);

  const generateEmbedCode = () => {
    const svgCode = exportSVG(project, { compressed: true });
    const escapedSvg = svgCode.replace(/`/g, '\\`').replace(/\$/g, '\\$');
    return `<!-- Embed this SVG animation directly in your HTML -->
<div id="svg-animation-container"></div>

<script>
  (function() {
    const container = document.getElementById('svg-animation-container');
    container.innerHTML = \`${escapedSvg}\`;
  })();
</script>

<!-- Or use the full version with GSAP animations -->
${exportJS(project, { compressed })}`;
  };

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      const textarea = document.createElement('textarea');
      textarea.value = code;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const formatLabels: Record<CodeFormat, { label: string; icon: React.ReactNode; desc: string }> = {
    svg: { label: 'SVG', icon: <FileText size={14} />, desc: 'Pure SVG file' },
    html: { label: 'HTML/JS', icon: <FileCode size={14} />, desc: 'Full page with GSAP' },
    embed: { label: 'Embed', icon: <Code size={14} />, desc: 'Embed snippet' },
  };

  const lineCount = code.split('\n').length;
  const byteSize = new Blob([code]).size;
  const sizeStr = byteSize > 1024 ? `${(byteSize / 1024).toFixed(1)} KB` : `${byteSize} B`;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={() => setActiveModal('none')}>
      <div className="bg-bg-secondary border border-border-primary rounded-xl w-[85vw] max-w-[1000px] h-[80vh] flex flex-col" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between px-6 py-4 border-b border-border-primary">
          <div className="flex items-center gap-3">
            <Code size={20} className="text-accent-secondary" />
            <h2 className="text-lg font-semibold text-text-primary">Code Preview</h2>
          </div>
          <button onClick={() => setActiveModal('none')} className="btn-icon text-text-secondary hover:text-text-primary text-xl">×</button>
        </div>

        <div className="flex items-center gap-3 px-6 py-3 border-b border-border-primary">
          {(Object.entries(formatLabels) as [CodeFormat, typeof formatLabels[CodeFormat]][]).map(([key, { label, icon, desc }]) => (
            <button
              key={key}
              onClick={() => setFormat(key)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                format === key
                  ? 'bg-accent-secondary/20 text-accent-secondary border border-accent-secondary/30'
                  : 'bg-bg-tertiary/50 text-text-secondary hover:text-text-primary border border-transparent'
              }`}
              title={desc}
            >
              {icon}
              {label}
            </button>
          ))}

          <div className="flex-1" />

          <label className="flex items-center gap-2 text-sm text-text-secondary cursor-pointer">
            <input
              type="checkbox"
              checked={compressed}
              onChange={(e) => setCompressed(e.target.checked)}
              className="accent-accent-secondary"
            />
            Compressed
          </label>

          <button
            onClick={handleCopy}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              copied
                ? 'bg-accent-success/20 text-accent-success border border-accent-success/30'
                : 'bg-accent-primary text-white hover:bg-accent-primary/90'
            }`}
          >
            {copied ? <><Check size={14} /> Copied!</> : <><Copy size={14} /> Copy Code</>}
          </button>
        </div>

        <div className="flex-1 overflow-auto p-4">
          <div className="relative">
            <pre className="bg-bg-primary rounded-lg p-4 overflow-auto text-sm font-mono text-text-primary leading-relaxed border border-border-primary">
              <code>{code}</code>
            </pre>
          </div>
        </div>

        <div className="flex items-center justify-between px-6 py-3 border-t border-border-primary text-xs text-text-muted">
          <div className="flex items-center gap-4">
            <span>{lineCount} lines</span>
            <span>{sizeStr}</span>
            <span>{format.toUpperCase()} format</span>
          </div>
          <div className="text-text-muted">
            {format === 'embed' && 'Ready to paste into your webpage'}
            {format === 'svg' && 'Can be opened directly in browser'}
            {format === 'html' && 'Self-contained HTML with GSAP animations'}
          </div>
        </div>
      </div>
    </div>
  );
};
