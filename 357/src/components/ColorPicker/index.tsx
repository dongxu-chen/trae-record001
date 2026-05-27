import React, { useState, useRef, useEffect } from 'react';
import { HexColorPicker } from 'react-colorful';
import { Check, X } from 'lucide-react';
import './index.less';

interface ColorPickerProps {
  color: string;
  onChange: (color: string) => void;
  label?: string;
  showAlpha?: boolean;
}

const ColorPicker: React.FC<ColorPickerProps> = ({ color, onChange, label }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [tempColor, setTempColor] = useState(color);
  const pickerRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    setTempColor(color);
  }, [color]);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        pickerRef.current &&
        !pickerRef.current.contains(event.target as Node) &&
        triggerRef.current &&
        !triggerRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen]);

  const handleConfirm = () => {
    onChange(tempColor);
    setIsOpen(false);
  };

  const handleCancel = () => {
    setTempColor(color);
    setIsOpen(false);
  };

  return (
    <div className="color-picker-wrapper">
      {label && <span className="color-picker-label">{label}</span>}
      <button
        ref={triggerRef}
        className="color-picker-trigger"
        onClick={() => setIsOpen(!isOpen)}
        style={{ backgroundColor: color }}
        title={color}
      />
      {isOpen && (
        <div ref={pickerRef} className="color-picker-popup">
          <HexColorPicker color={tempColor} onChange={setTempColor} />
          <div className="color-picker-input-row">
            <input
              type="text"
              className="color-picker-input"
              value={tempColor}
              onChange={(e) => setTempColor(e.target.value)}
            />
          </div>
          <div className="color-picker-actions">
            <button className="color-picker-btn cancel" onClick={handleCancel}>
              <X size={14} />
              取消
            </button>
            <button className="color-picker-btn confirm" onClick={handleConfirm}>
              <Check size={14} />
              确定
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default React.memo(ColorPicker);
