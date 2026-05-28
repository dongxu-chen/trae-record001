import chroma from 'chroma-js';
import { ArrowRightLeft, RefreshCw } from 'lucide-react';
import { useColorStore } from '@/hooks/useColorStore';

export default function ColorCompare() {
  const currentColor = useColorStore((s) => s.currentColor);
  const compareColor = useColorStore((s) => s.compareColor);
  const setCurrentColor = useColorStore((s) => s.setCurrentColor);
  const setCompareColor = useColorStore((s) => s.setCompareColor);

  let delta = 0;
  try {
    delta = chroma.deltaE(currentColor, compareColor);
  } catch {
    delta = 0;
  }

  const handleSwap = () => {
    const c = currentColor;
    const n = compareColor;
    setCurrentColor(n);
    setCompareColor(c);
  };

  const handleUseCompare = () => {
    setCurrentColor(compareColor);
  };

  return (
    <div className="w-full max-w-xl rounded-2xl bg-neutral-900 p-6 shadow-xl ring-1 ring-neutral-800">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-neutral-100">Color Compare</h2>
        <button
          type="button"
          onClick={handleSwap}
          className="inline-flex items-center gap-1 rounded-lg bg-neutral-800 px-3 py-1.5 text-xs text-neutral-200 ring-1 ring-neutral-700 transition-colors hover:bg-neutral-700"
        >
          <ArrowRightLeft size={12} />
          Swap
        </button>
      </div>
      <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-3">
        <div className="rounded-xl bg-neutral-800 p-3 ring-1 ring-neutral-700">
          <div
            className="h-28 rounded-lg"
            style={{ backgroundColor: currentColor }}
          />
          <div className="mt-2 text-center font-mono text-xs text-neutral-300">
            {currentColor}
          </div>
          <div className="mt-1 text-center text-[10px] uppercase tracking-wide text-neutral-500">
            Current
          </div>
        </div>
        <div className="flex flex-col items-center gap-2">
          <div className="rounded-full bg-neutral-800 px-3 py-1 text-xs font-medium text-neutral-200 ring-1 ring-neutral-700">
            ΔE {delta.toFixed(2)}
          </div>
          <button
            type="button"
            onClick={handleUseCompare}
            className="inline-flex items-center gap-1 rounded-lg bg-emerald-600 px-2 py-1 text-[11px] text-white transition-colors hover:bg-emerald-500"
            title="Use compare color as current"
          >
            <RefreshCw size={11} />
            Use
          </button>
        </div>
        <div className="rounded-xl bg-neutral-800 p-3 ring-1 ring-neutral-700">
          <button
            type="button"
            onClick={handleUseCompare}
            className="block w-full cursor-pointer text-left"
            title="Click to set as current"
          >
            <div
              className="h-28 rounded-lg transition-transform hover:scale-[1.02]"
              style={{ backgroundColor: compareColor }}
            />
          </button>
          <div className="mt-2 text-center font-mono text-xs text-neutral-300">
            {compareColor}
          </div>
          <div className="mt-1 text-center text-[10px] uppercase tracking-wide text-neutral-500">
            Compare
          </div>
        </div>
      </div>
    </div>
  );
}
