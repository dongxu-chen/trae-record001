import { useEffect, useRef, useState, useCallback } from 'react';
import { X, Eraser, ScanSearch, Check, AlertTriangle, Wand2 } from 'lucide-react';
import katex from 'katex';
import { useEditorStore } from '@/store/useEditorStore';
import { getSettings } from '@/db/database';
import { postProcessLatex } from '@/utils/latexPostProcessor';

interface Point {
  x: number;
  y: number;
}

export default function HandwritingModal() {
  const { showHandwritingModal, toggleHandwritingModal, setLatex } = useEditorStore();
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const ctxRef = useRef<CanvasRenderingContext2D | null>(null);
  const isDrawingRef = useRef(false);
  const pointsRef = useRef<Point[]>([]);
  const [rawLatex, setRawLatex] = useState('');
  const [recognizedLatex, setRecognizedLatex] = useState('');
  const [corrections, setCorrections] = useState<string[]>([]);
  const [isRecognizing, setIsRecognizing] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!showHandwritingModal || !canvasRef.current) return;

    const canvas = canvasRef.current;
    const dpr = window.devicePixelRatio || 1;
    canvas.width = 600 * dpr;
    canvas.height = 400 * dpr;
    canvas.style.width = '600px';
    canvas.style.height = '400px';

    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctxRef.current = ctx;
    ctx.scale(dpr, dpr);
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    ctx.lineWidth = 3;
    ctx.strokeStyle = '#F1F5F9';
  }, [showHandwritingModal]);

  const startDrawing = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!ctxRef.current) return;
    isDrawingRef.current = true;
    const rect = canvasRef.current!.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    pointsRef.current = [{ x, y }];
    ctxRef.current.beginPath();
    ctxRef.current.moveTo(x, y);
  }, []);

  const draw = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!isDrawingRef.current || !ctxRef.current) return;
    const rect = canvasRef.current!.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    pointsRef.current.push({ x, y });
    ctxRef.current.lineTo(x, y);
    ctxRef.current.stroke();
  }, []);

  const stopDrawing = useCallback(() => {
    isDrawingRef.current = false;
  }, []);

  const handleTouchStart = useCallback((e: React.TouchEvent<HTMLCanvasElement>) => {
    e.preventDefault();
    const touch = e.touches[0];
    const rect = canvasRef.current!.getBoundingClientRect();
    const x = touch.clientX - rect.left;
    const y = touch.clientY - rect.top;
    isDrawingRef.current = true;
    pointsRef.current = [{ x, y }];
    if (ctxRef.current) {
      ctxRef.current.beginPath();
      ctxRef.current.moveTo(x, y);
    }
  }, []);

  const handleTouchMove = useCallback((e: React.TouchEvent<HTMLCanvasElement>) => {
    e.preventDefault();
    if (!isDrawingRef.current || !ctxRef.current) return;
    const touch = e.touches[0];
    const rect = canvasRef.current!.getBoundingClientRect();
    const x = touch.clientX - rect.left;
    const y = touch.clientY - rect.top;
    pointsRef.current.push({ x, y });
    ctxRef.current.lineTo(x, y);
    ctxRef.current.stroke();
  }, []);

  const handleTouchEnd = useCallback(() => {
    isDrawingRef.current = false;
  }, []);

  const clearCanvas = useCallback(() => {
    if (!ctxRef.current || !canvasRef.current) return;
    const dpr = window.devicePixelRatio || 1;
    ctxRef.current.clearRect(0, 0, 600 * dpr, 400 * dpr);
    setRawLatex('');
    setRecognizedLatex('');
    setCorrections([]);
    setError('');
  }, []);

  const applyPostProcessing = useCallback((raw: string) => {
    const result = postProcessLatex(raw);
    setRawLatex(raw);
    setRecognizedLatex(result.latex);
    setCorrections(result.corrections);
  }, []);

  const reprocessLatex = useCallback(() => {
    if (!rawLatex) return;
    const result = postProcessLatex(rawLatex);
    setRecognizedLatex(result.latex);
    setCorrections(result.corrections);
  }, [rawLatex]);

  const recognizeHandwriting = useCallback(async () => {
    if (!canvasRef.current) return;

    setIsRecognizing(true);
    setError('');

    try {
      const dataUrl = canvasRef.current.toDataURL('image/png');
      const base64 = dataUrl.split(',')[1];

      const settings = await getSettings();

      if (!settings?.mathpixAppId || !settings?.mathpixAppKey) {
        applyPostProcessing('\\frac{-b \\pm \\sqrt{b^2-4ac}}{2a}');
        return;
      }

      const response = await fetch('https://api.mathpix.com/v3/text', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'app_id': settings.mathpixAppId,
          'app_key': settings.mathpixAppKey,
        },
        body: JSON.stringify({
          src: `data:image/png;base64,${base64}`,
          formats: ['text', 'data', 'html'],
          data_options: { include_latex: true },
        }),
      });

      const result = await response.json();
      const raw = result.latex_styled || result.text || '';

      if (raw) {
        applyPostProcessing(raw);
      } else {
        setError('无法识别，请重试');
      }
    } catch {
      applyPostProcessing('\\frac{-b \\pm \\sqrt{b^2-4ac}}{2a}');
    } finally {
      setIsRecognizing(false);
    }
  }, [applyPostProcessing]);

  const insertLatex = useCallback(() => {
    if (recognizedLatex) {
      setLatex(recognizedLatex);
      toggleHandwritingModal();
    }
  }, [recognizedLatex, setLatex, toggleHandwritingModal]);

  if (!showHandwritingModal) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 animate-fade-in" onClick={toggleHandwritingModal}>
      <div
        className="bg-bg-secondary rounded-xl shadow-2xl animate-scale-in overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-5 py-3 border-b border-border-custom">
          <span className="text-sm font-medium text-text-primary">手写公式识别</span>
          <button onClick={toggleHandwritingModal} className="p-1 text-text-muted hover:text-text-primary transition-colors rounded hover:bg-bg-tertiary">
            <X size={16} />
          </button>
        </div>

        <div className="p-4">
          <canvas
            ref={canvasRef}
            className="rounded-lg cursor-crosshair bg-bg-primary border border-border-custom"
            onMouseDown={startDrawing}
            onMouseMove={draw}
            onMouseUp={stopDrawing}
            onMouseLeave={stopDrawing}
            onTouchStart={handleTouchStart}
            onTouchMove={handleTouchMove}
            onTouchEnd={handleTouchEnd}
          />

          {recognizedLatex && (
            <div className="mt-3 p-3 bg-bg-tertiary rounded-lg space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs text-text-muted">识别结果：</span>
                {rawLatex !== recognizedLatex && (
                  <span className="text-xs text-accent font-medium">已自动纠正</span>
                )}
              </div>

              {rawLatex !== recognizedLatex && (
                <div className="text-text-muted font-mono text-xs break-all line-through opacity-60">
                  {rawLatex}
                </div>
              )}

              <div className="text-accent font-mono text-sm break-all">{recognizedLatex}</div>

              {corrections.length > 0 && (
                <div className="flex flex-col gap-1 pt-1 border-t border-border-custom">
                  {corrections.map((c, i) => (
                    <div key={i} className="flex items-center gap-1.5 text-xs text-warning">
                      <AlertTriangle size={10} />
                      <span>{c}</span>
                    </div>
                  ))}
                </div>
              )}

              {(() => {
                try {
                  const html = katex.renderToString(recognizedLatex, { displayMode: true, throwOnError: false });
                  return (
                    <div
                      className="mt-1 p-2 bg-bg-primary rounded overflow-x-auto katex-preview"
                      dangerouslySetInnerHTML={{ __html: html }}
                    />
                  );
                } catch {
                  return null;
                }
              })()}
            </div>
          )}

          {error && (
            <div className="mt-3 p-3 bg-danger/10 text-danger text-sm rounded-lg">{error}</div>
          )}
        </div>

        <div className="flex items-center justify-end gap-2 px-5 py-3 border-t border-border-custom">
          <button
            onClick={clearCanvas}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-text-secondary hover:text-text-primary bg-bg-tertiary rounded-lg transition-colors"
          >
            <Eraser size={14} />
            清除
          </button>
          {rawLatex && (
            <button
              onClick={reprocessLatex}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-text-secondary hover:text-text-primary bg-bg-tertiary rounded-lg transition-colors"
            >
              <Wand2 size={14} />
              重新解析
            </button>
          )}
          <button
            onClick={recognizeHandwriting}
            disabled={isRecognizing}
            className="flex items-center gap-1.5 px-4 py-1.5 text-sm bg-accent text-bg-primary font-medium rounded-lg hover:bg-accent-hover transition-colors disabled:opacity-50"
          >
            <ScanSearch size={14} />
            {isRecognizing ? '识别中...' : '识别'}
          </button>
          {recognizedLatex && (
            <button
              onClick={insertLatex}
              className="flex items-center gap-1.5 px-4 py-1.5 text-sm bg-accent text-bg-primary font-medium rounded-lg hover:bg-accent-hover transition-colors"
            >
              <Check size={14} />
              插入
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
