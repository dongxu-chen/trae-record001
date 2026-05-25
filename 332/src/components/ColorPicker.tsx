import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Pipette } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ColorPickerProps {
  label: string;
  value: string;
  onChange: (color: string) => void;
  presetColors?: string[];
}

const defaultPresets = [
  '#1e3a8a', '#06b6d4', '#8b5cf6', '#ec4899',
  '#ef4444', '#f97316', '#eab308', '#22c55e',
  '#0f172a', '#334155', '#64748b', '#ffffff',
];

export default function ColorPicker({
  label,
  value,
  onChange,
  presetColors = defaultPresets,
}: ColorPickerProps) {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div ref={containerRef} className="relative">
      <label className="block text-sm font-medium text-slate-300 mb-2">
        {label}
      </label>
      <motion.button
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          'w-full flex items-center gap-3 px-4 py-3 rounded-xl bg-slate-800/50 border border-slate-700',
          'hover:border-slate-600 transition-colors'
        )}
      >
        <div
          className="w-8 h-8 rounded-lg border-2 border-slate-600 shadow-inner"
          style={{ backgroundColor: value }}
        />
        <span className="font-mono text-sm text-slate-300">{value.toUpperCase()}</span>
        <Pipette size={16} className="ml-auto text-slate-500" />
      </motion.button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="absolute z-50 mt-2 p-4 w-72 rounded-xl bg-slate-800 border border-slate-700 shadow-2xl"
          >
            <input
              type="color"
              value={value}
              onChange={(e) => onChange(e.target.value)}
              className="w-full h-12 rounded-lg cursor-pointer mb-4 bg-transparent"
            />
            <input
              type="text"
              value={value}
              onChange={(e) => onChange(e.target.value)}
              placeholder="#RRGGBB"
              className="w-full px-3 py-2 rounded-lg bg-slate-900/50 border border-slate-700 text-sm font-mono text-slate-200 focus:outline-none focus:border-blue-500 mb-4"
            />
            <div className="grid grid-cols-6 gap-2">
              {presetColors.map((color) => (
                <motion.button
                  key={color}
                  whileHover={{ scale: 1.1 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={() => {
                    onChange(color);
                    setIsOpen(false);
                  }}
                  className={cn(
                    'w-8 h-8 rounded-lg border-2 transition-all',
                    value.toLowerCase() === color.toLowerCase()
                      ? 'border-blue-500 ring-2 ring-blue-500/30'
                      : 'border-slate-600 hover:border-slate-500'
                  )}
                  style={{ backgroundColor: color }}
                />
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
