import { useState, useMemo } from 'react';
import { Copy, Sun, Moon, Palette } from 'lucide-react';
import { useColorStore } from '@/hooks/useColorStore';
import { getColorName } from '@/utils/colorNames';

export default function ColorPreview() {
  const currentColor = useColorStore((s) => s.currentColor);
  const [darkBg, setDarkBg] = useState<boolean>(true);
  const [copied, setCopied] = useState<boolean>(false);

  const colorName = useMemo(() => getColorName(currentColor), [currentColor]);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(currentColor);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      setCopied(false);
    }
  };

  return (
    <div
      className="w-full rounded-2xl shadow-xl ring-1 transition-colors"
      style={{
        backgroundColor: darkBg ? '#0f0f10' : '#f5f5f7',
        borderColor: darkBg ? '#262626' : '#d4d4d8',
      }}
    >
      <div
        className="h-48 rounded-t-2xl"
        style={{ backgroundColor: currentColor }}
      />
      <div className="p-4">
        <div className="flex items-center gap-2 mb-2">
          <Palette className="w-4 h-4" style={{ color: darkBg ? '#a3a3a3' : '#525252' }} />
          <span className="text-sm font-medium" style={{ color: darkBg ? '#e5e5e5' : '#171717' }}>
            {colorName.name}
          </span>
        </div>
        <div className="flex items-center justify-between">
          <div
            className="font-mono text-sm"
            style={{ color: darkBg ? '#e5e5e5' : '#171717' }}
          >
            {currentColor}
          </div>
          <button
            type="button"
            onClick={handleCopy}
            className="inline-flex items-center gap-1 rounded-lg px-2 py-1 text-xs transition-colors"
            style={{
              backgroundColor: darkBg ? '#262626' : '#e5e5e5',
              color: darkBg ? '#e5e5e5' : '#171717',
            }}
          >
            <Copy size={12} />
            {copied ? 'Copied' : 'Copy'}
          </button>
        </div>
        <div className="mt-3 flex items-center justify-end gap-2">
          <button
            type="button"
            onClick={() => setDarkBg(true)}
            className="inline-flex items-center gap-1 rounded-lg px-2 py-1 text-xs transition-colors"
            style={{
              backgroundColor: darkBg ? '#0a0a0a' : 'transparent',
              color: darkBg ? '#e5e5e5' : '#525252',
              border: `1px solid ${darkBg ? '#525252' : 'transparent'}`,
            }}
            aria-label="Dark background"
          >
            <Moon size={12} />
            Dark
          </button>
          <button
            type="button"
            onClick={() => setDarkBg(false)}
            className="inline-flex items-center gap-1 rounded-lg px-2 py-1 text-xs transition-colors"
            style={{
              backgroundColor: !darkBg ? '#ffffff' : 'transparent',
              color: !darkBg ? '#171717' : '#a3a3a3',
              border: `1px solid ${!darkBg ? '#a3a3a3' : 'transparent'}`,
            }}
            aria-label="Light background"
          >
            <Sun size={12} />
            Light
          </button>
        </div>
      </div>
    </div>
  );
}
