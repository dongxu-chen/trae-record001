import { useState } from 'react';
import { HexColorPicker } from 'react-colorful';
import { Palette } from 'lucide-react';
import { useColorStore } from '@/hooks/useColorStore';
import { isValidHex } from '@/utils/colorConverter';

export default function ColorPickerComp() {
  const { currentColor, setCurrentColor } = useColorStore();
  const [hexInput, setHexInput] = useState(currentColor);

  const handlePickerChange = (color: string) => {
    setHexInput(color);
    setCurrentColor(color);
  };

  const handleHexInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value.startsWith('#') ? e.target.value : `#${e.target.value}`;
    setHexInput(value);
    if (isValidHex(value)) {
      setCurrentColor(value);
    }
  };

  return (
    <div className="bg-[#1e1e2e] rounded-xl p-5 shadow-lg">
      <div className="flex items-center gap-2 mb-4">
        <Palette className="w-5 h-5 text-gray-300" />
        <h3 className="text-gray-200 font-medium">调色板</h3>
      </div>
      <div className="flex justify-center mb-4">
        <HexColorPicker color={currentColor} onChange={handlePickerChange} />
      </div>
      <div className="flex items-center gap-2">
        <span className="text-gray-400 text-sm w-12">HEX</span>
        <input
          type="text"
          value={hexInput}
          onChange={handleHexInput}
          className="flex-1 bg-[#2a2a3e] text-gray-200 rounded-lg px-3 py-2 font-mono text-sm outline-none border border-transparent focus:border-[#5b5fc7]"
        />
      </div>
    </div>
  );
}
