import { useRef, useEffect, useState, useCallback } from "react";
import { cn } from "@/lib/utils";

interface ActionSegment {
  id: string;
  action: string;
  startTime: number;
  endTime: number;
  confidence: number;
  color: string;
}

interface TimelineProps {
  segments: ActionSegment[];
  currentTime: number;
  duration: number;
  onTimeChange: (time: number) => void;
  className?: string;
}

const actionColors: Record<string, string> = {
  "站立": "#165DFF",
  "行走": "#00FFA3",
  "跑步": "#FF7D00",
  "坐下": "#FF4D4F",
  "躺下": "#722ED1",
  "挥手": "#13C2C2",
  "跳跃": "#FAAD14",
  "摔倒": "#F5222D",
  "其他": "#8C8C8C",
};

export default function Timeline({
  segments,
  currentTime,
  duration,
  onTimeChange,
  className,
}: TimelineProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [scale, setScale] = useState(1);
  const [offset, setOffset] = useState(0);
  const [hoveredSegment, setHoveredSegment] = useState<ActionSegment | null>(null);
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });
  const dragStartRef = useRef({ x: 0, offset: 0 });

  const pixelsPerSecond = 100 * scale;

  const drawTimeline = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();

    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);

    const width = rect.width;
    const height = rect.height;

    ctx.clearRect(0, 0, width, height);

    const bgGradient = ctx.createLinearGradient(0, 0, 0, height);
    bgGradient.addColorStop(0, "rgba(22, 93, 255, 0.05)");
    bgGradient.addColorStop(1, "rgba(0, 255, 163, 0.02)");
    ctx.fillStyle = bgGradient;
    ctx.fillRect(0, 0, width, height);

    ctx.strokeStyle = "rgba(255, 255, 255, 0.05)";
    ctx.lineWidth = 1;

    const visibleStart = -offset / pixelsPerSecond;
    const visibleEnd = visibleStart + width / pixelsPerSecond;

    const gridStep = scale > 2 ? 1 : scale > 1 ? 5 : 10;
    for (let t = Math.floor(visibleStart / gridStep) * gridStep; t <= visibleEnd; t += gridStep) {
      const x = (t * pixelsPerSecond) + offset;
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, height);
      ctx.stroke();

      if (t >= 0 && t <= duration) {
        ctx.fillStyle = "rgba(255, 255, 255, 0.4)";
        ctx.font = "10px monospace";
        ctx.textAlign = "center";
        ctx.fillText(`${t}s`, x, height - 5);
      }
    }

    const trackY = 20;
    const trackHeight = height - 60;

    segments.forEach((segment) => {
      const x1 = (segment.startTime * pixelsPerSecond) + offset;
      const x2 = (segment.endTime * pixelsPerSecond) + offset;
      const segWidth = x2 - x1;

      if (x2 < 0 || x1 > width) return;

      const color = segment.color || actionColors[segment.action] || actionColors["其他"];
      
      const gradient = ctx.createLinearGradient(x1, trackY, x1, trackY + trackHeight);
      gradient.addColorStop(0, `${color}99`);
      gradient.addColorStop(0.5, `${color}CC`);
      gradient.addColorStop(1, `${color}99`);

      ctx.fillStyle = gradient;
      ctx.beginPath();
      ctx.roundRect(x1, trackY, segWidth, trackHeight, 4);
      ctx.fill();

      ctx.strokeStyle = `${color}FF`;
      ctx.lineWidth = 1;
      ctx.stroke();

      if (segWidth > 40) {
        ctx.fillStyle = "rgba(255, 255, 255, 0.9)";
        ctx.font = "11px 'Inter', sans-serif";
        ctx.textAlign = "center";
        ctx.fillText(segment.action, x1 + segWidth / 2, trackY + trackHeight / 2 + 4);
      }
    });

    const currentX = (currentTime * pixelsPerSecond) + offset;
    
    ctx.shadowColor = "#F5222D";
    ctx.shadowBlur = 10;
    ctx.strokeStyle = "#F5222D";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(currentX, 0);
    ctx.lineTo(currentX, height);
    ctx.stroke();

    ctx.shadowBlur = 0;
    ctx.fillStyle = "#F5222D";
    ctx.beginPath();
    ctx.moveTo(currentX - 6, 0);
    ctx.lineTo(currentX + 6, 0);
    ctx.lineTo(currentX, 10);
    ctx.closePath();
    ctx.fill();

    ctx.fillStyle = "#F5222D";
    ctx.fillRect(currentX - 30, height - 22, 60, 20);
    ctx.fillStyle = "#fff";
    ctx.font = "11px monospace";
    ctx.textAlign = "center";
    ctx.fillText(currentTime.toFixed(1) + "s", currentX, height - 7);
  }, [segments, currentTime, duration, scale, offset, pixelsPerSecond]);

  const getTimeAtX = useCallback((clientX: number) => {
    const canvas = canvasRef.current;
    if (!canvas) return 0;
    
    const rect = canvas.getBoundingClientRect();
    const x = clientX - rect.left;
    const time = (x - offset) / pixelsPerSecond;
    
    return Math.max(0, Math.min(duration, time));
  }, [offset, pixelsPerSecond, duration]);

  const findSegmentAtX = useCallback((clientX: number) => {
    const time = getTimeAtX(clientX);
    return segments.find(
      (s) => time >= s.startTime && time <= s.endTime
    ) || null;
  }, [getTimeAtX, segments]);

  const handleWheel = useCallback((e: WheelEvent) => {
    e.preventDefault();
    e.stopPropagation();

    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    const newScale = Math.max(0.2, Math.min(10, scale * delta));
    
    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const timeAtMouse = (mouseX - offset) / pixelsPerSecond;
    
    const newPixelsPerSecond = 100 * newScale;
    const newOffset = mouseX - timeAtMouse * newPixelsPerSecond;

    setScale(newScale);
    setOffset(newOffset);
  }, [scale, offset, pixelsPerSecond]);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (e.button === 1 || (e.button === 0 && e.shiftKey)) {
      setIsDragging(true);
      dragStartRef.current = { x: e.clientX, offset };
      return;
    }

    const time = getTimeAtX(e.clientX);
    onTimeChange(time);
  }, [getTimeAtX, offset, onTimeChange]);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    setMousePos({ x: e.clientX, y: e.clientY });

    const segment = findSegmentAtX(e.clientX);
    setHoveredSegment(segment);

    if (isDragging) {
      const deltaX = e.clientX - dragStartRef.current.x;
      setOffset(dragStartRef.current.offset + deltaX);
    }
  }, [isDragging, findSegmentAtX]);

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  const handleMouseLeave = useCallback(() => {
    setIsDragging(false);
    setHoveredSegment(null);
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    canvas.addEventListener("wheel", handleWheel, { passive: false });
    return () => canvas.removeEventListener("wheel", handleWheel);
  }, [handleWheel]);

  useEffect(() => {
    drawTimeline();
  }, [drawTimeline]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const currentX = (currentTime * pixelsPerSecond) + offset;

    if (currentX < 50 || currentX > rect.width - 50) {
      setOffset(rect.width / 2 - currentTime * pixelsPerSecond);
    }
  }, [currentTime, pixelsPerSecond]);

  useEffect(() => {
    const handleResize = () => drawTimeline();
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, [drawTimeline]);

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = (seconds % 60).toFixed(2);
    return mins > 0 ? `${mins}m ${secs}s` : `${secs}s`;
  };

  return (
    <div
      ref={containerRef}
      className={cn(
        "relative w-full h-full bg-slate-900/50 rounded-lg border border-slate-700/50 overflow-hidden",
        isDragging && "cursor-grabbing",
        !isDragging && "cursor-crosshair",
        className
      )}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseLeave}
    >
      <canvas
        ref={canvasRef}
        className="w-full h-full"
        style={{ touchAction: "none" }}
      />

      {hoveredSegment && (
        <div
          className="absolute z-50 bg-slate-900/95 backdrop-blur-sm border border-slate-600 rounded-lg p-3 shadow-2xl pointer-events-none animate-slide-in"
          style={{
            left: mousePos.x - containerRef.current?.getBoundingClientRect().left! + 15,
            top: mousePos.y - containerRef.current?.getBoundingClientRect().top! - 100,
            minWidth: "200px",
          }}
        >
          <div className="flex items-center gap-2 mb-2">
            <div
              className="w-3 h-3 rounded"
              style={{
                backgroundColor: hoveredSegment.color || actionColors[hoveredSegment.action],
                boxShadow: `0 0 10px ${hoveredSegment.color || actionColors[hoveredSegment.action]}`,
              }}
            />
            <span className="font-bold text-white">{hoveredSegment.action}</span>
          </div>
          <div className="space-y-1 text-xs">
            <div className="flex justify-between">
              <span className="text-slate-400">开始时间</span>
              <span className="text-slate-200 font-mono">{formatDuration(hoveredSegment.startTime)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">结束时间</span>
              <span className="text-slate-200 font-mono">{formatDuration(hoveredSegment.endTime)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">持续时间</span>
              <span className="text-accent font-mono">
                {formatDuration(hoveredSegment.endTime - hoveredSegment.startTime)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">平均置信度</span>
              <span className="text-primary font-mono">{(hoveredSegment.confidence * 100).toFixed(1)}%</span>
            </div>
          </div>
        </div>
      )}

      <div className="absolute top-2 left-2 flex gap-2">
        <button
          className="px-2 py-1 text-xs bg-slate-800/80 hover:bg-slate-700/80 text-slate-300 rounded border border-slate-600/50 transition-colors"
          onClick={() => setScale(Math.max(0.2, scale * 0.8))}
        >
          −
        </button>
        <span className="px-2 py-1 text-xs bg-slate-800/80 text-slate-300 rounded border border-slate-600/50 font-mono">
          {scale.toFixed(1)}x
        </span>
        <button
          className="px-2 py-1 text-xs bg-slate-800/80 hover:bg-slate-700/80 text-slate-300 rounded border border-slate-600/50 transition-colors"
          onClick={() => setScale(Math.min(10, scale * 1.2))}
        >
          +
        </button>
        <button
          className="px-2 py-1 text-xs bg-slate-800/80 hover:bg-slate-700/80 text-slate-300 rounded border border-slate-600/50 transition-colors ml-2"
          onClick={() => {
            setScale(1);
            setOffset(0);
          }}
        >
          重置
        </button>
      </div>

      <div className="absolute bottom-2 right-2 text-[10px] text-slate-500">
        滚轮缩放 | Shift+拖拽平移 | 点击跳转
      </div>
    </div>
  );
}
