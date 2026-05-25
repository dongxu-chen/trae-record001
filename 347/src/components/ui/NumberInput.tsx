import * as React from "react";
import { ChevronUp, ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

export type NumberInputAxis = "x" | "y" | "z" | "none";

export interface NumberInputProps {
  value?: number;
  defaultValue?: number;
  onChange?: (value: number) => void;
  min?: number;
  max?: number;
  step?: number;
  precision?: number;
  axis?: NumberInputAxis;
  placeholder?: string;
  disabled?: boolean;
  className?: string;
}

const NumberInput = React.forwardRef<HTMLInputElement, NumberInputProps>(
  (
    {
      value,
      defaultValue = 0,
      onChange,
      min = -Infinity,
      max = Infinity,
      step = 1,
      precision = 2,
      axis = "none",
      placeholder,
      disabled = false,
      className,
    },
    ref
  ) => {
    const [internalValue, setInternalValue] = React.useState<number>(
      value ?? defaultValue
    );
    const [inputValue, setInputValue] = React.useState<string>(
      String(value ?? defaultValue)
    );
    const [isDragging, setIsDragging] = React.useState(false);
    const dragStartRef = React.useRef<{ x: number; value: number } | null>(null);

    const currentValue = value ?? internalValue;

    const axisColors: Record<NumberInputAxis, string> = {
      x: "text-red-500 bg-red-500/10 border-red-500/30",
      y: "text-green-500 bg-green-500/10 border-green-500/30",
      z: "text-blue-500 bg-blue-500/10 border-blue-500/30",
      none: "",
    };

    const axisLabels: Record<NumberInputAxis, string> = {
      x: "X",
      y: "Y",
      z: "Z",
      none: "",
    };

    const clampValue = (val: number) => {
      return Math.min(max, Math.max(min, val));
    };

    const formatValue = (val: number) => {
      return Number(val.toFixed(precision)).toString();
    };

    const updateValue = (newValue: number) => {
      const clamped = clampValue(newValue);
      const formatted = parseFloat(formatValue(clamped));
      setInternalValue(formatted);
      setInputValue(formatValue(formatted));
      onChange?.(formatted);
    };

    const increment = () => {
      if (disabled) return;
      updateValue(currentValue + step);
    };

    const decrement = () => {
      if (disabled) return;
      updateValue(currentValue - step);
    };

    const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
      const val = e.target.value;
      setInputValue(val);

      if (val === "" || val === "-" || val === ".") return;

      const num = parseFloat(val);
      if (!isNaN(num)) {
        const clamped = clampValue(num);
        setInternalValue(clamped);
        onChange?.(clamped);
      }
    };

    const handleInputBlur = () => {
      const num = parseFloat(inputValue);
      if (isNaN(num)) {
        setInputValue(formatValue(currentValue));
      } else {
        updateValue(num);
      }
    };

    const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === "Enter") {
        handleInputBlur();
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        increment();
      } else if (e.key === "ArrowDown") {
        e.preventDefault();
        decrement();
      }
    };

    const handleLabelMouseDown = (e: React.MouseEvent) => {
      if (disabled || axis === "none") return;
      e.preventDefault();
      setIsDragging(true);
      dragStartRef.current = {
        x: e.clientX,
        value: currentValue,
      };

      const handleMouseMove = (moveEvent: MouseEvent) => {
        if (!dragStartRef.current) return;
        const delta = moveEvent.clientX - dragStartRef.current.x;
        const sensitivity = step * 0.5;
        const newValue = dragStartRef.current.value + delta * sensitivity;
        updateValue(newValue);
      };

      const handleMouseUp = () => {
        setIsDragging(false);
        dragStartRef.current = null;
        document.removeEventListener("mousemove", handleMouseMove);
        document.removeEventListener("mouseup", handleMouseUp);
      };

      document.addEventListener("mousemove", handleMouseMove);
      document.addEventListener("mouseup", handleMouseUp);
    };

    React.useEffect(() => {
      if (value !== undefined) {
        setInternalValue(value);
        setInputValue(formatValue(value));
      }
    }, [value]);

    return (
      <div
        className={cn(
          "flex items-center h-9 bg-space-800 rounded-md border border-space-600 overflow-hidden transition-colors focus-within:border-cyber-500/60 focus-within:shadow-cyber-glow-sm",
          disabled && "opacity-50 cursor-not-allowed",
          className
        )}
      >
        {axis !== "none" && (
          <div
            className={cn(
              "w-9 h-full flex items-center justify-center font-bold text-sm border-r select-none",
              axisColors[axis],
              !disabled && "cursor-ew-resize",
              isDragging && "ring-2 ring-cyber-500/50"
            )}
            onMouseDown={handleLabelMouseDown}
            title="拖拽调整数值"
          >
            {axisLabels[axis]}
          </div>
        )}
        <input
          ref={ref}
          type="text"
          inputMode="decimal"
          value={inputValue}
          onChange={handleInputChange}
          onBlur={handleInputBlur}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={disabled}
          className="flex-1 bg-transparent text-white text-sm px-3 py-1.5 outline-none font-mono tabular-nums"
        />
        <div className="flex flex-col border-l border-space-600">
          <button
            type="button"
            onClick={increment}
            disabled={disabled || currentValue >= max}
            className="flex-1 px-1.5 text-cyber-400 hover:bg-space-700 hover:text-cyber-300 active:bg-space-600 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            <ChevronUp size={12} strokeWidth={2.5} />
          </button>
          <div className="h-px bg-space-600" />
          <button
            type="button"
            onClick={decrement}
            disabled={disabled || currentValue <= min}
            className="flex-1 px-1.5 text-cyber-400 hover:bg-space-700 hover:text-cyber-300 active:bg-space-600 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            <ChevronDown size={12} strokeWidth={2.5} />
          </button>
        </div>
      </div>
    );
  }
);

NumberInput.displayName = "NumberInput";

export { NumberInput };
