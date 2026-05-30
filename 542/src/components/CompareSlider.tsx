import { useCallback, useRef, useState, useEffect } from 'react';
import { useAppStore } from '@/store/useAppStore';

export default function CompareSlider() {
  const { comparePosition, setComparePosition } = useAppStore();
  const trackRef = useRef<HTMLDivElement>(null);
  const [isDragging, setIsDragging] = useState(false);

  const updatePosition = useCallback(
    (clientX: number) => {
      if (!trackRef.current) return;
      const rect = trackRef.current.getBoundingClientRect();
      const x = clientX - rect.left;
      const pct = Math.min(100, Math.max(0, (x / rect.width) * 100));
      setComparePosition(pct);
    },
    [setComparePosition]
  );

  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      setIsDragging(true);
      updatePosition(e.clientX);
    },
    [updatePosition]
  );

  useEffect(() => {
    if (!isDragging) return;

    const handleMouseMove = (e: MouseEvent) => {
      updatePosition(e.clientX);
    };

    const handleMouseUp = () => {
      setIsDragging(false);
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDragging, updatePosition]);

  return (
    <div
      ref={trackRef}
      className="w-full h-2 rounded-full bg-zinc-800 relative cursor-ew-resize"
      onMouseDown={handleMouseDown}
    >
      <div
        className="absolute top-0 left-0 h-full rounded-full bg-gradient-to-r from-[#00d4aa] to-[#00d4aa]/60"
        style={{ width: `${comparePosition}%` }}
      />
      <div
        className="absolute top-1/2 -translate-y-1/2 w-4 h-4 rounded-full bg-white shadow-lg border-2 border-[#00d4aa] transition-transform"
        style={{ left: `${comparePosition}%`, transform: `translate(-50%, -50%) ${isDragging ? 'scale(1.2)' : 'scale(1)'}` }}
      />
    </div>
  );
}
