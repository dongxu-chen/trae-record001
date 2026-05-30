import { Pipette } from 'lucide-react';
import { useAppStore } from '@/store/useAppStore';
import { rgbToHex, rgbToHsl } from '@/utils/color';

export default function ColorPicker() {
  const { pickedColor, simulatedPickedColor, selectedType } = useAppStore();

  if (!pickedColor) return null;

  const hex = rgbToHex(pickedColor);
  const hsl = rgbToHsl(pickedColor);
  const simHex = simulatedPickedColor ? rgbToHex(simulatedPickedColor) : null;
  const simHsl = simulatedPickedColor ? rgbToHsl(simulatedPickedColor) : null;

  return (
    <div className="bg-zinc-900 rounded-xl border border-zinc-800 p-4">
      <div className="flex items-center gap-2 mb-3">
        <Pipette className="w-4 h-4 text-[#00d4aa]" />
        <span className="text-sm font-medium text-zinc-300">颜色拾取</span>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-2">
          <p className="text-xs text-zinc-500">原始颜色</p>
          <div className="flex items-center gap-2">
            <div
              className="w-10 h-10 rounded-lg border border-zinc-700 shrink-0"
              style={{ backgroundColor: hex }}
            />
            <div className="font-mono text-xs space-y-0.5">
              <p className="text-zinc-300">{hex.toUpperCase()}</p>
              <p className="text-zinc-500">
                RGB({pickedColor.r}, {pickedColor.g}, {pickedColor.b})
              </p>
              <p className="text-zinc-500">
                HSL({hsl.h}, {hsl.s}%, {hsl.l}%)
              </p>
            </div>
          </div>
        </div>

        {simulatedPickedColor && simHex && simHsl && (
          <div className="space-y-2">
            <p className="text-xs text-[#ff6b35]">色盲模拟</p>
            <div className="flex items-center gap-2">
              <div
                className="w-10 h-10 rounded-lg border border-zinc-700 shrink-0"
                style={{ backgroundColor: simHex }}
              />
              <div className="font-mono text-xs space-y-0.5">
                <p className="text-zinc-300">{simHex.toUpperCase()}</p>
                <p className="text-zinc-500">
                  RGB({simulatedPickedColor.r}, {simulatedPickedColor.g},{' '}
                  {simulatedPickedColor.b})
                </p>
                <p className="text-zinc-500">
                  HSL({simHsl.h}, {simHsl.s}%, {simHsl.l}%)
                </p>
              </div>
            </div>
          </div>
        )}
      </div>

      {simulatedPickedColor && (
        <div className="mt-3 flex items-center gap-2">
          <div
            className="w-full h-6 rounded border border-zinc-700"
            style={{
              background: `linear-gradient(to right, ${hex}, ${simHex})`,
            }}
          />
          <span className="text-xs text-zinc-500 shrink-0 font-mono">
            {selectedType}
          </span>
        </div>
      )}
    </div>
  );
}
