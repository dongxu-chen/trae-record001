import * as React from "react";
import { GripVertical, GripHorizontal } from "lucide-react";
import { cn } from "@/lib/utils";

export type ResizeDirection = "horizontal" | "vertical";

export interface ResizableHandleProps {
  direction?: ResizeDirection;
  onResizeStart?: (e: React.MouseEvent) => void;
  onResize?: (delta: number) => void;
  onResizeEnd?: () => void;
  minSize?: number;
  maxSize?: number;
  className?: string;
  showGrip?: boolean;
  disabled?: boolean;
}

const ResizableHandle: React.FC<ResizableHandleProps> = ({
  direction = "horizontal",
  onResizeStart,
  onResize,
  onResizeEnd,
  className,
  showGrip = true,
  disabled = false,
}) => {
  const [isResizing, setIsResizing] = React.useState(false);

  const handleMouseDown = (e: React.MouseEvent) => {
    if (disabled) return;
    e.preventDefault();
    e.stopPropagation();
    setIsResizing(true);
    onResizeStart?.(e);

    const startPos = direction === "horizontal" ? e.clientX : e.clientY;

    const handleMouseMove = (moveEvent: MouseEvent) => {
      const currentPos =
        direction === "horizontal" ? moveEvent.clientX : moveEvent.clientY;
      const delta = currentPos - startPos;
      onResize?.(delta);
    };

    const handleMouseUp = () => {
      setIsResizing(false);
      onResizeEnd?.();
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };

    document.body.style.cursor =
      direction === "horizontal" ? "col-resize" : "row-resize";
    document.body.style.userSelect = "none";
    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);
  };

  React.useEffect(() => {
    return () => {
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };
  }, []);

  const isHorizontal = direction === "horizontal";

  return (
    <div
      className={cn(
        "relative flex items-center justify-center group transition-colors",
        isHorizontal
          ? "w-1.5 h-full cursor-col-resize"
          : "h-1.5 w-full cursor-row-resize",
        disabled && "cursor-not-allowed opacity-50",
        className
      )}
      onMouseDown={handleMouseDown}
    >
      <div
        className={cn(
          "absolute transition-all duration-150",
          isHorizontal
            ? "h-full w-0.5 left-1/2 -translate-x-1/2"
            : "w-full h-0.5 top-1/2 -translate-y-1/2",
          isResizing
            ? "bg-cyber-500"
            : "bg-transparent group-hover:bg-cyber-500/50"
        )}
      />

      {showGrip && (
        <div
          className={cn(
            "absolute flex items-center justify-center transition-all duration-150",
            isHorizontal
              ? "h-8 w-3 bg-space-700 rounded border border-space-600"
              : "w-8 h-3 bg-space-700 rounded border border-space-600",
            isResizing
              ? "border-cyber-500 shadow-cyber-glow-sm"
              : "group-hover:border-cyber-500/50",
            disabled && "opacity-50"
          )}
        >
          {isHorizontal ? (
            <GripVertical
              size={12}
              className={cn(
                "transition-colors",
                isResizing ? "text-cyber-400" : "text-gray-500 group-hover:text-cyber-400"
              )}
            />
          ) : (
            <GripHorizontal
              size={12}
              className={cn(
                "transition-colors",
                isResizing ? "text-cyber-400" : "text-gray-500 group-hover:text-cyber-400"
              )}
            />
          )}
        </div>
      )}

      {isResizing && (
        <div
          className={cn(
            "fixed inset-0 z-50",
            isHorizontal ? "cursor-col-resize" : "cursor-row-resize"
          )}
          style={{ background: "transparent" }}
        />
      )}
    </div>
  );
};

ResizableHandle.displayName = "ResizableHandle";

export { ResizableHandle };
