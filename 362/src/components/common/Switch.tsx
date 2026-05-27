import React from 'react';

interface SwitchProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
  className?: string;
}

export const Switch: React.FC<SwitchProps> = ({ checked, onChange, disabled = false, className = '' }) => {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      data-state={checked ? 'checked' : 'unchecked'}
      disabled={disabled}
      onClick={() => !disabled && onChange(!checked)}
      className={`switch ${className} ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
    >
      <span data-state={checked ? 'checked' : 'unchecked'} className="switch-thumb" />
    </button>
  );
};
