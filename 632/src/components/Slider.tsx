import { useState } from 'react';
import { motion } from 'framer-motion';

interface SliderProps {
  label: string;
  value: number;
  min: number;
  max: number;
  step?: number;
  onChange: (value: number) => void;
  unit?: string;
  showInput?: boolean;
  hint?: string;
  labelLeft?: string;
  labelRight?: string;
}

export function Slider({
  label,
  value,
  min,
  max,
  step = 1,
  onChange,
  unit = '',
  showInput = true,
  hint,
  labelLeft,
  labelRight
}: SliderProps) {
  const [isHovered, setIsHovered] = useState(false);
  const percentage = ((value - min) / (max - min)) * 100;

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = parseFloat(e.target.value);
    if (!isNaN(newValue)) {
      onChange(Math.max(min, Math.min(max, newValue)));
    }
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <label className="text-sm font-medium text-deep-space-200">
          {label}
          {hint && (
            <span className="ml-1 text-xs text-deep-space-500">
              ({hint})
            </span>
          )}
        </label>
        {showInput && (
          <motion.div
            className="flex items-center gap-1 bg-deep-space-800 px-2 py-1 rounded-md border border-deep-space-700"
            animate={{ borderColor: isHovered ? '#38bdf8' : '#334155' }}
          >
            <input
              type="number"
              value={value}
              min={min}
              max={max}
              step={step}
              onChange={handleInputChange}
              className="w-14 bg-transparent text-right text-sm font-mono text-neon-blue-400 outline-none"
            />
            <span className="text-xs text-deep-space-500">{unit}</span>
          </motion.div>
        )}
      </div>
      
      <div className="relative">
        <div className="h-2 bg-deep-space-700 rounded-full overflow-hidden">
          <motion.div
            className="h-full rounded-full"
            style={{ 
              width: `${percentage}%`,
              background: labelLeft && labelRight 
                ? 'linear-gradient(to right, #38bdf8, #a855f7, #f97316)'
                : 'linear-gradient(to right, #0ea5e9, #38bdf8)'
            }}
          />
        </div>
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={value}
          onChange={(e) => onChange(parseFloat(e.target.value))}
          onMouseEnter={() => setIsHovered(true)}
          onMouseLeave={() => setIsHovered(false)}
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
        />
        <motion.div
          className="absolute top-1/2 -translate-y-1/2 w-4 h-4 rounded-full pointer-events-none"
          style={{ 
            left: `calc(${percentage}% - 8px)`,
            background: labelLeft && labelRight && percentage > 50 
              ? '#f97316' 
              : labelLeft && labelRight && percentage < 50
              ? '#38bdf8'
              : '#38bdf8'
          }}
          animate={{
            boxShadow: isHovered 
              ? '0 0 20px rgba(56, 189, 248, 0.8), 0 0 40px rgba(56, 189, 248, 0.4)'
              : '0 0 10px rgba(56, 189, 248, 0.5)'
          }}
        />
      </div>
      
      <div className="flex justify-between text-[10px] text-deep-space-500 font-mono">
        <span>{labelLeft || `${min}${unit}`}</span>
        <span>{labelRight || `${max}${unit}`}</span>
      </div>
    </div>
  );
}
