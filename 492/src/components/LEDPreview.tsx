import React, { useEffect, useRef, useState, useCallback, useMemo } from 'react';
import { Maximize2, Minimize2, Play, Pause } from 'lucide-react';
import { useLEDStore } from '../store/ledStore';
import { BackgroundEffectEngine } from './BackgroundEffectEngine';
import { hyphenateText, wrapTextWithHyphenation, wrapTextSimple } from '../utils/textWrapper';

const TARGET_FPS = 60;
const FRAME_DURATION = 1000 / TARGET_FPS;

interface ProcessedLine {
  id: string;
  originalText: string;
  hyphenatedText: string;
  color: string;
  wrappedLines: string[];
  lineWidths: number[];
  totalWidth: number;
}

export const LEDPreview: React.FC = () => {
  const bgCanvasRef = useRef<HTMLCanvasElement>(null);
  const textCanvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const effectEngineRef = useRef<BackgroundEffectEngine | null>(null);
  
  const bgAnimationRef = useRef<number | null>(null);
  const textAnimationRef = useRef<number | null>(null);
  
  const scrollOffsetRef = useRef<number>(0);
  const lastBgTimeRef = useRef<number>(0);
  const lastTextTimeRef = useRef<number>(0);
  const lagBgRef = useRef<number>(0);
  const lagTextRef = useRef<number>(0);
  
  const processedLinesRef = useRef<ProcessedLine[]>([]);
  const canvasSizeRef = useRef<{ width: number; height: number }>({ width: 0, height: 0 });
  
  const [isFullscreen, setIsFullscreen] = useState(false);

  const {
    lines,
    font,
    scroll,
    background,
    isPlaying,
    togglePlaying
  } = useLEDStore();

  const maxTextWidth = useMemo(() => {
    return canvasSizeRef.current.width * 0.9;
  }, [canvasSizeRef.current.width]);

  const processLines = useCallback(async () => {
    const textCanvas = textCanvasRef.current;
    if (!textCanvas) return;

    const ctx = textCanvas.getContext('2d');
    if (!ctx) return;

    ctx.font = `${font.weight} ${font.size}px ${font.family}`;
    const maxWidth = canvasSizeRef.current.width * 0.9;

    const processed: ProcessedLine[] = [];

    for (const line of lines) {
      const hyphenated = await hyphenateText(line.text);
      const wrapResult = hyphenated.includes('\u00AD')
        ? wrapTextWithHyphenation(ctx, hyphenated, maxWidth)
        : wrapTextSimple(ctx, hyphenated, maxWidth);

      const totalWidth = Math.max(...wrapResult.lineWidths, 0);

      processed.push({
        id: line.id,
        originalText: line.text,
        hyphenatedText: hyphenated,
        color: line.color,
        wrappedLines: wrapResult.lines,
        lineWidths: wrapResult.lineWidths,
        totalWidth
      });
    }

    processedLinesRef.current = processed;
  }, [lines, font]);

  const resizeCanvases = useCallback(() => {
    const bgCanvas = bgCanvasRef.current;
    const textCanvas = textCanvasRef.current;
    const container = containerRef.current;
    
    if (!bgCanvas || !textCanvas || !container) return;

    const dpr = window.devicePixelRatio || 1;
    const rect = container.getBoundingClientRect();
    
    bgCanvas.width = rect.width * dpr;
    bgCanvas.height = rect.height * dpr;
    textCanvas.width = rect.width * dpr;
    textCanvas.height = rect.height * dpr;

    const bgCtx = bgCanvas.getContext('2d');
    const textCtx = textCanvas.getContext('2d');
    
    if (bgCtx) bgCtx.scale(dpr, dpr);
    if (textCtx) textCtx.scale(dpr, dpr);

    canvasSizeRef.current = { width: rect.width, height: rect.height };

    if (effectEngineRef.current) {
      effectEngineRef.current.resize(rect.width, rect.height);
    }

    processLines();
  }, [processLines]);

  const initEffectEngine = useCallback(() => {
    if (!bgCanvasRef.current) return;
    
    const engine = new BackgroundEffectEngine(bgCanvasRef.current);
    engine.setEffect(background.effect);
    engine.setEffectColor(background.effectColor);
    engine.setEffectIntensity(background.effectIntensity);
    effectEngineRef.current = engine;
  }, [background.effect, background.effectColor, background.effectIntensity]);

  const renderBackground = useCallback((timestamp: number) => {
    const canvas = bgCanvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const deltaTime = timestamp - lastBgTimeRef.current;
    lastBgTimeRef.current = timestamp;
    lagBgRef.current += deltaTime;

    while (lagBgRef.current >= FRAME_DURATION) {
      const { width, height } = canvasSizeRef.current;

      ctx.fillStyle = background.color;
      ctx.fillRect(0, 0, width, height);

      if (effectEngineRef.current) {
        effectEngineRef.current.render();
      }

      lagBgRef.current -= FRAME_DURATION;
    }

    bgAnimationRef.current = requestAnimationFrame(renderBackground);
  }, [background.color]);

  const renderText = useCallback((timestamp: number) => {
    const canvas = textCanvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const deltaTime = timestamp - lastTextTimeRef.current;
    lastTextTimeRef.current = timestamp;
    lagTextRef.current += deltaTime;

    while (lagTextRef.current >= FRAME_DURATION) {
      const { width, height } = canvasSizeRef.current;

      ctx.clearRect(0, 0, width, height);

      if (isPlaying) {
        const speedMultiplier = scroll.speed * 0.5;
        const speedPerFrame = speedMultiplier * (FRAME_DURATION / 16.67);

        if (scroll.direction === 'left') {
          scrollOffsetRef.current -= speedPerFrame;
        } else if (scroll.direction === 'right') {
          scrollOffsetRef.current += speedPerFrame;
        } else if (scroll.direction === 'up') {
          scrollOffsetRef.current -= speedPerFrame;
        } else if (scroll.direction === 'down') {
          scrollOffsetRef.current += speedPerFrame;
        }
      }

      const processedLines = processedLinesRef.current;
      const lineHeight = font.size * 1.5;

      let totalWrappedLines = 0;
      const lineStartIndices: number[] = [];
      for (const line of processedLines) {
        lineStartIndices.push(totalWrappedLines);
        totalWrappedLines += line.wrappedLines.length || 1;
      }

      const totalHeight = totalWrappedLines * lineHeight;
      const startY = (height - totalHeight) / 2 + lineHeight / 2;

      processedLines.forEach((line, lineIndex) => {
        const wrappedLines = line.wrappedLines.length > 0 ? line.wrappedLines : [''];
        const lineStartIndex = lineStartIndices[lineIndex];

        wrappedLines.forEach((wrappedText, wrapIndex) => {
          const textY = startY + (lineStartIndex + wrapIndex) * lineHeight;

          ctx.save();
          ctx.font = `${font.weight} ${font.size}px ${font.family}`;
          ctx.textBaseline = 'middle';

          const textWidth = line.lineWidths[wrapIndex] || ctx.measureText(wrappedText).width;
          const loopWidth = Math.max(textWidth, width * 0.3) + width * 0.5;

          if (font.glow) {
            ctx.shadowColor = line.color;
            ctx.shadowBlur = font.glowIntensity;
          }

          ctx.fillStyle = line.color;

          if (scroll.direction === 'left' || scroll.direction === 'right') {
            let offsetX = scrollOffsetRef.current % loopWidth;
            if (offsetX > 0) offsetX -= loopWidth;

            for (let i = -1; i <= 2; i++) {
              const x = offsetX + width / 2 - textWidth / 2 + i * loopWidth;
              ctx.fillText(wrappedText, x, textY);
            }
          } else {
            let offsetY = scrollOffsetRef.current % (totalHeight + height * 0.3);
            if (offsetY > 0) offsetY -= (totalHeight + height * 0.3);

            const centerX = width / 2 - textWidth / 2;
            
            for (let i = -1; i <= 2; i++) {
              const drawY = textY + offsetY + i * (totalHeight + height * 0.3);
              ctx.fillText(wrappedText, centerX, drawY);
            }
          }

          ctx.restore();
        });
      });

      if (scroll.mode === 'once') {
        const maxWidth = Math.max(...processedLines.map(l => l.totalWidth), width * 0.3);
        const maxOffset = scroll.direction === 'left' || scroll.direction === 'right'
          ? maxWidth + width
          : totalHeight + height;
          
        if (Math.abs(scrollOffsetRef.current) > maxOffset) {
          scrollOffsetRef.current = 0;
        }
      }

      lagTextRef.current -= FRAME_DURATION;
    }

    textAnimationRef.current = requestAnimationFrame(renderText);
  }, [isPlaying, scroll, font]);

  useEffect(() => {
    const ro = new ResizeObserver(() => {
      resizeCanvases();
    });

    if (containerRef.current) {
      ro.observe(containerRef.current);
    }

    return () => ro.disconnect();
  }, [resizeCanvases]);

  useEffect(() => {
    processLines();
  }, [processLines]);

  useEffect(() => {
    initEffectEngine();
    resizeCanvases();

    lastBgTimeRef.current = performance.now();
    lastTextTimeRef.current = performance.now();

    bgAnimationRef.current = requestAnimationFrame(renderBackground);
    textAnimationRef.current = requestAnimationFrame(renderText);

    return () => {
      if (bgAnimationRef.current) {
        cancelAnimationFrame(bgAnimationRef.current);
      }
      if (textAnimationRef.current) {
        cancelAnimationFrame(textAnimationRef.current);
      }
    };
  }, [initEffectEngine, resizeCanvases, renderBackground, renderText]);

  useEffect(() => {
    if (effectEngineRef.current) {
      effectEngineRef.current.setEffect(background.effect);
      effectEngineRef.current.setEffectColor(background.effectColor);
      effectEngineRef.current.setEffectIntensity(background.effectIntensity);
    }
  }, [background.effect, background.effectColor, background.effectIntensity]);

  const toggleFullscreen = () => {
    if (!containerRef.current) return;

    if (!document.fullscreenElement) {
      containerRef.current.requestFullscreen();
      setIsFullscreen(true);
    } else {
      document.exitFullscreen();
      setIsFullscreen(false);
    }
  };

  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement);
      setTimeout(resizeCanvases, 100);
    };

    document.addEventListener('fullscreenchange', handleFullscreenChange);
    return () => document.removeEventListener('fullscreenchange', handleFullscreenChange);
  }, [resizeCanvases]);

  return (
    <div 
      ref={containerRef}
      className="relative w-full h-full bg-gray-900 rounded-xl overflow-hidden border border-gray-700 shadow-2xl"
    >
      <canvas
        ref={bgCanvasRef}
        className="absolute inset-0 w-full h-full"
        style={{ zIndex: 0 }}
      />
      <canvas
        ref={textCanvasRef}
        className="absolute inset-0 w-full h-full"
        style={{ zIndex: 1 }}
      />

      <div className="absolute top-4 right-4 flex gap-2 z-10">
        <button
          onClick={togglePlaying}
          className="p-2.5 bg-black/50 backdrop-blur-md rounded-lg border border-white/10 hover:bg-black/70 transition-all hover:scale-105"
          title={isPlaying ? '暂停' : '播放'}
        >
          {isPlaying ? (
            <Pause className="w-5 h-5 text-white" />
          ) : (
            <Play className="w-5 h-5 text-white" />
          )}
        </button>
        <button
          onClick={toggleFullscreen}
          className="p-2.5 bg-black/50 backdrop-blur-md rounded-lg border border-white/10 hover:bg-black/70 transition-all hover:scale-105"
          title={isFullscreen ? '退出全屏' : '全屏'}
        >
          {isFullscreen ? (
            <Minimize2 className="w-5 h-5 text-white" />
          ) : (
            <Maximize2 className="w-5 h-5 text-white" />
          )}
        </button>
      </div>

      <div className="absolute bottom-4 left-4 px-3 py-1.5 bg-black/50 backdrop-blur-md rounded-lg border border-white/10 z-10">
        <span className="text-xs text-gray-300">
          {lines.length} 行 · {scroll.direction === 'left' ? '左滚' : scroll.direction === 'right' ? '右滚' : scroll.direction === 'up' ? '上滚' : '下滚'} · 速度 {scroll.speed}x · 智能断字
        </span>
      </div>
    </div>
  );
};
