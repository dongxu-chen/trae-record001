import { WcagBadge } from '@/components/WcagBadge';

interface ContrastPanelProps {
  foreground: { r: number; g: number; b: number };
  background: { r: number; g: number; b: number };
  ratio: number;
}

export default function ContrastPanel({ foreground, background, ratio }: ContrastPanelProps) {
  const fgHex = `#${foreground.r.toString(16).padStart(2, '0')}${foreground.g.toString(16).padStart(2, '0')}${foreground.b.toString(16).padStart(2, '0')}`;
  const bgHex = `#${background.r.toString(16).padStart(2, '0')}${background.g.toString(16).padStart(2, '0')}${background.b.toString(16).padStart(2, '0')}`;

  const aaNormal = ratio >= 4.5;
  const aaLarge = ratio >= 3;
  const aaaNormal = ratio >= 7;
  const aaaLarge = ratio >= 4.5;

  return (
    <div className="bg-zinc-900 rounded-xl border border-zinc-800 p-4 space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-zinc-300">对比度检测</span>
        <span
          className={`text-2xl font-mono font-bold ${
            ratio >= 4.5 ? 'text-[#00d4aa]' : ratio >= 3 ? 'text-yellow-500' : 'text-[#ff6b35]'
          }`}
        >
          {ratio.toFixed(2)}:1
        </span>
      </div>

      <div className="flex items-center gap-3">
        <div className="flex-1 flex items-center gap-2">
          <div
            className="w-8 h-8 rounded-lg border border-zinc-700 shrink-0"
            style={{ backgroundColor: fgHex }}
          />
          <div className="text-xs font-mono text-zinc-400">
            <p>前景</p>
            <p>{fgHex.toUpperCase()}</p>
          </div>
        </div>
        <div className="text-zinc-600">→</div>
        <div className="flex-1 flex items-center gap-2">
          <div
            className="w-8 h-8 rounded-lg border border-zinc-700 shrink-0"
            style={{ backgroundColor: bgHex }}
          />
          <div className="text-xs font-mono text-zinc-400">
            <p>背景</p>
            <p>{bgHex.toUpperCase()}</p>
          </div>
        </div>
      </div>

      <div className="rounded-lg bg-zinc-800/50 p-3" style={{ color: fgHex, backgroundColor: bgHex }}>
        <p className="text-sm font-medium">示例文字 Sample Text Aa</p>
        <p className="text-xs mt-1">小号文字示例 small text sample</p>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <WcagBadge level="AA" size="normal" pass={aaNormal} />
        <WcagBadge level="AA" size="large" pass={aaLarge} />
        <WcagBadge level="AAA" size="normal" pass={aaaNormal} />
        <WcagBadge level="AAA" size="large" pass={aaaLarge} />
      </div>
    </div>
  );
}
