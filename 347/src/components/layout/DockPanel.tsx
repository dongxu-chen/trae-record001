import * as React from "react";
import { ChevronUp, ChevronDown, GripVertical, X } from "lucide-react";
import { cn } from "@/lib/utils";

export type DockPosition = "left" | "right" | "top" | "bottom";

export interface DockPanelProps {
  title?: React.ReactNode;
  icon?: React.ReactNode;
  children?: React.ReactNode;
  position?: DockPosition;
  defaultCollapsed?: boolean;
  collapsed?: boolean;
  onCollapsedChange?: (collapsed: boolean) => void;
  resizable?: boolean;
  defaultSize?: number;
  minSize?: number;
  maxSize?: number;
  size?: number;
  onSizeChange?: (size: number) => void;
  onClose?: () => void;
  showHeader?: boolean;
  className?: string;
  headerClassName?: string;
  contentClassName?: string;
}

const DockPanel: React.FC<DockPanelProps> = ({
  title,
  icon,
  children,
  position = "left",
  defaultCollapsed = false,
  collapsed: controlledCollapsed,
  onCollapsedChange,
  resizable = true,
  defaultSize = 280,
  minSize = 200,
  maxSize = 600,
  size: controlledSize,
  onSizeChange,
  onClose,
  showHeader = true,
  className,
  headerClassName,
  contentClassName,
}) => {
  const [internalCollapsed, setInternalCollapsed] = React.useState(defaultCollapsed);
  const [internalSize, setInternalSize] = React.useState(defaultSize);
  const [isResizing, setIsResizing] = React.useState(false);

  const isCollapsed = controlledCollapsed ?? internalCollapsed;
  const currentSize = controlledSize ?? internalSize;

  const isHorizontal = position === "left" || position === "right";

  const toggleCollapse = () => {
    const newCollapsed = !isCollapsed;
    if (controlledCollapsed === undefined) {
      setInternalCollapsed(newCollapsed);
    }
    onCollapsedChange?.(newCollapsed);
  };

  const handleResizeStart = (e: React.MouseEvent) => {
    if (!resizable || isCollapsed) return;
    e.preventDefault();
    e.stopPropagation();
    setIsResizing(true);

    const startPos = isHorizontal ? e.clientX : e.clientY;
    const startSize = currentSize;

    const handleMouseMove = (moveEvent: MouseEvent) => {
      const currentPos = isHorizontal ? moveEvent.clientX : moveEvent.clientY;
      let delta = currentPos - startPos;

      if (position === "left" || position === "top") {
        delta = delta;
      } else {
        delta = -delta;
      }

      let newSize = startSize + delta;
      newSize = Math.max(minSize, Math.min(maxSize, newSize));

      if (controlledSize === undefined) {
        setInternalSize(newSize);
      }
      onSizeChange?.(newSize);
    };

    const handleMouseUp = () => {
      setIsResizing(false);
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };

    document.body.style.cursor = isHorizontal ? "col-resize" : "row-resize";
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

  const getResizeHandlePosition = () => {
    switch (position) {
      case "left":
        return "right-0 top-0 bottom-0 w-1 cursor-col-resize";
      case "right":
        return "left-0 top-0 bottom-0 w-1 cursor-col-resize";
      case "top":
        return "bottom-0 left-0 right-0 h-1 cursor-row-resize";
      case "bottom":
        return "top-0 left-0 right-0 h-1 cursor-row-resize";
    }
  };

  const panelStyle: React.CSSProperties = isCollapsed
    ? {
        [isHorizontal ? "width" : "height"]: 40,
        minWidth: isHorizontal ? 40 : undefined,
        minHeight: !isHorizontal ? 40 : undefined,
      }
    : {
        [isHorizontal ? "width" : "height"]: currentSize,
        minWidth: isHorizontal ? minSize : undefined,
        minHeight: !isHorizontal ? minSize : undefined,
        maxWidth: isHorizontal ? maxSize : undefined,
        maxHeight: !isHorizontal ? maxSize : undefined,
      };

  const collapseIcon = isCollapsed ? (
    position === "left" ? (
      <ChevronDown size={16} />
    ) : position === "right" ? (
      <ChevronDown size={16} />
    ) : (
      <ChevronDown size={16} />
    )
  ) : (
    <ChevronUp size={16} />
  );

  return (
    <div
      className={cn(
        "relative flex flex-col bg-space-800 border border-space-600 transition-all duration-300",
        isResizing && "shadow-cyber-glow-sm",
        className
      )}
      style={panelStyle}
    >
      {showHeader && (
        <div
          className={cn(
            "flex items-center gap-2 px-3 py-2 bg-space-700 border-b border-space-600 shrink-0",
            isCollapsed && "justify-center px-1",
            headerClassName
          )}
        >
          {!isCollapsed && <GripVertical size={14} className="text-gray-500 shrink-0" />}
          {!isCollapsed && icon && <span className="text-cyber-400 shrink-0">{icon}</span>}
          {!isCollapsed && title && (
            <span className="text-sm font-medium text-gray-200 flex-1 truncate">
              {title}
            </span>
          )}
          {isCollapsed && title && (
            <span className="text-xs font-medium text-gray-400 writing-vertical">
              {typeof title === "string" ? title : ""}
            </span>
          )}
          <div className="flex items-center gap-1 shrink-0">
            {onClose && !isCollapsed && (
              <button
                onClick={onClose}
                className="p-1 rounded text-gray-400 hover:text-white hover:bg-space-600 transition-colors"
                title="关闭"
              >
                <X size={14} />
              </button>
            )}
            <button
              onClick={toggleCollapse}
              className="p-1 rounded text-gray-400 hover:text-cyber-400 hover:bg-space-600 transition-colors"
              title={isCollapsed ? "展开" : "折叠"}
            >
              {collapseIcon}
            </button>
          </div>
        </div>
      )}

      {!isCollapsed && (
        <div
          className={cn(
            "flex-1 overflow-auto",
            contentClassName
          )}
        >
          {children}
        </div>
      )}

      {resizable && !isCollapsed && (
        <div
          className={cn(
            "absolute z-10 group",
            getResizeHandlePosition()
          )}
          onMouseDown={handleResizeStart}
        >
          <div
            className={cn(
              "absolute inset-0 transition-colors",
              isResizing
                ? "bg-cyber-500"
                : "bg-transparent group-hover:bg-cyber-500/50"
            )}
          />
        </div>
      )}
    </div>
  );
};

DockPanel.displayName = "DockPanel";

export { DockPanel };
