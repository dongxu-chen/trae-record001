import { useCallback } from 'react';
import { useEditorStore } from '@/store/useEditorStore';

export default function LatexCodePanel() {
  const latex = useEditorStore((s) => s.latex);
  const setLatex = useEditorStore((s) => s.setLatex);

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      setLatex(e.target.value);
    },
    [setLatex],
  );

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(latex);
    } catch {
      // fallback
    }
  }, [latex]);

  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-center justify-between px-1">
        <span className="text-xs text-text-muted font-medium tracking-wide uppercase">
          LaTeX 代码
        </span>
        <button
          onClick={handleCopy}
          className="text-xs text-text-muted hover:text-accent transition-colors px-1.5 py-0.5 rounded hover:bg-bg-tertiary"
        >
          复制
        </button>
      </div>
      <textarea
        value={latex}
        onChange={handleChange}
        spellCheck={false}
        className="w-full h-28 bg-bg-tertiary text-text-primary font-mono text-sm p-3 rounded-lg border border-border-custom focus:border-accent focus:outline-none resize-none scrollbar-thin placeholder:text-text-muted"
        placeholder="在此输入 LaTeX 代码..."
      />
    </div>
  );
}
