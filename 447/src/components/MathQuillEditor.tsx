import { useEffect, useRef } from 'react';
import { useEditorStore } from '@/store/useEditorStore';
import { setMathQuillInstance, type MQMathField } from '@/utils/mathquillInstance';

interface MQInterface {
  MathField(el: HTMLElement, config?: Record<string, unknown>): MQMathField;
  StaticMath(el: HTMLElement): MQMathField;
}

export default function MathQuillEditor() {
  const editorRef = useRef<HTMLDivElement>(null);
  const mqRef = useRef<MQMathField | null>(null);
  const setLatex = useEditorStore((s) => s.setLatex);
  const latex = useEditorStore((s) => s.latex);
  const isInternalUpdate = useRef(false);

  useEffect(() => {
    let destroyed = false;

    async function init() {
      const $ = (await import('jquery')).default;
      (window as any).jQuery = $;
      (window as any).$ = $;

      await import('mathquill-js');

      if (destroyed || !editorRef.current) return;

      const MQ: MQInterface = (window as any).MathQuill.getInterface(2);

      const mathField = MQ.MathField(editorRef.current, {
        handlers: {
          edit: (mf: MQMathField) => {
            isInternalUpdate.current = true;
            setLatex(mf.latex());
            setTimeout(() => {
              isInternalUpdate.current = false;
            }, 0);
          },
        },
        spaceBehavesLikeTab: true,
      });

      mqRef.current = mathField;
      setMathQuillInstance(mathField);

      mathField.focus();
    }

    init();

    return () => {
      destroyed = true;
      mqRef.current = null;
      setMathQuillInstance(null);
    };
  }, [setLatex]);

  useEffect(() => {
    if (
      mqRef.current &&
      !isInternalUpdate.current &&
      latex !== mqRef.current.latex()
    ) {
      mqRef.current.latex(latex);
    }
  }, [latex]);

  return (
    <div
      id="mathquill-editor"
      ref={editorRef}
      className="w-full min-h-[80px] rounded-lg bg-bg-secondary p-4 focus-within:ring-2 focus-within:ring-accent focus-within:ring-offset-2 focus-within:ring-offset-bg-primary transition-shadow"
    />
  );
}
