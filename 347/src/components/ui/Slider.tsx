import * as React from "react";
import { cn } from "@/lib/utils";

export interface SliderProps {
  min?: number;
  max?: number;
  step?: number;
  value?: number | [number, number];
  defaultValue?: number | [number, number];
  onChange?: (value: number | [number, number]) => void;
  color?: string;
  className?: string;
  disabled?: boolean;
}

const Slider = React.forwardRef<HTMLDivElement, SliderProps>(
  (
    {
      min = 0,
      max = 100,
      step = 1,
      value,
      defaultValue = 0,
      onChange,
      color,
      className,
      disabled = false,
    },
    ref
  ) => {
    const isRange = Array.isArray(value ?? defaultValue);
    const [internalValue, setInternalValue] = React.useState<
      number | [number, number]
    >(value ?? defaultValue);
    const trackRef = React.useRef<HTMLDivElement>(null);
    const activeThumbRef = React.useRef<0 | 1 | null>(null);

    const currentValue = value ?? internalValue;

    const getPercentage = (val: number) => {
      return ((val - min) / (max - min)) * 100;
    };

    const getValueFromPosition = (clientX: number) => {
      if (!trackRef.current) return min;
      const rect = trackRef.current.getBoundingClientRect();
      const percentage = (clientX - rect.left) / rect.width;
      const rawValue = min + percentage * (max - min);
      const steppedValue = Math.round(rawValue / step) * step;
      return Math.min(max, Math.max(min, steppedValue));
    };

    const handleThumbMouseDown = (
      e: React.MouseEvent,
      thumbIndex: 0 | 1 = 0
    ) => {
      if (disabled) return;
      e.preventDefault();
      activeThumbRef.current = thumbIndex;

      const handleMouseMove = (moveEvent: MouseEvent) => {
        const newValue = getValueFromPosition(moveEvent.clientX);

        if (isRange) {
          const currentRange = currentValue as [number, number];
          const newRange: [number, number] = [...currentRange];
          newRange[thumbIndex] = newValue;

          if (thumbIndex === 0 && newRange[0] > newRange[1]) {
            newRange[0] = newRange[1];
          } else if (thumbIndex === 1 && newRange[1] < newRange[0]) {
            newRange[1] = newRange[0];
          }

          setInternalValue(newRange);
          onChange?.(newRange);
        } else {
          setInternalValue(newValue);
          onChange?.(newValue);
        }
      };

      const handleMouseUp = () => {
        activeThumbRef.current = null;
        document.removeEventListener("mousemove", handleMouseMove);
        document.removeEventListener("mouseup", handleMouseUp);
      };

      document.addEventListener("mousemove", handleMouseMove);
      document.addEventListener("mouseup", handleMouseUp);
    };

    const handleTrackClick = (e: React.MouseEvent) => {
      if (disabled) return;
      const newValue = getValueFromPosition(e.clientX);

      if (isRange) {
        const currentRange = currentValue as [number, number];
        const distToStart = Math.abs(newValue - currentRange[0]);
        const distToEnd = Math.abs(newValue - currentRange[1]);
        const newRange: [number, number] = [...currentRange];

        if (distToStart <= distToEnd) {
          newRange[0] = Math.min(newValue, newRange[1]);
        } else {
          newRange[1] = Math.max(newValue, newRange[0]);
        }

        setInternalValue(newRange);
        onChange?.(newRange);
      } else {
        setInternalValue(newValue);
        onChange?.(newValue);
      }
    };

    React.useEffect(() => {
      if (value !== undefined) {
        setInternalValue(value);
      }
    }, [value]);

    const fillStart = isRange
      ? getPercentage((currentValue as [number, number])[0])
      : 0;
    const fillEnd = isRange
      ? getPercentage((currentValue as [number, number])[1])
      : getPercentage(currentValue as number);

    const customColorStyle = color
      ? {
          backgroundColor: color,
          boxShadow: `0 0 10px ${color}40`,
        }
      : undefined;

    return (
      <div
        ref={ref}
        className={cn(
          "relative flex items-center w-full h-5",
          disabled && "opacity-50 cursor-not-allowed",
          className
        )}
      >
        <div
          ref={trackRef}
          className="relative w-full h-1.5 bg-space-700 rounded-full cursor-pointer"
          onClick={handleTrackClick}
        >
          <div
            className="absolute h-full bg-cyber-500 rounded-full transition-all duration-75"
            style={{
              left: `${fillStart}%`,
              width: `${fillEnd - fillStart}%`,
              ...(color ? { backgroundColor: color } : {}),
            }}
          />
        </div>

        {isRange ? (
          <>
            <div
              className={cn(
                "absolute w-4 h-4 rounded-full border-2 border-space-900 bg-cyber-500 cursor-grab active:cursor-grabbing transition-transform hover:scale-110",
                !color && "shadow-cyber-glow-sm"
              )}
              style={{
                left: `calc(${fillStart}% - 8px)`,
                ...customColorStyle,
              }}
              onMouseDown={(e) => handleThumbMouseDown(e, 0)}
            />
            <div
              className={cn(
                "absolute w-4 h-4 rounded-full border-2 border-space-900 bg-cyber-500 cursor-grab active:cursor-grabbing transition-transform hover:scale-110",
                !color && "shadow-cyber-glow-sm"
              )}
              style={{
                left: `calc(${fillEnd}% - 8px)`,
                ...customColorStyle,
              }}
              onMouseDown={(e) => handleThumbMouseDown(e, 1)}
            />
          </>
        ) : (
          <div
            className={cn(
              "absolute w-4 h-4 rounded-full border-2 border-space-900 bg-cyber-500 cursor-grab active:cursor-grabbing transition-transform hover:scale-110",
              !color && "shadow-cyber-glow-sm"
            )}
            style={{
              left: `calc(${fillEnd}% - 8px)`,
              ...customColorStyle,
            }}
            onMouseDown={(e) => handleThumbMouseDown(e, 0)}
          />
        )}
      </div>
    );
  }
);

Slider.displayName = "Slider";

export { Slider };
