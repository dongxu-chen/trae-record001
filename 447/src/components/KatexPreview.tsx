import { useEffect, useRef } from 'react';
import katex from 'katex';
import 'katex/dist/katex.min.css';
import { useEditorStore } from '@/store/useEditorStore';
import { incrementalRender } from '@/utils/incrementalRenderer';

export default function KatexPreview() {
  const latex = useEditorStore((s) => s.latex);
  const containerRef = useRef<HTMLDivElement>(null);
  const prevLatexRef = useRef('');

  useEffect(() => {
    if (!containerRef.current) return;
    if (!latex) {
      prevLatexRef.current = '';
      return;
    }

    const renderFn = (tex: string, el: HTMLElement) => {
      try {
        katex.render(tex, el, {
          throwOnError: true,
          displayMode: true,
        });
      } catch (err) {
        if (err instanceof katex.ParseError) {
          el.innerHTML = `<span style="color:#EF4444">${err.message}</span>`;
        } else {
          el.innerHTML = `<span style="color:#EF4444">渲染出错</span>`;
        }
      }
    };

    incrementalRender(prevLatexRef.current, latex, containerRef.current, renderFn);
    prevLatexRef.current = latex;
  }, [latex]);

  return (
    <div
      id="katex-preview"
      className="katex-preview w-full h-full flex items-center justify-center bg-[#1E293B] rounded-lg p-4 overflow-auto"
    >
      {latex ? (
        <div ref={containerRef} />
      ) : (
        <span className="text-gray-500">在此预览公式</span>
      )}
    </div>
  );
}
